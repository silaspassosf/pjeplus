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

import re
import time
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

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

# =============================================================================
# def_chip
# Fonte: atos/movimentos_chips.py
# =============================================================================


def def_chip(
    driver: WebDriver,
    numero_processo: str = "",
    observacao: str = "",
    chips_para_remover: Optional[List[str]] = None,
    debug: bool = False,
    timeout: int = 10,
) -> bool:
    """Remove chips especificos do processo.

    Args:
        driver: WebDriver do Selenium.
        numero_processo: Numero do processo (opcional, para logs).
        observacao: Observacao que disparou a acao (opcional, para logs).
        chips_para_remover: Lista de strings dos chips a remover.
            Se None, usa ["Prazo vencido", "pos sentenca"].
        debug: Se True, exibe logs detalhados.
        timeout: Timeout para aguardar elementos.

    Returns:
        bool: True se ao menos um chip foi removido, False caso contrario.
    """
    chips_removidos = 0

    def log_msg(msg: str) -> None:
        if debug:
            try:
                logger.debug(msg)
            except Exception:
                pass

    try:
        if chips_para_remover is None:
            chips_para_remover = ["Prazo vencido", "pos sentenca"]
            log_msg(f"Usando chips padrao: {chips_para_remover}")

        log_msg(f"Iniciando remocao de chips para processo {numero_processo}")
        log_msg(f"Chips a remover: {chips_para_remover}")

        chips_xpath = "//mat-chip"
        chip_elements = driver.find_elements(By.XPATH, chips_xpath)
        chips_encontrados = []

        log_msg(f"Encontrados {len(chip_elements)} chips na pagina")

        for chip_element in chip_elements:
            try:
                chip_text = chip_element.text.strip()
                log_msg(f"Analisando chip: '{chip_text}'")
                if any(rem_text in chip_text for rem_text in chips_para_remover):
                    chips_encontrados.append((chip_element, chip_text))
                    log_msg(f"  -> Chip encontrado para remocao: '{chip_text}'")
            except Exception as e:
                log_msg(f"Erro ao ler chip: {e}")
                continue

        if not chips_encontrados:
            log_msg("Nenhum chip para remover encontrado - operacao concluida com sucesso")
            return True

        log_msg(f"Encontrados {len(chips_encontrados)} chips para remover")

        for chip_element, chip_text in chips_encontrados:
            try:
                log_msg(f"Removendo chip: '{chip_text}'")
                botao_remover = chip_element.find_element(
                    By.CSS_SELECTOR,
                    "button[mattooltip*='Remover Chip'], button.etq-botao-excluir",
                )
                botao_remover.click()
                log_msg("  -> Botao remover clicado")
                time.sleep(1)

                try:
                    botao_sim = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "//button[.//span[contains(text(), 'Sim')]]")
                        )
                    )
                    log_msg(f"Confirmando remocao do chip '{chip_text}'")
                    botao_sim.click()
                    time.sleep(2)
                    chips_removidos += 1
                    log_msg(f"  -> Chip '{chip_text}' removido com sucesso")
                except Exception as e:
                    log_msg(f"  -> Erro ao confirmar remocao do chip '{chip_text}': {e}")
                    continue
            except Exception as e:
                log_msg(f"  -> Erro ao processar chip '{chip_text}': {e}")
                continue

        if chips_removidos > 0:
            log_msg(f"Total de chips removidos: {chips_removidos}")
            return True
        log_msg("Nenhum chip foi removido")
        return False
    except Exception as e:
        log_msg(f"Erro geral na remocao de chips: {e}")
    return False




def _preencher_input_js(
    driver: WebDriver,
    seletor: str,
    valor: Union[str, int],
    max_tentativas: int = 3,
    debug: bool = False,
) -> bool:
    """Preenche input via querySelector + setter de prototype (Angular-friendly)."""
    for tentativa in range(1, max_tentativas + 1):
        try:
            ok = driver.execute_script(
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
                time.sleep(0.4)
        except Exception:
            if tentativa < max_tentativas:
                time.sleep(0.4)
    return False


def _escolher_opcao_select_js(
    driver: WebDriver,
    seletor_select: str,
    valor_desejado: str,
    debug: bool = False,
) -> bool:
    """Abre mat-select e clica na opcao correspondente."""
    try:
        select_el = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_select))
        )
        if not select_el:
            return False
        driver.execute_script("arguments[0].click();", select_el)

        # Aguardar mat-options via MutationObserver (overlay Angular Material)
        aguardar_renderizacao_nativa(driver, 'mat-option[role="option"]', 'aparecer', 10)

        opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"]')

        def _norm(s: str) -> str:
            return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().strip().lower()

        valor_norm = _norm(valor_desejado)
        for opcao in opcoes:
            texto = _norm(opcao.get_attribute("innerText") or opcao.text or "")
            if valor_norm in texto or texto in valor_norm:
                driver.execute_script("arguments[0].click();", opcao)
                return True

        driver.execute_script("arguments[0].blur();", select_el)
        return False
    except Exception as e:
        logger.warning(f"[SELECT] Falha em _escolher_opcao_select_js: {e}")
        return False


def _clicar_radio_button_js(driver: WebDriver, texto_label: str, debug: bool = False) -> bool:
    """Clica no input[type=radio] dentro do mat-radio-button correspondente."""
    try:
        ok = driver.execute_script(
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
    driver: WebDriver,
    nome_attr: str,
    texto_botao: Optional[str] = None,
) -> Optional[Any]:
    """Localiza um botao por name/attr.name com fallback por texto visivel."""
    try:
        botoes = driver.find_elements(By.CSS_SELECTOR, "button")
        for botao in botoes:
            try:
                nome = (botao.get_attribute("name") or "").strip()
                if nome == nome_attr:
                    return botao
            except Exception:
                continue
    except Exception:
        pass

    if texto_botao:
        try:
            spans = driver.find_elements(By.CSS_SELECTOR, "button span, span.mat-button-wrapper")
            for span in spans:
                try:
                    texto = (span.text or "").strip().lower()
                    if texto == texto_botao.strip().lower():
                        return span.find_element(By.XPATH, "./ancestor::button[1]")
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
    driver: WebDriver,
    id_processo: str,
    timeout: int = 15,
) -> Optional[str]:
    """Abre a pagina /retificar em nova aba e aguarda carregamento.

    Args:
        driver: WebDriver Selenium.
        id_processo: ID do processo (numero).
        timeout: Timeout em segundos.

    Returns:
        Handle da nova aba se sucesso, None caso contrario.
    """
    try:
        aba_origem = driver.current_window_handle
        url = f"https://pje.trt2.jus.br/pjekz/processo/{id_processo}/retificar"

        abas_antes = set(driver.window_handles)
        driver.execute_script("window.open(arguments[0], '_blank');", url)
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
    driver: WebDriver,
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
        driver: WebDriver Selenium.
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
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", step_partes)
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
        btn_adicionar = grid.find_element(
            By.CSS_SELECTOR,
            'button[aria-label="Adicionar parte ao processo"]',
        )
        if not btn_adicionar:
            log_msg("Botao 'Adicionar parte' nao encontrado")
            return False
        driver.execute_script("arguments[0].click();", btn_adicionar)
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
        abas_tab = driver.find_elements(By.CSS_SELECTOR, 'div[role="tab"]')
        aba_mpt = None
        for tab in abas_tab:
            try:
                texto = (tab.text or tab.get_attribute("innerText") or "").strip()
                if "minist" in texto.lower() and "publico" in texto.lower() and "trabalho" in texto.lower():
                    aba_mpt = tab
                    break
            except Exception:
                continue

        if not aba_mpt:
            log_msg("Aba 'Ministerio publico do trabalho' nao encontrada")
            return False
        driver.execute_script("arguments[0].click();", aba_mpt)
        time.sleep(0.5)
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
        driver.execute_script("arguments[0].click();", btn_selecionar)
        log_msg("'Selecionar' clicado")

        # 8. Clicar "Inserir"
        btn_inserir = None
        for botao in driver.find_elements(By.CSS_SELECTOR, "button"):
            try:
                texto = (botao.text or "").strip().lower()
                if texto == "inserir":
                    btn_inserir = botao
                    break
            except Exception:
                continue

        if not btn_inserir:
            log_msg("Botao 'Inserir' nao encontrado")
            return False
        driver.execute_script("arguments[0].click();", btn_inserir)
        log_msg("'Inserir' clicado — MPT inserido como CUSTOS LEGIS")

        return True

    except Exception as e:
        log_msg(f"Erro: {e}")
        return False


def retificar_autuacao_inserir_terceiro(
    driver: WebDriver,
    id_processo: str,
    cpf_cnpj: str,
    debug: bool = False,
    timeout: int = 10,
) -> bool:
    """Insere parte como TERCEIRO INTERESSADO generico.

    Equivalente JS: acao7('terceiro', cpf_cnpj) em gigs-plugin.js code 10.

    Args:
        driver: WebDriver Selenium.
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
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", step_partes)
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
        btn_adicionar = grid.find_element(By.CSS_SELECTOR, 'button[aria-label="Adicionar parte ao processo"]')
        driver.execute_script("arguments[0].click();", btn_adicionar)

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
        for botao in driver.find_elements(By.CSS_SELECTOR, "button"):
            if (botao.text or "").strip().lower() == "inserir":
                driver.execute_script("arguments[0].click();", botao)
                log_msg("Terceiro interessado inserido")
                return True

        return False
    except Exception as e:
        log_msg(f"Erro: {e}")
        return False


def retificar_autuacao_inserir_uniao(
    driver: WebDriver,
    id_processo: str,
    debug: bool = False,
    timeout: int = 10,
) -> bool:
    """Insere UNIAO como terceiro interessado (CUSTOS LEGIS).

    Equivalente JS: acao1() em gigs-plugin.js code 0.

    Args:
        driver: WebDriver Selenium.
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
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", step_partes)
        safe_click_no_scroll(driver, step_partes)

        grid = esperar_elemento(
            driver,
            'pje-autuacao-grid-partes[titulogrid="Outros participantes"]',
            timeout=timeout,
        )
        if not grid:
            return False

        btn_adicionar = grid.find_element(By.CSS_SELECTOR, 'button[aria-label="Adicionar parte ao processo"]')
        driver.execute_script("arguments[0].click();", btn_adicionar)

        if not _escolher_opcao_select_js(
            driver,
            'mat-select[aria-label="Tipo de participação"]',
            "CUSTOS LEGIS",
            debug=debug,
        ):
            return False

        # Aba Uniao
        abas_tab = driver.find_elements(By.CSS_SELECTOR, 'div[role="tab"]')
        aba_uniao = None
        for tab in abas_tab:
            texto = (tab.text or tab.get_attribute("innerText") or "").strip().lower()
            if "uniao" in texto:
                aba_uniao = tab
                break

        if not aba_uniao:
            log_msg("Aba 'Uniao' nao encontrada")
            return False
        driver.execute_script("arguments[0].click();", aba_uniao)
        time.sleep(0.5)

        btn_selecionar = esperar_elemento(driver, 'button[aria-label="Selecionar"]', timeout=5)
        if not btn_selecionar:
            return False
        driver.execute_script("arguments[0].click();", btn_selecionar)

        for botao in driver.find_elements(By.CSS_SELECTOR, "button"):
            if (botao.text or "").strip().lower() == "inserir":
                driver.execute_script("arguments[0].click();", botao)
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
    modelo_nome='zordd',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios=None,
    trocar_modelo=True,
    wrapper_name='pec_ord'
)

pec_sum = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='zsumd',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios=None,
    trocar_modelo=True,
    wrapper_name='pec_sum'
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


def mov_aud(driver: WebDriver, debug: bool = False) -> bool:
    """Movimenta o processo para 'Aguardando audiência'.

    Encapsula ``movimentar_inteligente`` com destino fixo.
    Usada apos execucao de pec_ord/pec_sum no fluxo de triagem (bucket C).

    Args:
        driver: WebDriver Selenium.
        debug: Se True, exibe logs detalhados.

    Returns:
        True se o movimento foi executado com sucesso.
    """
    return bool(movimentar_inteligente(driver, 'Aguardando audiência', timeout=8))
