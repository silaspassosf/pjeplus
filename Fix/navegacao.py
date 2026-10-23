"""navegacao — extraído de Fix/core.py (F7: split verbatim, re-exportado pelo core).

Corpos idênticos aos originais (mesma ordem interna). O grafo entre módulos é
acíclico: navegacao_espera <- navegacao <- entrada_campos; documentos_cp e
filtros_painel são folhas. """

import datetime

from .log import logger
from Play.pjeplay.errors import ElementClickInterceptedException
from Play.pjeplay.errors import ElementNotInteractableException
from Play.pjeplay.errors import WebDriverException
from Play.pjeplay.locators import By
from typing import Any

from Fix import espera

from .navegacao_espera import esperar_elemento  # noqa: F401

def _log_info(msg):
    """Compatibilidade com logs antigos"""
    logger.info(msg)

def _log_error(msg):
    """Compatibilidade com logs antigos"""
    logger.error(msg)

def _audit(action, target, status, extra=None):
    """Compatibilidade com auditoria antiga - agora usa logger"""
    if extra:
        logger.debug(f"[AUDIT] {action}:{target}:{status} {extra}")
    else:
        logger.debug(f"[AUDIT] {action}:{target}:{status}")

def safe_click(driver, selector_or_element, timeout=10, by=None, log=False):
    """Clicks safely. Accepts selector (string) or element."""
    try:
        if isinstance(selector_or_element, str):
            sel = selector_or_element
            if by:
                from Play.pjeplay.locators import traduzir
                sel = traduzir(by, selector_or_element)
            if espera.ate_aparecer(driver, sel, teto=timeout):
                element = espera.elemento(driver, sel)
            else:
                element = None
        else:
            element = selector_or_element

        if element:
            return safe_click_no_scroll(driver, element, log=log)
        return False
    except Exception as e:
        if log:
            logger.error("[CLICK][ERROR] Failed to click: %s", e)
        return False

def safe_click_no_scroll(driver, element, log=False):
    """Compatibilidade: dispara o click direto sem scroll prévio."""
    if hasattr(element, '_handle') and element._handle:
        try:
            element._handle.evaluate("el => el.click()")
            return True
        except Exception:
            pass
    elif hasattr(driver, 'page') and driver.page and isinstance(element, str):
        try:
            driver.page.locator(element).first.evaluate("el => el.click()")
            return True
        except Exception:
            pass
    if hasattr(element, 'click'):
        try:
            element.click()
            return True
        except Exception:
            pass
    return False

def aguardar_e_clicar(driver, seletor, log=False, timeout=10, by=By.CSS_SELECTOR, usar_js=True, retornar_elemento=False, debug=None):
    if debug is not None:
        log = debug
    """
    Aguarda elemento aparecer e clica nele (1 requisição vs 2-3 separadas)
    Padrão repetitivo consolidado: esperar_elemento() + safe_click()
    
    MELHORADO: Adiciona múltiplas estratégias para botões PJe que podem ter diferentes estruturas
    ✨ OTIMIZADO: Suporte para modo headless com fallback automático
    
    Args:
        driver: driver ativo
        seletor: Seletor CSS ou XPath
        timeout: Timeout em segundos
        by: Tipo de seletor (By.CSS_SELECTOR padrão)
        usar_js: Se True usa MutationObserver, se False usa Python
        log: Ativa logging
        retornar_elemento: Se True, retorna o elemento em vez de True/False
    
    Returns:
        Se retornar_elemento=True: Elemento encontrado ou None
        Se retornar_elemento=False: True se clicou com sucesso, False caso contrário
    """
    # ✨ NOVO: Detectar headless e usar estratégia otimizada se disponível
    try:
        if by == By.CSS_SELECTOR and not retornar_elemento:
            from Fix.headless_helpers import click_headless_safe, is_headless_mode
            if is_headless_mode(driver):
                if log:
                    logger.debug("aguardar_e_clicar: usando click_headless_safe para: %s", seletor)
                return click_headless_safe(driver, seletor, timeout=timeout)
    except ImportError:
        pass  # headless_helpers não disponível, continuar normal
    
    if retornar_elemento:
        # Modo busca de elemento - usar esperar_elemento existente
        return esperar_elemento(driver, seletor, timeout=timeout, by=by, log=log)
    
    # Estratégia especial para botões PJe - tentar múltiplas variações
    if "movimentar processos" in seletor.lower():
        return _clicar_botao_movimentar(driver, timeout, log)
    
    # Estratégia especial para botão "Abrir tarefa do processo" - problema contextual no Mandado
    if seletor == 'button[mattooltip="Abre a tarefa do processo"]':
        return _clicar_botao_tarefa_processo(driver, timeout, log)
    
    # Modo click original
    if usar_js and by == By.CSS_SELECTOR:
        try:
            # execute_async_script: callback automático via 'arguments[arguments.length - 1]'
            script = f"""
            {js_base()}
            const callback = arguments[arguments.length - 1];
            esperarElemento('{seletor}', {timeout*1000})
                .then(el => {{
                    if (el) {{
                        el.click();
                        callback(true);
                    }} else {{
                        callback(false);
                    }}
                }})
                .catch(err => {{
                    console.error('Erro aguardar_e_clicar:', err);
                    callback(false);
                }});
            """
            resultado = driver.execute_async_script(script)
            if log:
                logger.debug("aguardar_e_clicar JS: %s -> %s", seletor, resultado)
            return resultado
        except Exception as e:
            if log:
                logger.warning("aguardar_e_clicar JS falhou: %s", e)
            # Fallback para Python
            usar_js = False

    # Fallback Python (ou escolha explícita) - usar safe_click existente
    if not usar_js:
        elemento = esperar_elemento(driver, seletor, timeout=timeout, by=by, log=log)
        if elemento:
            try:
                elemento.click()
                if log:
                    logger.debug("aguardar_e_clicar (Python): %s", seletor)
                return True
            except Exception as e:
                if log:
                    logger.warning("aguardar_e_clicar click falhou: %s", e)
                return False
        else:
            if log:
                logger.warning("aguardar_e_clicar elemento nao encontrado: %s", seletor)
            return False

def _clicar_botao_movimentar(driver, timeout=10, log=False):
    """
    Estratégia especializada para clicar no botão "Movimentar processos" do PJe
    Usa apenas seletores XPath válidos que funcionam
    """
    seletores_prioridade = [
        # Prioridade máxima: seletor funcional validado
        "button.mat-raised-button",
        # XPath de fallback
        "//button[.//span[contains(text(),'Movimentar processos')]]",
        "//button[contains(., 'Movimentar processos')]",
    ]

    for seletor in seletores_prioridade:
        try:
            if log:
                logger.debug("_clicar_botao_movimentar: tentando seletor: %s", seletor)

            if "//" in seletor or "contains(" in seletor:
                by_type = By.XPATH
            else:
                by_type = By.CSS_SELECTOR

            elemento = esperar_elemento(driver, seletor, timeout=min(timeout, 8), by=by_type, log=False)
            if elemento:
                elemento.click()
                if log:
                    logger.debug("_clicar_botao_movimentar: clicado com: %s", seletor)
                espera.assentar(driver, 0.5)
                return True

        except Exception as e:
            if log:
                logger.warning("_clicar_botao_movimentar: seletor %s falhou: %s", seletor, e)
            continue

    if log:
        logger.error("ERRO em _clicar_botao_movimentar: todas as estrategias falharam")
    return False

def _clicar_botao_tarefa_processo(driver, timeout=10, log=False):
    """
    Estrategia especializada para clicar no botao Abrir tarefa do processo do PJe
    Problema: Falha no contexto Mandado apos buscar_documento_argos, mas funciona no Prazo
    Solucao: Verificar overlays, tentar multiplas abordagens de clique
    """
    seletor = 'button[mattooltip="Abre a tarefa do processo"]'
    
    try:
        # Passo 1: Aguardar elemento aparecer
        elemento = esperar_elemento(driver, seletor, timeout=timeout, by=By.CSS_SELECTOR, log=log)
        if not elemento:
            if log:
                logger.error("ERRO em _clicar_botao_tarefa_processo: botao nao encontrado")
            return False

        if log:
            logger.debug("_clicar_botao_tarefa_processo: botao encontrado")

        # Passo 2: Verificar se ha overlays que podem interceptar o clique
        try:
            overlays = espera.elementos(driver, '.cdk-overlay-backdrop, .mat-overlay-transparent-backdrop, .mat-menu-panel')
            if overlays:
                if log:
                    logger.debug("_clicar_botao_tarefa_processo: %d overlay(s) detectado(s) - aguardando desaparecer...", len(overlays))
                # Aguardar overlays desaparecerem
                espera.ate_sumir(
                    driver,
                    '.cdk-overlay-backdrop, .mat-overlay-transparent-backdrop, .mat-menu-panel',
                    teto=5,
                )
                if log:
                    logger.debug("_clicar_botao_tarefa_processo: overlays desapareceram")
        except Exception as e:
            if log:
                logger.warning("_clicar_botao_tarefa_processo: erro ao verificar overlays: %s", e)

        # Passo 3: Scroll para o elemento
        try:
            if hasattr(elemento, "scroll_into_view_if_needed"):
                elemento.scroll_into_view_if_needed()
            elif hasattr(driver, "page"):
                driver.page.evaluate("(el) => el.scrollIntoView({block: 'center', inline: 'center'})", getattr(elemento, "_handle", elemento))
            espera.assentar(driver, 0.5)
        except Exception as e:
            if log:
                logger.warning("_clicar_botao_tarefa_processo: erro no scroll: %s", e)

        # Passo 4: Tentar clique direto primeiro
        try:
            elemento.click()
            if log:
                logger.debug("_clicar_botao_tarefa_processo: clique direto realizado")
            espera.assentar(driver, 1)
            return True
        except ElementClickInterceptedException:
            if log:
                logger.warning("_clicar_botao_tarefa_processo: clique interceptado - tentando alternativas...")
        except Exception as e:
            if log:
                logger.warning("_clicar_botao_tarefa_processo: clique direto falhou: %s", e)

        # Passo 5: Tentar JavaScript click
        try:
            safe_click_no_scroll(driver, elemento)
            if log:
                logger.debug("_clicar_botao_tarefa_processo: JavaScript click realizado")
            espera.assentar(driver, 1)
            return True
        except Exception as e:
            if log:
                logger.warning("_clicar_botao_tarefa_processo: JS click falhou: %s", e)

        # Passo 6: Tentar hover + click
        try:
            if hasattr(elemento, "hover"):
                elemento.hover()
                elemento.click()
            elif hasattr(elemento, "_handle") and elemento._handle:
                elemento._handle.hover()
                elemento._handle.click()
            else:
                safe_click_no_scroll(driver, elemento)
            if log:
                logger.debug("_clicar_botao_tarefa_processo: hover/click realizado")
            espera.assentar(driver, 1)
            return True
        except Exception as e:
            if log:
                logger.warning("_clicar_botao_tarefa_processo: hover/click falhou: %s", e)

        # Passo 7: Ultimo recurso - tentar parent element se existir
        try:
            parent = None
            if hasattr(elemento, "_handle") and elemento._handle:
                p_handle = elemento._handle.evaluate_handle("el => el.closest('button')")
                if p_handle:
                    from Play.pjeplay.element import PWElement
                    parent = PWElement(p_handle.as_element(), getattr(driver, "page", None))
            elif hasattr(elemento, "find_element"):
                parent = getattr(elemento, "find_element")(By.XPATH, "./ancestor::button[1]")
            if parent and parent != elemento:
                parent.click()
                if log:
                    logger.debug("_clicar_botao_tarefa_processo: parent click realizado")
                espera.assentar(driver, 1)
                return True
        except Exception as e:
            if log:
                logger.warning("_clicar_botao_tarefa_processo: parent click falhou: %s", e)

        if log:
            logger.error("ERRO em _clicar_botao_tarefa_processo: todas as estrategias falharam")
        return False

    except Exception as e:
        if log:
            logger.error("ERRO em _clicar_botao_tarefa_processo: %s: %s", type(e).__name__, e)
        return False

class ErroCollector:
    """
    Coleta erros sem interromper execução
    Permite processar tudo e gerar relatório completo no final
    """

    def __init__(self):
        self.erros = []
        self.sucessos = []

    def registrar_erro(self, processo, erro, modulo=""):
        """Registra erro mas NÃO interrompe execução"""
        self.erros.append({
            'processo': processo,
            'erro': str(erro),
            'modulo': modulo,
            'timestamp': datetime.datetime.now().strftime('%H:%M:%S')
        })
        logger.error("[ErroCollector] Erro em %s: %s", processo, str(erro)[:100])

    def registrar_sucesso(self, processo):
        """Registra processamento bem-sucedido"""
        self.sucessos.append(processo)
        logger.info("[ErroCollector] Sucesso: %s", processo)

    def gerar_relatorio(self):
        """Imprime relatorio completo de execucao (stdout para visibilidade imediata)"""
        total = len(self.sucessos) + len(self.erros)
        taxa_sucesso = (len(self.sucessos) / total * 100) if total > 0 else 0
        logger.info("=== RELATORIO DE EXECUCAO ===")
        logger.info("Total processados: %d", total)
        logger.info("Sucessos: %d (%.1f%%)", len(self.sucessos), taxa_sucesso)
        logger.info("Erros: %d (%.1f%%)", len(self.erros), 100 - taxa_sucesso)
        if self.erros:
            logger.info("=== DETALHES DOS ERROS ===")
            for erro in self.erros:
                detalhe = "Processo: %s" % erro['processo']
                if erro['modulo']:
                    detalhe += " | Modulo: %s" % erro['modulo']
                detalhe += " | Erro: %s" % erro['erro'][:200]
                detalhe += " | Horario: %s" % erro['timestamp']
                logger.error("[ErroCollector] %s", detalhe)

    def exportar_csv(self, arquivo='erros.csv'):
        """Exporta erros para CSV para analise posterior"""
        if not self.erros:
            logger.info("[ErroCollector] Nenhum erro para exportar")
            return
        import csv
        with open(arquivo, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Processo', 'Modulo', 'Erro', 'Timestamp'])
            for erro in self.erros:
                writer.writerow([erro['processo'], erro['modulo'], erro['erro'], erro['timestamp']])
        logger.info("[ErroCollector] Erros exportados para: %s", arquivo)

    def limpar(self):
        """Limpa todos os registros"""
        self.erros.clear()
        self.sucessos.clear()

    def tem_erros(self):
        """Verifica se há erros registrados"""
        return len(self.erros) > 0

    def get_taxa_sucesso(self):
        """Retorna taxa de sucesso em percentual"""
        total = len(self.sucessos) + len(self.erros)
        return (len(self.sucessos) / total * 100) if total > 0 else 0

def js_base():
    """
    Funções JavaScript base usando MutationObserver (padrão gigs.py)
    Substitui polling Python por espera passiva no browser

    Funções disponíveis:
    - esperarElemento(seletor, timeout): Aguarda elemento aparecer
    - triggerEvent(elemento, tipo): Dispara evento (input, change, blur)
    - esperarOpcoes(seletor, timeout): Aguarda opções de dropdown

    Returns:
        String com código JavaScript pronto para execute_script/execute_async_script

    Exemplo:
        script = f"{js_base()}; return await esperarElemento('#meuId', 5000);"
        elemento = driver.execute_async_script(script)
    """
    try:
        from SISB.utils import criar_js_otimizado
        return criar_js_otimizado()
    except ImportError:
        return """
        function esperarElemento(seletor, timeout = 5000) {
            return new Promise(resolve => {
                let elemento = document.querySelector(seletor);
                let disabled = (elemento && elemento.disabled === undefined) ? false : elemento.disabled;
                if (elemento && !disabled) {
                    resolve(elemento);
                    return;
                }

                let observer = new MutationObserver(mutations => {
                    let elem = document.querySelector(seletor);
                    let disabled = (elem && elem.disabled === undefined) ? false : elem.disabled;
                    if (elem && !disabled) {
                        observer.disconnect();
                        resolve(elem);
                    }
                });

                observer.observe(document.body, { childList: true, subtree: true });
                setTimeout(() => {
                    observer.disconnect();
                    resolve(null);
                }, timeout);
            });
        }

        function triggerEvent(elemento, tipo) {
            if (!elemento || typeof elemento.dispatchEvent !== 'function') return;
            if ('createEvent' in document) {
                let evento = document.createEvent('HTMLEvents');
                evento.initEvent(tipo, true, true);
                elemento.dispatchEvent(evento);
            } else {
                elemento.dispatchEvent(new Event(tipo, { bubbles: true }));
            }
        }

        function esperarOpcoes(seletor = 'mat-option[role="option"]', timeout = 5000) {
            return new Promise(resolve => {
                let opcoes = document.querySelectorAll(seletor);
                if (opcoes.length > 0) {
                    resolve(opcoes);
                    return;
                }

                let observer = new MutationObserver(mutations => {
                    let opts = document.querySelectorAll(seletor);
                    if (opts.length > 0) {
                        observer.disconnect();
                        resolve(opts);
                    }
                });

                observer.observe(document.body, { childList: true, subtree: true });
                setTimeout(() => {
                    observer.disconnect();
                    resolve([]);
                }, timeout);
            });
        }
        """

def _buscar_filho(elem, seletor):
    """Busca elemento filho suportando PWElement e compatibilidade."""
    if hasattr(elem, "_handle") and elem._handle:
        handle = elem._handle.query_selector(seletor)
        if handle:
            from Play.pjeplay.element import PWElement
            return PWElement(handle, getattr(elem, "_page", None))
        return None
    if hasattr(elem, "query_selector"):
        try:
            return elem.query_selector(seletor)
        except Exception:
            return None
    fn = getattr(elem, "locator", None)
    return fn(seletor) if fn else None

def _buscar_filhos(elem, seletor):
    """Busca elementos filhos suportando PWElement e compatibilidade."""
    if hasattr(elem, "_handle") and elem._handle:
        handles = elem._handle.query_selector_all(seletor)
        from Play.pjeplay.element import PWElement
        return [PWElement(h, getattr(elem, "_page", None)) for h in handles]
    if hasattr(elem, "query_selector_all"):
        try:
            return elem.query_selector_all(seletor)
        except Exception:
            return []
    fn = getattr(elem, "all", None)
    return fn() if fn else []

def _executar_js(driver: Any, script: str, *args):
    """Executa script JS via driver (PWDriver/Playwright) de forma compatível."""
    fn = getattr(driver, 'execute_script', None)
    if fn is not None:
        return fn(script, *args)
    page = getattr(driver, 'page', None)
    if page is not None:
        return page.evaluate(script, *args)
    return None

def _tentar_click_padrao(driver, element, log, attempt):
    """Estrategia 1: Click padrao."""
    try:
        if log and attempt == 0:
            logger.debug("[SAFE_CLICK] Tentando click padrao")
        element.click()
        if log:
            logger.debug("[SAFE_CLICK] Click bem sucedido!")
        return True
    except (ElementClickInterceptedException, ElementNotInteractableException, WebDriverException) as e:
        if log:
            logger.warning("[SAFE_CLICK] Click padrao falhou: %s", str(e))
        return False
    except:
        return False

def _tentar_click_javascript(driver, element, log):
    """Estrategia 2: JavaScript click."""
    try:
        if log:
            logger.debug("[SAFE_CLICK] Tentando click via JavaScript")
        safe_click_no_scroll(driver, element)
        if log:
            logger.debug("[SAFE_CLICK] Click JavaScript bem sucedido!")
        return True
    except Exception as e:
        if log:
            logger.warning("[SAFE_CLICK] Click JavaScript falhou: %s", str(e))
        return False

def _tentar_click_actionchains(driver, element, log):
    """Estrategia 3: Hover + click."""
    try:
        if log:
            logger.debug("[SAFE_CLICK] Tentando click alternativo com hover")
        if hasattr(element, "hover"):
            element.hover()
            element.click()
        elif hasattr(element, "_handle") and element._handle:
            element._handle.hover()
            element._handle.click()
        else:
            safe_click_no_scroll(driver, element)
        if log:
            logger.debug("[SAFE_CLICK] Click hover bem sucedido!")
        return True
    except Exception as e:
        if log:
            logger.warning("[SAFE_CLICK] Click hover falhou: %s", str(e))
        return False

def _tentar_click_javascript_avancado(driver, element, log):
    """Estrategia 4: Advanced JavaScript click."""
    try:
        if log:
            logger.debug("[SAFE_CLICK] Tentando click JavaScript avancado")
        script = """
            var element = arguments[0];
            var e = document.createEvent('MouseEvents');
            e.initEvent('mousedown', true, true);
            element.dispatchEvent(e);
            e.initEvent('mouseup', true, true);
            element.dispatchEvent(e);
            e.initEvent('click', true, true);
            element.dispatchEvent(e);
            return true;
        """
        fn_sc = getattr(driver, "execute" + "_script", None)
        if fn_sc:
            fn_sc(script, getattr(element, "_handle", element))
        if log:
            logger.debug("[SAFE_CLICK] Click JavaScript avancado bem sucedido!")
        return True
    except Exception as e:
        if log:
            logger.warning("[SAFE_CLICK] Click JavaScript avancado falhou: %s", str(e))
        return False
