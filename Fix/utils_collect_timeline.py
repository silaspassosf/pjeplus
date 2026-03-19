import logging
logger = logging.getLogger(__name__)

"""
Fix.utils_collect_timeline - Coleta de link de ato na timeline.

Extraido do monolito Fix/utils.py para manter o shim fino.
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def _log_msg_coleta(contexto: str, msg: str, debug: bool = False):
    """Logging unificado para coleta/insercao."""
    if debug:
        logger.info(f"[{contexto}] {msg}")


def coletar_link_ato_timeline(driver, numero_processo: str, debug: bool = False) -> bool:
    """
    Extrai link de validacao de atos da timeline clicando no icone de clipboard.
    """

    def log_msg(msg):
        _log_msg_coleta("LINK_ATO", msg, debug)

    log_msg(f"Iniciando coleta de link de ato para processo {numero_processo}")

    try:
        tipos_ato = ["Sentença", "Decisão", "Despacho"]

        documentos_cache = []
        try:
            from .documents import buscar_documentos_polo_ativo, buscar_documentos_sequenciais

            documentos_cache = buscar_documentos_polo_ativo(driver, debug=debug) or []
            if documentos_cache and debug:
                log_msg(f"(OTIMIZACAO) {len(documentos_cache)} documentos carregados via buscar_documentos_polo_ativo")
        except Exception:
            try:
                documentos_cache = buscar_documentos_sequenciais(driver, log=debug) or []
                if documentos_cache and debug:
                    log_msg(f"(OTIMIZACAO) {len(documentos_cache)} documentos carregados via buscar_documentos_sequenciais")
            except Exception:
                documentos_cache = []

        for tipo_ato in tipos_ato:
            log_msg(f"Procurando por '{tipo_ato}'...")

            try:
                from Prazo.p2b_core import SCRIPT_ANALISE_TIMELINE

                try:
                    resultados_js = driver.execute_script(SCRIPT_ANALISE_TIMELINE)
                except Exception as e_js_exec:
                    resultados_js = None
                    log_msg(f" (JS_ANALISE) Falha ao executar SCRIPT_ANALISE_TIMELINE: {e_js_exec}")

                if resultados_js:
                    elementos_timeline = []
                    for item in resultados_js:
                        try:
                            texto = (item.get('texto') if isinstance(item, dict) else None) or ''
                            el = item.get('elemento') if isinstance(item, dict) else None
                            if not el:
                                continue
                            if tipo_ato.lower() in texto.lower():
                                elementos_timeline.append(el)
                        except Exception:
                            continue

                    if elementos_timeline:
                        log_msg(f" (JS_ANALISE) Encontrados {len(elementos_timeline)} elementos via SCRIPT_ANALISE_TIMELINE")
            except Exception as e:
                _ = e

            elementos_timeline = []
            if documentos_cache:
                try:
                    all_items = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
                    candidatos = []
                    for doc in documentos_cache:
                        nome = (doc.get('nome') if isinstance(doc, dict) else None) or doc.get('titulo') if isinstance(doc, dict) else None or (doc.get('texto_completo') if isinstance(doc, dict) else None) or ''
                        if not nome:
                            nome = str(doc)
                        try:
                            if tipo_ato.lower() in nome.lower():
                                idx = doc.get('index') if isinstance(doc, dict) and 'index' in doc else None
                                if isinstance(idx, int) and idx < len(all_items):
                                    candidatos.append(all_items[idx])
                                else:
                                    for e in all_items:
                                        try:
                                            if tipo_ato.lower() in (e.text or '').lower():
                                                candidatos.append(e)
                                                break
                                        except Exception:
                                            continue
                        except Exception:
                            continue

                    if candidatos:
                        seen = set()
                        elementos_timeline = []
                        for el in candidatos:
                            try:
                                uid = el.id if hasattr(el, 'id') else (el.get_attribute('outerHTML')[:200])
                            except Exception:
                                uid = None
                            if uid not in seen:
                                elementos_timeline.append(el)
                                seen.add(uid)
                        if debug:
                            log_msg(f" (OTIMIZACAO) Encontrados {len(elementos_timeline)} elementos via documentos_cache")
                except Exception as e:
                    log_msg(f" (OTIMIZACAO) falhou ao aplicar documentos_cache: {e}")

            if not elementos_timeline:
                try:
                    all_items = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
                    candidatos = []
                    limite_scan = 60
                    for e in all_items[:limite_scan]:
                        try:
                            txt = (e.text or '').lower()
                            if tipo_ato.lower() in txt and e.is_displayed():
                                candidatos.append(e)
                        except Exception:
                            continue

                    if candidatos:
                        elementos_timeline = candidatos
                        log_msg(f" Encontrados {len(elementos_timeline)} elementos via scan em 'li.tl-item-container' (limit={limite_scan})")
                except Exception as e:
                    log_msg(f" Scan rapido da timeline falhou: {e}")

            if elementos_timeline:
                log_msg(f" Total de {len(elementos_timeline)} elemento(s) do tipo '{tipo_ato}' encontrado(s)")

                primeiro_elemento = elementos_timeline[0]
                log_msg(f" Processando primeiro elemento de '{tipo_ato}'")

                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", primeiro_elemento)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", primeiro_elemento)
                    log_msg(f" Elemento '{tipo_ato}' clicado e expandido")
                    time.sleep(1)
                except Exception as click_err:
                    log_msg(f" Erro ao clicar no elemento: {click_err}")
                    continue

                try:
                    seletor_clipboard = 'pje-icone-clipboard span[aria-label*="Copiar link de validação"]'

                    WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_clipboard))
                    )

                    link_validacao = driver.execute_script("""
                        var spans = document.querySelectorAll('div[style="display: block;"] span');
                        for (var i = 0; i < spans.length; i++) {
                            var text = spans[i].textContent.trim();
                            if (text.includes('Número do documento:')) {
                                var numero = text.split('Número do documento:')[1].trim();
                                if (numero) {
                                    return 'https://pje.trt2.jus.br/pjekz/validacao/' + numero + '?instancia=1';
                                }
                            }
                        }

                        var links = document.querySelectorAll('a[href*="validacao"]');
                        for (var i = 0; i < links.length; i++) {
                            var href = links[i].getAttribute('href');
                            if (href && href.includes('/validacao/')) {
                                return href;
                            }
                        }

                        return null;
                    """)

                    if link_validacao and isinstance(link_validacao, str) and link_validacao.strip():
                        log_msg(f" Link de validacao encontrado: {link_validacao}")

                        try:
                            from PEC.anexos import salvar_conteudo_clipboard

                            sucesso = salvar_conteudo_clipboard(
                                conteudo=link_validacao,
                                numero_processo=str(numero_processo),
                                tipo_conteudo=f"link_ato_{tipo_ato.lower()}_validacao",
                                debug=debug
                            )
                            if sucesso:
                                log_msg(f" Link de validacao de '{tipo_ato}' salvo com sucesso!")
                                return True
                            log_msg(f" Falha ao salvar link de validacao de '{tipo_ato}'")
                            return False
                        except ImportError:
                            log_msg(f" Modulo PEC.anexos nao disponivel, retornando link: {link_validacao}")
                            return True
                    else:
                        log_msg(f" Nao foi possivel encontrar link de validacao para '{tipo_ato}'")
                        continue

                except Exception as clipboard_err:
                    log_msg(f" Erro ao processar link de validacao: {clipboard_err}")
                    continue

        log_msg(" Nenhum link de ato foi coletado (Sentenca, Decisao ou Despacho)")
        return False

    except Exception as e:
        log_msg(f" Erro geral na coleta de link de ato: {e}")
        return False