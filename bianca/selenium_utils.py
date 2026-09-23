# -*- coding: utf-8 -*-
"""
bianca/selenium_utils.py - Utilitarios de automacao do navegador para o modulo Bianca.

Fornece primitivas de interacao delegando ao nucleo Playwright-native (Fix.core,
Fix.browser_suporte, Fix.espera) mantendo total retrocompatibilidade com a API legada.

Funcoes exportadas:
  esperar_elemento, safe_click, preencher_campo, selecionar_opcao,
  com_retry, buscar_seletor_robusto, aguardar_renderizacao_nativa,
  aplicar_filtro_100, filtrofases, resetar_driver,
  aguardar_e_clicar, safe_click_no_scroll, fechar_abas_extras,
  trocar_para_nova_aba, limpar_overlays_headless, js_base
"""

import re
from typing import Any, Callable, Dict, List, Optional, Union

from Fix import espera
from Fix.core import (
    aguardar_e_clicar as _fix_aguardar_e_clicar,
    aguardar_renderizacao_nativa as _fix_aguardar_renderizacao_nativa,
    buscar_seletor_robusto as _fix_buscar_seletor_robusto,
    esperar_elemento as _fix_esperar_elemento,
    preencher_campo as _fix_preencher_campo,
    safe_click as _fix_safe_click,
    safe_click_no_scroll as _fix_safe_click_no_scroll,
)
from Fix.browser_suporte import (
    forcar_fechamento_abas_extras as _fix_forcar_fechamento_abas_extras,
    limpar_overlays_headless as _fix_limpar_overlays_headless,
    trocar_para_nova_aba as _fix_trocar_para_nova_aba,
)
from bianca.utils import logger


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
# JavaScript base helpers (MutationObserver pattern)
# =============================================================================

def js_base() -> str:
    """JavaScript utility functions using MutationObserver."""
    return (
        """
    function esperarElemento(seletor, timeout) {
        timeout = timeout || 5000;
        return new Promise(function(resolve) {
            var elemento = document.querySelector(seletor);
            var disabled = (elemento && elemento.disabled === undefined)
                ? false : elemento.disabled;
            if (elemento && !disabled) {
                resolve(elemento);
                return;
            }
            var observer = new MutationObserver(function() {
                var elem = document.querySelector(seletor);
                var d = (elem && elem.disabled === undefined)
                    ? false : elem.disabled;
                if (elem && !d) {
                    observer.disconnect();
                    resolve(elem);
                }
            });
            observer.observe(document.body, {childList: true, subtree: true});
            setTimeout(function() {
                observer.disconnect();
                resolve(null);
            }, timeout);
        });
    }
    function triggerEvent(elemento, tipo) {
        if (!elemento) return;
        if ('createEvent' in document) {
            var e = document.createEvent('HTMLEvents');
            e.initEvent(tipo, true, true);
            elemento.dispatchEvent(e);
        } else {
            elemento.dispatchEvent(new Event(tipo, {bubbles: true}));
        }
    }
    function esperarOpcoes(seletor, timeout) {
        seletor = seletor || 'mat-option[role="option"]';
        timeout = timeout || 5000;
        return new Promise(function(resolve) {
            var opcoes = document.querySelectorAll(seletor);
            if (opcoes.length > 0) { resolve(opcoes); return; }
            var observer = new MutationObserver(function() {
                var opts = document.querySelectorAll(seletor);
                if (opts.length > 0) {
                    observer.disconnect();
                    resolve(opts);
                }
            });
            observer.observe(document.body, {childList: true, subtree: true});
            setTimeout(function() {
                observer.disconnect();
                resolve([]);
            }, timeout);
        });
    }
    """
    )


# =============================================================================
# Delegated Core Primitives (Fix.core)
# =============================================================================

def safe_click_no_scroll(driver: Any, element: Any) -> bool:
    """Dispara click sem scroll previo."""
    return bool(_fix_safe_click_no_scroll(driver, element))


def limpar_overlays_headless(driver: Any) -> bool:
    """Remove modals, tooltips e overlays que bloqueiam cliques."""
    return bool(_fix_limpar_overlays_headless(driver))


def aguardar_renderizacao_nativa(
    driver: Any,
    seletor_ou_condicao: Optional[str] = None,
    acao: Optional[str] = None,
    tempo_limite: Optional[int] = None,
) -> bool:
    """Aguarda renderizacao Angular nativa."""
    return bool(_fix_aguardar_renderizacao_nativa(driver, seletor_ou_condicao, acao, tempo_limite))


def esperar_elemento(
    driver: Any,
    seletor: str,
    timeout: int = 10,
    by: Any = None,
    visivel: bool = True,
    log: bool = False,
) -> Optional[Any]:
    """Aguarda presenca ou visibilidade de elemento no DOM."""
    return _fix_esperar_elemento(driver, seletor, timeout=timeout, by=by, visivel=visivel, log=log)


def aguardar_e_clicar(
    driver: Any,
    seletor: str,
    timeout: int = 10,
    log: bool = False,
    usar_js: bool = False,
) -> bool:
    """Aguarda elemento e clica de forma segura."""
    return bool(_fix_aguardar_e_clicar(driver, seletor, timeout=timeout, log=log, usar_js=usar_js))


def safe_click(
    driver: Any,
    elemento_ou_seletor: Any,
    timeout: int = 10,
    delay_depois: float = 0,
    log: bool = False,
) -> bool:
    """Clica em elemento com retries e verificacoes."""
    return bool(_fix_safe_click(driver, elemento_ou_seletor, timeout=timeout, delay_depois=delay_depois, log=log))


def preencher_campo(
    driver: Any,
    seletor: str,
    valor: str,
    timeout: int = 10,
    limpar_antes: bool = True,
    log: bool = False,
) -> bool:
    """Preenche campo de formulario Angular."""
    return bool(_fix_preencher_campo(driver, seletor, valor, timeout=timeout, limpar_antes=limpar_antes, log=log))


def buscar_seletor_robusto(
    driver: Any,
    seletores: List[str],
    timeout: int = 10,
    log: bool = False,
) -> Optional[Any]:
    """Busca primeiro elemento que corresponder a lista de seletores."""
    return _fix_buscar_seletor_robusto(driver, seletores, timeout=timeout, log=log)


def trocar_para_nova_aba(driver: Any, aba_original: Optional[str] = None) -> Optional[str]:
    """Troca o foco para a nova aba aberta."""
    orig = aba_original or getattr(driver, "current_window_handle", None)
    return _fix_trocar_para_nova_aba(driver, orig)


def fechar_abas_extras(driver: Any, handle_principal: Optional[str] = None) -> bool:
    """Fecha todas as abas exceto a principal."""
    principal = handle_principal or getattr(driver, "current_window_handle", None)
    if principal:
        _fix_forcar_fechamento_abas_extras(driver, principal)
        return True
    return True


# =============================================================================
# Retry Helper
# =============================================================================

def com_retry(
    func: Callable,
    max_tentativas: int = 3,
    backoff_base: float = 2,
    log: bool = False,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Executa funcao com retry e backoff exponencial."""
    for tentativa in range(max_tentativas):
        try:
            resultado = func(*args, **kwargs)
            if resultado or resultado == 0:
                if log:
                    logger.debug("com_retry: sucesso na tentativa %d", tentativa + 1)
                return resultado
        except Exception as e:
            if log:
                logger.warning("com_retry tentativa %d/%d: %s", tentativa + 1, max_tentativas, e)
            if tentativa < max_tentativas - 1:
                delay = backoff_base**tentativa
                if log:
                    logger.debug("com_retry: aguardando %ds...", delay)
                espera.assentar(None, delay)
            else:
                if log:
                    logger.error("com_retry: todas %d tentativas falharam", max_tentativas)
                return None
    return None


# =============================================================================
# Painel Loader & Buttons
# =============================================================================

def _aguardar_loader_painel(driver: Any, timeout: int = 10) -> None:
    """Aguarda sumir o loader do painel."""
    loader_xpath = "//pje-loader | //div[contains(@class, 'pje-loader')]"
    try:
        if espera.ate_presenca(driver, loader_xpath, teto=1):
            espera.ate_desaparecer(driver, loader_xpath, teto=timeout)
            espera.assentar(driver, 0.3)
    except Exception:
        pass


def _clicar_botao_movimentar(
    driver: Any, timeout: int = 10, log: bool = False
) -> bool:
    """Estrategia especializada para clicar em 'Movimentar processos'."""
    seletores = [
        "button.mat-raised-button",
        "//button[.//span[contains(text(),'Movimentar processos')]]",
        "//button[contains(., 'Movimentar processos')]",
    ]

    for sel in seletores:
        try:
            elemento = esperar_elemento(
                driver, sel, timeout=min(timeout, 8)
            )
            if elemento:
                safe_click_no_scroll(driver, elemento)
                if log:
                    logger.debug("Movimentar clicado com: %s", sel)
                espera.assentar(driver, 0.5)
                return True
        except Exception as e:
            if log:
                logger.warning("Seletor '%s' falhou: %s", sel, e)
            continue

    if log:
        logger.error("Todas as estrategias para Movimentar falharam")
    return False


def _clicar_botao_tarefa_processo(
    driver: Any, timeout: int = 10, log: bool = False
) -> bool:
    """Estrategia especializada para clicar em 'Abrir tarefa do processo'."""
    seletor = 'button[mattooltip="Abre a tarefa do processo"]'

    try:
        elemento = esperar_elemento(
            driver, seletor, timeout=timeout, log=log
        )
        if not elemento:
            if log:
                logger.error("Botao 'Abre a tarefa do processo' nao encontrado")
            return False

        # Scroll para o elemento
        _executar_js(
            driver,
            "arguments[0].scrollIntoView({block: 'center'});",
            elemento,
        )
        espera.assentar(driver, 0.5)

        if safe_click_no_scroll(driver, elemento):
            if log:
                logger.debug("Tarefa processo: clique ok")
            espera.assentar(driver, 1)
            return True

        if log:
            logger.error("Todas as estrategias para tarefa processo falharam")
        return False

    except Exception as e:
        if log:
            logger.error("Erro em _clicar_botao_tarefa_processo: %s", e)
        return False


# =============================================================================
# selecionar_opcao
# =============================================================================

def _abrir_e_selecionar_opcao(
    driver: Any,
    dropdown: Any,
    texto_opcao: str,
    exato: bool = False,
    log: bool = False,
) -> bool:
    """Abre dropdown e seleciona opcao pelo texto."""
    dropdown_aberto = False

    for tentativa in range(3):
        try:
            if tentativa == 0:
                safe_click_no_scroll(driver, dropdown)
            elif tentativa == 1:
                _executar_js(driver, "arguments[0].focus();", dropdown)
                _pressionar_tecla(driver, dropdown, "Enter", _KEY_ENTER)
            else:
                _executar_js(driver, "arguments[0].focus();", dropdown)
                _pressionar_tecla(driver, dropdown, "ArrowDown", _KEY_ARROW_DOWN)
            dropdown_aberto = True
            break
        except Exception:
            continue

    if not dropdown_aberto:
        return False

    espera.ate_presenca(driver, 'mat-option[role="option"], option', teto=3)
    opcoes = espera.elementos(
        driver,
        'mat-option[role="option"] span.mat-option-text, option',
        teto=2,
    )
    for opcao in opcoes:
        try:
            texto = (getattr(opcao, "text", "") or "").strip().lower()
            if exato:
                encontrado = texto == texto_opcao.lower()
            else:
                encontrado = texto_opcao.lower() in texto
            if encontrado:
                safe_click_no_scroll(driver, opcao)
                espera.assentar(driver, 0.3)
                if log:
                    logger.debug("Opcao '%s' selecionada", texto_opcao)
                return True
        except Exception:
            continue

    return False


def _selecionar_opcao_auto(
    driver: Any,
    texto_opcao: str,
    timeout: int = 10,
    exato: bool = False,
    log: bool = False,
) -> bool:
    """Auto-detecao de dropdown para selecionar_opcao."""
    estrategias = [
        'mat-select[formcontrolname="destinos"]',
        'mat-select[aria-label*="Tarefa destino"]',
        'mat-select[aria-label*="destino"]',
        'mat-select[placeholder*="destino"]',
        'mat-select[formcontrolname*="destino"]',
        "mat-select",
    ]

    for seletor_auto in estrategias:
        try:
            dropdown = espera.elemento(driver, seletor_auto, teto=5)
            if dropdown and _abrir_e_selecionar_opcao(
                driver, dropdown, texto_opcao, exato, log
            ):
                if log:
                    logger.debug(
                        "Auto-seletor '%s' funcionou", seletor_auto
                    )
                return True
        except Exception as e_auto:
            if log:
                logger.debug(
                    "Auto-seletor '%s' falhou: %s", seletor_auto, e_auto
                )
            continue

    if log:
        logger.error("Auto-detecao falhou para '%s'", texto_opcao)
    return False


def _selecionar_opcao_por_seletores(
    driver: Any,
    texto_opcao: str,
    seletores: List[str],
    timeout: int = 10,
    exato: bool = False,
    log: bool = False,
) -> bool:
    """Seleciona opcao tentando cada seletor da lista."""
    for seletor_atual in seletores:
        try:
            dropdown = espera.elemento(driver, seletor_atual, teto=timeout)
            if dropdown and _abrir_e_selecionar_opcao(
                driver, dropdown, texto_opcao, exato, log
            ):
                return True
        except Exception as e:
            if log:
                logger.debug(
                    "Seletor '%s' falhou: %s", seletor_atual, e
                )
            continue

    if log:
        logger.error(
            "Nenhum seletor funcionou para '%s'", texto_opcao
        )
    return False


def selecionar_opcao(
    driver: Any,
    seletor_dropdown: Optional[str],
    texto_opcao: str,
    timeout: int = 10,
    exato: bool = False,
    log: bool = False,
) -> bool:
    """Abre dropdown e seleciona opcao por texto."""
    if not seletor_dropdown or seletor_dropdown == 'auto':
        return _selecionar_opcao_auto(
            driver, texto_opcao, timeout, exato, log
        )

    mapa_seletores = {
        'destino': [
            'mat-select[formcontrolname="destinos"]',
            'mat-select[aria-label*="Tarefa destino"]',
            'mat-select[aria-label*="destino"]',
        ],
        'fase': [
            'mat-select[formcontrolname="fpglobal_faseProcessual"]',
            'mat-select[placeholder*="Fase processual"]',
        ],
    }

    if seletor_dropdown in mapa_seletores:
        return _selecionar_opcao_por_seletores(
            driver,
            texto_opcao,
            mapa_seletores[seletor_dropdown],
            timeout,
            exato,
            log,
        )

    return _selecionar_opcao_por_seletores(
        driver, texto_opcao, [seletor_dropdown], timeout, exato, log
    )


# =============================================================================
# PJe-specific filters
# =============================================================================

def aplicar_filtro_100(driver: Any) -> bool:
    """Aplica filtro para exibir 100 itens por pagina no painel global."""
    def _selecionar() -> bool:
        try:
            span_20 = espera.elemento(
                driver,
                "//span[contains(@class,'mat-select-min-line') and normalize-space(text())='20']",
                teto=3,
            )
            if not span_20:
                # Pode ja estar em 100
                return True
            mat_select = _sub_el(span_20, "xpath=ancestor::mat-select[@role='combobox']") or espera.elemento(driver, "mat-select[role='combobox']", teto=2)
            if mat_select:
                safe_click_no_scroll(driver, mat_select)
            aguardar_renderizacao_nativa(driver)

            espera.ate_presenca(driver, ".cdk-overlay-pane", teto=5)
            opcao_100 = espera.elemento(
                driver,
                "//mat-option[.//span[normalize-space(text())='100']]",
                teto=3,
            )
            if opcao_100:
                safe_click_no_scroll(driver, opcao_100)
            aguardar_renderizacao_nativa(driver)
            logger.debug("Clique na opcao 100 confirmado.")
            return True
        except Exception as e:
            logger.warning("Falha ao clicar em 100: %s", e)
            return False

    resultado = com_retry(
        _selecionar, max_tentativas=3, backoff_base=1.5, log=True
    )

    if resultado:
        logger.info("Filtro lista 100 aplicado")
    else:
        logger.error("Filtro lista 100 falhou apos todas tentativas")

    return bool(resultado)


def filtrofases(
    driver: Any,
    fases_alvo: Optional[List[str]] = None,
    tarefas_alvo: Optional[List[str]] = None,
    seletor_tarefa: str = "Tarefa do processo",
) -> bool:
    """Aplica filtros de fase processual e tarefa no painel global."""
    if fases_alvo is None:
        fases_alvo = ["liquidacao", "execucao"]

    fases = [f.strip().capitalize() for f in fases_alvo]

    logger.info("Filtrando fase processual: %s...", ", ".join(fases))

    # 1. Filtro de fase processual
    try:
        seletor_fase = (
            'mat-select[formcontrolname="fpglobal_faseProcessual"], '
            'mat-select[placeholder*="Fase processual"]'
        )
        if not aguardar_e_clicar(
            driver, seletor_fase, timeout=5, usar_js=True
        ):
            logger.error("Dropdown de fase nao encontrado.")
            return False

        aguardar_renderizacao_nativa(driver)

        script_fases = """
        var fases = arguments[0];
        var sucesso = 0;
        for (var i = 0; i < fases.length; i++) {
            var opcoes = document.querySelectorAll(
                'mat-option span.mat-option-text'
            );
            for (var j = 0; j < opcoes.length; j++) {
                if (opcoes[j].textContent.trim().toLowerCase() === fases[i].toLowerCase()) {
                    opcoes[j].parentElement.click();
                    sucesso++;
                    break;
                }
            }
        }
        return sucesso;
        """
        selecionadas = _executar_js(driver, script_fases, fases) or 0
        if selecionadas < 1:
            logger.error("Nao encontrou opcoes %s no painel.", fases_alvo)
            return False

        logger.debug("%d/%d fases selecionadas.", selecionadas, len(fases))
        corpo = espera.elemento(driver, "body", teto=2)
        _pressionar_tecla(driver, corpo, "Escape", _KEY_ESCAPE)
        aguardar_renderizacao_nativa(driver)

    except Exception as e:
        logger.error("Erro no filtro de fase: %s", e)
        return False

    # 2. Filtro de tarefa (opcional)
    if tarefas_alvo:
        logger.info("Filtrando tarefa: %s...", ", ".join(tarefas_alvo))
        try:
            tarefa_element = None
            for xpath in [
                f"//span[contains(text(), '{seletor_tarefa}')]",
                "//mat-label[contains(text(), 'Tarefa')]",
                "//label[contains(text(), 'Tarefa')]",
            ]:
                try:
                    tarefa_element = espera.elemento(driver, xpath, teto=2)
                    if tarefa_element:
                        break
                except Exception:
                    continue

            if not tarefa_element:
                logger.warning(
                    "Seletor de tarefa '%s' nao encontrado -- pulando.",
                    seletor_tarefa,
                )
            else:
                safe_click_no_scroll(driver, tarefa_element)
                aguardar_renderizacao_nativa(driver)

                script_tarefas = """
                var tarefas = arguments[0];
                var sucesso = 0;
                for (var i = 0; i < tarefas.length; i++) {
                    var opcoes = document.querySelectorAll(
                        'mat-option span.mat-option-text'
                    );
                    for (var j = 0; j < opcoes.length; j++) {
                        if (opcoes[j].textContent.trim().toLowerCase()
                            === tarefas[i].toLowerCase()) {
                            opcoes[j].parentElement.click();
                            sucesso++;
                            break;
                        }
                    }
                }
                return sucesso;
                """
                selecionadas = _executar_js(
                    driver, script_tarefas, tarefas_alvo
                ) or 0
                if selecionadas < 1:
                    logger.warning(
                        "Nao encontrou opcoes %s no painel de tarefas.",
                        tarefas_alvo,
                    )
                else:
                    logger.debug(
                        "%d/%d tarefas selecionadas.",
                        selecionadas,
                        len(tarefas_alvo),
                    )
                corpo = espera.elemento(driver, "body", teto=2)
                _pressionar_tecla(driver, corpo, "Escape", _KEY_ESCAPE)
                aguardar_renderizacao_nativa(driver)
        except Exception as e:
            logger.error("Erro no filtro de tarefa: %s", e)
            return False

    # 3. Clicar no botao de filtrar
    try:
        botao = espera.elemento(driver, "i.fas.fa-filter", teto=3)
        if botao:
            safe_click_no_scroll(driver, botao)
            logger.debug("Filtros aplicados.")
            _aguardar_loader_painel(driver)
    except Exception as e:
        logger.warning("Nao conseguiu clicar no botao de filtrar: %s", e)

    logger.info("Filtros aplicados com sucesso.")
    return True


# =============================================================================
# Driver Reset
# =============================================================================

def resetar_driver(driver: Any) -> bool:
    """Reseta estado do driver para pagina inicial do PJe."""
    try:
        fechar_abas_extras(driver)
        _executar_js(driver, "document.body.style.zoom='100%'")
        if hasattr(driver, "get"):
            driver.get("https://pje.trt2.jus.br/pjekz/")
        elif hasattr(driver, "page") and hasattr(driver.page, "goto"):
            driver.page.goto("https://pje.trt2.jus.br/pjekz/")
        espera.ate_url_conter(driver, "pjekz", teto=5)
        aguardar_renderizacao_nativa(driver)
        return True
    except Exception as e:
        logger.warning("Falha ao resetar driver: %s", e)
        return False
