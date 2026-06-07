# -*- coding: utf-8 -*-
"""
bianca/triagem/runner.py -- Executor autonomo do fluxo de Triagem Inicial.

Melhorias em relacao a triagem_engine.py original:
  1. Progress tracking (evita reprocessamento)
  2. should_skip usa ``ProgressoTriagem.processo_ja_executado()``
  3. persist_result salva progresso via ``marcar_processo_executado()``
  4. Limpeza de abas extras apos cada processo
  5. Logging estruturado com numero do processo e indice

Uso:
    from bianca.triagem.runner import run_triagem
    resultado = run_triagem(driver)
"""

import traceback
from typing import Any, Dict, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from bianca.config import URL_LISTA_TRIAGEM, URL_PJE_BASE
from bianca.extracao import criar_comentario, criar_gigs
from bianca.selenium_utils import aguardar_renderizacao_nativa, esperar_elemento
from bianca.triagem.acoes import _aplicar_acao_pos_triagem
from bianca.triagem.api import (
    _is_triagem_inicial,
    buscar_lista_triagem,
    enriquecer_processo,
)
from bianca.triagem.progress import ProgressoTriagem
from bianca.triagem.service import triagem_peticao
from bianca.utils import resultado_falha, resultado_ok, run_batch


def _fechar_tabs_acesso_negado(drv, handle_principal: str, numero: str = "?") -> int:
    """Fecha todas as abas com URL acesso-negado, exceto a principal.

    Retorna o numero de abas fechadas.
    """
    fechadas = 0
    for h in list(drv.window_handles):
        if h == handle_principal:
            continue
        try:
            drv.switch_to.window(h)
            if "acesso-negado" in (drv.current_url or "").lower():
                print("[TRIAGEM][%s] Fechando aba acesso-negado: %s" % (numero, drv.current_url))
                drv.close()
                fechadas += 1
        except Exception:
            pass
    # Garantir foco no handle principal
    try:
        drv.switch_to.window(handle_principal)
    except Exception:
        pass
    return fechadas

_progresso = ProgressoTriagem()


def run_triagem(driver: Optional[WebDriver] = None) -> Optional[Dict[str, Any]]:
    """Fluxo principal de triagem inicial.

    Etapas:
      1. Navega para URL_LISTA_TRIAGEM
      2. Busca lista de processos via API
      3. Filtra apenas itens da fila "Triagem Inicial"
      4. Enriquece cada item com metadados (bucket, tipo, etc.)
      5. Carrega progresso e filtra ja executados
      6. Para cada processo pendente: analisa peticao, cria comentario,
         executa acao pos-triagem e salva progresso

    Args:
        driver: WebDriver Selenium opcional. Se None, cria um novo.

    Returns:
        Dict com {
            'sucesso': bool,
            'processados': int,
            'sucesso_count': int,
            'total': int,
        } ou None em caso de erro fatal.
    """
    print("[TRIAGEM] Iniciando run_triagem...")

    if driver:
        drv = driver
    else:
        from bianca.driver import criar_driver_e_fazer_login
        drv = criar_driver_e_fazer_login()
        if not drv:
            print("[TRIAGEM] Falha ao criar driver e fazer login")
            return None

    try:
        handle_principal = drv.current_window_handle
        print("[TRIAGEM] Navegando para %s" % URL_LISTA_TRIAGEM)
        drv.get(URL_LISTA_TRIAGEM)
        esperar_elemento(drv, 'tr.cdk-drag,.cdk-virtual-scroll-viewport', timeout=15)

        # Buscar lista
        itens_brutos = buscar_lista_triagem(drv)
        if not itens_brutos:
            print("[TRIAGEM] API nao retornou itens")
            return {"sucesso": False, "erro": "Lista vazia"}

        # Filtrar apenas Triagem Inicial
        triagem_itens = [i for i in itens_brutos if _is_triagem_inicial(i)]
        if not triagem_itens:
            print("[TRIAGEM] Campo tarefa nao identificou Triagem Inicial -- usando todos")
            triagem_itens = itens_brutos

        # Enriquecer
        lista = [p for p in (enriquecer_processo(i) for i in triagem_itens) if p]
        if not lista:
            print("[TRIAGEM] Nenhum processo enriquecido")
            return {"sucesso": False, "erro": "Nenhum processo enriquecido"}

        print("[TRIAGEM] %s processos de Triagem Inicial (de %s brutos)" % (len(lista), len(itens_brutos)))

        # --- Progress tracking ---
        progresso = _progresso.carregar_progresso()
        pendentes = len(lista)
        if progresso:
            ja_executados = sum(
                1 for p in lista
                if _progresso.processo_ja_executado(p.get("numero", ""), progresso)
            )
            pendentes = len(lista) - ja_executados
            print("[TRIAGEM] %s ja executados, %s pendentes" % (ja_executados, pendentes))

        if pendentes == 0 and progresso:
            print("[TRIAGEM] Todos os processos ja foram executados")
            return {"sucesso": True, "processados": 0, "total": len(lista)}

        # --- Pipeline batch ---
        def should_skip(proc):
            numero = proc.get("numero", "")
            if not numero:
                return False
            return _progresso.processo_ja_executado(numero, progresso)

        def open_item(proc):
            numero = proc.get("numero", "?")
            id_processo = proc.get("id_processo")
            if not id_processo:
                return resultado_falha("Sem id_processo")
            try:
                # Limpeza de abas extras
                for h in list(drv.window_handles):
                    if h != handle_principal:
                        try:
                            drv.switch_to.window(h)
                            drv.close()
                        except Exception:
                            pass
                drv.switch_to.window(handle_principal)

                url = "%s/processo/%s/detalhe" % (URL_PJE_BASE, id_processo)
                drv.get(url)
                esperar_elemento(drv, "pje-cabecalho-processo,pje-timeline",
                                 by=By.CSS_SELECTOR, timeout=15)
                aguardar_renderizacao_nativa(drv, timeout=5)
                return resultado_ok()
            except Exception as e:
                return resultado_falha(str(e))

        def execute_item(proc, open_result):
            numero = proc.get("numero", "?")
            try:
                print("[TRIAGEM][%s] Processando..." % numero)

                triagem_txt = triagem_peticao(drv)
                proc["triagem"] = triagem_txt
                if triagem_txt:
                    print("[TRIAGEM][%s] Saida triagem_peticao:\n%s" % (numero, triagem_txt))

                if isinstance(triagem_txt, str) and triagem_txt.startswith("ERRO: ERRO_CRITICO_401"):
                    print("[TRIAGEM][%s] ERRO 401 -- sessao rejeitada" % numero)
                    return resultado_falha("ERRO_CRITICO_401", critical=True)

                # Comentario com resultado da triagem (antes da decisao de acao)
                if triagem_txt:
                    try:
                        # Determinar estado de fluxo (nao e pos-acao)
                        from bianca.triagem.acoes import _determinar_acao_pos_triagem, _RE_BUCKET_B2, _RE_BUCKET_C, _RE_BUCKET_D
                        bucket, _ = _determinar_acao_pos_triagem(triagem_txt)
                        if bucket == 'pre_bucket':
                            if _RE_BUCKET_B2.search(triagem_txt): bucket = 'b2_incompetencia'
                            elif _RE_BUCKET_C.search(triagem_txt): bucket = 'c_pedidos'
                            elif _RE_BUCKET_D.search(triagem_txt): bucket = 'd_docs'
                            else: bucket = 'b1_normal'
                        
                        status_str = ""
                        if bucket == 'b2_incompetencia': status_str = "Incompetencia territorial"
                        elif bucket == 'c_pedidos': status_str = "Pedidos nao liquidados"
                        elif bucket == 'd_docs': status_str = "Falta de documentos"
                        else:
                            bp = proc.get("bucket", "C")
                            if bp == "A": status_str = "Sem aud - marcado e despachado?"
                            elif bp == "B": status_str = "100% digital - despachado?"
                            elif bp == "C": status_str = "Direto - citado?"
                            elif bp == "D": status_str = "HTE"

                        observacao = "BIANCA - TRIAGEM\n"
                        if status_str:
                            observacao += f"ESTADO DE FLUXO: {status_str}\n\n"
                        else:
                            observacao += "\n"
                        observacao += str(triagem_txt)

                        sucesso_cmt = criar_comentario(drv, observacao)
                        if not sucesso_cmt:
                            print(f"[TRIAGEM][{numero}] Comentario pode nao ter sido salvo")
                    except Exception as e:
                        print(f"[TRIAGEM][{numero}] Falha ao registrar comentario: {e}")

                # Barreira: aguardar tabela GIGS pronta
                aguardar_renderizacao_nativa(
                    drv, 'pje-gigs-lista-atividades button', 'aparecer', 8)

                # Acao pos-triagem
                ok, status_line = _aplicar_acao_pos_triagem(drv, numero, proc, triagem_txt)
                print("[TRIAGEM][%s] Resultado acao_pos_triagem: ok=%s status=%r" % (numero, ok, status_line))

                # Detectar acesso-negado em qualquer aba aberta pela acao
                _fechar_tabs_acesso_negado(drv, handle_principal, numero)

                # Verificar se o handle principal acabou em acesso-negado
                try:
                    drv.switch_to.window(handle_principal)
                    if "acesso-negado" in (drv.current_url or "").lower():
                        print("[TRIAGEM][%s] acesso-negado na aba principal — parada critica" % numero)
                        return resultado_falha("ACESSO_NEGADO", critical=True)
                except Exception:
                    pass

                return resultado_ok() if ok else resultado_falha("Acao pos-triagem falhou")

            except Exception as e:
                print("[TRIAGEM][%s] Erro: %s" % (numero, e))
                return resultado_falha(str(e))

        def persist_result(proc, result):
            numero = proc.get("numero", "?")
            status = "SUCESSO" if result.get("ok") else "FALHA"
            erro = result.get("erro") if not result.get("ok") else None
            _progresso.marcar_processo_executado(numero, status, erro, progresso)

        batch_result = run_batch(
            items=lista,
            should_skip=should_skip,
            open_item=open_item,
            execute_item=execute_item,
            persist_result=persist_result,
            label="TRIAGEM",
            stop_on_critical=True,
        )

        ok_count = batch_result['sucesso']
        falha_count = batch_result['falha']
        total_count = ok_count + falha_count
        print("[TRIAGEM] Concluido: %s processados (%s sucesso, %s falha)" % (total_count, ok_count, falha_count))

        return {
            "sucesso": ok_count > 0 or len(lista) == 0,
            "processados": total_count,
            "sucesso_count": ok_count,
            "total": len(lista),
            "critical_stop": batch_result.get("critical_stop", False),
            "critical_reason": batch_result.get("critical_reason"),
        }

    except Exception as e:
        print("[TRIAGEM] Erro fatal: %s" % e)
        traceback.print_exc()
        return None
    finally:
        if not driver and drv:
            try:
                drv.quit()
            except Exception:
                pass
