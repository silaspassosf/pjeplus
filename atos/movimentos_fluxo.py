import logging
logger = logging.getLogger(__name__)

from typing import Optional, Any
from Fix.utils import remover_acentos

from .core import *
from Fix.core import (
    aguardar_renderizacao_nativa,
    safe_click,
    safe_click_no_scroll,
    esperar_elemento,
    buscar_seletor_robusto,
)
import Fix.espera as espera


def _obter_abas(driver) -> list:
    """Retorna lista de handles/páginas de forma unificada."""
    context = getattr(driver, 'context', None)
    if context and hasattr(context, 'pages'):
        return list(context.pages)
    handles = getattr(driver, '_handles', None)
    if handles:
        return list(handles.keys())
    return list(getattr(driver, 'window_handles', []))


def _trocar_para_aba(driver, aba) -> None:
    """Troca o foco para a aba especificada (Page do Playwright ou handle)."""
    if hasattr(aba, 'bring_to_front'):
        aba.bring_to_front()
        if hasattr(driver, '_page'):
            driver._page = aba
    elif isinstance(aba, str):
        driver.switch_to.window(aba)


def _trocar_para_aba_detalhe(driver, debug: bool = False) -> bool:
    """Busca e troca para a aba que contém /detalhe na URL."""
    url_atual = getattr(driver, 'current_url', '') or ''
    if '/detalhe' in url_atual:
        return True

    context = getattr(driver, 'context', None)
    if context and hasattr(context, 'pages'):
        for p in context.pages:
            if '/detalhe' in (p.url or ''):
                p.bring_to_front()
                if hasattr(driver, '_page'):
                    driver._page = p
                if debug:
                    logger.debug(f"[MOV] Aba /detalhe encontrada: {p.url}")
                return True

    for h in _obter_abas(driver):
        try:
            _trocar_para_aba(driver, h)
            if '/detalhe' in (getattr(driver, 'current_url', '') or ''):
                if debug:
                    logger.debug(f"[MOV] Aba /detalhe encontrada: {driver.current_url}")
                return True
        except Exception:
            continue

    return False


def _localizar_botao_tarefa(driver: Any, timeout: int = 8):
    """Tentativa robusta de localizar o botão 'Abrir tarefa do processo'."""
    try:
        btn = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=timeout)
        if btn:
            return btn
    except Exception:
        pass

    try:
        textos = ['Abre a tarefa do processo', 'Abrir tarefa', 'tarefa do processo', 'tarefa']
        el = buscar_seletor_robusto(driver, textos, timeout=timeout)
        if el:
            return el
    except Exception:
        pass

    try:
        alt = ["button[mattooltip*='tarefa']", "button[aria-label*='tarefa']", "button[title*='tarefa']"]
        for s in alt:
            try:
                el = espera.elemento(driver, s, teto=1)
                if el and getattr(el, 'is_displayed', lambda: True)():
                    return el
            except Exception:
                continue
    except Exception:
        pass

    return None


def _obter_tarefa_atual_robusta(driver: Any, timeout: int = 6, debug: bool = False) -> Optional[str]:
    """Obtém a tarefa atual pelos mesmos seletores do ato_judicial (sem ler o cabeçalho inteiro)."""
    seletores_tarefa = [
        'pje-cabecalho-tarefa h1.titulo-tarefa',
        'pje-cabecalho-tarefa h1',
        'span.texto-tarefa-processo',
        'mat-card-title',
    ]

    for seletor in seletores_tarefa:
        try:
            for el in espera.elementos(driver, seletor, teto=1):
                texto = (getattr(el, 'text', '') or '').strip()
                if texto:
                    return texto
        except Exception:
            continue

    tarefa_cache = (getattr(driver, 'pje_tarefa_atual', '') or '').strip()
    if tarefa_cache:
        return tarefa_cache

    url_atual = getattr(driver, 'current_url', '') or ''
    if '/tarefa/' in url_atual:
        try:
            titulo = (getattr(driver, 'title', '') or '').strip()
            if titulo:
                return titulo
        except Exception:
            pass
        return 'Tarefa'

    if '/detalhe' in url_atual:
        try:
            tarefa_btn = _localizar_botao_tarefa(driver, timeout=max(2, timeout // 2))
            if tarefa_btn:
                tarefa_texto = ''
                try:
                    span_tarefa = espera.elemento(driver, '.texto-tarefa-processo', teto=1)
                    if span_tarefa and (getattr(span_tarefa, 'text', '') or '').strip():
                        tarefa_texto = span_tarefa.text.strip()
                except Exception:
                    pass

                if not tarefa_texto:
                    tarefa_texto = (getattr(tarefa_btn, 'text', '') or '').strip()

                if tarefa_texto:
                    if debug:
                        logger.info(f'[MOV_INT] Tarefa identificada pelo botão: {tarefa_texto}')

                    try:
                        handle_orig = getattr(driver, 'current_window_handle', None)
                        if safe_click_no_scroll(driver, tarefa_btn, log=debug):
                            try:
                                from Fix.browser_suporte import aguardar_nova_aba
                                if handle_orig:
                                    nova_aba = aguardar_nova_aba(driver, handle_orig, timeout=4)
                                    if nova_aba:
                                        driver.switch_to.window(nova_aba)
                            except Exception:
                                pass

                            for seletor_fallback in ['pje-cabecalho-tarefa h1.titulo-tarefa', 'span.texto-tarefa-processo', 'mat-card-title', 'h1']:
                                try:
                                    for el in espera.elementos(driver, seletor_fallback, teto=1):
                                        texto = (getattr(el, 'text', '') or '').strip()
                                        if texto:
                                            return texto
                                except Exception:
                                    continue
                    except Exception:
                        pass

                    return tarefa_texto
        except Exception:
            pass

    return None


def mov_simples(
    driver: Any,
    seletor_alvo: str,
    texto_confirmacao: Optional[str] = None,
    debug: bool = False,
    timeout: int = 15
) -> bool:
    """Versão SIMPLIFICADA do movimento - apenas uma tentativa:"""
    def log_debug(msg):
        if debug:
            try:
                logger.debug(msg)
            except Exception:
                pass

    try:
        log_debug("Buscando aba /detalhe...")
        if '/processo/' not in (getattr(driver, 'current_url', '') or ''):
            _trocar_para_aba_detalhe(driver, debug=debug)

        if not texto_confirmacao:
            from .judicial_api import cls_api_habilitada, extrair_destino_de_seletor, transitar_tarefa_api
            destino_api = extrair_destino_de_seletor(seletor_alvo)
            if destino_api and cls_api_habilitada():
                res_api = transitar_tarefa_api(driver, destino_api, abrir_url=True)
                if res_api:
                    return res_api.get('_status_api') != 'bloqueado_regra'

        if not _trocar_para_aba_detalhe(driver, debug=debug):
            logger.error('[MOV_SIMPLES][ERRO] Aba /detalhe não encontrada!')
            return False

        log_debug("Procurando botão 'Abrir tarefa do processo'...")
        btn_abrir_tarefa = _localizar_botao_tarefa(driver, timeout=max(2, timeout//2))
        if not btn_abrir_tarefa:
            logger.error(f'[MOV_SIMPLES][ERRO] Botão "Abrir tarefa do processo" não encontrado!')
            return False

        tarefa_do_botao = None
        try:
            span_tarefa = espera.elemento(driver, '.texto-tarefa-processo', teto=1)
            if span_tarefa and (getattr(span_tarefa, 'text', '') or '').strip():
                tarefa_do_botao = span_tarefa.text.strip()
                log_debug(f"Tarefa identificada: '{tarefa_do_botao}'")
        except Exception:
            pass

        if not tarefa_do_botao:
            try:
                tarefa_do_botao = (getattr(btn_abrir_tarefa, 'text', '') or '').strip()
                log_debug(f"Tarefa identificada (texto completo): '{tarefa_do_botao}'")
            except Exception:
                log_debug("Não foi possível capturar nome da tarefa")

        handle_orig = getattr(driver, 'current_window_handle', None)
        click_resultado = safe_click_no_scroll(driver, btn_abrir_tarefa, log=debug)

        if not click_resultado:
            logger.error(f'[MOV_SIMPLES][ERRO] Falha no clique do botão da tarefa')
            return False

        nova_aba = None
        try:
            from Fix.browser_suporte import aguardar_nova_aba
            if handle_orig:
                nova_aba = aguardar_nova_aba(driver, handle_orig, timeout=6)
        except Exception:
            pass

        if nova_aba:
            driver.switch_to.window(nova_aba)
            log_debug("Foco trocado para nova aba da tarefa")
        else:
            log_debug("Nenhuma nova aba detectada, prosseguindo na aba atual")

        log_debug(f"Procurando botão alvo: {seletor_alvo}")
        btn_alvo = espera.elemento(driver, seletor_alvo, teto=timeout//2)
        if btn_alvo:
            safe_click(driver, btn_alvo)
        else:
            logger.error(f'[MOV_SIMPLES][ERRO] Botão alvo não encontrado: {seletor_alvo}')
            return False

        if texto_confirmacao:
            try:
                xpath_confirma = f"//button[contains(., '{texto_confirmacao}') or .//span[contains(., '{texto_confirmacao}')]]"
                btn_confirma = espera.elemento(driver, xpath_confirma, teto=timeout//2)
                if btn_confirma:
                    safe_click(driver, btn_confirma)
                else:
                    logger.error(f'[MOV_SIMPLES][ERRO] Não foi possível clicar no botão de confirmação "{texto_confirmacao}"')
                    return False
            except Exception as e:
                logger.error(f'[MOV_SIMPLES][ERRO] Não foi possível clicar no botão de confirmação "{texto_confirmacao}": {e}')
                return False

        return True

    except Exception as e:
        logger.error(f'[MOV_SIMPLES][ERRO] Falha geral no movimento simples: {e}')
        return False


def mov(
    driver: Any,
    seletor_alvo: str,
    texto_confirmacao: Optional[str] = None,
    debug: bool = False,
    timeout: int = 15
) -> bool:
    """Fluxo geral MELHORADO para movimentos:"""
    logger.info(f'[MOV] Iniciando movimento geral - Seletor: {seletor_alvo}')

    if not texto_confirmacao:
        try:
            if '/processo/' not in (getattr(driver, 'current_url', '') or ''):
                _trocar_para_aba_detalhe(driver, debug=debug)
            from .judicial_api import cls_api_habilitada, extrair_destino_de_seletor, transitar_tarefa_api
            destino_api = extrair_destino_de_seletor(seletor_alvo)
            if destino_api and cls_api_habilitada():
                res_api = transitar_tarefa_api(driver, destino_api, abrir_url=True)
                if res_api:
                    return res_api.get('_status_api') != 'bloqueado_regra'
        except Exception as e:
            logger.warning(f'[MOV] Fallback DOM após exceção na via API: {e}')

    def log_debug(msg):
        if debug:
            try:
                logger.debug(msg)
            except Exception:
                pass

    def tentar_encontrar_alvo():
        """Tenta encontrar o botão alvo, com fallback para Análise"""
        try:
            btn_alvo = espera.elemento(driver, seletor_alvo, teto=timeout//3)
            if btn_alvo:
                safe_click(driver, btn_alvo)
                return True
        except Exception:
            pass

        if seletor_alvo == "button[aria-label='Aguardando prazo']":
            try:
                elementos_analise = espera.elementos(driver, "//*[contains(translate(text(), 'ANÁLISE', 'análise'), 'análise')]", teto=1)
                em_analise = any('análise' in (getattr(el, 'text', '') or '').lower() for el in elementos_analise if getattr(el, 'is_displayed', lambda: True)())
                if em_analise:
                    log_debug("Já está em 'Análise' e botão 'Aguardando prazo' não disponível - está correto")
                    return True
            except Exception:
                pass

        log_debug("Botão alvo não encontrado. Tentando clicar em 'Análise'...")
        btn_analise = None

        btns_analise = espera.elementos(driver, "//button[contains(translate(normalize-space(text()), 'ANÁLISE', 'análise'), 'análise')]", teto=2)
        for btn in btns_analise:
            if getattr(btn, 'is_displayed', lambda: True)() and getattr(btn, 'is_enabled', lambda: True)():
                btn_analise = btn
                break

        if not btn_analise:
            btns_analise = espera.elementos(driver, "button[aria-label*='Análise']", teto=2)
            for btn in btns_analise:
                if getattr(btn, 'is_displayed', lambda: True)() and getattr(btn, 'is_enabled', lambda: True)():
                    btn_analise = btn
                    break

        if btn_analise:
            safe_click(driver, btn_analise)
            try:
                aguardar_renderizacao_nativa(driver, 'pje-botoes-transicao', modo='aparecer', timeout=8)
            except Exception:
                pass

            try:
                btn_alvo = espera.elemento(driver, seletor_alvo, teto=timeout//3)
                if btn_alvo:
                    safe_click(driver, btn_alvo)
                    return True
            except Exception:
                pass
            log_debug("Botão alvo não encontrado mesmo após 'Análise'")
            return False
        else:
            log_debug("Botão 'Análise' não encontrado")
            return False

    for tentativa in range(1, 3):
        try:
            if not _trocar_para_aba_detalhe(driver, debug=debug):
                logger.error(f'[MOV][ERRO] Tentativa {tentativa}: Não foi possível encontrar aba /detalhe')
                if tentativa == 2:
                    return False
                continue

            log_debug("Procurando botão 'Abrir tarefa do processo'...")
            btn_abrir_tarefa = _localizar_botao_tarefa(driver, timeout=max(2, timeout//2))
            if not btn_abrir_tarefa:
                logger.error(f'[MOV][ERRO] Tentativa {tentativa}: Botão "Abrir tarefa do processo" não encontrado!')
                if tentativa == 2:
                    return False
                continue

            tarefa_do_botao = None
            try:
                span_tarefa = espera.elemento(driver, '.texto-tarefa-processo', teto=1)
                if span_tarefa and (getattr(span_tarefa, 'text', '') or '').strip():
                    tarefa_do_botao = span_tarefa.text.strip()
                    log_debug(f"Tarefa identificada: '{tarefa_do_botao}'")
            except Exception:
                pass

            if not tarefa_do_botao:
                try:
                    tarefa_do_botao = (getattr(btn_abrir_tarefa, 'text', '') or '').strip()
                    log_debug(f"Tarefa identificada (texto completo): '{tarefa_do_botao}'")
                except Exception:
                    log_debug("Não foi possível capturar nome da tarefa")

            handle_orig = getattr(driver, 'current_window_handle', None)
            click_resultado = safe_click_no_scroll(driver, btn_abrir_tarefa, log=debug)

            if not click_resultado:
                logger.error(f'[MOV][ERRO] Tentativa {tentativa}: Falha no clique do botão da tarefa')
                if tentativa == 2:
                    return False
                continue

            nova_aba = None
            try:
                from Fix.browser_suporte import aguardar_nova_aba
                if handle_orig:
                    nova_aba = aguardar_nova_aba(driver, handle_orig, timeout=6)
            except Exception:
                pass

            if nova_aba:
                driver.switch_to.window(nova_aba)
                log_debug("Foco trocado para nova aba da tarefa")
            else:
                log_debug("Nenhuma nova aba detectada, prosseguindo na aba atual")

            if tentar_encontrar_alvo():
                if texto_confirmacao:
                    try:
                        xpath_confirma = f"//button[contains(., '{texto_confirmacao}') or .//span[contains(., '{texto_confirmacao}')]]"
                        btn_confirma = espera.elemento(driver, xpath_confirma, teto=timeout//2)
                        if btn_confirma:
                            safe_click(driver, btn_confirma)
                        else:
                            logger.error(f'[MOV][ERRO] Botão de confirmação "{texto_confirmacao}" não encontrado')
                            return False
                    except Exception as e:
                        logger.error(f'[MOV][ERRO] Não foi possível clicar no botão de confirmação "{texto_confirmacao}": {e}')
                        return False

                return True
            else:
                logger.warning(f'[MOV][WARN] Tentativa {tentativa}: Não foi possível encontrar o alvo, tentando novamente...')
                if tentativa == 2:
                    logger.error('[MOV][ERRO] Esgotadas todas as tentativas')
                    return False
                try:
                    abas = _obter_abas(driver)
                    if nova_aba and nova_aba in abas:
                        try:
                            driver.close()
                        except Exception:
                            pass
                        abas_restantes = _obter_abas(driver)
                        if abas_restantes:
                            _trocar_para_aba(driver, abas_restantes[0])
                except Exception:
                    pass
                continue

        except Exception as e:
            logger.error(f'[MOV][ERRO] Tentativa {tentativa}: Falha no fluxo de movimento: {e}')
            if tentativa == 2:
                return False
            continue

    return False


def _remover_acentos(texto: str) -> str:
    if not texto:
        return ''
    return remover_acentos(texto)


def _localizar_botao_destino_movimento(driver: Any, destino: str, timeout: int = 8):
    """Localiza o botão de destino alinhado ao gigs-plugin/mini-selenium:"""
    destino_lower = (destino or '').strip().lower()
    if not destino_lower:
        return None

    destino_normalizado = _remover_acentos(destino_lower)

    def _texto_normalizado(texto: str) -> str:
        import re as _re
        texto = _remover_acentos((texto or '').strip().lower())
        return _re.sub(r'[\r\n\t]+', ' ', texto)

    def _match(el) -> bool:
        try:
            texto = _texto_normalizado((getattr(el, 'text_content', None) and el.text_content()) or getattr(el, 'text', '') or '')
            aria = _texto_normalizado(el.get_attribute('aria-label') or el.get_attribute('title') or '')
            return (destino_normalizado in texto or destino_normalizado in aria) and getattr(el, 'is_displayed', lambda: True)() and not el.get_attribute('disabled')
        except Exception:
            return False

    try:
        for el in espera.elementos(driver, 'pje-botoes-transicao button', teto=min(1.5, timeout)):
            if _match(el):
                return el
    except Exception:
        pass

    try:
        for el in espera.elementos(driver, 'button, input[type="button"]', teto=min(1.5, timeout)):
            if _match(el):
                return el
    except Exception:
        pass

    return None


def _consultar_tarefa_recente_api(driver: Any, id_processo: str) -> Optional[tuple]:
    """Consulta (id_tarefa, nome_tarefa) via API com cache curto (5s) para evitar GET duplicado."""
    import time as _time
    from Fix.variaveis import session_from_driver

    cache = getattr(driver, '_pje_cache_tarefa_api', None)
    if (
        isinstance(cache, tuple)
        and len(cache) == 4
        and cache[0] == id_processo
        and (_time.monotonic() - cache[3]) < 5.0
    ):
        return cache[1], cache[2]

    sess, host = session_from_driver(driver)
    endpoint = f"https://{host}/pje-comum-api/api/processos/id/{id_processo}/tarefas?maisRecente=true"
    r = sess.get(endpoint, timeout=10)
    r.raise_for_status()
    dados = r.json()

    registro = dados[0] if (isinstance(dados, list) and dados) else (dados if isinstance(dados, dict) else None)
    if not isinstance(registro, dict):
        return None

    id_tarefa = registro.get('idTarefa') or registro.get('id')
    nome_tarefa = ''
    for campo in ('nomeTarefa', 'nome', 'tarefa', 'descricao', 'titulo'):
        val = registro.get(campo)
        if isinstance(val, str) and val.strip():
            nome_tarefa = val.strip()
            break

    try:
        driver._pje_cache_tarefa_api = (id_processo, id_tarefa, nome_tarefa, _time.monotonic())
    except Exception:
        pass
    return id_tarefa, nome_tarefa


def abrir_tarefa_por_api(driver: Any, timeout: int = 10) -> bool:
    """Abre a tarefa mais recente do processo via API REST (padrão gigs-plugin)."""
    import re as _re

    try:
        url_atual = driver.current_url or ''
        if '/tarefa' in url_atual:
            return True
        if '/processo/' not in url_atual:
            return False

        m = _re.search(r'/processo/(\d+)', url_atual)
        if not m:
            return False
        id_processo = m.group(1)
        base = url_atual.split('/pjekz/')[0]

        try:
            res_api = _consultar_tarefa_recente_api(driver, id_processo)
        except Exception as e:
            logger.warning(f'[API_TAREFA] Consulta API falhou para processo {id_processo}: {e}')
            return False

        if not res_api or not res_api[0]:
            logger.warning(f'[API_TAREFA] idTarefa não encontrado na resposta para processo {id_processo}')
            return False

        id_tarefa, nome_tarefa_api = res_api

        url_tarefa = f"{base}/pjekz/processo/{id_processo}/tarefa/{id_tarefa}"
        try:
            driver.pje_tarefa_atual = nome_tarefa_api
            driver.pje_tarefa_pronta = None
        except Exception:
            pass
        try:
            driver.get(url_tarefa)
        except Exception as e:
            logger.error(f'[API_TAREFA] Erro ao navegar para tarefa: {e}')
            return False

        try:
            from Fix.core import garantir_carregamento_pagina
            garantir_carregamento_pagina(
                driver,
                seletor_esperado='pje-cabecalho-tarefa h1.titulo-tarefa, pje-cabecalho-tarefa h1, nav.container-botoes button, pje-botoes-transicao button',
                timeout_refresh=10.0,
                url_alvo=url_tarefa,
            )
        except Exception:
            pass

        logger.info(f'[API_TAREFA] Tarefa aberta via API com sucesso: processo={id_processo} tarefa={id_tarefa}')
        return True

    except Exception as e:
        logger.error(f'[API_TAREFA] Falha ao abrir tarefa via API: {e}', exc_info=True)
        return False


def _tarefa_atual_via_api(driver: Any) -> Optional[str]:
    """Nome da tarefa mais recente do processo via API, SEM navegar o browser."""
    import re as _re

    try:
        url_atual = driver.current_url or ''
        if '/tarefa' in url_atual or '/processo/' not in url_atual:
            return None
        m = _re.search(r'/processo/(\d+)', url_atual)
        if not m:
            return None
        res_api = _consultar_tarefa_recente_api(driver, m.group(1))
        if res_api and res_api[1]:
            return res_api[1]
        return None
    except Exception:
        return None


def movimentar_inteligente(driver: Any, destino: str, ultimo_lance: str = '', chip: Optional[str] = None, responsavel: Optional[str] = None, timeout: int = 15, profundidade: int = 0, pular_abertura_api: bool = False) -> bool:
    """Movimentação inteligente de processos baseada na máquina de estados do gigs-plugin.js (acao_bt_aaMovimento)."""
    if profundidade >= 3:
        logger.error(f'[MOV_INT] Limite de {profundidade} navegacoes atingido sem conseguir "{destino}" — abortando')
        return False

    try:
        from .movimentos_navegacao import clicar_botao_por_texto, movimentar_analise, navegar_para_tarefa
        from .judicial_api import cls_api_habilitada, transitar_tarefa_api

        # Via primária 100% API REST (sem cliques em botões de transição); fallback para DOM abaixo.
        if '?' not in (destino or '') and cls_api_habilitada():
            precisa_tela = bool(ultimo_lance or chip or responsavel)
            try:
                res_mov_api = transitar_tarefa_api(driver, destino, abrir_url=True)
            except Exception as e:
                logger.warning(f'[MOV_INT] Exceção na via API — seguindo pelo DOM: {e}')
                res_mov_api = None

            if res_mov_api:
                status_api = res_mov_api.get('_status_api')
                if status_api == 'bloqueado_regra':
                    return False
                if status_api in ('transitada', 'ja_no_destino', 'prazo_ja_em_analise'):
                    if precisa_tela and status_api != 'prazo_ja_em_analise':
                        if ultimo_lance:
                            try:
                                clicar_ultimo_lance(driver, ultimo_lance)
                            except Exception:
                                pass
                        if chip or responsavel:
                            try:
                                chip_responsavel(driver, chip=chip, responsavel=responsavel)
                            except Exception:
                                pass
                    return True

        if '?' not in (destino or ''):
            tarefa_api = _tarefa_atual_via_api(driver)
            if tarefa_api:
                destino_pre = _remover_acentos((destino or '').lower())
                if destino_pre and destino_pre in _remover_acentos(tarefa_api.lower()):
                    logger.info(f"[MOV_INT] tarefa já está em '{tarefa_api}' (via API) — nada a fazer")
                    return True

        if not pular_abertura_api:
            abrir_tarefa_por_api(driver, timeout=timeout)

        tarefa_text = _obter_tarefa_atual_robusta(driver, timeout=max(3, timeout // 2), debug=True)
        if not tarefa_text:
            if navegar_para_tarefa(driver, 'análise', debug=True, timeout=timeout):
                tarefa_text = _obter_tarefa_atual_robusta(driver, timeout=max(3, timeout // 2), debug=True)

        if not tarefa_text:
            logger.warning('[MOV_INT] Não foi possível determinar tarefa atual — abortando')
            return False

        tarefa_norm = _remover_acentos((tarefa_text or '').lower())
        destino_norm = _remover_acentos((destino or '').lower())
        if '?' in destino:
            destino_norm = destino_norm.replace('?', '') + ' ' + tarefa_norm

        logger.info(f"[MOV_INT] tarefa='{tarefa_text}' destino='{destino}'")

        if destino_norm and destino_norm in tarefa_norm:
            logger.info("[MOV_INT] Processo já se encontra na tarefa de destino.")
            if ultimo_lance:
                try:
                    clicar_ultimo_lance(driver, ultimo_lance)
                except Exception:
                    pass
            if chip or responsavel:
                try:
                    chip_responsavel(driver, chip=chip, responsavel=responsavel)
                except Exception:
                    pass
            return True

        if 'elaborar' in tarefa_norm or 'assinar' in tarefa_norm:
            logger.warning('[MOV_INT] Processo em tarefa de elaborar/assinar — movimento cancelado para evitar perda de minuta')
            return False

        if 'controle de acordo' in tarefa_norm:
            logger.warning('[MOV_INT] Processo em controle de acordo — requer movimentação manual')
            return False

        aguardar_renderizacao_nativa(
            driver,
            'nav.container-botoes button, pje-botoes-transicao button',
            modo='aparecer',
            timeout=min(10, timeout),
        )

        if 'analise' in tarefa_norm:
            if clicar_botao_por_texto(driver, destino, debug=True):
                logger.info(f'[MOV_INT] Botão destino "{destino}" clicado na tarefa Análise!')
                if ultimo_lance:
                    try:
                        clicar_ultimo_lance(driver, ultimo_lance)
                    except Exception:
                        pass
                if chip or responsavel:
                    try:
                        chip_responsavel(driver, chip=chip, responsavel=responsavel)
                    except Exception:
                        pass
                return True

            if 'aguardando prazo' in destino_norm or 'prazo' in destino_norm:
                logger.info("[MOV_INT] Já está em 'Análise' e botão 'Aguardando prazo' não disponível — conforme LEGADO L4869, está correto.")
                return True

            logger.warning(f'[MOV_INT] Botão destino "{destino}" não encontrado na tarefa Análise')
            return False

        # 'Cumprimento de Providências' e 'Prazos Vencidos' (quando destino não é Conclusão/Análise)
        # exigem passar por Análise antes — evita polling inútil procurando destino direto.
        exige_analise = (
            'cumprimento de providencias' in tarefa_norm
            or (
                'prazos vencidos' in tarefa_norm
                and 'conclusao' not in destino_norm
                and 'analise' not in destino_norm
            )
        )
        # Os botões de transição já foram renderizados acima; checagem direta rápida (0.3s).
        if not exige_analise and clicar_botao_por_texto(driver, destino, timeout=0.3, debug=True):
            logger.info(f'[MOV_INT] Botão destino "{destino}" clicado diretamente na tarefa atual!')
            if ultimo_lance:
                try:
                    clicar_ultimo_lance(driver, ultimo_lance)
                except Exception:
                    pass
            if chip or responsavel:
                try:
                    chip_responsavel(driver, chip=chip, responsavel=responsavel)
                except Exception:
                    pass
            return True

        logger.info(f'[MOV_INT] Transicionando de "{tarefa_text}" para Análise...')
        if movimentar_analise(driver, tarefa_text, debug=True):
            try:
                driver.pje_tarefa_atual = ''
            except Exception:
                pass
            if 'analise' in destino_norm:
                if ultimo_lance:
                    try:
                        clicar_ultimo_lance(driver, ultimo_lance)
                    except Exception:
                        pass
                if chip or responsavel:
                    try:
                        chip_responsavel(driver, chip=chip, responsavel=responsavel)
                    except Exception:
                        pass
                return True

            # Alinhado a navegar_para_tarefa (fluxo_cls): após clicar em Análise,
            # aguarda diretamente o botão de destino aparecer (sem sleep fixo nem reler h1 antigo).
            if clicar_botao_por_texto(driver, destino, timeout=max(5, timeout), debug=True):
                logger.info(f'[MOV_INT] Botão destino "{destino}" clicado após Análise!')
                if ultimo_lance:
                    try:
                        clicar_ultimo_lance(driver, ultimo_lance)
                    except Exception:
                        pass
                if chip or responsavel:
                    try:
                        chip_responsavel(driver, chip=chip, responsavel=responsavel)
                    except Exception:
                        pass
                return True

            if 'aguardando prazo' in destino_norm or 'prazo' in destino_norm:
                logger.info("[MOV_INT] Transicionou para Análise e botão 'Aguardando prazo' não disponível — conforme LEGADO L4869, está correto.")
                return True

            logger.warning(f'[MOV_INT] Botão destino "{destino}" não encontrado após transição para Análise')
            return False

        if navegar_para_tarefa(driver, 'análise', debug=True, timeout=timeout, tarefa_atual_conhecida=tarefa_text):
            try:
                driver.pje_tarefa_atual = ''
            except Exception:
                pass
            if clicar_botao_por_texto(driver, destino, timeout=max(5, timeout), debug=True):
                logger.info(f'[MOV_INT] Botão destino "{destino}" clicado após navegar_para_tarefa!')
                if ultimo_lance:
                    try:
                        clicar_ultimo_lance(driver, ultimo_lance)
                    except Exception:
                        pass
                if chip or responsavel:
                    try:
                        chip_responsavel(driver, chip=chip, responsavel=responsavel)
                    except Exception:
                        pass
                return True
            if 'aguardando prazo' in destino_norm or 'prazo' in destino_norm:
                return True
            return False

        logger.warning(f'[MOV_INT] Não foi possível transicionar para Análise a partir de "{tarefa_text}"')
        return False

    except Exception as e:
        logger.error(f'[MOV_INT][ERRO] {e}')
        return False


def clicar_ultimo_lance(driver: Any, texto_ultimo_lance: str, timeout: int = 5) -> bool:
    """Tenta clicar no último lance indicado pelo texto."""
    try:
        if not texto_ultimo_lance:
            return False
        btn = None
        try:
            btn = esperar_elemento(driver, 'button', texto=texto_ultimo_lance, timeout=max(2, timeout//2))
        except Exception:
            btn = None

        if not btn:
            try:
                btns = espera.elementos(driver, f"//button[contains(., '{texto_ultimo_lance}')]", teto=max(2, timeout//2))
                for b in btns:
                    try:
                        if getattr(b, 'is_displayed', lambda: True)() and getattr(b, 'is_enabled', lambda: True)():
                            btn = b
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        if btn:
            try:
                safe_click_no_scroll(driver, btn)
                return True
            except Exception:
                return False
        return False
    except Exception:
        return False


def chip_responsavel(driver, chip: Optional[str] = None, responsavel: Optional[str] = None, timeout: int = 5) -> None:
    """Clica no chip (se solicitado) e tenta abrir seleção de responsável (GIGS) se solicitado."""
    try:
        if chip:
            try:
                el = esperar_elemento(driver, 'button[aria-label="Incluir Chip Amarelo"]', timeout=max(1, timeout//2))
                if el:
                    safe_click_no_scroll(driver, el)
            except Exception:
                pass

        if responsavel:
            try:
                gg = buscar_seletor_robusto(driver, ['Abrir o GIGS', 'GIGS'], timeout=max(1, timeout//2))
                if gg:
                    safe_click_no_scroll(driver, gg)
            except Exception:
                pass
    except Exception:
        pass
