# -*- coding: utf-8 -*-
"""
bianca/atos_utils.py - Chip removal and PEC creation wrappers.

Funcoes exportadas:
  - def_chip             (de atos/movimentos_chips.py)
  - make_comunicacao_wrapper  (de atos/comunicacao.py)
    - pec_ord, pec_sum, pec_ordc, pec_sumc, pec_ordc2, pec_sumc2  (de atos/wrappers_pec.py)

Nenhuma dependencia externa a selenium, bianca.* e biblioteca padrao.
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
from bianca.utils import logger

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


# =============================================================================
# Helpers internos para PEC orquestrada
# =============================================================================


def _remover_acentos(texto: str) -> str:
    if not texto:
        return ""
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caractere) != "Mn"
    )


def _abrir_tarefa_mais_recente_por_api(driver: WebDriver, timeout: int = 8) -> bool:
    try:
        url_atual = driver.current_url or ""
        if "/tarefa/" in url_atual:
            return True
        if "/processo/" not in url_atual:
            return False

        match = re.search(r"/processo/(\d+)", url_atual)
        if not match:
            return False

        id_processo = match.group(1)
        base = url_atual.split("/pjekz/")[0]
        dados = driver.execute_async_script(
            """
            const url = arguments[0];
            const done = arguments[arguments.length - 1];
            fetch(url, {method: 'GET', credentials: 'include', headers: {'Content-Type':'application/json'}})
                .then(resp => resp.json())
                .then(json => done(json))
                .catch(err => done({__erro: err && err.message ? err.message : String(err)}));
            """,
            f"{base}/pje-comum-api/api/processos/id/{id_processo}/tarefas?maisRecente=true",
        )

        id_tarefa = None
        if isinstance(dados, list) and dados:
            id_tarefa = dados[0].get("id") or dados[0].get("idTarefa")
        elif isinstance(dados, dict) and not dados.get("__erro"):
            id_tarefa = dados.get("id") or dados.get("idTarefa")

        if not id_tarefa:
            return False

        abas_antes = set(driver.window_handles)
        url_tarefa = f"{base}/pjekz/processo/{id_processo}/tarefa/{id_tarefa}"
        driver.execute_script("window.open(arguments[0], '_blank');", url_tarefa)
        nova_aba = trocar_para_nova_aba(driver, next(iter(abas_antes)) if abas_antes else None)
        if nova_aba:
            driver.switch_to.window(nova_aba)

        aguardar_renderizacao_nativa(driver, "pje-cabecalho-tarefa", "aparecer", timeout)
        aguardar_renderizacao_nativa(driver, "pje-botoes-transicao button", "aparecer", timeout)
        return True
    except Exception:
        return False


def _abrir_tarefa_processo_local(driver: WebDriver, timeout: int = 8) -> bool:
    try:
        if "/tarefa/" in (driver.current_url or ""):
            return True

        tarefa_btn = None
        for seletor in [
            'button[mattooltip="Abre a tarefa do processo"]',
            "button[mattooltip*='tarefa']",
            "button[aria-label*='tarefa']",
            "button[title*='tarefa']",
        ]:
            tarefa_btn = esperar_elemento(driver, seletor, timeout=max(2, timeout // 2))
            if tarefa_btn:
                break

        if not tarefa_btn:
            tarefa_btn = buscar_seletor_robusto(
                driver,
                ["Abre a tarefa do processo", "Abrir tarefa", "tarefa do processo", "tarefa"],
            )

        if not tarefa_btn:
            return False

        abas_antes = set(driver.window_handles)
        if not safe_click_no_scroll(driver, tarefa_btn):
            safe_click(driver, tarefa_btn)

        nova_aba = trocar_para_nova_aba(driver, next(iter(abas_antes)) if abas_antes else None)
        if nova_aba:
            driver.switch_to.window(nova_aba)

        aguardar_renderizacao_nativa(driver, "pje-cabecalho-tarefa", "aparecer", timeout)
        aguardar_renderizacao_nativa(driver, "pje-botoes-transicao button", "aparecer", timeout)
        return True
    except Exception:
        return False


def _localizar_botao_destino_movimento_local(
    driver: WebDriver,
    destino: str,
    timeout: int = 8,
) -> Optional[Any]:
    seletores = [
        "button[aria-label*='Aguardando audiência']",
        "button[aria-label*='Aguardando audiencia']",
        "button[aria-label*='Aguardando']",
    ]

    for seletor in seletores:
        botao = esperar_elemento(driver, seletor, timeout=max(2, timeout // 2))
        if botao:
            return botao

    try:
        xpath = (
            "//button[contains(@aria-label, 'Aguardando audiência') or "
            "contains(@aria-label, 'Aguardando audiencia') or "
            ".//span[contains(normalize-space(.), 'Aguardando audiência')] or "
            ".//span[contains(normalize-space(.), 'Aguardando audiencia')] or "
            "contains(normalize-space(.), 'Aguardando audiência') or "
            "contains(normalize-space(.), 'Aguardando audiencia')]"
        )
        botao = esperar_elemento(driver, xpath, by=By.XPATH, timeout=max(2, timeout // 2))
        if botao:
            return botao
    except Exception:
        pass

    destino_norm = _remover_acentos(destino).lower()
    try:
        for botao in driver.find_elements(By.CSS_SELECTOR, "button"):
            try:
                texto = " ".join(
                    filtro
                    for filtro in [
                        botao.text or "",
                        botao.get_attribute("aria-label") or "",
                        botao.get_attribute("title") or "",
                    ]
                    if filtro
                )
                if destino_norm in _remover_acentos(texto).lower():
                    return botao
            except Exception:
                continue
    except Exception:
        pass

    return None


def mov_int(driver: WebDriver, destino: str = "Aguardando audiência", debug: bool = False, timeout: int = 8) -> bool:
    def log_msg(msg: str) -> None:
        if debug:
            try:
                logger.info(msg)
            except Exception:
                pass

    try:
        log_msg(f"[MOV_INT] destino='{destino}'")

        if not _abrir_tarefa_mais_recente_por_api(driver, timeout=timeout):
            log_msg("[MOV_INT] Abertura via API falhou; tentando botao da tarefa")
            if not _abrir_tarefa_processo_local(driver, timeout=timeout):
                log_msg("[MOV_INT][ERRO] Nao foi possivel abrir a tarefa do processo")
                return False

        tarefa_atual = esperar_elemento(driver, 'pje-cabecalho-tarefa h1.titulo-tarefa', timeout=max(2, timeout // 2))
        tarefa_texto = (tarefa_atual.text or "").strip() if tarefa_atual else ""
        if tarefa_texto and _remover_acentos(destino).lower() in _remover_acentos(tarefa_texto).lower():
            log_msg(f"[MOV_INT] Processo ja esta em '{tarefa_texto}'")
            return True

        botao_destino = _localizar_botao_destino_movimento_local(driver, destino, timeout=timeout)
        if not botao_destino:
            log_msg(f"[MOV_INT][ERRO] Botao de destino nao encontrado: {destino}")
            return False

        if not safe_click_no_scroll(driver, botao_destino):
            safe_click(driver, botao_destino)

        log_msg(f"[MOV_INT] Movimento executado para '{destino}'")
        return True
    except Exception as e:
        log_msg(f"[MOV_INT][ERRO] Falha ao movimentar: {e}")
        return False


def mov_aud(driver: WebDriver, debug: bool = False) -> bool:
    return mov_int(driver, destino="Aguardando audiência", debug=debug, timeout=8)


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

        # Aguardar mat-options aparecerem
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-option[role="option"]'))
            )
        except Exception:
            pass

        opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"]')
        for opcao in opcoes:
            texto = (opcao.get_attribute("innerText") or opcao.text or "").strip()
            if valor_desejado.lower() in texto.lower():
                driver.execute_script("arguments[0].click();", opcao)
                return True

        driver.execute_script("arguments[0].blur();", select_el)
        return False
    except Exception as e:
        if debug:
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


def _inserir_modelo_minuta(
    driver: WebDriver,
    modelo_alvo: str,
    debug: bool = False,
    log: Optional[Callable[[str], None]] = None,
) -> bool:
    """Insere modelo com esperas curtas, evitando waits redundantes."""
    if log is None:
        log = logger.info

    filtro = esperar_elemento(driver, "input#inputFiltro", timeout=6)
    if not filtro:
        log(f"[MODELO][ERRO] Campo de filtro nao encontrado para {modelo_alvo}")
        return False

    driver.execute_script(
        """
        var el = arguments[0];
        el.removeAttribute('disabled');
        el.removeAttribute('readonly');
        el.focus();
        el.value = arguments[1];
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        el.dispatchEvent(new Event('keyup', {bubbles: true}));
    """,
        filtro,
        modelo_alvo,
    )

    nodo = esperar_elemento(driver, ".nodo-filtrado", timeout=6)
    if not nodo:
        log(f"[MODELO][ERRO] Nodo filtrado nao encontrado para {modelo_alvo}")
        return False

    driver.execute_script("arguments[0].click();", nodo)

    btn_inserir = esperar_elemento(
        driver,
        "pje-dialogo-visualizar-modelo .div-botao-inserir button, pje-dialogo-visualizar-modelo button",
        timeout=6,
    )
    if not btn_inserir:
        log(f"[MODELO][ERRO] Botao inserir nao encontrado para {modelo_alvo}")
        return False

    driver.execute_script("arguments[0].click();", btn_inserir)
    aguardar_renderizacao_nativa(driver, "simple-snack-bar", "aparecer", 4)
    aguardar_renderizacao_nativa(driver, "pje-dialogo-visualizar-modelo", "sumir", 4)

    if debug:
        log(f"[MODELO] Modelo inserido: {modelo_alvo}")
    return True


def _alterar_linhas_para_correios(
    driver: WebDriver,
    log: Optional[Callable[[str], None]] = None,
) -> int:
    """Troca meios 'Domicilio' por 'Correio' e retorna quantas linhas mudaram."""
    if log is None:
        log = logger.info

    alteradas = 0
    linhas = driver.find_elements(By.CSS_SELECTOR, "tbody.cdk-drop-list tr.cdk-drag")
    for linha in linhas:
        try:
            meio = linha.find_element(
                By.CSS_SELECTOR,
                "pje-pec-coluna-meio-expedicao .mat-select-value-text .mat-select-min-line",
            )
            if "domicilio" not in (meio.text or "").strip().lower():
                continue

            dropdown = linha.find_element(
                By.CSS_SELECTOR,
                'mat-select[placeholder="Meios de Expedicao"]',
            )
            driver.execute_script("arguments[0].click();", dropdown)

            try:
                WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "mat-option"))
                )
            except Exception:
                pass

            for opt in driver.find_elements(By.CSS_SELECTOR, "mat-option"):
                if "correio" in (opt.text or "").strip().lower():
                    driver.execute_script("arguments[0].click();", opt)
                    alteradas += 1
                    log("[COMUNICACAO] Domicilio -> Correio")
                    break
        except Exception:
            continue

    return alteradas


def _modelo_correios_para_reaplicar(modelo_atual: str) -> Optional[str]:
    mapa = {
        "zordd": "zordc",
        "zsumd": "zsumc",
    }
    return mapa.get((modelo_atual or "").strip().lower())


def _trocar_modelo_minuta_correios(
    driver: WebDriver,
    modelo_atual: str,
    debug: bool = False,
    log: Optional[Callable[[str], None]] = None,
) -> bool:
    """Reaplica modelo *c quando houver linhas em Correios antes do salvar final."""
    if log is None:
        log = logger.info

    modelo_reaplicar = _modelo_correios_para_reaplicar(modelo_atual)
    if not modelo_reaplicar:
        return False

    linhas = driver.find_elements(By.CSS_SELECTOR, "tbody.cdk-drop-list tr.cdk-drag")
    linhas_correios = []
    for linha in linhas:
        try:
            meio = linha.find_element(
                By.CSS_SELECTOR,
                "pje-pec-coluna-meio-expedicao .mat-select-min-line",
            )
            if "correio" in (meio.text or "").strip().lower():
                linhas_correios.append(linha)
        except Exception:
            continue

    if not linhas_correios:
        return False

    for indice, linha in enumerate(linhas_correios, start=1):
        try:
            botao = linha.find_element(
                By.CSS_SELECTOR,
                'pje-pec-coluna-confeccionar-ato button[aria-label="Confeccionar ato"]',
            )
            driver.execute_script("arguments[0].click();", botao)

            editor = esperar_elemento(
                driver,
                '.ck-editor__editable[contenteditable="true"]',
                timeout=6,
            )
            if not editor:
                log(f"[MODELO][WARN] Editor nao abriu na linha Correios {indice}")
                continue

            limpo = driver.execute_script(
                """
                var el = arguments[0];
                var ck = el.ckeditorInstance || (el.closest('.ck-editor') ? el.closest('.ck-editor').ckeditorInstance : null);
                if (ck) {
                    ck.setData('');
                    return ck.getData().trim() === '';
                }
                el.focus();
                el.innerHTML = '';
                el.dispatchEvent(new InputEvent('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
                return el.innerText.trim().length === 0;
            """,
                editor,
            )
            if not limpo:
                log(f"[MODELO][WARN] Editor nao limpou na linha Correios {indice}")
                continue

            if not _inserir_modelo_minuta(driver, modelo_reaplicar, debug=debug, log=log):
                log(f"[MODELO][WARN] Falha ao reaplicar {modelo_reaplicar} na linha Correios {indice}")
                continue

            log(f"[COMUNICACAO] Modelo {modelo_reaplicar} reaplicado na linha Correios {indice}")
        except Exception as e:
            log(f"[MODELO][WARN] Falha ao trocar modelo na linha Correios {indice}: {e}")

    return True


# =============================================================================
# make_comunicacao_wrapper
# Fonte: atos/comunicacao.py (adaptada)
# =============================================================================


def _extrair_observacao_gigs_vencida_xs_pec(driver: WebDriver, debug: bool = False) -> Optional[str]:
    """Extrai observacao da linha GIGS vencida (icone vermelho) com XS e PEC."""
    try:
        linhas = driver.find_elements(By.CSS_SELECTOR, "#tabela-atividades tbody tr")
        for linha in linhas:
            try:
                icone_vermelho = linha.find_elements(
                    By.CSS_SELECTOR, "i.fa-clock.danger, i.danger.fa-clock"
                )
                if not icone_vermelho:
                    continue
                span_descricao = linha.find_element(By.CSS_SELECTOR, "span.descricao")
                texto_descricao = (span_descricao.text or "").strip()
                if not texto_descricao:
                    continue
                texto_lower = texto_descricao.lower()
                if "xs" not in texto_lower:
                    continue
                if texto_lower.startswith("prazo:"):
                    texto_descricao = texto_descricao[6:].strip()
                if debug:
                    logger.info(
                        f"[COMUNICACAO][GIGS] Observacao extraida: {texto_descricao}"
                    )
                return texto_descricao
            except Exception:
                continue
        if debug:
            logger.info(
                "[COMUNICACAO][GIGS] Nenhuma linha vencida com XS+PEC encontrada"
            )
        return None
    except Exception as e:
        if debug:
            logger.info(f"[COMUNICACAO][GIGS][ERRO] Falha ao extrair observacao: {e}")
        return None


def make_comunicacao_wrapper(
    tipo_expediente: str,
    prazo: int,
    nome_comunicacao: str,
    sigilo: str,
    modelo_nome: str,
    subtipo: Optional[str] = None,
    descricao: Optional[str] = None,
    tipo_prazo: str = "dias uteis",
    gigs_extra: Optional[Union[bool, Tuple, List, Any]] = None,
    coleta_conteudo: Optional[str] = None,
    inserir_conteudo: Optional[str] = None,
    cliques_polo_passivo: int = 1,
    destinatarios: str = "extraido",
    mudar_expediente: Optional[bool] = None,
    endereco_tipo: Optional[str] = None,
    trocar_modelo: bool = False,
    wrapper_name: Optional[str] = None,
    terceiro_default: bool = False,
    assinar: bool = False,
) -> Callable[..., bool]:
    """Factory que retorna uma funcao wrapper para criacao de PEC.

    Parametros de configuracao sao capturados no closure e aplicados
    quando o wrapper resultante e chamado com ``(driver, ...)``.
    """

    def wrapper(
        driver: WebDriver,
        numero_processo: Optional[str] = None,
        observacao: Optional[str] = None,
        destinatarios_override: Optional[List[Dict[str, Any]]] = None,
        debug: bool = False,
        **overrides: Any,
    ) -> bool:
        """Wrapper que executa o fluxo completo de criacao de PEC."""
        # --- 0. GIGS extra antes do fluxo ---
        if gigs_extra:
            try:
                if gigs_extra is True:
                    criar_gigs(driver, prazo, "", nome_comunicacao)
                elif isinstance(gigs_extra, (tuple, list)):
                    if len(gigs_extra) >= 3:
                        dias_uteis, responsavel, obs_gigs = gigs_extra[:3]
                        criar_gigs(driver, dias_uteis, responsavel, obs_gigs)
                    elif len(gigs_extra) == 2:
                        dias_uteis, obs_gigs = gigs_extra
                        criar_gigs(driver, dias_uteis, "", obs_gigs)
                    else:
                        criar_gigs(driver, gigs_extra)
                else:
                    criar_gigs(driver, gigs_extra)
            except Exception as e:
                try:
                    logger.info(
                        f"[GIGS_WRAPPER][ERRO] Falha ao executar criar_gigs: {e}"
                    )
                except Exception:
                    pass

        # Resolver destinatarios
        dest_param = (
            destinatarios_override
            if destinatarios_override is not None
            else (overrides.get("destinatarios") if "destinatarios" in overrides else destinatarios)
        )

        # Modo 'informado' — extrair observacao de GIGS vencida
        if dest_param == "informado":
            obs_gigs = _extrair_observacao_gigs_vencida_xs_pec(driver, debug=debug)
            if obs_gigs:
                observacao = obs_gigs
            else:
                if not observacao or not (isinstance(observacao, str) and observacao.strip()):
                    logger.info(
                        "[COMUNICACAO][GIGS] Observacao nao localizada - fallback polo_passivo_2x"
                    )
                    dest_param = "polo_passivo_2x"

        log_fn: Callable[[str], None] = overrides.get("log", logger.info)

        try:
            # --- 1. Navegar para pagina de minutas ---
            log_fn(f"[COMUNICACAO] Abrindo minutas para {nome_comunicacao}")
            houve_correios = False
            current_url = driver.current_url
            match = re.search(r"/processo/(\d+)/detalhe", current_url)
            if not match:
                raise Exception("ID do processo nao encontrado na URL /detalhe")

            processo_id = match.group(1)
            url_minutas = (
                driver.current_url.split("/detalhe")[0]
                + f"/processo/{processo_id}/comunicacoesprocessuais/minutas"
            )
            abas_antes = driver.window_handles
            driver.execute_script(f"window.open('{url_minutas}', '_blank');")

            for _ in range(15):
                abas = driver.window_handles
                if len(abas) > len(abas_antes):
                    driver.switch_to.window(abas[-1])
                    break
                try:
                    driver.execute_script(
                        "return window.requestAnimationFrame(function(){});"
                    )
                except Exception:
                    pass
            else:
                raise Exception("Nova aba de minutas nao abriu")

            # Aguardar carregamento
            try:
                WebDriverWait(driver, 20).until(
                    lambda d: "/minutas" in (d.current_url or "")
                )
            except Exception:
                raise Exception("URL de minutas nao carregou")

            log_fn(f"[COMUNICACAO] Tela de minutas carregada para {nome_comunicacao}")

            # --- 2. Preencher minuta ---
            log_fn("[COMUNICACAO] Executando preenchimento da minuta")

            log_msg = log_fn  # alias

            # 2a. Selecionar tipo de expediente
            log_msg(f"1. Selecionando tipo de expediente: {tipo_expediente}")
            if not _escolher_opcao_select_js(
                driver, 'mat-select[placeholder="Tipo de Expediente"]', tipo_expediente, debug=debug
            ):
                raise Exception("Falha ao selecionar tipo de expediente")

            # 2b. Selecionar tipo de prazo
            log_msg(f"2. Selecionando tipo de prazo: {tipo_prazo}")
            prazo_efetivo = prazo
            tipo_prazo_efetivo = tipo_prazo
            if str(prazo) == "0" or prazo == 0:
                tipo_prazo_efetivo = "sem prazo"
            if not _clicar_radio_button_js(driver, tipo_prazo_efetivo, debug=debug):
                raise Exception(f'Tipo de prazo "{tipo_prazo_efetivo}" nao encontrado')

            # 2c. Preencher prazo
            if prazo_efetivo and tipo_prazo_efetivo != "sem prazo":
                log_msg(f"3. Preenchendo prazo: {prazo_efetivo}")
                seletores = [
                    'input[aria-label="Prazo em dias uteis"]',
                    'input[placeholder*="dias uteis"]',
                    'mat-form-field input[type="number"]',
                    'input[formcontrolname="prazo"]',
                ]
                preenchido = False
                for sel in seletores:
                    if _preencher_input_js(driver, sel, prazo_efetivo, debug=debug):
                        preenchido = True
                        break
                if not preenchido:
                    try:
                        inp = esperar_elemento(
                            driver, 'mat-form-field input[type="number"]', timeout=5
                        )
                        if inp:
                            inp.clear()
                            inp.send_keys(str(prazo_efetivo))
                            preenchido = True
                    except Exception:
                        log_msg("[AVISO] Nao foi possivel preencher prazo")

            # 2d. Clicar "Confeccionar ato agrupado" (gigs: clicarBotao)
            log_msg('4. Clicando "Confeccionar ato agrupado"')
            btn_conf = esperar_elemento(
                driver, 'button[aria-label="Confeccionar ato agrupado"]', timeout=10
            )
            if btn_conf:
                driver.execute_script('arguments[0].click();', btn_conf)

            # 2e. Subtipo
            if subtipo:
                log_msg(f"5. Selecionando subtipo: {subtipo}")
                try:
                    inp_sub = esperar_elemento(
                        driver, 'input[data-placeholder="Tipo de Documento"]', timeout=10
                    )
                    if inp_sub:
                        driver.execute_script(
                            """
                            var el = arguments[0];
                            el.focus();
                            el.dispatchEvent(
                                new KeyboardEvent('keydown', {
                                    keyCode: 13, which: 13, bubbles: true
                                })
                            );
                        """,
                            inp_sub,
                        )
                        try:
                            WebDriverWait(driver, 3).until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, "mat-option")
                                )
                            )
                        except Exception:
                            pass
                        opcoes = driver.find_elements(By.CSS_SELECTOR, "mat-option")
                        for opt in opcoes:
                            if subtipo.lower() in (opt.text or "").lower():
                                driver.execute_script("arguments[0].click();", opt)
                                log_msg(f" Subtipo selecionado: {subtipo}")
                                break
                except Exception as e:
                    log_msg(f"[SUBTIPO] Erro: {e}")

            # 2f. Descricao
            desc = descricao if descricao else nome_comunicacao
            log_msg(f"6. Preenchendo descricao: {desc}")
            if not _preencher_input_js(
                driver, 'input[aria-label="Descricao"]', desc, debug=debug
            ):
                log_msg("[ERRO] Falha ao preencher descricao")

            # 2g. Sigilo
            if str(sigilo).lower() in ("sim", "true", "1"):
                log_msg("7. Marcando sigilo")
                try:
                    inp_sig = driver.find_element(By.CSS_SELECTOR, 'input[name="sigiloso"]')
                    if not inp_sig.is_selected():
                        driver.execute_script("arguments[0].click();", inp_sig)
                except Exception as e:
                    log_msg(f"[WARN] Falha ao marcar sigilo: {e}")

            # 2h. Modelo
            if modelo_nome:
                log_msg(f"8. Selecionando modelo: {modelo_nome}")
                try:
                    if not _inserir_modelo_minuta(driver, modelo_nome, debug=debug, log=log_msg):
                        raise Exception(f"Falha ao inserir modelo {modelo_nome}")
                    log_msg(" Modelo inserido - aguardando snackbar de confirmacao")
                    log_msg(" Snackbar confirmou insercao do modelo no editor")
                except Exception as e:
                    log_msg(f"[MODELO][ERRO] Falha ao inserir modelo: {e}")
                    raise

            # 2i. Salvar e finalizar minuta (gigs: clicarBotao)
            log_msg("9. Salvando e finalizando minuta")
            btn_salvar = esperar_elemento(driver, 'button[aria-label="Salvar"]', timeout=10)
            if btn_salvar:
                driver.execute_script('arguments[0].click();', btn_salvar)
            btn_finalizar = esperar_elemento(driver, 'button[aria-label="Finalizar minuta"]', timeout=10)
            if btn_finalizar:
                driver.execute_script('arguments[0].click();', btn_finalizar)
            aguardar_renderizacao_nativa(driver, 'pje-pec-dialogo-ato', 'sumir', 15)
            log_msg("[COMUNICACAO] Preenchimento concluido")

            # --- 3. Selecionar destinatarios ---
            log_msg("[COMUNICACAO] Selecionando destinatarios")
            if dest_param and dest_param != "":
                if dest_param in ("polo_passivo", "polo_passivo_2x"):
                    cliques = overrides.get(
                        "cliques_polo_passivo", cliques_polo_passivo
                    )
                    if "2x" in str(dest_param):
                        cliques = 2
                    for i in range(int(cliques)):
                        try:
                            aguardar_e_clicar(
                                driver,
                                'button[name="btnIntimarSomentePoloPassivo"]',
                                timeout=10,
                            )
                        except Exception as e:
                            log_msg(
                                f"[DESTINATARIOS] Falha ao clicar polo passivo "
                                f"(tentativa {i+1}): {e}"
                            )
                elif isinstance(dest_param, list):
                    log_msg(
                        "[DESTINATARIOS] Lista de destinatarios fornecida "
                        f"({len(dest_param)} itens)"
                    )
                else:
                    log_msg(f"[DESTINATARIOS] Modo nao implementado: {dest_param}")

            # --- 4. Alterar meio de expedicao se necessario ---
            if endereco_tipo == "correios":
                log_msg("[COMUNICACAO] Alterando meio de expedicao para correios")
                try:
                    houve_correios = _alterar_linhas_para_correios(driver, log=log_msg) > 0
                except Exception as e:
                    log_msg(
                        f"[COMUNICACAO][WARN] Falha ao alterar meio expedicao: {e}"
                    )
            elif mudar_expediente:
                log_msg(
                    "[COMUNICACAO] mudar_expediente=True - alterando meio para correios"
                )
                try:
                    houve_correios = _alterar_linhas_para_correios(driver, log=log_msg) > 0
                except Exception as e:
                    log_msg(
                        f"[COMUNICACAO][WARN] Falha alterar expediente "
                        f"(mudar_expediente): {e}"
                    )

            if trocar_modelo and houve_correios:
                log_msg("[COMUNICACAO] Correios detectado - reaplicando modelo *c antes do salvar")
                _trocar_modelo_minuta_correios(
                    driver,
                    modelo_nome,
                    debug=debug,
                    log=log_msg,
                )

            # --- 5. Salvar minuta final ---
            log_msg("[COMUNICACAO] Salvando minuta final")
            btn_salvar = _localizar_botao_acao(
                driver,
                "btnSalvarExpedientes",
                texto_botao="Salvar",
            )
            if not btn_salvar:
                raise Exception("Botao Salvar nao encontrado")
            driver.execute_script("arguments[0].click();", btn_salvar)

            try:
                WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, 'button[name="btnFinalizarExpedientes"]')
                    )
                )
            except Exception:
                pass

            if assinar:
                try:
                    btn_assinar = driver.find_element(
                        By.XPATH,
                        "//button[.//span[contains(normalize-space(text()),"
                        "'Assinar ato')]]",
                    )
                    driver.execute_script("arguments[0].click();", btn_assinar)
                    try:
                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "snack-bar-container")
                            )
                        )
                    except Exception:
                        pass
                except Exception as e:
                    log_msg(f"[COMUNICACAO][WARN] Falha ao assinar: {e}")

            log_msg(f"[COMUNICACAO] Minuta salva para {nome_comunicacao}")

            # --- 6. Fechar aba de minutas e voltar para detalhe ---
            try:
                handles = driver.window_handles
                if len(handles) > 1:
                    driver.close()
                    driver.switch_to.window(handles[0])
                    log_msg(
                        f"[COMUNICACAO] Aba de minutas fechada; "
                        f"retornou a aba de detalhe"
                    )
            except Exception as e:
                log_msg(
                    f"[COMUNICACAO] Falha ao fechar aba de minutas: {e}"
                )

            log_msg(
                f"[COMUNICACAO] Fluxo concluido com sucesso para "
                f"{nome_comunicacao}"
            )
            return True

        except Exception as e:
            log_msg(f"[COMUNICACAO][ERRO] Falha no fluxo: {e}")
            return False

    # Preservar nome do wrapper para debug
    if wrapper_name:
        wrapper.__name__ = wrapper_name
    else:
        wrapper.__name__ = f"pec_wrapper_{tipo_expediente}_{modelo_nome}"

    return wrapper


# =============================================================================
# PEC Wrapper Objects
# Fonte: atos/wrappers_pec.py
# =============================================================================

pec_ord = make_comunicacao_wrapper(
    tipo_expediente="Notificacao Inicial",
    prazo=5,
    nome_comunicacao="Notificacao",
    sigilo=False,
    modelo_nome="zordd",
    subtipo="Notificacao",
    gigs_extra=None,
    destinatarios=None,
    trocar_modelo=True,
    wrapper_name="pec_ord",
)

pec_sum = make_comunicacao_wrapper(
    tipo_expediente="Notificacao Inicial",
    prazo=5,
    nome_comunicacao="Notificacao",
    sigilo=False,
    modelo_nome="zsumd",
    subtipo="Notificacao",
    gigs_extra=None,
    destinatarios=None,
    trocar_modelo=True,
    wrapper_name="pec_sum",
)

pec_ordc = make_comunicacao_wrapper(
    tipo_expediente="Notificacao Inicial",
    prazo=5,
    nome_comunicacao="Notificacao",
    sigilo=False,
    modelo_nome="zordc",
    subtipo="Notificacao",
    gigs_extra=None,
    destinatarios=None,
    mudar_expediente=True,
)

pec_sumc = make_comunicacao_wrapper(
    tipo_expediente="Notificacao Inicial",
    prazo=5,
    nome_comunicacao="Notificacao",
    sigilo=False,
    modelo_nome="zsumc",
    subtipo="Notificacao",
    gigs_extra=None,
    destinatarios=None,
    mudar_expediente=True,
)

pec_ordc2 = make_comunicacao_wrapper(
    tipo_expediente="Notificacao Inicial",
    prazo=5,
    nome_comunicacao="Notificacao",
    sigilo=False,
    modelo_nome="ordc2",
    subtipo="Notificacao",
    gigs_extra=None,
    destinatarios="polo_passivo",
    cliques_polo_passivo=1,
    endereco_tipo="correios",
)

pec_sumc2 = make_comunicacao_wrapper(
    tipo_expediente="Notificacao Inicial",
    prazo=5,
    nome_comunicacao="Notificacao",
    sigilo=False,
    modelo_nome="sumc2",
    subtipo="Notificacao",
    gigs_extra=None,
    destinatarios="polo_passivo",
    cliques_polo_passivo=1,
    endereco_tipo="correios",
)

pec_arord = make_comunicacao_wrapper(
    tipo_expediente="Notificacao Inicial",
    prazo=5,
    nome_comunicacao="Notificacao",
    sigilo=False,
    modelo_nome="AR-Or",
    subtipo="Notificacao",
    gigs_extra=None,
    destinatarios="polo_passivo",
    cliques_polo_passivo=0,
    endereco_tipo="correios",
)

pec_arsum = make_comunicacao_wrapper(
    tipo_expediente="Notificacao Inicial",
    prazo=5,
    nome_comunicacao="Notificacao",
    sigilo=False,
    modelo_nome="AR-Su",
    subtipo="Notificacao",
    gigs_extra=None,
    destinatarios="polo_passivo",
    cliques_polo_passivo=0,
    endereco_tipo="correios",
)


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
