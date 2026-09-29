# -*- coding: utf-8 -*-
"""
bianca/atos_utils.py - Chip removal and PEC creation wrappers.

Funcoes exportadas:
  - def_chip                   (remocao de chips)
  - make_comunicacao_wrapper    (factory de atos/comunicacao.py)
    - pec_ord, pec_sum          (notificacao inicial — modelos zordd/zsumd)
    - pec_ordc, pec_sumc        (notificacao inicial — modelos zordc/zsumc)
    - pec_arord, pec_arsum      (notificacao inicial AR — modelos AR-Or/AR-Su)
  - make_ato_wrapper            (factory de atos/judicial_fluxo.py)
    - ato_100                   (ato 100% digital, modelo aud100)
    - ato_unap                  (ato sem audiencia, modelo aud una presenc)
  - mov_aud                     (movimentar para Aguardando audiencia)

Dependencias externas limitadas a factories de atos/ (comunicacao, judicial_fluxo,
movimentos_fluxo). Nao importa wrappers prontos de atos/wrappers_*.py.
"""

import unicodedata
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from Fix import espera
from atos.movimentos_chips import def_chip
from bianca.extracao import criar_gigs
from bianca.selenium_utils import (
    aguardar_e_clicar,
    aguardar_renderizacao_nativa,
    buscar_seletor_robusto,
    esperar_elemento,
    safe_click,
    safe_click_no_scroll,
    trocar_para_nova_aba,
)
from Fix.core import wait_for_clickable
from bianca.utils import logger
from Fix.variaveis import url_processo_detalhe


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


def _preencher_input_js(
    driver: Any,
    seletor: str,
    valor: Union[str, int],
    max_tentativas: int = 3,
    debug: bool = False,
) -> bool:
    """Preenche input via querySelector + setter de prototype (Angular-friendly)."""
    for tentativa in range(1, max_tentativas + 1):
        try:
            ok = _executar_js(
                driver,
                """
                var seletor = arguments[0];
                var val = arguments[1];
                var el = document.querySelector(seletor);
                if (!el) { return false; }
                window.focus();
                el.focus();
                Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set.call(el, val);
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
                el.dispatchEvent(new Event('dateChange', {bubbles: true}));
                el.dispatchEvent(new Event('keyup', {bubbles: true}));
                el.dispatchEvent(
                    new KeyboardEvent('keydown', {
                        key: 'Enter', keyCode: 13, which: 13, bubbles: true
                    })
                );
                el.blur();
                return true;
            """,
                seletor,
                str(valor),
            )
            if ok:
                if debug:
                    logger.debug(f"[INPUT][OK] {seletor}='{valor}'")
                return True
            if tentativa < max_tentativas:
                espera.assentar(driver, 0.4)
        except Exception:
            if tentativa < max_tentativas:
                espera.assentar(driver, 0.4)
    return False


def _escolher_opcao_select_js(
    driver: Any,
    seletor_select: str,
    valor_desejado: str,
    debug: bool = False,
) -> bool:
    """Abre mat-select e clica na opcao correspondente."""
    try:
        select_el = espera.elemento(driver, seletor_select, teto=10)
        if not select_el:
            return False
        _executar_js(driver, "arguments[0].click();", select_el)

        # Aguardar mat-options via MutationObserver (overlay Angular Material)
        aguardar_renderizacao_nativa(driver, 'mat-option[role="option"]', 'aparecer', 10)

        opcoes = espera.elementos(driver, 'mat-option[role="option"]', teto=5)

        def _norm(s: str) -> str:
            return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().strip().lower()

        valor_norm = _norm(valor_desejado)
        for opcao in opcoes:
            texto = _norm(getattr(opcao, "text", "") or (opcao.get_attribute("innerText") if hasattr(opcao, "get_attribute") else "") or "")
            if valor_norm in texto or texto in valor_norm:
                _executar_js(driver, "arguments[0].click();", opcao)
                return True

        _executar_js(driver, "arguments[0].blur();", select_el)
        return False
    except Exception as e:
        logger.warning(f"[SELECT] Falha em _escolher_opcao_select_js: {e}")
        return False


def _clicar_radio_button_js(driver: Any, texto_label: str, debug: bool = False) -> bool:
    """Clica no input[type=radio] dentro do mat-radio-button correspondente."""
    try:
        ok = _executar_js(
            driver,
            """
            var textoAlvo = arguments[0];
            function normLabel(s) {
                return s.normalize('NFD')
                    .replace(/[\\u0300-\\u036f]/g, '')
                    .toLowerCase();
            }
            var radios = document.querySelectorAll('mat-radio-button');
            for (var i = 0; i < radios.length; i++) {
                var label = normLabel(
                    (radios[i].innerText || radios[i].textContent || '').trim()
                );
                if (label.indexOf(textoAlvo) !== -1) {
                    var inp = radios[i].querySelector('input[type="radio"]');
                    if (inp) { inp.click(); return true; }
                }
            }
            return false;
        """,
            texto_label,
        )
        return bool(ok)
    except Exception as e:
        if debug:
            logger.warning(f"[RADIO] Falha em _clicar_radio_button_js: {e}")
        return False


def _localizar_botao_acao(
    driver: Any,
    nome_attr: str,
    texto_botao: Optional[str] = None,
) -> Optional[Any]:
    """Localiza um botao por name/attr.name com fallback por texto visivel."""
    try:
        botoes = espera.elementos(driver, "button", teto=2)
        for botao in botoes:
            try:
                nome = (getattr(botao, "name", None) or (botao.get_attribute("name") if hasattr(botao, "get_attribute") else "") or "").strip()
                if nome == nome_attr:
                    return botao
            except Exception:
                continue
    except Exception:
        pass

    if texto_botao:
        try:
            spans = espera.elementos(driver, "button span, span.mat-button-wrapper", teto=2)
            for span in spans:
                try:
                    texto = (getattr(span, "text", "") or "").strip().lower()
                    if texto == texto_botao.strip().lower():
                        return _sub_el(span, "xpath=./ancestor::button[1]") or span
                except Exception:
                    continue
        except Exception:
            pass

    return None


# =============================================================================
# Retificar Autuacao — helpers para insercao de partes
# Fonte: maispje/PJe-Atual/gigs-plugin.js (acao9, acao7, acao1)
# =============================================================================


def _abrir_pagina_retificar(
    driver: Any,
    id_processo: str,
    timeout: int = 15,
) -> Optional[str]:
    """Abre a pagina /retificar em nova aba e aguarda carregamento.

    Args:
        driver: Instancia do navegador.
        id_processo: ID do processo (numero).
        timeout: Timeout em segundos.

    Returns:
        Handle da nova aba se sucesso, None caso contrario.
    """
    try:
        aba_origem = getattr(driver, "current_window_handle", None)
        url = f"https://pje.trt2.jus.br/pjekz/processo/{id_processo}/retificar"

        _executar_js(driver, "window.open(arguments[0], '_blank');", url)
        nova_aba = trocar_para_nova_aba(driver, aba_origem)
        if not nova_aba:
            return None

        # Aguardar step-headers carregarem
        esperar_elemento(
            driver,
            "mat-step-header[aria-posinset='1']",
            timeout=timeout,
        )
        return nova_aba
    except Exception:
        return None


def retificar_autuacao_inserir_custos_legis_mpt(
    driver: Any,
    id_processo: str,
    debug: bool = False,
    timeout: int = 10,
) -> bool:
    """Insere MPT como CUSTOS LEGIS na autuacao do processo.

    Equivalente JS: acao9() em gigs-plugin.js linha 14816.
    Fluxo: step Partes -> grid Outros participantes -> Adicionar parte ->
           selecionar CUSTOS LEGIS -> aba Ministerio publico do trabalho ->
           Selecionar -> Inserir.

    Args:
        driver: Instancia do navegador.
        id_processo: ID do processo.
        debug: Se True, exibe logs detalhados.
        timeout: Timeout base em segundos.

    Returns:
        True se inserido com sucesso, False caso contrario.
    """
    def log_msg(msg: str) -> None:
        if debug:
            try:
                logger.info(f"[RETIFICAR/MPT] {msg}")
            except Exception:
                pass

    try:
        # 1. Abrir pagina de retificacao
        aba_retificar = _abrir_pagina_retificar(driver, id_processo, timeout=timeout)
        if not aba_retificar:
            log_msg("Falha ao abrir pagina /retificar")
            return False

        # 2. Clicar step "Partes" (posinset="3" = terceiro step)
        step_partes = esperar_elemento(
            driver,
            'mat-step-header[aria-posinset="3"]',
            timeout=5,
        )
        if not step_partes:
            log_msg("Step 'Partes' nao encontrado")
            return False
        _executar_js(driver, "arguments[0].scrollIntoView({block:'center'});", step_partes)
        safe_click_no_scroll(driver, step_partes)
        log_msg("Step 'Partes' clicado")

        # 3. Localizar grid "Outros participantes"
        grid = esperar_elemento(
            driver,
            'pje-autuacao-grid-partes[titulogrid="Outros participantes"]',
            timeout=timeout,
        )
        if not grid:
            log_msg("Grid 'Outros participantes' nao encontrado")
            return False

        # 4. Clicar "Adicionar parte ao processo"
        btn_adicionar = _sub_el(
            grid,
            'button[aria-label="Adicionar parte ao processo"]',
        ) or espera.elemento(driver, 'button[aria-label="Adicionar parte ao processo"]', teto=3)
        if not btn_adicionar:
            log_msg("Botao 'Adicionar parte' nao encontrado")
            return False
        _executar_js(driver, "arguments[0].click();", btn_adicionar)
        log_msg("Botao 'Adicionar parte' clicado")

        # 5. Selecionar "CUSTOS LEGIS" no tipo de participacao
        if not _escolher_opcao_select_js(
            driver,
            'mat-select[aria-label="Tipo de participação"]',
            "CUSTOS LEGIS",
            debug=debug,
        ):
            log_msg("Falha ao selecionar 'CUSTOS LEGIS'")
            return False
        log_msg("'CUSTOS LEGIS' selecionado")

        # 6. Clicar aba "Ministério público do trabalho"
        abas_tab = espera.elementos(driver, 'div[role="tab"]', teto=5)
        aba_mpt = None
        for tab in abas_tab:
            try:
                texto = (getattr(tab, "text", "") or (tab.get_attribute("innerText") if hasattr(tab, "get_attribute") else "") or "").strip()
                if "minist" in texto.lower() and "publico" in texto.lower() and "trabalho" in texto.lower():
                    aba_mpt = tab
                    break
            except Exception:
                continue

        if not aba_mpt:
            log_msg("Aba 'Ministerio publico do trabalho' nao encontrada")
            return False
        _executar_js(driver, "arguments[0].click();", aba_mpt)
        espera.assentar(driver, 0.5)
        log_msg("Aba MPT clicada")

        # 7. Clicar "Selecionar"
        btn_selecionar = esperar_elemento(
            driver,
            'button[aria-label="Selecionar"]',
            timeout=5,
        )
        if not btn_selecionar:
            log_msg("Botao 'Selecionar' nao encontrado")
            return False
        _executar_js(driver, "arguments[0].click();", btn_selecionar)
        log_msg("'Selecionar' clicado")

        # 8. Clicar "Inserir"
        btn_inserir = None
        for botao in espera.elementos(driver, "button", teto=3):
            try:
                texto = (getattr(botao, "text", "") or "").strip().lower()
                if texto == "inserir":
                    btn_inserir = botao
                    break
            except Exception:
                continue

        if not btn_inserir:
            log_msg("Botao 'Inserir' nao encontrado")
            return False
        _executar_js(driver, "arguments[0].click();", btn_inserir)
        log_msg("'Inserir' clicado — MPT inserido como CUSTOS LEGIS")

        return True

    except Exception as e:
        log_msg(f"Erro: {e}")
        return False


def retificar_autuacao_inserir_terceiro(
    driver: Any,
    id_processo: str,
    cpf_cnpj: str,
    debug: bool = False,
    timeout: int = 10,
) -> bool:
    """Insere parte como TERCEIRO INTERESSADO generico.

    Equivalente JS: acao7('terceiro', cpf_cnpj) em gigs-plugin.js code 10.

    Args:
        driver: Instancia do navegador.
        id_processo: ID do processo.
        cpf_cnpj: CPF ou CNPJ da parte a inserir.
        debug: Se True, exibe logs detalhados.
        timeout: Timeout base em segundos.

    Returns:
        True se inserido com sucesso, False caso contrario.
    """
    def log_msg(msg: str) -> None:
        if debug:
            try:
                logger.info(f"[RETIFICAR/TERCEIRO] {msg}")
            except Exception:
                pass

    try:
        aba_retificar = _abrir_pagina_retificar(driver, id_processo, timeout=timeout)
        if not aba_retificar:
            return False

        # Step Partes
        step_partes = esperar_elemento(driver, 'mat-step-header[aria-posinset="3"]', timeout=5)
        if not step_partes:
            return False
        _executar_js(driver, "arguments[0].scrollIntoView({block:'center'});", step_partes)
        safe_click_no_scroll(driver, step_partes)

        # Grid Outros participantes
        grid = esperar_elemento(
            driver,
            'pje-autuacao-grid-partes[titulogrid="Outros participantes"]',
            timeout=timeout,
        )
        if not grid:
            return False

        # Adicionar parte
        btn_adicionar = _sub_el(grid, 'button[aria-label="Adicionar parte ao processo"]') or espera.elemento(driver, 'button[aria-label="Adicionar parte ao processo"]', teto=3)
        if btn_adicionar:
            _executar_js(driver, "arguments[0].click();", btn_adicionar)

        # Selecionar TERCEIRO INTERESSADO
        if not _escolher_opcao_select_js(
            driver,
            'mat-select[aria-label="Tipo de participação"]',
            "TERCEIRO INTERESSADO",
            debug=debug,
        ):
            return False

        # Preencher CPF/CNPJ
        input_doc = esperar_elemento(driver, 'input[formcontrolname="cpfCnpj"]', timeout=5)
        if not input_doc:
            return False
        _preencher_input_js(driver, 'input[formcontrolname="cpfCnpj"]', cpf_cnpj, debug=debug)

        # Clicar Inserir
        for botao in espera.elementos(driver, "button", teto=3):
            if (getattr(botao, "text", "") or "").strip().lower() == "inserir":
                _executar_js(driver, "arguments[0].click();", botao)
                log_msg("Terceiro interessado inserido")
                return True

        return False
    except Exception as e:
        log_msg(f"Erro: {e}")
        return False


def retificar_autuacao_inserir_uniao(
    driver: Any,
    id_processo: str,
    debug: bool = False,
    timeout: int = 10,
) -> bool:
    """Insere UNIAO como terceiro interessado (CUSTOS LEGIS).

    Equivalente JS: acao1() em gigs-plugin.js code 0.

    Args:
        driver: Instancia do navegador.
        id_processo: ID do processo.
        debug: Se True, exibe logs detalhados.
        timeout: Timeout base em segundos.

    Returns:
        True se inserido com sucesso, False caso contrario.
    """
    def log_msg(msg: str) -> None:
        if debug:
            try:
                logger.info(f"[RETIFICAR/UNIAO] {msg}")
            except Exception:
                pass

    try:
        aba_retificar = _abrir_pagina_retificar(driver, id_processo, timeout=timeout)
        if not aba_retificar:
            return False

        step_partes = esperar_elemento(driver, 'mat-step-header[aria-posinset="3"]', timeout=5)
        if not step_partes:
            return False
        _executar_js(driver, "arguments[0].scrollIntoView({block:'center'});", step_partes)
        safe_click_no_scroll(driver, step_partes)

        grid = esperar_elemento(
            driver,
            'pje-autuacao-grid-partes[titulogrid="Outros participantes"]',
            timeout=timeout,
        )
        if not grid:
            return False

        btn_adicionar = _sub_el(grid, 'button[aria-label="Adicionar parte ao processo"]') or espera.elemento(driver, 'button[aria-label="Adicionar parte ao processo"]', teto=3)
        if btn_adicionar:
            _executar_js(driver, "arguments[0].click();", btn_adicionar)

        if not _escolher_opcao_select_js(
            driver,
            'mat-select[aria-label="Tipo de participação"]',
            "CUSTOS LEGIS",
            debug=debug,
        ):
            return False

        # Aba Uniao
        abas_tab = espera.elementos(driver, 'div[role="tab"]', teto=5)
        aba_uniao = None
        for tab in abas_tab:
            texto = (getattr(tab, "text", "") or (tab.get_attribute("innerText") if hasattr(tab, "get_attribute") else "") or "").strip().lower()
            if "uniao" in texto:
                aba_uniao = tab
                break

        if not aba_uniao:
            log_msg("Aba 'Uniao' nao encontrada")
            return False
        _executar_js(driver, "arguments[0].click();", aba_uniao)
        espera.assentar(driver, 0.5)

        btn_selecionar = esperar_elemento(driver, 'button[aria-label="Selecionar"]', timeout=5)
        if not btn_selecionar:
            return False
        _executar_js(driver, "arguments[0].click();", btn_selecionar)

        for botao in espera.elementos(driver, "button", teto=3):
            if (getattr(botao, "text", "") or "").strip().lower() == "inserir":
                _executar_js(driver, "arguments[0].click();", botao)
                log_msg("Uniao inserida como CUSTOS LEGIS")
                return True

        return False
    except Exception as e:
        log_msg(f"Erro: {e}")
        return False


# =============================================================================
# ato_100 — Ato 100% digital (modelo aud100)
# Wrapper local para o fluxo Bianca (NAO importa wrappers de atos/)
# =============================================================================

from atos.judicial_fluxo import make_ato_wrapper

ato_100 = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='aud100',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    Assinar=False
)


# =============================================================================
# PEC wrappers — Notificacoes Iniciais (pec_ord, pec_sum, pec_ordc, pec_sumc)
# Wrappers locais para o fluxo Bianca (NAO importa wrappers de atos/)
# =============================================================================

from atos.comunicacao import make_comunicacao_wrapper

pec_ord = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='ordd',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios=None,
    trocar_modelo=True,
    wrapper_name='pec_ord',
    modelo_troca_correios='ar-ord'
)

pec_sum = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='sumd',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios=None,
    trocar_modelo=True,
    wrapper_name='pec_sum',
    modelo_troca_correios='ar-sum'
)

pec_ordc = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='zordc',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios=None,
    mudar_expediente=True,
)

pec_sumc = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='zsumc',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios=None,
    mudar_expediente=True,
)

pec_arord = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='AR-Or',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios='polo_passivo',
    cliques_polo_passivo=0,
    endereco_tipo='correios',
)

pec_arsum = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='AR-Su',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios='polo_passivo',
    cliques_polo_passivo=0,
    endereco_tipo='correios',
)

ato_unap = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='aud una presenc',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    Assinar=False
)


# =============================================================================
# mov_aud — Movimentar para Aguardando audiência
# Wrapper local para o fluxo Bianca (NAO importa wrappers de atos/)
# =============================================================================

from atos.movimentos_fluxo import movimentar_inteligente


def mov_aud(driver: Any, debug: bool = False) -> bool:
    """Movimenta o processo para 'Aguardando audiência'.

    Encapsula ``movimentar_inteligente`` com destino fixo.
    Usada apos execucao de pec_ord/pec_sum no fluxo de triagem (bucket C).

    Args:
        driver: Instancia do navegador.
        debug: Se True, exibe logs detalhados.

    Returns:
        True se o movimento foi executado com sucesso.
    """
    return bool(movimentar_inteligente(driver, 'Aguardando audiência', timeout=8))
