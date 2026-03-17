import logging
logger = logging.getLogger(__name__)

"""
Fix.utils_collect_content - Coleta de conteudo por JS/CSS e transcricao.

Extraido do monolito Fix/utils.py para manter o shim fino.
"""

import re
import time
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def _log_msg_coleta(contexto: str, msg: str, debug: bool = False):
    """Logging unificado para coleta/insercao."""
    if debug:
        logger.info(f"[{contexto}] {msg}")


def coletar_conteudo_formatado_documento(driver, numero_processo: str = None, debug: bool = False) -> bool:
    """
    Extrai conteudo HTML de documento clicando em "Visualizar HTML original"
    e formata como transcricao.
    """

    def log_msg(msg):
        _log_msg_coleta("CONTEUDO_FORMATADO", msg, debug)

    log_msg(f"Iniciando coleta de conteudo formatado para processo {numero_processo or 'atual'}")

    try:
        tipo_documento = "documento"
        id_documento = "N/A"

        try:
            titulo_el = driver.find_element(By.CSS_SELECTOR, 'pje-historico-scroll-titulo h1, pje-historico-scroll-titulo h2, pje-historico-scroll-titulo strong')
            titulo_texto = titulo_el.text.strip()

            if titulo_texto:
                log_msg(f" Titulo encontrado: {titulo_texto}")

                match_tipo = re.search(r'^(.+?)\s*\(ID', titulo_texto)
                if match_tipo:
                    tipo_documento = match_tipo.group(1).strip()

                match_id = re.search(r'ID\s*(\d+)', titulo_texto)
                if match_id:
                    id_documento = match_id.group(1)

                log_msg(f" Tipo: {tipo_documento}, ID: {id_documento}")
        except Exception as e_titulo:
            log_msg(f" Nao foi possivel extrair metadados do titulo: {e_titulo}")

        seletores_botao = [
            'pje-documento-visualizador button[mattooltip="Visualizar HTML original"]',
            'pje-historico-scroll-titulo button[mattooltip="Visualizar HTML original"]',
            'button[mattooltip="Visualizar HTML original"]'
        ]

        botao_clicado = False
        for seletor in seletores_botao:
            try:
                botao = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
                )
                driver.execute_script("arguments[0].click();", botao)
                log_msg(f" Botao 'Visualizar HTML original' clicado (seletor: {seletor})")
                botao_clicado = True
                break
            except Exception:
                continue

        if not botao_clicado:
            log_msg(" Botao 'Visualizar HTML original' nao encontrado")
            return False

        time.sleep(0.5)
        try:
            modal = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-dialog-container pje-documento-original'))
            )
            log_msg(" Modal de documento original aberto")
        except Exception as e_modal:
            log_msg(f" Modal nao abriu: {e_modal}")
            return False

        time.sleep(0.5)
        try:
            preview_el = modal.find_element(By.CSS_SELECTOR, '#previewModeloDocumento')
            conteudo_texto = preview_el.text.strip()

            if not conteudo_texto:
                log_msg(" Preview esta vazio, tentando textContent via JS")
                conteudo_texto = driver.execute_script(
                    "return arguments[0].textContent;", preview_el
                ).strip()

            if not conteudo_texto:
                log_msg(" Conteudo do documento esta vazio")
                try:
                    botao_fechar = modal.find_element(By.CSS_SELECTOR, 'button[mat-dialog-close], button[aria-label*="Fechar"]')
                    driver.execute_script("arguments[0].click();", botao_fechar)
                except Exception as e:
                    _ = e
                return False

            log_msg(f" Conteudo extraido ({len(conteudo_texto)} caracteres)")

        except Exception as e_preview:
            log_msg(f" Erro ao extrair conteudo do preview: {e_preview}")
            return False

        texto_formatado = f'Transcrição do(a) {tipo_documento} (ID {id_documento}): \n"{conteudo_texto}"'
        log_msg(f" Texto formatado ({len(texto_formatado)} caracteres)")

        try:
            botao_fechar = modal.find_element(By.CSS_SELECTOR, 'button[mat-dialog-close], button[aria-label*="Fechar"]')
            driver.execute_script("arguments[0].click();", botao_fechar)
            log_msg(" Modal fechado")
            time.sleep(0.3)
        except Exception as e_fechar:
            log_msg(f" Aviso: nao foi possivel fechar modal: {e_fechar}")

        try:
            from PEC.anexos import salvar_conteudo_clipboard

            sucesso = salvar_conteudo_clipboard(texto_formatado, numero_processo or "atual", "conteudo_formatado", debug)
            if sucesso:
                log_msg(" Conteudo formatado salvo no clipboard interno")
            return sucesso
        except ImportError:
            log_msg(" Modulo PEC.anexos nao disponivel para salvar no clipboard")
            try:
                import pyperclip

                pyperclip.copy(texto_formatado)
                log_msg(" Conteudo copiado para clipboard do sistema (fallback)")
                return True
            except Exception:
                log_msg(" Nao foi possivel salvar no clipboard")
                return False

    except Exception as e:
        log_msg(f" Erro geral na coleta de conteudo formatado: {e}")
        return False


def coletar_conteudo_js(driver, numero_processo: str, codigo_js: str, tipo_conteudo: str, debug: bool = False) -> bool:
    """Coleta conteudo usando JavaScript personalizado."""

    def log_msg(msg):
        _log_msg_coleta("JS_COLETA", msg, debug)

    log_msg(f"Iniciando coleta JS para processo {numero_processo}")

    try:
        resultado = driver.execute_script(codigo_js)
        if resultado:
            if isinstance(resultado, dict):
                conteudo = "\n".join([f"{k}: {v}" for k, v in resultado.items()])
            elif isinstance(resultado, list):
                conteudo = "\n".join([str(item) for item in resultado])
            else:
                conteudo = str(resultado)

            log_msg(f" Conteudo extraido: {conteudo[:100]}...")

            try:
                from PEC.anexos import salvar_conteudo_clipboard

                return salvar_conteudo_clipboard(conteudo, numero_processo, tipo_conteudo, debug)
            except ImportError:
                log_msg(" Modulo PEC.anexos nao disponivel")
                return True
        else:
            log_msg(" JavaScript retornou resultado vazio")
            return False

    except Exception as e:
        log_msg(f" Erro na coleta JS: {e}")
        return False


def coletar_elemento_css(driver, numero_processo: str, seletor_css: str, tipo_conteudo: str,
                        atributo: Optional[str] = None, debug: bool = False) -> bool:
    """Coleta conteudo de elemento por seletor CSS."""

    def log_msg(msg):
        _log_msg_coleta("CSS_COLETA", msg, debug)

    log_msg(f"Iniciando coleta CSS para processo {numero_processo}")

    try:
        elemento = driver.find_element(By.CSS_SELECTOR, seletor_css)

        if elemento and elemento.is_displayed():
            if atributo:
                conteudo = elemento.get_attribute(atributo)
                log_msg(f" Atributo '{atributo}' extraido")
            else:
                conteudo = elemento.text.strip()
                log_msg(" Texto do elemento extraido")

            if conteudo:
                try:
                    from PEC.anexos import salvar_conteudo_clipboard

                    return salvar_conteudo_clipboard(conteudo, numero_processo, tipo_conteudo, debug)
                except ImportError:
                    log_msg(" Modulo PEC.anexos nao disponivel")
                    return True
            else:
                log_msg(" Elemento encontrado mas conteudo vazio")
                return False
        else:
            log_msg(f" Elemento nao encontrado: {seletor_css}")
            return False

    except Exception as e:
        log_msg(f" Erro na coleta CSS: {e}")
        return False


def executar_coleta_parametrizavel(driver, numero_processo, tipo_coleta, parametros=None, debug=False):
    """Compatibilidade com coleta_atos.py."""
    if tipo_coleta == "link_ato":
        from .utils_collect_timeline import coletar_link_ato_timeline

        return coletar_link_ato_timeline(driver, numero_processo, debug)
    elif tipo_coleta == "conteudo_formatado":
        return coletar_conteudo_formatado_documento(driver, numero_processo, debug)
    elif tipo_coleta == "js_generico":
        return coletar_conteudo_js(driver, numero_processo, parametros.get('codigo_js', ''), parametros.get('tipo_conteudo', 'js'), debug)
    elif tipo_coleta == "elemento_css":
        return coletar_elemento_css(driver, numero_processo, parametros.get('seletor_css', ''), parametros.get('tipo_conteudo', 'css'), parametros.get('atributo'), debug)
    return False