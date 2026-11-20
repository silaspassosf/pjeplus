"""Mandado - Entrada API (Entrypoint Unico do x.py)"""


import importlib.util
import logging
import os
import re
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

from utilitarios_processamento import run_batch, create_skip_checker, resultado_ok, resultado_falha
from Fix.variaveis import url_processo_detalhe

with open("log.py", "w", encoding="utf-8") as f:
    f.write(f"# Ultima execucao: {datetime.now()}\n")
    f.write(f"# Script: {os.path.abspath(sys.argv[0])}\n")
    f.write(f"# Argumentos: {' '.join(sys.argv[1:])}\n")


def _api_core_types():
    from Fix.variaveis import PjeApiClient, session_from_driver
    return PjeApiClient, session_from_driver


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
    from Fix.variaveis import buscar_todas_paginas
    return buscar_todas_paginas(
        client,
        path,
        params_base=params_base,
        tamanho_pagina=tamanho_pagina,
        pagina_inicial=max(1, int(pagina_inicial or 1)),
        limite_paginas=limite_paginas,
        timeout=timeout,
    )


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


def _url_invalida(driver):
    """True quando a aba atual não está numa página utilizável de processo."""
    try:
        url = (getattr(driver, 'current_url', '') or '').lower()
    except Exception:
        return True
    if not url:
        return True
    if 'acesso-negado' in url or 'access-denied' in url or 'login.seam' in url or 'login.jsp' in url:
        return True
    return False


def _recuperar_sessao(driver, tentativas=1):
    """Recupera a sessão quando a aba caiu em /acesso-negado."""
    for n in range(1, tentativas + 1):
        try:
            logger.warning('[MANDADOS_API][SESSAO] Aba inválida (%s) — tentativa %d/%d de recuperar',
                           (getattr(driver, 'current_url', '') or '')[:90], n, tentativas)
        except Exception:
            pass

        url_atual = (getattr(driver, 'current_url', '') or '').lower()

        if 'acesso-negado' not in url_atual and 'login' not in url_atual:
            try:
                driver.refresh()
                wait_for_page_load(driver, timeout=15)
            except Exception:
                pass
            if not _url_invalida(driver):
                logger.info('[MANDADOS_API][SESSAO] Recuperado com refresh')
                return True

        try:
            from Fix.sessao import carregar_cookies_sessao
            if carregar_cookies_sessao(driver):
                if not _url_invalida(driver):
                    logger.info('[MANDADOS_API][SESSAO] Recuperado via cookies salvos')
                    return True
        except Exception as e:
            logger.warning('[MANDADOS_API][SESSAO] Cookies falharam: %s', str(e)[:80])

        try:
            driver.get('https://pje.trt2.jus.br/pjekz/')
            wait_for_page_load(driver, timeout=15)
            if not _url_invalida(driver):
                logger.info('[MANDADOS_API][SESSAO] Recuperado voltando ao painel')
                return True
        except Exception:
            pass

        try:
            logger.info('[MANDADOS_API][SESSAO] Tentando reautenticação via login_cpf...')
            from Fix.utils import login_cpf
            from Fix.sessao import salvar_cookies_sessao
            if login_cpf(driver):
                try:
                    salvar_cookies_sessao(driver, info_extra='recuperacao_acesso_negado_mandado')
                except Exception:
                    pass
                if not _url_invalida(driver):
                    logger.info('[MANDADOS_API][SESSAO] Recuperado com sucesso via login_cpf')
                    return True
        except Exception as e_login:
            logger.warning('[MANDADOS_API][SESSAO] Falha no login_cpf: %s', str(e_login)[:80])

    return False


def _garantir_processo_aberto(driver, detalhe_url, num=''):
    """Abre `detalhe_url` e garante que a aba está mesmo no processo."""
    for tentativa in range(1, 3):
        try:
            driver.get(detalhe_url)
            wait_for_page_load(driver, timeout=15)
        except Exception as e:
            logger.warning('[MANDADOS_API] Falha ao abrir #%s (tentativa %d): %s', num, tentativa, str(e)[:80])

        if not _url_invalida(driver):
            return True

        logger.warning('[MANDADOS_API] #%s abriu em %s', num, (getattr(driver, 'current_url', '') or '')[:100])
        if tentativa == 1 and _recuperar_sessao(driver):
            continue

    logger.error('[MANDADOS_API] #%s: sessão inválida — não foi possível recuperar, pulando', num)
    return False


def processar_mandados_devolvidos_api(driver, pagina=1, tamanho_pagina=50, ordenacao_crescente=True):
    """Fluxo completo de mandados devolvidos (Argos, Certidões e Outros) sobre Fix/motor_fluxo."""
    from Fix.core import wait_for_page_load
    from Fix.motor_fluxo import FluxoSpec, executar_fluxo_lote, extrair_id_numero
    from Fix.variaveis import url_processo_detalhe
    from Mandado.fluxo_ui import ativar_filtro_mandados_devolvidos

    mandados = obter_mandados_devolvidos(
        driver, pagina=pagina, tamanho_pagina=tamanho_pagina, ordenacao_crescente=ordenacao_crescente
    )
    if not mandados:
        logger.info('[MANDADOS_API] Nenhum mandado devolvido encontrado')
        return False

    url_escaninho = "https://pje.trt2.jus.br/pjekz/escaninho/documentos-internos"
    if "escaninho/documentos-internos" not in driver.current_url:
        driver.get(url_escaninho)
        wait_for_page_load(driver, timeout=15)

    ativar_filtro_mandados_devolvidos(driver)
    escaninho_handle = driver.current_window_handle

    client = _criar_api_client(driver)
    buckets = {'argos': [], 'certidao': [], 'outros': []}
    for item in mandados:
        id_p, num = extrair_id_numero(item)
        if not (id_p or num):
            continue
        tipo = _classificar_tipo_timeline_api(client, id_p) if id_p else None
        chave_bucket = 'argos' if tipo == 'argos' else ('certidao' if tipo == 'outros' else 'outros')
        buckets[chave_bucket].append({'id': id_p, 'numero': num})

    itens_argos_sigilo, itens_certidao, itens_outros = buckets['argos'], buckets['certidao'], buckets['outros']
    if not (itens_argos_sigilo or itens_certidao or itens_outros):
        logger.info('[MANDADOS_API] Nenhum item na fila')
        return False

    logger.info(
        '[MANDADOS_API] %d Argos/Sigilo, %d Certidoes de Oficial, %d outros na fila',
        len(itens_argos_sigilo), len(itens_certidao), len(itens_outros),
    )

    def _marcar_se_ok(item, result):
        if result.get('ok') and not (result.get('dados') or {}).get('pulado'):
            num = item.get('numero') or item.get('id')
            if num:
                _marcar_concluido_mandado(str(num))

    def _url_mandado(item):
        return url_processo_detalhe(item['id'] or item['numero'])

    # BLOCO 1: ARGOS / SIGILO / DEVOLUCAO DE PESQUISA
    if itens_argos_sigilo:
        logger.info('[MANDADOS_API] BLOCO 1: Processando %d itens Argos/Sigilo...', len(itens_argos_sigilo))

        def _abrir_argos(drv, it):
            if _garantir_processo_aberto(drv, _url_mandado(it), it['numero']):
                return resultado_ok()
            _fechar_abas_extras(drv, escaninho_handle)
            try:
                drv.get(url_escaninho)
                wait_for_page_load(drv, timeout=10)
            except Exception:
                pass
            return resultado_falha('garantir_processo_aberto_falhou')

        def _exec_argos(drv, it):
            from Mandado.fluxo_argos import processar_argos
            logger.info('[MANDADOS_API][BLOCO1] Processando Argos/Sigilo: #%s', it['numero'])
            return resultado_ok() if processar_argos(drv, log=True) else resultado_falha('processar_argos_false')

        executar_fluxo_lote(
            driver,
            itens_argos_sigilo,
            FluxoSpec(
                nome='mandado_argos',
                tag_log='[MANDADOS_API][BLOCO1]',
                executar=_exec_argos,
                obter_url=_url_mandado,
                should_skip=lambda it: _should_skip_mandado(it['numero']),
                open_item_fn=_abrir_argos,
                persist_result=_marcar_se_ok,
                aba_ancora=escaninho_handle,
                fechar_abas_ao_final=True,
                stop_on_critical=False,
            ),
        )
        driver.get(url_escaninho)
        wait_for_page_load(driver, timeout=10)
        ativar_filtro_mandados_devolvidos(driver)

    # BLOCO 2: CERTIDOES DE OFICIAL
    if itens_certidao:
        def _exec_certidao(drv, it):
            num = it['numero']
            tipo = _selecionar_doc_via_timeline(drv, log=True)
            if tipo == 'outros':
                if _classificar_tipo_processo_cabecalho(drv, log=True) == 'CartPrecCiv':
                    res_cp = fluxo_mandados_cp(drv, numero_processo=str(num), escaninho_handle=escaninho_handle, log=True)
                    return resultado_ok() if res_cp in ('incompleto', 'completo') else resultado_falha('fluxo_cp_falhou')
                regra, texto_neg = fluxo_mandados_outros(drv, log=True, com_texto=True)
                if not regra:
                    return resultado_ok(pulado=True)
                if regra == 'positivo':
                    arquivar_mandado_positivo_reconhecido(drv, numero_processo=str(num), escaninho_handle=escaninho_handle, log=True)
                else:
                    arquivar_mandado_outros_reconhecido(
                        drv, numero_processo=str(num), escaninho_handle=escaninho_handle,
                        log=True, ao_meios_texto=texto_neg or None,
                    )
                return resultado_ok()
            if tipo == 'argos':
                from Mandado.fluxo_argos import processar_argos
                return resultado_ok() if processar_argos(drv, log=True) else resultado_falha('processar_argos_false')
            return resultado_ok(pulado=True)

        executar_fluxo_lote(
            driver,
            itens_certidao,
            FluxoSpec(
                nome='mandado_certidao',
                tag_log='[MANDADOS_API][BLOCO2]',
                executar=_exec_certidao,
                obter_url=_url_mandado,
                should_skip=lambda it: _should_skip_mandado(it['numero']),
                persist_result=_marcar_se_ok,
                modo_aba='nova_aba',
                aba_ancora=escaninho_handle,
                seletor_pronto='li.tl-item-container',
                validar_conexao=False,
                validar_url_invalida=_url_invalida,
                recuperar_sessao=_recuperar_sessao,
                fechar_abas_ao_final=True,
                stop_on_critical=False,
            ),
        )

    # BLOCO 3: OUTROS
    logger.info('[MANDADOS_API] Iniciando processamento do resto (%d itens)...', len(itens_outros))

    def _exec_outros(drv, it):
        res = processar_mandado_detalhe(
            drv, numero_processo=it.get('numero'), id_processo=it.get('id'), escaninho_handle=escaninho_handle
        )
        if res == 'PULAR':
            return resultado_ok(pulado=True)
        return resultado_ok() if res else resultado_falha('processar_mandado_detalhe retornou False')

    res_outros = executar_fluxo_lote(
        driver,
        itens_outros,
        FluxoSpec(
            nome='mandado_outros',
            tag_log='[MANDADOS_API]',
            executar=_exec_outros,
            should_skip=create_skip_checker('mandado'),
            open_item_fn=lambda _d, _it: resultado_ok(),
            persist_result=_marcar_se_ok,
            fechar_abas_ao_final=False,
            stop_on_critical=False,
        ),
    )
    stats = res_outros['stats']
    logger.info(
        '[MANDADOS_API] Concluido — total=%d sucesso=%d pulados=%d falha=%d',
        stats['total'], stats['sucesso'], stats['pulados'], stats['falha'],
    )
    if stats['falha']:
        labels = [str(r['item'].get('numero') or r['item'].get('id', '')) for r in stats['itens'] if r['status'] == 'falha']
        logger.warning('[MANDADOS_API] Falhas: %s', labels)
    return True


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


_TERMOS_ARGOS = (
    'pesquisa patrimonial', 'argos', 'devolucao de ordem de pesquisa',
    'devolucao de ordem',
)
_TERMOS_OUTROS = (
    'certidao de oficial de justica', 'certidao de oficial', 'oficial de justica',
    'certidao de devolucao de mandado', 'devolucao de mandado',
)


def _classificar_tipo_timeline_api(client, id_processo):
    """Classifica o processo em 'argos'/'outros' consultando a timeline via API,"""
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
        if any(t in titulo for t in _TERMOS_OUTROS):
            return 'outros'
        if any(t in titulo for t in _TERMOS_ARGOS):
            return 'argos'

    return None


def _selecionar_doc_via_timeline(driver, log=True):
    """Localiza e clica na primeira ocorrencia relevante da timeline (mais recente)."""
    links = espera.elementos(driver, 'li.tl-item-container a.tl-documento:not([target="_blank"])', teto=2)
    for link in links:
        norm = normalizar_texto(link.text or '')

        if any(t in norm for t in _TERMOS_OUTROS):
            tipo = 'outros'
        elif any(t in norm for t in _TERMOS_ARGOS):
            tipo = 'argos'
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
    """Le o span 'align-end' do cabecalho do processo (pje-cabecalho-processo"""
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
            regra, texto_negativo = fluxo_mandados_outros(driver, log=False, com_texto=True)
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
                        ao_meios_texto=texto_negativo or None,
                    )
            return True

        logger.info(f"[MANDADOS_API] Tipo nao mapeado para {id_processo or numero_processo} (nenhum doc relevante na timeline) — pulando")
        return 'PULAR'
    except Exception as e:
        logger.error(f"[MANDADOS_API] Erro ao processar {id_processo or numero_processo}: {e}")
        return False
    finally:
        _fechar_abas_extras(driver, handle_principal)


def retirar_sigilo_demais_documentos_especificos(driver, documentos_sequenciais, log=True):
    """COMPATIBILIDADE: Chama retirar_sigilo_fluxo_argos e retorna lista de demais documentos."""
    resultado = retirar_sigilo_fluxo_argos(driver, documentos_sequenciais, log)
    return resultado.get('demais_documentos', [])


def retirar_sigilo_documentos_especificos(driver, documentos_sequenciais, log=True):
    """FUNCAO EFICIENTE - Remove sigilo APENAS dos documentos especificos fornecidos:"""
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

    if log:

        for doc in documentos_processados:
            status_icon = "" if doc['status'] == 'sucesso' else "" if doc['status'] == 'erro' else ""

    return documentos_processados


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


def _expediente_prazo30_aberto(driver, log: bool = True):
    """Consulta a API de expedientes e diz se há intimação de prazo 30 em aberto."""
    id_processo = None
    try:
        m = re.search(r'/processo/(\d+)', getattr(driver, 'current_url', '') or '')
        id_processo = m.group(1) if m else None
    except Exception:
        pass
    if not id_processo:
        if log:
            logger.info('[INTIMACAO][API] id do processo ausente na URL — usando dialog')
        return None

    try:
        client = _criar_api_client(driver)
    except Exception as e:
        if log:
            logger.info('[INTIMACAO][API] Sem client de API (%s) — usando dialog', str(e)[:60])
        return None

    itens = []
    try:
        for pagina in range(1, 21):
            res = client.gateway_get(
                f'/pje-comum-api/api/processos/id/{id_processo}/expedientes',
                params={'pagina': pagina, 'tamanhoPagina': 50, 'instancia': 1},
                timeout=15,
            )
            if not res.get('ok'):
                if log:
                    logger.info('[INTIMACAO][API] Consulta falhou (%s) — usando dialog',
                                str(res.get('error'))[:80])
                return None
            dados = res.get('data') or {}
            lista = dados.get('resultado') or []
            itens.extend(lista)
            if len(lista) < 50:
                break
    except Exception as e:
        if log:
            logger.info('[INTIMACAO][API] Erro na consulta (%s) — usando dialog', str(e)[:60])
        return None

    abertos_30 = [it for it in itens
                  if str(it.get('prazoLegal')) == '30' and not it.get('fechado')]

    if log:
        logger.info('[INTIMACAO][API] %d expediente(s) consultados; %d com prazo 30 em aberto',
                    len(itens), len(abertos_30))
    return bool(abertos_30)


def fechar_intimacao(driver: Any, log: bool = True) -> bool:
    """Fecha a intimacao do processo."""
    logger.info('[INTIMACAO] === INICIO ===')
    try:
        # A consulta não usa DOM, então evita o trecho mais frágil da função
        tem_30 = _expediente_prazo30_aberto(driver, log=log)
        if tem_30 is False:
            logger.info('[INTIMACAO] [0] Nenhuma intimação de prazo 30 em aberto (API) — nada a fazer')
            return True

        logger.info('[INTIMACAO] [1] Tentando abrir menu #botao-menu...')
        try:
            btn_menu = espera.elemento(driver, '#botao-menu', teto=2, visivel=False)
            if btn_menu is None:
                raise TimeoutError('botao-menu nao encontrado')
            safe_click_no_scroll(driver, btn_menu)
        except Exception:
            logger.info('[INTIMACAO] [1]  FALHOU: Nao conseguiu abrir menu')
            return False
        logger.info('[INTIMACAO] [1]  Menu aberto')

        logger.info('[INTIMACAO] [2] Tentando clicar Expedientes...')
        try:
            btn_exp = espera.elemento(driver, 'button[aria-label="Expedientes"]', teto=3, visivel=False)
            if btn_exp is None:
                raise TimeoutError('botao Expedientes nao encontrado')
            safe_click_no_scroll(driver, btn_exp)
        except Exception:
            logger.info('[INTIMACAO] [2]  FALHOU: Nao conseguiu clicar Expedientes')
            _fechar_modal_esc(driver)
            return False
        logger.info('[INTIMACAO] [2]  Botao Expedientes clicado')

        logger.info('[INTIMACAO] [3] Aguardando modal abrir...')
        espera.elemento(driver, 'tbody tr', teto=5, visivel=False)
        espera.assentar(driver, 1, motivo='[INTIMACAO] tabela de expedientes popular')

        logger.info('[INTIMACAO] [4] Buscando linhas com prazo 30...')
        rows = espera.elementos(driver, 'tbody tr', teto=2)
        logger.info(f'[INTIMACAO] [4] Total de linhas encontradas: {len(rows)}')

        linha_prazo_30 = None

        for i, row in enumerate(rows):
            try:
                cells = espera.elementos(row, 'td', teto=0.5)
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
            _fechar_modal_esc(driver)
            espera.ate_js(driver, "document.readyState === 'complete'", teto=2)
            return True

        logger.info('[INTIMACAO] [5] Tentando marcar checkbox...')
        if not _selecionar_checkbox_intimacao(driver, linha_prazo_30, log=log):
            logger.info('[INTIMACAO] [5]  FALHOU: Nao conseguiu marcar checkbox')
            _fechar_modal_esc(driver)
            espera.ate_js(driver, "document.readyState === 'complete'", teto=2)
            return False
        logger.info('[INTIMACAO] [5]  Checkbox marcado')

        logger.info('[INTIMACAO] [6] Tentando clicar Fechar Expedientes...')
        if not aguardar_e_clicar(driver, 'button[aria-label="Fechar Expedientes"]', timeout=5):
            logger.info('[INTIMACAO] [6]  FALHOU: Nao conseguiu clicar Fechar Expedientes')
            _fechar_modal_esc(driver)
            return False
        logger.info('[INTIMACAO] [6]  Botao Fechar Expedientes clicado')
        aguardar_renderizacao_nativa(driver, '.cdk-overlay-container mat-dialog-container', modo='aparecer', timeout=5)

        logger.info('[INTIMACAO] [7] Confirmando fechamento...')
        btn_sim = None
        try:
            xpath_sim = "//mat-dialog-container//button[.//span[normalize-space(.)='Sim'] or normalize-space(.)='Sim'] | //div[contains(@class,'cdk-overlay-pane')]//button[.//span[normalize-space(.)='Sim'] or normalize-space(.)='Sim'] | //button[.//span[normalize-space(.)='Sim'] or normalize-space(.)='Sim']"
            btn_sim = espera.elemento(driver, xpath_sim, teto=2, visivel=False)
            if btn_sim is None:
                raise TimeoutError('botao Sim nao encontrado')
            safe_click_no_scroll(driver, btn_sim)
        except Exception:
            logger.info('[INTIMACAO] [7]  FALHOU: botao Sim nao encontrado rapidamente')
            return False

        logger.info('[INTIMACAO] [8] Aguardando timeline estabilizar...')
        espera.elemento(driver, 'li.tl-item-container', teto=3, visivel=False)

        logger.info('[INTIMACAO] === SUCESSO ===')

        return True

    except Exception as e:
        logger.info(f'[INTIMACAO] === ERRO GERAL: {str(e)[:150]} ===')
        try:
            _fechar_modal_esc(driver)
        except Exception:
            pass
        return False
