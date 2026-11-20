# -*- coding: utf-8 -*-
"""bianca/triagem/runner.py -- Executor autonomo do fluxo de Triagem Inicial."""

import traceback
from typing import Any, Dict, Optional


from bianca.config import URL_LISTA_TRIAGEM, URL_PJE_BASE
from Fix.extracao import criar_comentario, criar_gigs
from bianca.selenium_utils import aguardar_renderizacao_nativa, esperar_elemento
from bianca.triagem.acoes import _aplicar_acao_pos_triagem
from bianca.triagem.api import (
    _is_triagem_inicial,
    buscar_lista_triagem,
    enriquecer_processo,
)
from Fix.monitoramento_progresso_unificado import (
    carregar_progresso_unificado,
    marcar_processo_executado_unificado,
    processo_ja_executado_unificado,
)
from bianca.triagem.service import triagem_peticao
from utilitarios_processamento import resultado_falha, resultado_ok, run_batch


def _fechar_tabs_acesso_negado(drv, handle_principal: str, numero: str = "?") -> int:
    """Fecha todas as abas com URL acesso-negado, exceto a principal."""
    fechadas = 0
    for h in list(getattr(drv, 'window_handles', [])):
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
    try:
        drv.switch_to.window(handle_principal)
    except Exception:
        pass
    return fechadas

_TIPO_EXECUCAO = 'triagem'


def run_triagem(driver: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Fluxo principal de triagem inicial."""
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

        itens_brutos = buscar_lista_triagem(drv)
        if not itens_brutos:
            print("[TRIAGEM] API nao retornou itens")
            return {"sucesso": False, "erro": "Lista vazia"}

        triagem_itens = [i for i in itens_brutos if _is_triagem_inicial(i)]
        if not triagem_itens:
            print("[TRIAGEM] Campo tarefa nao identificou Triagem Inicial -- usando todos")
            triagem_itens = itens_brutos

        try:
            from Fix.variaveis import PjeApiClient, session_from_driver
            sess, host = session_from_driver(drv)
            _client = PjeApiClient(sess, host)
        except Exception as e:
            print("[TRIAGEM] Sem cliente de API (%s) -- usando juizoDigital da lista" % e)
            _client = None

        lista = [p for p in (enriquecer_processo(i, _client) for i in triagem_itens) if p]
        if not lista:
            print("[TRIAGEM] Nenhum processo enriquecido")
            return {"sucesso": False, "erro": "Nenhum processo enriquecido"}

        print("[TRIAGEM] %s processos de Triagem Inicial (de %s brutos)" % (len(lista), len(itens_brutos)))

        progresso = carregar_progresso_unificado(_TIPO_EXECUCAO)
        pendentes = len(lista)
        if progresso:
            ja_executados = sum(
                1 for p in lista
                if processo_ja_executado_unificado(p.get("numero", ""), progresso)
            )
            pendentes = len(lista) - ja_executados
            print("[TRIAGEM] %s ja executados, %s pendentes" % (ja_executados, pendentes))

        if pendentes == 0 and progresso:
            print("[TRIAGEM] Todos os processos ja foram executados")
            return {"sucesso": True, "processados": 0, "total": len(lista)}

        def should_skip(proc):
            numero = proc.get("numero", "")
            if not numero:
                return False
            return processo_ja_executado_unificado(numero, progresso)

        def open_item(proc):
            numero = proc.get("numero", "?")
            id_processo = proc.get("id_processo")
            if not id_processo:
                return resultado_falha("Sem id_processo")
            try:
                for h in list(getattr(drv, 'window_handles', [])):
                    if h != handle_principal:
                        try:
                            drv.switch_to.window(h)
                            drv.close()
                        except Exception:
                            pass
                drv.switch_to.window(handle_principal)

                url = "%s/processo/%s/detalhe" % (URL_PJE_BASE, id_processo)
                drv.get(url)
                esperar_elemento(drv, "pje-cabecalho-processo,pje-timeline", timeout=15)
                aguardar_renderizacao_nativa(drv, timeout=5)
                return resultado_ok()
            except Exception as e:
                return resultado_falha(str(e))

        def execute_item(proc):
            numero = proc.get("numero", "?")
            try:
                print("[TRIAGEM][%s] Processando..." % numero)

                if proc.get("bucket") == "CP":
                    print("[TRIAGEM][%s] Carta Precatória — apenas comentário" % numero)
                    try:
                        criar_comentario(drv, "Bianca - CP despachar")
                    except Exception as e:
                        print(f"[TRIAGEM][{numero}] Falha ao registrar comentario CP: {e}")
                    return resultado_ok()

                triagem_txt = triagem_peticao(drv)
                proc["triagem"] = triagem_txt
                if triagem_txt:
                    print("[TRIAGEM][%s] Saida triagem_peticao:\n%s" % (numero, triagem_txt))

                if isinstance(triagem_txt, str) and triagem_txt.startswith("ERRO: ERRO_CRITICO_401"):
                    print("[TRIAGEM][%s] ERRO 401 -- sessao rejeitada" % numero)
                    return resultado_falha("ERRO_CRITICO_401", critical=True)

                if triagem_txt:
                    try:
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
                            from bianca.triagem.acoes import _tem_audiencia_marcada, _usa_padrao_novo

                            tem_aud = _tem_audiencia_marcada(drv, proc)
                            tem_100 = bool(proc.get('digital', proc.get('tem_100', False)))

                            if tem_aud:
                                proc["bucket"] = "B" if tem_100 else "C"
                                if tem_100:
                                    status_str = "100% digital - despachado?"
                                elif _usa_padrao_novo(proc, numero):
                                    status_str = "Direto (seg/ter/sex) - despachado (ato_vpp)?"
                                else:
                                    status_str = "Direto - aud marcada / citado?"
                            else:
                                proc["bucket"] = "A"
                                if proc.get('pular_marcar_aud'):
                                    status_str = "100% digital - sem aud (pula marcacao)?" if tem_100 else "Sem aud (pula marcacao)?"
                                else:
                                    status_str = "100% digital - marcado e despachado?" if tem_100 else "Sem aud - marcado e despachado?"

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

                aguardar_renderizacao_nativa(
                    drv, 'pje-gigs-lista-atividades', 'aparecer', 8)

                ok, status_line = _aplicar_acao_pos_triagem(drv, numero, proc, triagem_txt)
                print("[TRIAGEM][%s] Resultado acao_pos_triagem: ok=%s status=%r" % (numero, ok, status_line))

                _fechar_tabs_acesso_negado(drv, handle_principal, numero)

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
            ok = bool(result.get("ok"))
            erro = result.get("erro") if not ok else None
            marcar_processo_executado_unificado(
                _TIPO_EXECUCAO, numero, progresso, sucesso=ok, motivo=erro
            )

        batch_result = run_batch(
            items=lista,
            should_skip=should_skip,
            open_item=open_item,
            execute_item=execute_item,
            persist_result=persist_result,
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
