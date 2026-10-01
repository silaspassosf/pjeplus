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

import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from Fix.utils import normalizar_texto

from typing import Any, Optional, Dict, List

from Fix import espera
from Fix.core import (
    wait_for_page_load, safe_click_no_scroll, esperar_elemento,
    aguardar_renderizacao_nativa, aguardar_e_clicar, safe_click
)
from Fix.log import logger
from utilitarios_processamento import mark_done, is_done, get_concluidos
from Fix.browser_suporte import abrir_url_nova_aba
from Fix.abas import fechar_abas_extras as _fechar_abas_extras, aguardar_nova_aba


def _fechar_modal_esc(driver: Any):
    """Fecha modal enviando Escape pelo teclado."""
    try:
        if hasattr(driver, 'page'):
            driver.page.keyboard.press('Escape')
        elif hasattr(driver, '_page'):
            driver._page.keyboard.press('Escape')
        elif hasattr(driver, 'keyboard'):
            driver.keyboard.press('Escape')
    except Exception:
        pass

from Mandado.apoio_fluxos import (
    fluxo_mandados_outros,
    fluxo_mandados_cp,
    arquivar_mandado_outros_reconhecido,
    arquivar_mandado_positivo_reconhecido,
)

# ── Canonicos (apoio_fluxos consolida utils, sigilo, lembrete) ──
from Mandado.apoio_fluxos import (
    lembrete_bloq,
    retirar_sigilo,
    retirar_sigilo_fluxo_argos,
    retirar_sigilo_certidao_devolucao_primeiro,
)



# ══════════════════════ 1. API ENTRY ══════════════════════

def _criar_api_client(driver):
    """Cria PjeApiClient a partir do driver (import direto de Fix.variaveis)."""
    from Fix.variaveis import PjeApiClient, session_from_driver
    sess, trt_host = session_from_driver(driver)
    return PjeApiClient(sess, trt_host, grau=1)


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


def _should_skip_mandado(numero: str) -> bool:
    """Verifica se mandado ja foi concluido em execucao anterior."""
    if not numero:
        return False
    return is_done('mandado', str(numero))


def _marcar_concluido_mandado(numero: str) -> None:
    """Marca mandado como concluido no progresso.json."""
    if numero:
        mark_done('mandado', str(numero), sucesso=True)


def processar_mandados_devolvidos_api(driver, pagina=1, tamanho_pagina=50, ordenacao_crescente=True):
    """Fluxo completo: consulta API + lista fila + processa certidões na UI + depois o resto via engine run_batch."""
    mandados = obter_mandados_devolvidos(driver, pagina=pagina, tamanho_pagina=tamanho_pagina, ordenacao_crescente=ordenacao_crescente)

    if not mandados:
        logger.info('[MANDADOS_API] Nenhum mandado devolvido encontrado')
        return False

    # ABRIR ESCANINHO E FILTRAR (passo 1)
    from Mandado.fluxo_ui import ativar_filtro_mandados_devolvidos
    from Fix.core import wait_for_page_load
    
    url_escaninho = "https://pje.trt2.jus.br/pjekz/escaninho/documentos-internos"
    if "escaninho/documentos-internos" not in driver.current_url:
        driver.get(url_escaninho)
        wait_for_page_load(driver, timeout=15)
        
    ativar_filtro_mandados_devolvidos(driver)
    escaninho_handle = driver.current_window_handle

    # ── Montar fila: extrair id/numero de cada item sem chamar API por processo.
    # A classificacao real (argos vs outros) e feita pela timeline DOM ao abrir
    # cada processo — igual ao comportamento pre-refac, evita N chamadas HTTP
    # sequenciais antes de processar o 1o mandado.
    itens_fila = []
    for item in mandados:
        processo_obj = item.get('processo') or {}
        id_p = processo_obj.get('id') or processo_obj.get('idProcesso') or item.get('idProcesso') or item.get('id')
        num = processo_obj.get('numero') or processo_obj.get('numeroProcesso') or item.get('numeroProcesso') or item.get('numero')
        if not (id_p or num):
            continue
        itens_fila.append({'id': id_p, 'numero': num})

    if not itens_fila:
        logger.info('[MANDADOS_API] Nenhum item na fila')
        return False

    logger.info(f'[MANDADOS_API] {len(itens_fila)} mandado(s) na fila')

    # ════════════════════════════════════════
    # FILA UNIFICADA: itera todos os mandados, classifica no DOM ao abrir
    # cada processo (igual ao comportamento pre-refac). O fluxo Argos e
    # Outros sao disparados conforme o tipo detectado pelo _selecionar_doc_via_timeline.
    # ════════════════════════════════════════
    from Fix.variaveis import url_processo_detalhe
    from Mandado.fluxo_argos import processar_argos

    concluidos_antes = get_concluidos('mandado')
    if concluidos_antes:
        logger.info(f'[MANDADOS_API] {len(concluidos_antes)} ja concluidos — serao pulados')

    for it in itens_fila:
        num = it['numero']
        id_p = it['id']

        if _should_skip_mandado(num):
            logger.info(f'[MANDADOS_API] #{num} ja concluido — pulando')
            continue

        logger.info(f'[MANDADOS_API] Processando: #{num}')
        detalhe_url = url_processo_detalhe(id_p or num)

        # Abre em NOVA ABA — preserva escaninho_handle intacto durante todo
        # o processamento (processar_argos pode abrir/fechar abas proprias).
        novo_handle = abrir_url_nova_aba(driver, detalhe_url, timeout=12)

        try:
            wait_for_page_load(driver, timeout=15)
            # Aguarda timeline renderizar antes de classificar
            aguardar_renderizacao_nativa(driver, 'li.tl-item-container', timeout=10)

            tipo = _selecionar_doc_via_timeline(driver, log=True)

            if tipo == 'argos':
                logger.info(f'[MANDADOS_API] #{num} -> Argos (timeline DOM)')
                result = processar_argos(driver, log=True)
                if result:
                    _marcar_concluido_mandado(str(num))
                else:
                    logger.warning(f'[MANDADOS_API] #{num}: processar_argos retornou False')

            elif tipo == 'outros':
                tipo_cabecalho = _classificar_tipo_processo_cabecalho(driver, log=True)
                if tipo_cabecalho == 'CartPrecCiv':
                    logger.info(f'[MANDADOS_API] #{num} -> Outros/CP')
                    resultado_cp = fluxo_mandados_cp(driver, numero_processo=str(num), escaninho_handle=escaninho_handle, log=True)
                    if resultado_cp == 'incompleto':
                        logger.info(f'[MANDADOS_API] #{num}: CP incompleto — GIGS xs1 + apagar executado')
                        _marcar_concluido_mandado(str(num))
                    elif resultado_cp == 'completo':
                        logger.info(f'[MANDADOS_API] #{num}: CP completo — processo arquivado')
                        _marcar_concluido_mandado(str(num))
                    else:
                        logger.warning(f'[MANDADOS_API] #{num}: Fluxo CP falhou')
                else:
                    logger.info(f'[MANDADOS_API] #{num} -> Outros (geral)')
                    regra = fluxo_mandados_outros(driver, log=True)
                    if regra:
                        if regra == 'positivo':
                            arquivar_mandado_positivo_reconhecido(driver, numero_processo=str(num), escaninho_handle=escaninho_handle, log=True)
                        else:
                            arquivar_mandado_outros_reconhecido(driver, numero_processo=str(num), escaninho_handle=escaninho_handle, log=True)
                        _marcar_concluido_mandado(str(num))
                    else:
                        logger.info(f'[MANDADOS_API] #{num}: Nenhuma regra reconhecida — pulando')

            else:
                logger.info(f'[MANDADOS_API] #{num}: Nenhum doc relevante na timeline — pulando')

        except Exception as e:
            logger.error(f'[MANDADOS_API] Erro ao processar #{num}: {e}')
        finally:
            # Fecha a aba do processo e volta ao escaninho
            _fechar_abas_extras(driver, escaninho_handle)
            try:
                driver.switch_to.window(escaninho_handle)
            except Exception:
                pass

    logger.info('[MANDADOS_API] Fila processada — concluido')
    return True


# ══════════════════════ 2. TIMELINE / SELECAO DE DOCUMENTO ══════════════════════

_TERMOS_ARGOS = (
    'pesquisa patrimonial', 'argos', 'devolucao de ordem de pesquisa',
    'certidao de devolucao', 'devolucao de ordem',
)
_TERMOS_OUTROS = (
    'certidao de oficial de justica', 'certidao de oficial', 'oficial de justica',
)


def _classificar_tipo_timeline_api(client, id_processo):
    """Classifica o processo em 'argos'/'outros' consultando a timeline via API,
    SEM abrir aba/navegador. Usa os mesmos criterios de _selecionar_doc_via_timeline
    (primeira ocorrencia relevante, timeline vem ordenada do mais recente).
    Retorna 'argos', 'outros' ou None (nenhum doc relevante / falha na API).
    """
    if not id_processo:
        return None
    try:
        itens = client.timeline(str(id_processo), buscarDocumentos=True, buscarMovimentos=False)
    except Exception as e:
        logger.warning(f"[MANDADOS_API] Falha ao consultar timeline via API para {id_processo}: {e}")
        return None

    if not itens:
        return None

    for doc in itens:
        titulo = normalizar_texto(doc.get('titulo') or doc.get('tipo') or '')
        if any(t in titulo for t in _TERMOS_ARGOS):
            return 'argos'
        if any(t in titulo for t in _TERMOS_OUTROS):
            return 'outros'

    return None


def _selecionar_doc_via_timeline(driver, log=True):
    """
    Localiza e clica na primeira ocorrencia relevante da timeline (mais recente).
    Usa safe_click_no_scroll (dispatchEvent) — independente de scroll.
    Retorna 'argos', 'outros' ou None se nenhum doc relevante encontrado.
    Regras espelham classificarItem() de lista.timeline.js e fluxo_mandado() do LEGADO.
    """
    links = espera.elementos(driver, 'li.tl-item-container a.tl-documento:not([target="_blank"])', teto=2)
    for link in links:
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


def _classificar_tipo_processo_cabecalho(driver: Any, log: bool = True):
    """Le o span 'align-end' do cabecalho do processo (pje-cabecalho-processo
    > pje-descricao-processo) e retorna seu texto (ex.: 'CartPrecCiv',
    'ATOrd') — mesmo seletor ja usado em f.py/bianca/dom_engine.py para
    extrair o tipo do processo. Usado aqui para decidir Fluxo CP vs fluxo
    geral de Outros.

    Retorna o texto (trim) ou None se o cabecalho/span nao for encontrado.
    """
    try:
        spans = espera.elementos(driver, 'pje-cabecalho-processo pje-descricao-processo span.align-end', teto=2)
        for span in spans:
            t = (span.text or '').strip()
            if t:
                return t
        return None
    except Exception as e:
        if log:
            logger.warning(f'[MANDADOS_API] Falha ao ler cabecalho do processo: {e}')
        return None


# ══════════════════════ 3. DETAIL PROCESSING ══════════════════════

def processar_mandado_detalhe(driver, numero_processo=None, id_processo=None, escaninho_handle=None):
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
            tipo_cabecalho = _classificar_tipo_processo_cabecalho(driver, log=False)
            if tipo_cabecalho == 'CartPrecCiv':
                logger.info(f"[MANDADOS_API] {id_processo or numero_processo} -> Outros/CP (cabecalho=CartPrecCiv)")
                resultado_cp = fluxo_mandados_cp(
                    driver,
                    numero_processo=str(numero_processo or id_processo),
                    escaninho_handle=escaninho_handle,
                    log=False,
                )
                return resultado_cp is not None

            logger.info(f"[MANDADOS_API] {id_processo or numero_processo} -> Outros (via timeline)")
            regra = fluxo_mandados_outros(driver, log=False)
            if regra:
                if regra == 'positivo':
                    arquivar_mandado_positivo_reconhecido(
                        driver,
                        numero_processo=str(numero_processo or id_processo),
                        escaninho_handle=escaninho_handle,
                        log=False,
                    )
                else:
                    arquivar_mandado_outros_reconhecido(
                        driver,
                        numero_processo=str(numero_processo or id_processo),
                        escaninho_handle=escaninho_handle,
                        log=False,
                    )
            return True

        logger.info(f"[MANDADOS_API] Tipo nao mapeado para {id_processo or numero_processo} (nenhum doc relevante na timeline) — pulando")
        return 'PULAR'
    except Exception as e:
        logger.error(f"[MANDADOS_API] Erro ao processar {id_processo or numero_processo}: {e}")
        return False
    finally:
        _fechar_abas_extras(driver, handle_principal)


# ══════════════════════ 5. FECHAMENTO DE INTIMACAO ══════════════════════

def _selecionar_checkbox_intimacao(driver: Any, linha: Any, log: bool = True) -> bool:
    """Marca o checkbox da linha alvo usando poucas tentativas eficientes."""
    try:
        checkbox_element = espera.elemento(linha, 'mat-checkbox', teto=1)
        input_checkbox = espera.elemento(checkbox_element, 'input[type="checkbox"]', teto=1)
    except Exception:
        return False

    tentativas = (
        lambda: safe_click(driver, checkbox_element, timeout=3, log=False),
        lambda: safe_click(driver, input_checkbox, timeout=3, log=False),
        lambda: safe_click_no_scroll(driver, checkbox_element),
        lambda: safe_click_no_scroll(driver, input_checkbox),
    )

    def marcado() -> bool:
        try:
            if hasattr(input_checkbox, 'is_checked'):
                return input_checkbox.is_checked()
            return getattr(input_checkbox, 'is_selected', lambda: False)()
        except Exception:
            try:
                novo_input = espera.elemento(linha, 'mat-checkbox input[type="checkbox"]', teto=0.5)
                if novo_input:
                    if hasattr(novo_input, 'is_checked'):
                        return novo_input.is_checked()
                    return getattr(novo_input, 'is_selected', lambda: False)()
                return False
            except Exception:
                return False

    for tentativa in tentativas:
        try:
            tentativa()
            t_fim = time.monotonic() + 1.0
            while time.monotonic() < t_fim:
                if marcado():
                    return True
                espera.assentar(driver, 0.05)
        except Exception:
            continue

    return False


def fechar_intimacao(driver: Any, log: bool = True) -> bool:
    """Fecha a intimacao do processo via catálogo de ações semânticas."""
    logger.debug('[INTIMACAO] === INICIO ===')
    from Fix.seletores_catalogo import buscar_elemento_por_acao, clicar_por_acao
    try:
        # 1. Abrir menu
        logger.debug('[INTIMACAO] [1] Abrindo menu...')
        if not clicar_por_acao(driver, "abrir_menu_tarefa", contexto="mandado", timeout=2):
            logger.error('[INTIMACAO] [1] FALHOU: Nao conseguiu abrir menu')
            return False

        # 2. Clicar Expedientes
        logger.debug('[INTIMACAO] [2] Clicando Expedientes...')
        if not clicar_por_acao(driver, "abrir_expedientes", contexto="mandado", timeout=3):
            logger.error('[INTIMACAO] [2] FALHOU: Nao conseguiu clicar Expedientes')
            _fechar_modal_esc(driver)
            return False

        # 3. Aguardar modal
        logger.debug('[INTIMACAO] [3] Aguardando modal abrir...')
        espera.elemento(driver, 'tbody tr', teto=5, visivel=False)

        # 4. Buscar linha prazo 30
        logger.debug('[INTIMACAO] [4] Buscando linhas com prazo 30...')
        rows = espera.elementos(driver, 'tbody tr', teto=2)
        logger.debug('[INTIMACAO] [4] Total de linhas encontradas: %d', len(rows))

        linha_prazo_30 = None
        for i, row in enumerate(rows):
            try:
                cells = espera.elementos(row, 'td', teto=0.5)
                if len(cells) >= 11:
                    prazo = cells[8].text.strip()
                    fechado = cells[10].text.strip().lower()

                    if prazo == '30' and fechado != "sim":
                        linha_prazo_30 = row
                        logger.debug('[INTIMACAO] [4] Linha %d selecionada (prazo 30, nao fechado)', i + 1)
                        break
            except Exception as e:
                logger.debug('[INTIMACAO] [4] Erro na linha %d: %s', i + 1, str(e)[:40])
                continue

        if not linha_prazo_30:
            logger.debug('[INTIMACAO] [4] Nenhuma linha prazo 30 nao fechada encontrada')
            _fechar_modal_esc(driver)
            espera.ate_js(driver, "document.readyState === 'complete'", teto=2)
            return True

        # 5. Clicar checkbox
        logger.debug('[INTIMACAO] [5] Marcando checkbox...')
        if not _selecionar_checkbox_intimacao(driver, linha_prazo_30, log=log):
            logger.error('[INTIMACAO] [5] FALHOU: Nao conseguiu marcar checkbox')
            _fechar_modal_esc(driver)
            espera.ate_js(driver, "document.readyState === 'complete'", teto=2)
            return False

        # 6. Clicar Fechar Expedientes
        logger.debug('[INTIMACAO] [6] Clicando Fechar Expedientes...')
        if not clicar_por_acao(driver, "fechar_expedientes", contexto="mandado", timeout=5):
            logger.error('[INTIMACAO] [6] FALHOU: Nao conseguiu clicar Fechar Expedientes')
            _fechar_modal_esc(driver)
            return False
        aguardar_renderizacao_nativa(driver, '.cdk-overlay-container mat-dialog-container', modo='aparecer', timeout=5)

        # 7. Confirmar no botao do dialogo
        logger.debug('[INTIMACAO] [7] Confirmando fechamento...')
        if not clicar_por_acao(driver, "confirmar_dialogo_sim", contexto="geral", timeout=3):
            logger.error('[INTIMACAO] [7] FALHOU: botao Sim nao encontrado')
            return False

        # 8. Aguardar timeline estabilizar
        logger.debug('[INTIMACAO] [8] Aguardando timeline estabilizar...')
        buscar_elemento_por_acao(driver, "abrir_timeline", contexto="geral", timeout=3)

        logger.debug('[INTIMACAO] === SUCESSO ===')
        return True

    except Exception as e:
        logger.error('[INTIMACAO] === ERRO GERAL: %s ===', str(e)[:150])
        try:
            _fechar_modal_esc(driver)
        except Exception:
            pass
        return False
