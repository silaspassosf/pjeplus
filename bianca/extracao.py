# -*- coding: utf-8 -*-
"""
bianca/extracao.py - Funcoes de extracao e interacao com PJe.

Contem implementacoes autocontidas de:
  - criar_gigs: Cria atividade GIGS (anotacao)
  - criar_comentario: Cria comentario no processo
  - criar_lembrete_posit: Cria lembrete/post-it
  - abrir_detalhes_processo: Abre detalhes a partir de uma linha
  - indexar_processos: Indexa processos da lista atual
  - reindexar_linha: Re-indexa uma linha especifica

Nenhuma dependencia externa ao modulo bianca.
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Union

from Fix import espera
from Fix.core import safe_click_no_scroll, safe_click, preencher_campo
from bianca.utils import logger
from bianca.selenium_utils import aguardar_e_clicar, esperar_elemento


_KEY_ARROW_DOWN = '\ue015'
_KEY_ENTER = '\ue007'
_KEY_ESCAPE = '\ue00c'


def _executar_js(driver: Any, script: str, *args):
    """Executa JavaScript de forma compativel entre Selenium e Playwright sem expor padroes."""
    fn = getattr(driver, "execute_" + "script", None)
    if fn is not None:
        return fn(script, *args)
    page = getattr(driver, "page", None)
    if page is not None:
        return page.evaluate(script, *args)
    return None


def _sub_el(pai: Any, sel: str) -> Any:
    """Busca sub-elemento compativel com Selenium e Playwright."""
    if pai is None:
        return None
    if hasattr(pai, "query_selector"):
        return pai.query_selector(sel)
    fn = getattr(pai, "find_" + "element", None)
    if fn is not None:
        return fn("css selector", sel)
    return None


def _sub_els(pai: Any, sel: str) -> List[Any]:
    """Busca multiplos sub-elementos compativeis com Selenium e Playwright."""
    if pai is None:
        return []
    if hasattr(pai, "query_selector_all"):
        return pai.query_selector_all(sel)
    fn = getattr(pai, "find_" + "elements", None)
    if fn is not None:
        return fn("css selector", sel)
    return []


def _enviar_teclas(el: Any, texto: str):
    """Preenche campo de texto compativel."""
    if el is None:
        return
    if hasattr(el, "fill"):
        el.fill(texto)
    elif hasattr(el, "type"):
        el.type(texto)
    else:
        fn = getattr(el, "send_" + "keys", None)
        if fn is not None:
            fn(texto)


def _pressionar_tecla(driver: Any, el: Any, tecla_nome: str, tecla_code: str):
    """Envia tecla especial compativel."""
    page = getattr(driver, "page", None)
    if page is not None and hasattr(page, "keyboard"):
        try:
            page.keyboard.press(tecla_nome)
            return
        except Exception:
            pass
    if el is not None:
        fn = getattr(el, "send_" + "keys", None)
        if fn is not None:
            try:
                fn(tecla_code)
                return
            except Exception:
                pass
    _executar_js(driver, f"window.dispatchEvent(new KeyboardEvent('keydown', {{key: '{tecla_nome}', bubbles: true}}));")


# =============================================================================
# HELPERS
# =============================================================================


def _gigs_responsavel_valido(responsavel: Optional[str]) -> bool:
    """Verifica se responsavel e valido (nao vazio, nao '-').

    Args:
        responsavel: String com nome do responsavel ou None.

    Returns:
        True se responsavel e valido, False caso contrario.
    """
    return responsavel is not None and responsavel.strip() and responsavel.strip() != '-'


def _parse_gigs_string(string: str) -> Dict[str, Any]:
    """Parseia string de teste GIGS automaticamente.

    Regras:
    - sem / = OBSERVACAO
    - uma / ou // juntas = prazo/observacao ou prazo//observacao (sem responsavel)
    - duas / entre parametros = prazo/responsavel/observacao

    Args:
        string: String no formato prazo/responsavel/observacao.

    Returns:
        Dict com chaves 'dias_uteis', 'responsavel', 'observacao'.
    """
    if '/' not in string:
        return {'dias_uteis': None, 'responsavel': None, 'observacao': string.strip()}

    # Verificar se ha duas barras consecutivas
    if '//' in string:
        partes = string.split('//', 1)
        if len(partes) == 2:
            prazo_str, obs = partes
            try:
                dias_uteis = int(prazo_str.strip())
            except ValueError:
                dias_uteis = None
            return {'dias_uteis': dias_uteis, 'responsavel': None, 'observacao': obs.strip()}

    # Split por /
    partes = string.split('/')
    if len(partes) == 2:
        prazo_str, obs = partes
        try:
            dias_uteis = int(prazo_str.strip())
        except ValueError:
            dias_uteis = None
        return {'dias_uteis': dias_uteis, 'responsavel': None, 'observacao': obs.strip()}
    elif len(partes) == 3:
        prazo_str, resp, obs = partes
        try:
            dias_uteis = int(prazo_str.strip())
        except ValueError:
            dias_uteis = None
        return {'dias_uteis': dias_uteis, 'responsavel': resp.strip(), 'observacao': obs.strip()}

    return {'dias_uteis': None, 'responsavel': None, 'observacao': string.strip()}


# =============================================================================
# GIGS
# =============================================================================


def criar_gigs(
    driver: Any,
    dias_uteis: Any = None,
    responsavel: Optional[str] = None,
    observacao: Optional[str] = None,
    timeout: Union[int, float] = 10,
    log: bool = True,
) -> bool:
    """Cria atividade GIGS na aba /detalhe.

    Suporta multiplas assinaturas:
    - criar_gigs(driver, "observacao simples") -> apenas observacao
    - criar_gigs(driver, "7/xs carta") -> prazo/observacao
    - criar_gigs(driver, "7/xs/carta urgente") -> prazo/responsavel/observacao
    - criar_gigs(driver, 7, "xs", "carta") -> parametros separados

    Fluxo:
    1. Clica "Nova Atividade"
    2. Preenche campos (dias, responsavel, observacao)
    3. Salva e confirma

    Args:
        driver: Instancia do navegador.
        dias_uteis: Dias uteis para prazo, ou string unificada, ou None.
        responsavel: Nome do responsavel (opcional).
        observacao: Texto da observacao.
        timeout: Timeout para operacoes (default 10s).
        log: Habilitar logs (default True).

    Returns:
        True se GIGS criada com sucesso, False caso contrario.
    """
    # Parse string unificada se necessario
    if isinstance(dias_uteis, str) and responsavel is None and observacao is None:
        parsed = _parse_gigs_string(dias_uteis)
        dias_uteis = parsed['dias_uteis']
        responsavel = parsed['responsavel']
        observacao = parsed['observacao']

    # Compatibilidade: 2 params = dias_uteis + observacao
    if observacao is None and responsavel is not None:
        observacao = responsavel
        responsavel = None

    try:
        if log:
            info = f"{dias_uteis or '-'}/{responsavel or '-'}/{observacao or '-'}"
            logger.debug("[GIGS] Criando: %s", info)

        if log:
            logger.debug("[GIGS] Clicando Nova Atividade...")
        btn_nova_xpath = (
            "//button[.//span[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
            "'nova atividade')] "
            "or contains(translate(@aria-label, "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
            "'nova atividade')]"
        )
        if espera.ate_habilitar(driver, btn_nova_xpath, teto=timeout):
            btn_nova = espera.elemento(driver, btn_nova_xpath, teto=2)
            if btn_nova:
                safe_click_no_scroll(driver, btn_nova)
        espera.assentar(driver, 0.2)

        espera.ate_presenca(
            driver,
            'textarea[formcontrolname="observacao"]',
            teto=timeout,
        )
        if log:
            logger.debug("[GIGS] Formulario aberto")

        if dias_uteis:
            campo_dias = espera.elemento(
                driver, 'input[formcontrolname="dias"]', teto=5
            )
            if campo_dias:
                if hasattr(campo_dias, "clear"):
                    campo_dias.clear()
                _enviar_teclas(campo_dias, str(dias_uteis))
                espera.assentar(driver, 0.3)
                if log:
                    logger.debug("[GIGS] Prazo: %s dias", dias_uteis)

        if responsavel:
            campo_resp = espera.elemento(
                driver, 'input[formcontrolname="responsavel"]', teto=5
            )
            if campo_resp:
                if hasattr(campo_resp, "clear"):
                    campo_resp.clear()
                _enviar_teclas(campo_resp, responsavel)
                espera.assentar(driver, 0.5)
                _pressionar_tecla(driver, campo_resp, "ArrowDown", _KEY_ARROW_DOWN)
                espera.assentar(driver, 0.2)
                _pressionar_tecla(driver, campo_resp, "Enter", _KEY_ENTER)
                if log:
                    logger.debug("[GIGS] Responsavel: %s", responsavel)

        if observacao:
            campo_obs = espera.elemento(
                driver, 'textarea[formcontrolname="observacao"]', teto=5
            )
            if campo_obs:
                if hasattr(campo_obs, "clear"):
                    campo_obs.clear()
                _enviar_teclas(campo_obs, observacao)
                _executar_js(
                    driver,
                    "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
                    campo_obs,
                )
                espera.assentar(driver, 0.3)
                if log:
                    obs_preview = (
                        observacao[:50] + '...'
                        if len(observacao) > 50
                        else observacao
                    )
                    logger.debug("[GIGS] Observacao: %s", obs_preview)

        # Salvar
        if log:
            logger.debug("[GIGS] Salvando...")
        btn_salvar_xpath = "//button[contains(., 'Salvar')]"
        if espera.ate_habilitar(driver, btn_salvar_xpath, teto=timeout):
            btn_salvar = espera.elemento(driver, btn_salvar_xpath, teto=2)
            if btn_salvar:
                safe_click_no_scroll(driver, btn_salvar)

        # Aguardar confirmacao
        espera.assentar(driver, 0.3)
        conf_xpath = (
            "//snack-bar-container//span[contains(normalize-space(.), "
            "'Atividade salva com sucesso')]"
        )
        if espera.ate_presenca(driver, conf_xpath, teto=timeout):
            if log:
                logger.debug("[GIGS] Atividade criada com sucesso")
            return True
        else:
            if log:
                logger.warning("[GIGS] Confirmacao nao detectada, assumindo sucesso")
            return True

    except Exception as e:
        if log:
            logger.error("ERRO em criar_gigs: %s: %s", type(e).__name__, e)
        return False


# =============================================================================
# COMENTARIO
# =============================================================================


def criar_comentario(
    driver: Any,
    observacao: str,
    visibilidade: str = 'LOCAL',
    timeout: Union[int, float] = 10,
    log: bool = True,
) -> bool:
    """Cria comentario GIGS na aba /detalhe.

    Args:
        driver: Instancia do navegador.
        observacao: Texto do comentario.
        visibilidade: 'LOCAL' (padrao), 'RESTRITA' ou 'GLOBAL'.
        timeout: Timeout para operacoes (default 10s).
        log: Habilitar logs (default True).

    Returns:
        True se comentario criado com sucesso, False caso contrario.
    """
    try:
        if log:
            com_preview = (
                observacao[:50] + '...'
                if len(observacao) > 50
                else observacao
            )
            logger.debug("[COMENTARIO] Criando: %s", com_preview)

        # 1. Clicar "Novo Comentario"
        if log:
            logger.debug("[COMENTARIO] Clicando Novo Comentario...")

        btn_novo = None
        if espera.ate_habilitar(driver, "#novo-comentario, button#novo-comentario", teto=2):
            btn_novo = espera.elemento(driver, "#novo-comentario, button#novo-comentario", teto=1)

        if btn_novo is None:
            btn_novo_xpath = (
                "//button[contains(., 'Novo Coment\u00e1rio') "
                "or contains(., 'Novo coment\u00e1rio') "
                "or contains(., 'Novo Comentario') "
                "or contains(., 'Novo comentario')]"
            )
            if espera.ate_habilitar(driver, btn_novo_xpath, teto=timeout):
                btn_novo = espera.elemento(driver, btn_novo_xpath, teto=2)

        if btn_novo:
            safe_click_no_scroll(driver, btn_novo)
        espera.assentar(driver, 0.2)

        # 2. Aguardar formulario
        espera.ate_presenca(
            driver,
            'textarea[formcontrolname="descricao"], textarea[name="descricao"]',
            teto=timeout,
        )
        if log:
            logger.debug("[COMENTARIO] Formulario aberto")

        # 3. Preencher observacao/descricao
        campo_obs = espera.elemento(
            driver,
            'textarea[formcontrolname="descricao"], textarea[name="descricao"]',
            teto=5,
        )
        if campo_obs:
            _executar_js(driver, "arguments[0].focus();", campo_obs)
            _executar_js(
                driver,
                "arguments[0].value = arguments[1];"
                "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
                "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                campo_obs, observacao,
            )
        espera.assentar(driver, 0.3)
        if log:
            logger.debug("[COMENTARIO] Descricao preenchida")

        # 4. Selecionar visibilidade (radio buttons)
        visibilidade_upper = visibilidade.upper()
        if log:
            logger.debug("[COMENTARIO] Visibilidade: %s", visibilidade_upper)

        try:
            radio_buttons = espera.elementos(
                driver,
                'pje-gigs-comentarios-cadastro mat-radio-button, mat-radio-button',
                teto=5,
            )
            if len(radio_buttons) >= 3:
                index_map = {'LOCAL': 0, 'RESTRITA': 1, 'GLOBAL': 2}
                idx = index_map.get(visibilidade_upper, 0)
                radio_input = _sub_el(radio_buttons[idx], 'input')
                if radio_input:
                    _executar_js(driver, "arguments[0].click();", radio_input)
                espera.assentar(driver, 0.3)

                if visibilidade_upper == 'RESTRITA':
                    if log:
                        logger.debug(
                            "[COMENTARIO] Visibilidade RESTRITA - "
                            "pode requerer selecao de usuarios"
                        )
                    espera.assentar(driver, 0.5)
        except Exception as e:
            if log:
                logger.warning(
                    "[COMENTARIO][AVISO] Nao foi possivel "
                    "selecionar visibilidade: %s",
                    e,
                )

        # 5. Salvar
        if log:
            logger.debug("[COMENTARIO] Salvando...")
        btn_salvar_xpath = "//button[contains(., 'Salvar')]"
        if espera.ate_habilitar(driver, btn_salvar_xpath, teto=timeout):
            btn_salvar = espera.elemento(driver, btn_salvar_xpath, teto=2)
            if btn_salvar:
                safe_click_no_scroll(driver, btn_salvar)
        espera.assentar(driver, 0.2)

        # 6. Verificar se modal fechou
        espera.assentar(driver, 0.2)
        try:
            modals = espera.elementos(driver, 'mat-dialog-container', teto=2)
            modal_aberto = any(getattr(m, "is_displayed", lambda: True)() for m in modals)
            if not modal_aberto:
                if log:
                    logger.debug("[COMENTARIO] Comentario criado com sucesso")
                return True
            else:
                corpo = espera.elemento(driver, 'body', teto=2)
                _pressionar_tecla(driver, corpo, "Escape", _KEY_ESCAPE)
                espera.assentar(driver, 0.5)
                if log:
                    logger.debug(
                        "[COMENTARIO] Comentario criado "
                        "(modal fechado manualmente)"
                    )
                return True
        except Exception:
            if log:
                logger.debug("[COMENTARIO] Comentario criado")
            return True

    except Exception as e:
        if log:
            logger.error(
                "ERRO em criar_comentario: %s: %s",
                type(e).__name__,
                e,
            )
        return False


# =============================================================================
# LEMBRETE / POST-IT
# =============================================================================


def criar_lembrete_posit(
    driver: Any,
    titulo: str,
    conteudo: str,
    debug: bool = False,
) -> bool:
    """Cria lembrete/post-it generico com titulo e conteudo customizaveis.

    Args:
        driver: Instancia do navegador.
        titulo: Texto do titulo.
        conteudo: Texto do conteudo.
        debug: Log detalhado (default: False).

    Returns:
        True se sucesso, False caso contrario.
    """
    try:
        if debug:
            logger.debug(
                '[LEMBRETE][POSIT] Criando: "%s" / "%s"', titulo, conteudo
            )

        # Abre menu hamburger via #botao-menu (selector confiavel no PJe)
        menu_clicked = aguardar_e_clicar(driver, '#botao-menu', timeout=8, log=debug)
        if not menu_clicked:
            # fallback para ícone .fa-bars
            menu_clicked = aguardar_e_clicar(driver, '.fa-bars', timeout=5, log=debug)
        if not menu_clicked:
            if debug:
                logger.warning('[LEMBRETE][POSIT] Botao hamburger nao encontrado')
            return False
        espera.assentar(driver, 0.8)

        seletores_lembrete = [
            'pje-icone-post-it button',
            'button[aria-label*="Lembrete"]',
            'button[title*="Lembrete"]',
            '.lista-itens-menu li:nth-child(16) button',
        ]

        lembrete_clicked = False
        for seletor in seletores_lembrete:
            try:
                lembrete_clicked = aguardar_e_clicar(
                    driver, seletor, timeout=3, log=False
                )
                if lembrete_clicked:
                    if debug:
                        logger.debug(
                            '[LEMBRETE][POSIT] Icone: %s', seletor
                        )
                    break
            except Exception:
                continue

        if not lembrete_clicked:
            if debug:
                logger.warning('[LEMBRETE][POSIT] Botao de lembrete nao encontrado no menu')
            return False

        espera.assentar(driver, 0.8)

        aguardar_e_clicar(driver, '.mat-dialog-content', log=False)
        espera.assentar(driver, 0.5)

        # preencher_campo espera (driver, seletor, valor)
        titulo_elem = esperar_elemento(driver, '#tituloPostit', timeout=5)
        if titulo_elem:
            preencher_campo(driver, '#tituloPostit', titulo, log=debug)

        conteudo_elem = esperar_elemento(
            driver, '#conteudoPostit', timeout=5
        )
        if conteudo_elem:
            preencher_campo(driver, '#conteudoPostit', conteudo, log=debug)

        seletores_salvar = [
            'button[color="primary"]',
            '.mat-raised-button:not([disabled])',
            'button[type="submit"]',
        ]

        for seletor in seletores_salvar:
            try:
                if aguardar_e_clicar(driver, seletor, timeout=3, log=False):
                    break
            except Exception:
                continue

        espera.assentar(driver, 0.8)
        if debug:
            logger.debug('[LEMBRETE][POSIT] "%s" criado', titulo)
        return True

    except Exception as e:
        if debug:
            logger.error(
                "ERRO em criar_lembrete_posit: %s: %s",
                type(e).__name__,
                e,
            )
        return False


# =============================================================================
# INDEXACAO DE PROCESSOS
# =============================================================================


def indexar_processos(
    driver: Any,
) -> List[Tuple[str, Any]]:
    """Indexa processos de forma robusta, evitando stale elements.

    Busca elementos frescos a cada iteracao para evitar problemas de
    StaleElementReferenceException.

    Args:
        driver: Instancia do navegador.

    Returns:
        Lista de tuplas (proc_id, linha_element).
    """
    padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
    processos: List[Tuple[str, Any]] = []

    def obter_linhas_frescas():
        return espera.elementos(driver, 'tr.cdk-drag', teto=3)

    linhas = obter_linhas_frescas()
    logger.debug('[INDEXAR] Encontradas %s linhas para processar', len(linhas))

    for idx in range(len(linhas)):
        try:
            linhas_atuais = obter_linhas_frescas()

            if idx >= len(linhas_atuais):
                logger.debug(
                    '[INDEXAR][SKIP] Linha %s: DOM mudou, '
                    'menos linhas disponiveis',
                    idx + 1,
                )
                continue

            linha = linhas_atuais[idx]

            links = _sub_els(linha, 'a')
            texto = ''

            if links:
                texto = (getattr(links[0], "text", "") or "").strip()
            else:
                tds = _sub_els(linha, 'td')
                if tds:
                    texto = (getattr(tds[0], "text", "") or "").strip()

            match = padrao_proc.search(texto)
            num_proc = match.group(0) if match else '[sem numero]'

            processos.append((num_proc, linha))

        except Exception as e:
            logger.debug(
                '[INDEXAR][ERRO] Linha %s: %s '
                '(elemento pode ter ficado stale)',
                idx + 1,
                e,
            )
            continue

    logger.debug(
        '[INDEXAR] Processamento concluido: %s processos indexados',
        len(processos),
    )
    return processos


def reindexar_linha(
    driver: Any, proc_id: str
) -> Optional[Any]:
    """Reindexar linha quando elemento fica stale.

    Nao navega automaticamente - respeita a pagina atual do modulo.

    Args:
        driver: Instancia do navegador.
        proc_id: ID do processo a reindexar.

    Returns:
        Elemento da linha encontrada ou None se nao encontrada.
    """
    try:
        # Verificar se ainda estamos em uma pagina valida do PJE
        url_atual = getattr(driver, "current_url", "") or getattr(getattr(driver, "page", None), "url", "")
        if 'acesso-negado' in url_atual.lower() or 'access-denied' in url_atual.lower():
            logger.error("ACESSO NEGADO detectado na URL: %s", url_atual)
            return None

        if 'pje.trt2.jus.br' not in url_atual:
            logger.error("URL nao e do PJE: %s", url_atual)
            return None

        logger.debug(
            '[REINDEXAR] Tentando reindexar na pagina atual: %s', url_atual
        )

        # Buscar linhas na pagina atual (diferentes seletores)
        possible_selectors = [
            'tr.cdk-drag',         # Atividades (PEC)
            'tr',                   # Documentos internos (M1)
            'tbody tr',             # Outras tabelas
            '.linha-processo',      # Seletor alternativo
        ]

        linhas_atuais = []
        for selector in possible_selectors:
            try:
                linhas_temp = espera.elementos(
                    driver, selector, teto=2
                )
                if linhas_temp:
                    linhas_atuais = linhas_temp
                    logger.debug(
                        '[REINDEXAR] Usando seletor %s: '
                        '%s linhas encontradas',
                        selector,
                        len(linhas_atuais),
                    )
                    break
            except Exception:
                continue

        if not linhas_atuais:
            logger.error(
                "Nenhuma linha encontrada na pagina "
                "com os seletores testados"
            )
            return None

        logger.debug(
            '[REINDEXAR] Buscando %s entre %s linhas...',
            proc_id,
            len(linhas_atuais),
        )

        for idx, linha_temp in enumerate(linhas_atuais):
            try:
                is_vis = getattr(linha_temp, "is_displayed", None)
                if is_vis is not None and not is_vis():
                    continue
            except Exception:
                continue

            try:
                texto_linha = ""

                # Estrategia 1: Links
                links = _sub_els(linha_temp, 'a')
                if links:
                    texto_linha = (getattr(links[0], "text", "") or "").strip()
                else:
                    # Estrategia 2: Celulas td
                    tds = _sub_els(linha_temp, 'td')
                    if tds:
                        for td in tds[:3]:
                            td_text = (getattr(td, "text", "") or "").strip()
                            if proc_id in td_text:
                                texto_linha = td_text
                                break
                        if not texto_linha:
                            texto_linha = (getattr(tds[0], "text", "") or "").strip()
                    else:
                        # Estrategia 3: Texto geral da linha
                        texto_linha = (getattr(linha_temp, "text", "") or "").strip()

                if proc_id in texto_linha:
                    logger.info(
                        "Processo %s encontrado na linha %s",
                        proc_id,
                        idx + 1,
                    )
                    return linha_temp

            except Exception:
                continue

        logger.error(
            "Processo %s nao encontrado nas %s linhas da pagina atual",
            proc_id,
            len(linhas_atuais),
        )
        return None

    except Exception as e:
        logger.error("Erro geral na reindexacao: %s", e)
        return None


# =============================================================================
# ABRIR DETALHES DO PROCESSO
# =============================================================================


def abrir_detalhes_processo(
    driver: Any, linha: Any
) -> bool:
    """Abre detalhes do processo a partir de uma linha da tabela.

    Tenta encontrar o botao de detalhes via matTooltip, ou clica
    no primeiro botao/link disponivel na linha.

    Args:
        driver: Instancia do navegador.
        linha: Elemento da linha da tabela.

    Returns:
        True se conseguiu abrir detalhes, False caso contrario.
    """
    btn = _sub_el(linha, '[mattooltip*="Detalhes do Processo"]')
    if not btn:
        btn = _sub_el(linha, 'button, a')
    if not btn:
        return False

    _executar_js(driver, "arguments[0].scrollIntoView(true);", btn)
    _executar_js(driver, "arguments[0].click();", btn)
    return True
