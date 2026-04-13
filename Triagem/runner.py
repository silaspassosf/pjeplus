"""Triagem/runner.py
Executor autônomo do fluxo de Triagem Inicial.

Reproduz a estrutura de execução de aud.py:
  1. Busca lista de processos Triagem Inicial via API
  2. Para cada processo: abre detalhe, executa triagem_peticao, cria comentário
  3. Aplica ação pós-triagem baseada em alertas (não em buckets fixos):
     - b1  sem alertas críticos → execução normal com buckets (A/B/C/D)
     - b2  alerta de incompetência territorial → sem ação
     - c   alerta de pedidos não liquidados → placeholder despacho liquidar
     - d   alerta de falta de documentos pessoais → placeholder apresentar doc

Uso:
  from Triagem.runner import run_triagem   # como módulo
  py -m Triagem.runner                     # execução direta
  py Triagem/runner.py                     # execução direta
"""
import traceback
import time
from typing import Optional, Dict, Any, List

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from Fix.gigs import criar_comentario
from Fix.core import esperar_elemento
from Fix.progresso_unificado import ProgressoUnificado
from Triagem.acoes import acao_bucket_a, acao_bucket_b, acao_bucket_c, acao_bucket_d
from Triagem.service import triagem_peticao

_progresso = ProgressoUnificado("TRIAGEM")

URL_LISTA_TRIAGEM = "https://pje.trt2.jus.br/pjekz/painel/global/10/lista-processos"


# ============================================================================
# CRIAÇÃO DE DRIVER / LOGIN
# ============================================================================

def _criar_driver_e_logar(driver: Optional[WebDriver]) -> Optional[WebDriver]:
    from Triagem.driver import criar_driver_e_logar
    return criar_driver_e_logar(driver)


# ============================================================================
# ANÁLISE DE ALERTAS DA TRIAGEM
# ============================================================================

def _tem_alerta_incompetencia(triagem_txt: str) -> bool:
    """Incompetência aparece na seção [COMPETENCIA] como 'Zona Sul nao detectado'
    seguida de foro (RUI BARBOSA ou ZONA LESTE)."""
    if not isinstance(triagem_txt, str):
        return False
    t = triagem_txt.lower()
    return (
        "zona sul nao detectado" in t
        or "incompetencia territorial" in t
        or "fora dos intervalos" in t
    )


def _tem_alerta_pedidos_nao_liquidados(triagem_txt: str) -> bool:
    """Verifica alerta de pedidos não liquidados na seção [Alertas]."""
    if not isinstance(triagem_txt, str):
        return False
    in_alertas = False
    for linha in triagem_txt.splitlines():
        s = linha.strip()
        if s == "[Alertas]":
            in_alertas = True
            continue
        if s.startswith("[") and s.endswith("]") and s != "[Alertas]":
            in_alertas = False
        if in_alertas and "pedidos liquidados" in s.lower():
            return True
    return False


def _tem_alerta_docs_pessoais(triagem_txt: str) -> bool:
    """Verifica alerta de documentos essenciais faltando na seção [Alertas]."""
    if not isinstance(triagem_txt, str):
        return False
    in_alertas = False
    for linha in triagem_txt.splitlines():
        s = linha.strip()
        if s == "[Alertas]":
            in_alertas = True
            continue
        if s.startswith("[") and s.endswith("]") and s != "[Alertas]":
            in_alertas = False
        if in_alertas and "documentos essenciais" in s.lower():
            return True
    return False


# ============================================================================
# AÇÕES PÓS-TRIAGEM
# ============================================================================

def _acao_b1_normal(driver: WebDriver, numero: str, processo_info: Dict) -> bool:
    """b1 — sem alertas críticos: execução normal via buckets locais."""
    bucket = processo_info.get("bucket", "C")
    print(f"[TRIAGEM][{numero}] b1 — sem alertas → bucket {bucket} (execução normal)")

    if bucket == "A":
        return acao_bucket_a(driver, numero, processo_info)

    if bucket == "B":
        return acao_bucket_b(driver, numero, processo_info)

    if bucket == "C":
        return acao_bucket_c(driver, numero, processo_info)

    if bucket == "D":
        return acao_bucket_d(driver, numero, processo_info)

    print(f"[TRIAGEM][{numero}] bucket desconhecido '{bucket}' — sem ação")
    return False


def _acao_b2_incompetencia(driver: WebDriver, numero: str, processo_info: Dict) -> bool:
    """b2 — incompetência territorial: sem nenhuma ação."""
    print(f"[TRIAGEM][{numero}] b2 — incompetência territorial → processo não processado")
    return True


def _acao_c_pedidos(driver: WebDriver, numero: str, processo_info: Dict) -> bool:
    """c — pedidos não liquidados: placeholder de despacho para liquidar."""
    print(f"[TRIAGEM][{numero}] c — pedidos não liquidados → placeholder despacho liquidar (TODO)")
    # TODO: implementar ato de despacho orientando liquidação dos pedidos
    return True


def _acao_d_docs(driver: WebDriver, numero: str, processo_info: Dict) -> bool:
    """d — falta de documentos pessoais: placeholder de apresentação de documento."""
    print(f"[TRIAGEM][{numero}] d — falta de documentos pessoais → placeholder apresentar doc (TODO)")
    # TODO: implementar ato de despacho para apresentação de documentos pessoais
    return True


def _aplicar_acao_pos_triagem(driver: WebDriver, numero: str,
                               processo_info: Dict, triagem_txt: str) -> bool:
    """Decide e executa ação pós-triagem com base nos alertas."""
    if not triagem_txt or (isinstance(triagem_txt, str) and triagem_txt.startswith("ERRO")):
        print(f"[TRIAGEM][{numero}] triagem com erro — sem ação")
        return False

    # b2: incompetência territorial → nada
    if _tem_alerta_incompetencia(triagem_txt):
        return _acao_b2_incompetencia(driver, numero, processo_info)

    # c: pedidos não liquidados → placeholder despacho
    if _tem_alerta_pedidos_nao_liquidados(triagem_txt):
        return _acao_c_pedidos(driver, numero, processo_info)

    # d: falta de documentos pessoais → placeholder apresentar doc
    if _tem_alerta_docs_pessoais(triagem_txt):
        return _acao_d_docs(driver, numero, processo_info)

    # b1: sem alertas críticos → execução normal de buckets
    return _acao_b1_normal(driver, numero, processo_info)


# ============================================================================
# PROCESSAMENTO DE PROCESSO INDIVIDUAL
# ============================================================================

def _processar_processo(driver: WebDriver, processo_info: Dict,
                        progresso: Dict) -> bool:
    numero = processo_info.get("numero", "?")
    id_processo = processo_info.get("id_processo")

    # Navegar para o detalhe
    try:
        url = f"https://pje.trt2.jus.br/pjekz/processo/{id_processo}/detalhe/"
        driver.get(url)
        esperar_elemento(driver, "pje-cabecalho-processo,pje-timeline",
                         by=By.CSS_SELECTOR, timeout=15)
    except Exception as e:
        print(f"[TRIAGEM][{numero}] ❌ Falha ao navegar: {e}")
        return False

    # Executar triagem
    triagem_txt = None
    try:
        print(f"[TRIAGEM][{numero}] Executando triagem_peticao...")
        triagem_txt = triagem_peticao(driver)
        processo_info["triagem"] = triagem_txt
    except Exception as e:
        triagem_txt = f"ERRO: {e}"
        processo_info["triagem"] = triagem_txt
        print(f"[TRIAGEM][{numero}] ⚠ Falha na triagem: {e}")

    # Filtro crítico 401 — não registrar progresso
    if isinstance(triagem_txt, str) and triagem_txt.startswith("ERRO: ERRO_CRITICO_401"):
        print(f"[TRIAGEM][{numero}] 🛑 ERRO 401 — sessão rejeitada, pular sem registrar")
        return False

    # Registrar comentário com resultado da triagem
    if triagem_txt:
        try:
            sucesso_cmt = criar_comentario(driver, triagem_txt)
            if not sucesso_cmt:
                print(f"[TRIAGEM][{numero}] ⚠ Comentário pode não ter sido salvo")
        except Exception as e:
            print(f"[TRIAGEM][{numero}] ⚠ Falha ao registrar comentário: {e}")
            traceback.print_exc()

    # Barreira: aguardar tabela de atividades GIGS pronta antes do bucket criar Nova atividade
    from Fix.utils_observer import aguardar_renderizacao_nativa as _aguardar
    _aguardar(driver, 'pje-gigs-lista-atividades button', 'aparecer', 8)

    # Aplicar ação pós-triagem baseada em alertas
    ok = False
    try:
        ok = _aplicar_acao_pos_triagem(driver, numero, processo_info, triagem_txt)
    except Exception as e:
        print(f"[TRIAGEM][{numero}] ❌ Erro na ação pós-triagem: {e}")
        traceback.print_exc()

    # Registrar progresso
    _progresso.marcar_processo_executado(
        numero, "SUCESSO" if ok else "FALHA", None, progresso)

    return ok


# ============================================================================
# FLUXO PRINCIPAL
# ============================================================================

def run_triagem(driver: Optional[WebDriver] = None) -> Optional[Dict[str, Any]]:
    """Fluxo principal de triagem.

    Espelha a estrutura de aud.run_aud():
      1. Cria/usa driver e faz login
      2. Busca lista Triagem Inicial via API
      3. Filtra processos já executados (progresso.json)
      4. Para cada processo pendente: triagem → comentário → ação pós-triagem
    """
    from Fix.utils import driver_pc, login_cpf
    from Fix.utils import configurar_recovery_driver, handle_exception_with_recovery

    configurar_recovery_driver(driver_pc, login_cpf)

    drv = _criar_driver_e_logar(driver)
    if not drv:
        print("[TRIAGEM] ❌ Falha ao obter driver")
        return None

    try:
        from Triagem.api import buscar_lista_triagem, enriquecer_processo, _is_triagem_inicial

        print(f"[TRIAGEM] Navegando para {URL_LISTA_TRIAGEM}")
        drv.get(URL_LISTA_TRIAGEM)
        time.sleep(3)

        # 1. Buscar lista
        itens_brutos = buscar_lista_triagem(drv)
        if not itens_brutos:
            print("[TRIAGEM] ❌ API não retornou itens — verificar sessão ou endpoint")
            return {"sucesso": False, "erro": "Lista vazia"}

        triagem_itens = [i for i in itens_brutos if _is_triagem_inicial(i)]
        if not triagem_itens:
            print("[TRIAGEM] Campo tarefa não identificou Triagem Inicial — usando todos os itens")
            triagem_itens = itens_brutos

        lista = [p for p in (enriquecer_processo(i) for i in triagem_itens) if p]
        if not lista:
            print("[TRIAGEM] ❌ Nenhum processo enriquecido")
            return {"sucesso": False, "erro": "Nenhum processo enriquecido"}

        print(f"[TRIAGEM] ✅ {len(lista)} processos de Triagem Inicial "
              f"(de {len(itens_brutos)} brutos)")

        # 2. Filtrar já executados
        progresso = _progresso.carregar_progresso()
        pendentes = [
            p for p in lista
            if not _progresso.processo_ja_executado(p.get("numero"), progresso)
        ]
        pulados = len(lista) - len(pendentes)
        print(f"[TRIAGEM] {pulados} pulados (já executados) / {len(pendentes)} a processar")

        if not pendentes:
            print("[TRIAGEM] ⚠ Todos os processos já foram executados!")
            return {"sucesso": True, "processados": 0, "total": len(lista)}

        # 3. Processar
        handle_principal = drv.current_window_handle
        resultados: List[Dict] = []

        for idx, proc in enumerate(pendentes):
            numero = proc.get("numero", "?")
            print(f"\n[TRIAGEM] ── {idx+1}/{len(pendentes)}: {numero} ──")

            ok = _processar_processo(drv, proc, progresso)
            resultados.append({"numero": numero, "ok": ok})

            # Limpar abas extras
            try:
                for h in list(drv.window_handles):
                    if h != handle_principal:
                        try:
                            drv.switch_to.window(h)
                            drv.close()
                        except Exception:
                            pass
                drv.switch_to.window(handle_principal)
            except Exception:
                pass

        ok_count = sum(1 for r in resultados if r["ok"])
        print(f"\n[TRIAGEM] ✅ Concluído: {ok_count}/{len(resultados)} com sucesso")

        return {
            "sucesso": ok_count > 0 or len(resultados) == 0,
            "processados": len(resultados),
            "sucesso_count": ok_count,
            "total": len(lista),
        }

    except Exception as e:
        novo = None
        try:
            from Fix.utils import handle_exception_with_recovery
            novo = handle_exception_with_recovery(e, drv, "TRIAGEM_RUN")
        except Exception:
            pass
        if not novo:
            print(f"[TRIAGEM] ❌ Erro fatal: {e}")
            traceback.print_exc()
        return None


if __name__ == "__main__":
    import sys
    import os
    # Garante imports do projeto raiz
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    print("[TRIAGEM] Executando como script")
    resultado = run_triagem(None)
    print(f"[TRIAGEM] Resultado: {resultado}")
