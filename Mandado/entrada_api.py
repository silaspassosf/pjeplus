"""Mandado - Entrada API (Entrypoint Unico do x.py)

Consolidado a partir de:
    Mandado/processamento_api.py  — entrada principal, timeline, despacho
    Mandado/utils.py              — utilitarios e compatibilidade (LEGADO)
    Mandado/utils_intimacao.py    — fechamento de intimacao

Entrypoint publico: processar_mandados_devolvidos_api()
Cadeia: processar_mandados_devolvidos_api -> processar_mandado_detalhe
        -> _selecionar_doc_via_timeline -> processar_argos | fluxo_mandados_outros
"""

# ══════════════════════ IMPORTS ══════════════════════

import importlib.util
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from Fix.utils import normalizar_texto

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from Fix.core import wait_for_page_load, safe_click_no_scroll, esperar_elemento
from Fix.log import logger
from Fix.monitoramento_progresso_unificado import marcar_processo_executado_unificado, carregar_progresso_unificado
from Fix.selenium_base import aguardar_e_clicar, safe_click
from Fix.core import aguardar_renderizacao_nativa
from Fix.abas import fechar_abas_extras as _fechar_abas_extras

from Mandado.apoio_fluxos import fluxo_mandados_outros

# ── Canonicos (apoio_fluxos consolida utils, sigilo, lembrete) ──
from Mandado.apoio_fluxos import (
    lembrete_bloq,
    retirar_sigilo,
    retirar_sigilo_fluxo_argos,
    retirar_sigilo_certidao_devolucao_primeiro,
)

from utilitarios_processamento import run_batch, create_skip_checker, resultado_ok, resultado_falha
from Fix.variaveis import url_processo_detalhe

# ── LEGADO (utils.py: bloco de diagnostico, preservado por fidelidade) ──
with open("log.py", "w", encoding="utf-8") as f:
    f.write(f"# Ultima execucao: {datetime.now()}\n")
    f.write(f"# Script: {os.path.abspath(sys.argv[0])}\n")
    f.write(f"# Argumentos: {' '.join(sys.argv[1:])}\n")


# ══════════════════════ 1. API ENTRY ══════════════════════

_API_CORE_TYPES = None


def _api_core_types():
    global _API_CORE_TYPES
    if _API_CORE_TYPES is not None:
        return _API_CORE_TYPES

    core_path = Path(__file__).resolve().parents[1] / 'api' / 'variaveis_client.py'
    spec = importlib.util.spec_from_file_location('pjeplus_api_variaveis_client_runtime', str(core_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f'[MANDADOS_API] Nao foi possivel carregar API Core: {core_path}')

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _API_CORE_TYPES = (module.PjeApiClient, module.session_from_driver)
    return _API_CORE_TYPES


def _criar_api_client(driver):
    pje_api_client_cls, session_from_driver_fn = _api_core_types()
    sess, trt_host = session_from_driver_fn(driver)
    return pje_api_client_cls(sess, trt_host, grau=1)


def _buscar_todas_paginas_gateway(
    client,
    path: str,
    *,
    params_base: dict,
    tamanho_pagina: int,
    pagina_inicial: int = 1,
    limite_paginas: int = 200,
    timeout: int = 20,
) -> dict:
    itens_total = []
    pagina = max(1, int(pagina_inicial or 1))

    for _ in range(limite_paginas):
        params = dict(params_base)
        params['pagina'] = pagina
        params['tamanhoPagina'] = tamanho_pagina

        resposta = client.gateway_get(path, params=params, timeout=timeout)
        if not resposta.get('ok'):
            return resposta

        payload = resposta.get('data')
        if isinstance(payload, dict):
            itens = payload.get('resultado') or payload.get('dados') or []
            qtd_paginas = payload.get('qtdPaginas') or payload.get('totalPaginas') or payload.get('totalPages')
            if not isinstance(itens, list):
                itens = []
        elif isinstance(payload, list):
            itens = payload
            qtd_paginas = None
        else:
            itens = []
            qtd_paginas = None

        itens_total.extend(itens)

        if isinstance(qtd_paginas, int):
            if pagina >= qtd_paginas:
                return {'ok': True, 'status': resposta.get('status'), 'data': itens_total, 'error': None}
        elif len(itens) < tamanho_pagina:
            return {'ok': True, 'status': resposta.get('status'), 'data': itens_total, 'error': None}

        pagina += 1

    return {
        'ok': False,
        'status': None,
        'data': None,
        'error': {
            'type': 'pagination_limit',
            'message': f'Limite de paginas atingido: {limite_paginas}',
            'method': 'GET',
            'path': path,
            'status': None,
        },
    }


def obter_mandados_devolvidos(driver, pagina=1, tamanho_pagina=50, ordenacao_crescente=True):
    """Retorna a lista de mandados devolvidos via endpoint interno."""
    client = _criar_api_client(driver)
    resposta = _buscar_todas_paginas_gateway(
        client,
        '/pje-comum-api/api/escaninhos/documentosinternos',
        params_base={
            'mandadosDevolvidos': 'true',
            'ordenacaoCrescente': str(ordenacao_crescente).lower(),
        },
        tamanho_pagina=tamanho_pagina,
        pagina_inicial=pagina,
        timeout=20,
    )

    if not resposta.get('ok'):
        erro = resposta.get('error') or {}
        raise RuntimeError(
            f"[MANDADOS_API] Erro HTTP: {resposta.get('status')}, payload: {erro.get('message')}"
        )

    data = resposta.get('data')

    if isinstance(data, dict):
        processos = data.get('resultado') or data.get('dados') or []
    elif isinstance(data, list):
        processos = data
    else:
        processos = []

    return processos


def _carregar_concluidos_mandado() -> set:
    """Lega progresso.json via System A e retorna set de numeros de processo MANDADO ja concluidos."""
    try:
        dados = carregar_progresso_unificado('mandado', suppress_load_log=True)
        return set(dados.get('processos_executados', []))
    except Exception:
        pass
    return set()


def _marcar_concluido_mandado(numero: str) -> None:
    """Marca numero como executado em progresso.json via System A."""
    try:
        dados = carregar_progresso_unificado('mandado', suppress_load_log=True)
        marcar_processo_executado_unificado('mandado', numero, dados, sucesso=True)
    except Exception as e:
        logger.warning(f'[MANDADOS_API] Falha ao salvar concluidos: {e}')


def processar_mandados_devolvidos_api(driver, pagina=1, tamanho_pagina=50, ordenacao_crescente=True):
    """Fluxo completo: consulta API + lista fila + processa via engine run_batch."""
    mandados = obter_mandados_devolvidos(driver, pagina=pagina, tamanho_pagina=tamanho_pagina, ordenacao_crescente=ordenacao_crescente)

    if not mandados:
        logger.info('[MANDADOS_API] Nenhum mandado devolvido encontrado')
        return False

    # ── Extrair itens normalizados
    itens = []
    for item in mandados:
        processo_obj = item.get('processo') or {}
        id_p = processo_obj.get('id') or processo_obj.get('idProcesso') or item.get('idProcesso') or item.get('id')
        num = processo_obj.get('numero') or processo_obj.get('numeroProcesso') or item.get('numeroProcesso') or item.get('numero')
        if id_p or num:
            itens.append({'id': id_p, 'numero': num})

    if not itens:
        logger.info('[MANDADOS_API] Nenhum item na fila')
        return False

    # ── Listar fila completa antes de comecar
    logger.info(f'[MANDADOS_API] {len(itens)} processo(s) na fila:')
    for i, it in enumerate(itens, 1):
        logger.info(f'[MANDADOS_API]   #{i}: id={it["id"]}  numero={it["numero"]}')

    # ── Verificar progresso de execucoes anteriores
    concluidos = _carregar_concluidos_mandado()
    if concluidos:
        logger.info(f'[MANDADOS_API] {len(concluidos)} processo(s) ja concluidos em execucao anterior — serao ignorados')

    # ── should_skip: factory do engine (baseada em progresso unificado)
    should_skip = create_skip_checker('mandado')

    def open_item(item):
        """No-op: navegacao e feita dentro de execute_item."""
        return resultado_ok()

    def execute_item(item):
        """Processa o mandado no processo aberto."""
        num = item.get('numero') or item.get('id')
        try:
            resultado = processar_mandado_detalhe(
                driver,
                numero_processo=item.get('numero'),
                id_processo=item.get('id'),
            )
            if resultado == 'PULAR':
                logger.info(f"[MANDADOS_API] #{num} pulado (tipo nao mapeado)")
                return resultado_ok(pulado=True)
            elif resultado:
                return resultado_ok()
            else:
                return resultado_falha("processar_mandado_detalhe retornou False")
        except Exception as e:
            logger.error(f"[MANDADOS_API] Erro ao processar {num}: {e}")
            return resultado_falha(str(e))

    def persist_result(item, result):
        """Persiste progresso apenas em caso de sucesso real (nao PULAR)."""
        if result.get('ok'):
            dados = result.get('dados') or {}
            if not dados.get('pulado'):
                num = item.get('numero') or item.get('id')
                if num:
                    logger.info(f"[MANDADOS_API] #{num} concluido")
                    _marcar_concluido_mandado(str(num))

    stats = run_batch(
        items=itens,
        should_skip=should_skip,
        open_item=open_item,
        execute_item=execute_item,
        persist_result=persist_result,
    )

    logger.info(
        f'[MANDADOS_API] Concluido — '
        f'total={stats["total"]} sucesso={stats["sucesso"]} '
        f'pulados={stats["pulados"]} falha={stats["falha"]}'
    )

    if stats["falha"]:
        falhas_reg = [r for r in stats["itens"] if r["status"] == "falha"]
        labels = [str(r["item"].get("numero") or r["item"].get("id", "")) for r in falhas_reg]
        logger.warning(f'[MANDADOS_API] Falhas: {labels}')

    # Mantem compatibilidade: True se ao menos um sucesso ou todos pulados
    return stats["sucesso"] > 0 or (stats["pulados"] == stats["total"] and stats["total"] > 0)


def _gigs_sem_prazo_via_js(driver, tamanho_pagina: int = 100) -> list:
    """Busca GIGS sem prazo (XS) reaproveitando o core de API/paginacao."""
    client = _criar_api_client(driver)
    resultado = _buscar_todas_paginas_gateway(
        client,
        '/pje-gigs-api/api/relatorioatividades/',
        params_base={
            'filtrarAtividadesSemPrazo': 'true',
            'filtrarAtividadesSemPrazoConcluidas': 'false',
            'ordenacaoCrescente': 'true',
            'filtrarPorDestinatario': 'false',
            'filtrarPorLocalizacao': 'false',
        },
        tamanho_pagina=tamanho_pagina,
        limite_paginas=200,
        timeout=20,
    )

    if not resultado.get('ok'):
        erro = (resultado.get('error') or {}).get('message') or 'sem_resposta'
        logger.error(f"[MANDADOS_API] falha GIGS sem prazo: {erro}")
        return []

    dados = resultado.get('data') or []

    # Filtrar somente GIGS com descricao xs (se aplica)
    filtrados = []
    for item in dados:
        tipo = (item.get('tipoAtividade') or {}).get('descricao', '') or (item.get('tipoAtividade') or {}).get('nome', '')
        if isinstance(tipo, str) and 'xs' in tipo.lower():
            filtrados.append(item)

    logger.info(f"[MANDADOS_API] GIGS sem prazo bruto {len(dados)}, filtrado xs {len(filtrados)}")
    return filtrados


def testar_api_gigs_sem_prazo(driver, tamanho_pagina: int = 100) -> list:
    """Teste local rapido do endpoint de GIGS sem prazo (XS)."""
    resultado = _gigs_sem_prazo_via_js(driver, tamanho_pagina=tamanho_pagina)
    logger.info(f"[MANDADOS_API] total capturado: {len(resultado)}")
    if resultado:
        logger.info(f"[MANDADOS_API] exemplo: {resultado[0]}")
    return resultado


# ══════════════════════ 2. TIMELINE / SELECAO DE DOCUMENTO ══════════════════════

_TERMOS_ARGOS = (
    'pesquisa patrimonial', 'argos', 'devolucao de ordem de pesquisa',
    'certidao de devolucao', 'devolucao de ordem',
)
_TERMOS_OUTROS = (
    'certidao de oficial de justica', 'certidao de oficial', 'oficial de justica',
)


def _selecionar_doc_via_timeline(driver, log=True):
    """
    Localiza e clica na primeira ocorrencia relevante da timeline (mais recente).
    Usa safe_click_no_scroll (dispatchEvent) — independente de scroll.
    Retorna 'argos', 'outros' ou None se nenhum doc relevante encontrado.
    Regras espelham classificarItem() de lista.timeline.js e fluxo_mandado() do LEGADO.
    """
    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
    for item in itens:
        try:
            link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
        except Exception:
            continue

        norm = normalizar_texto(link.text or '')

        if any(t in norm for t in _TERMOS_ARGOS):
            tipo = 'argos'
        elif any(t in norm for t in _TERMOS_OUTROS):
            tipo = 'outros'
        else:
            continue

        if log:
            logger.info(f"[MANDADOS_API] Timeline: primeiro doc relevante tipo={tipo} — '{(link.text or '')[:60]}'")

        if not safe_click_no_scroll(driver, link, log=log):
            logger.warning(f"[MANDADOS_API] Falha ao clicar doc timeline: '{(link.text or '')[:40]}'")
            return None

        aguardar_renderizacao_nativa(driver, "div.conteudo-principal")
        return tipo

    return None


# ══════════════════════ 3. DETAIL PROCESSING ══════════════════════

def processar_mandado_detalhe(driver, numero_processo=None, id_processo=None):
    """Navega para /processo/{id}/detalhe/ na aba atual, processa mandado e fecha abas extras."""
    if id_processo:
        detalhe_url = url_processo_detalhe(id_processo)
    elif numero_processo:
        detalhe_url = url_processo_detalhe(numero_processo)
    else:
        raise ValueError("id_processo ou numero_processo deve ser fornecido")

    handle_principal = driver.current_window_handle

    try:
        driver.get(detalhe_url)
        wait_for_page_load(driver, timeout=15)
        timeline_ok = esperar_elemento(driver, 'li.tl-item-container', timeout=15)
        if not timeline_ok:
            logger.error(f"[MANDADOS_API] Timeline nao encontrada para {id_processo or numero_processo}")
            return False

        tipo = _selecionar_doc_via_timeline(driver, log=True)

        # ── Despacho para Ramos ──
        if tipo == 'argos':
            logger.info(f"[MANDADOS_API] {id_processo or numero_processo} -> Argos (via timeline)")
            from Mandado.fluxo_argos import processar_argos
            return processar_argos(driver, log=True)

        if tipo == 'outros':
            logger.info(f"[MANDADOS_API] {id_processo or numero_processo} -> Outros (via timeline)")
            fluxo_mandados_outros(driver, log=False)
            return True

        logger.info(f"[MANDADOS_API] Tipo nao mapeado para {id_processo or numero_processo} (nenhum doc relevante na timeline) — pulando")
        return 'PULAR'
    except Exception as e:
        logger.error(f"[MANDADOS_API] Erro ao processar {id_processo or numero_processo}: {e}")
        return False
    finally:
        _fechar_abas_extras(driver, handle_principal)


# ══════════════════════ 4. UTILS / COMPATIBILIDADE ══════════════════════

def retirar_sigilo_demais_documentos_especificos(driver, documentos_sequenciais, log=True):
    """COMPATIBILIDADE: Chama retirar_sigilo_fluxo_argos e retorna lista de demais documentos."""
    resultado = retirar_sigilo_fluxo_argos(driver, documentos_sequenciais, log)
    return resultado.get('demais_documentos', [])


def retirar_sigilo_documentos_especificos(driver, documentos_sequenciais, log=True):
    """
     FUNCAO EFICIENTE - Remove sigilo APENAS dos documentos especificos fornecidos:
    Os documentos_sequenciais ja vem filtrados da buscar_documentos_sequenciais()
    MAXIMO 5 documentos: 1 certidao devolucao, 1 certidao expedicao, 1 intimacao, 1 decisao, 1 planilha

    NADA MAIS que isso - SEM VARRER TIMELINE INTEIRA!
    """
    if not documentos_sequenciais:
        return []

    #  EFICIENCIA: Os documentos ja vem filtrados, apenas remover sigilo diretamente
    documentos_processados = []
    total_processados = 0

    #  PROCESSAMENTO DIRETO: Remove sigilo apenas dos documentos fornecidos
    for i, elemento in enumerate(documentos_sequenciais):
        try:
            texto = elemento.text.strip()[:50] if elemento.text else f"DOCUMENTO_{i+1}"

            resultado_sigilo = retirar_sigilo(elemento, driver)

            if resultado_sigilo:
                documentos_processados.append({
                    'indice': i+1,
                    'texto': texto,
                    'status': 'sucesso'
                })
                total_processados += 1
            else:
                documentos_processados.append({
                    'indice': i+1,
                    'texto': texto,
                    'status': 'falha'
                })

        except Exception as e:
            if log:
                logger.error(f"[SIGILO_ESPECIFICO]  Erro ao processar documento {i+1}: {e}")
            documentos_processados.append({
                'indice': i+1,
                'texto': texto if 'texto' in locals() else f"DOCUMENTO_{i+1}",
                'status': 'erro',
                'erro': str(e)
            })

    #  RELATORIO FINAL
    if log:

        for doc in documentos_processados:
            status_icon = "" if doc['status'] == 'sucesso' else "" if doc['status'] == 'erro' else ""


    return documentos_processados


# ══════════════════════ 5. FECHAMENTO DE INTIMACAO ══════════════════════

def _selecionar_checkbox_intimacao(driver: WebDriver, linha: WebElement, log: bool = True) -> bool:
    """Marca o checkbox da linha alvo usando poucas tentativas eficientes."""
    try:
        checkbox_element = linha.find_element(By.CSS_SELECTOR, 'td:last-child div:not([hidden]) mat-checkbox')
        input_checkbox = checkbox_element.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
    except Exception:
        return False

    tentativas = (
        lambda: safe_click(driver, checkbox_element, timeout=3, log=False),
        lambda: safe_click(driver, input_checkbox, timeout=3, log=False),
        lambda: driver.execute_script("arguments[0].click();", checkbox_element),
        lambda: driver.execute_script("arguments[0].click();", input_checkbox),
    )

    def marcado() -> bool:
        try:
            return input_checkbox.is_selected()
        except StaleElementReferenceException:
            try:
                novo_input = linha.find_element(By.CSS_SELECTOR, 'td:last-child div:not([hidden]) mat-checkbox input[type="checkbox"]')
                return novo_input.is_selected()
            except Exception:
                return False

    for tentativa in tentativas:
        try:
            tentativa()
            try:
                WebDriverWait(driver, 1, poll_frequency=0.1).until(lambda d: marcado())
                return True
            except TimeoutException:
                continue
        except Exception:
            continue

    return False


def fechar_intimacao(driver: WebDriver, log: bool = True) -> bool:
    """Fecha a intimacao do processo."""
    logger.info('[INTIMACAO] === INICIO ===')
    try:
        # 1. Abrir menu
        logger.info('[INTIMACAO] [1] Tentando abrir menu #botao-menu...')
        if not aguardar_e_clicar(driver, '#botao-menu', timeout=10):
            logger.info('[INTIMACAO] [1]  FALHOU: Nao conseguiu abrir menu')
            return False
        logger.info('[INTIMACAO] [1]  Menu aberto')
        # UI-transition: aguardar_e_clicar a seguir ja tem WebDriverWait interno

        # 2. Clicar Expedientes
        logger.info('[INTIMACAO] [2] Tentando clicar Expedientes...')
        if not aguardar_e_clicar(driver, 'button[aria-label="Expedientes"]', timeout=5):
            logger.info('[INTIMACAO] [2]  FALHOU: Nao conseguiu clicar Expedientes')
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            return False
        logger.info('[INTIMACAO] [2]  Botao Expedientes clicado')

        # 3. Aguardar modal
        logger.info('[INTIMACAO] [3] Aguardando modal abrir...')
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'tbody tr'))
            )
        except TimeoutException:
            pass

        # 4. Buscar linha prazo 30
        logger.info('[INTIMACAO] [4] Buscando linhas com prazo 30...')
        rows = driver.find_elements(By.CSS_SELECTOR, 'tbody tr')
        logger.info(f'[INTIMACAO] [4] Total de linhas encontradas: {len(rows)}')

        linha_prazo_30 = None

        for i, row in enumerate(rows):
            try:
                cells = row.find_elements(By.TAG_NAME, 'td')
                if len(cells) >= 11:
                    prazo = cells[8].text.strip()
                    fechado = cells[10].text.strip().lower()

                    if prazo == '30' and fechado != "sim":
                        linha_prazo_30 = row
                        assinatura_linha = tuple(
                            cell.text.strip().lower()
                            for cell in cells[:10]
                        )
                        logger.info(f'[INTIMACAO] [4]  Linha {i+1} selecionada (prazo 30, nao fechado)')
                        break
            except Exception as e:
                logger.info(f'[INTIMACAO] [4] Erro na linha {i+1}: {str(e)[:40]}')
                continue

        if not linha_prazo_30:
            logger.info('[INTIMACAO] [4]  Nenhuma linha prazo 30 nao fechada encontrada')
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            try:
                WebDriverWait(driver, 2).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except TimeoutException:
                pass
            return True

        # 5. Clicar checkbox
        logger.info('[INTIMACAO] [5] Tentando marcar checkbox...')
        if not _selecionar_checkbox_intimacao(driver, linha_prazo_30, log=log):
            logger.info('[INTIMACAO] [5]  FALHOU: Nao conseguiu marcar checkbox')
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            try:
                WebDriverWait(driver, 2).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except TimeoutException:
                pass
            return False
        logger.info('[INTIMACAO] [5]  Checkbox marcado')

        # 6. Clicar Fechar Expedientes
        logger.info('[INTIMACAO] [6] Tentando clicar Fechar Expedientes...')
        if not aguardar_e_clicar(driver, 'button[aria-label="Fechar Expedientes"]', timeout=5):
            logger.info('[INTIMACAO] [6]  FALHOU: Nao conseguiu clicar Fechar Expedientes')
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            return False
        logger.info('[INTIMACAO] [6]  Botao Fechar Expedientes clicado')
        aguardar_renderizacao_nativa(driver, '.cdk-overlay-container mat-dialog-container', modo='aparecer', timeout=5)

        # 7. Confirmar no botao do dialogo, e nao por foco global
        logger.info('[INTIMACAO] [7] Confirmando fechamento...')
        btn_sim = None
        for xpath in (
            "//div[contains(@class,'cdk-overlay-container')]//mat-dialog-container//button[.//span[normalize-space(.)='Sim'] or normalize-space(.)='Sim']",
            "//div[contains(@class,'cdk-overlay-pane')]//button[.//span[normalize-space(.)='Sim'] or normalize-space(.)='Sim']",
            "//button[.//span[normalize-space(.)='Sim'] or normalize-space(.)='Sim']",
        ):
            try:
                btn_sim = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                break
            except TimeoutException:
                continue

        if not btn_sim:
            logger.info('[INTIMACAO] [7]  FALHOU: botao Sim nao encontrado')
            return False

        try:
            driver.execute_script('arguments[0].click();', btn_sim)
        except Exception:
            btn_sim.click()

        if not aguardar_renderizacao_nativa(driver, '.cdk-overlay-container mat-dialog-container', modo='sumir', timeout=5):
            logger.info('[INTIMACAO] [7]  FALHOU: dialogo de confirmacao permaneceu aberto')
            return False

        # Aguardar snackbar de sucesso para confirmar fechamento rápido
        logger.info('[INTIMACAO] [7] Aguardando snackbar de sucesso...')
        try:
            snack_sucesso = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'snack-bar-container, simple-snack-bar'))
            )
            logger.info(f'[INTIMACAO] [7]  Snackbar detectado: "{snack_sucesso.text}"')
            try:
                driver.execute_script("arguments[0].style.display = 'none';", snack_sucesso)
            except Exception:
                pass
        except TimeoutException:
            logger.info('[INTIMACAO] [7]  AVISO: snackbar de sucesso não detectado, assumindo sucesso se o modal fechou')

        # Aguardar timeline pronta apos fechamento (sem sleep fixo)
        logger.info('[INTIMACAO] [8] Aguardando timeline estabilizar...')
        try:
            WebDriverWait(driver, 3).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')) > 0
            )
        except TimeoutException:
            pass

        logger.info('[INTIMACAO] === SUCESSO ===')

        return True

    except Exception as e:
        logger.info(f'[INTIMACAO] === ERRO GERAL: {str(e)[:150]} ===')
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        except Exception:
            pass
        return False
