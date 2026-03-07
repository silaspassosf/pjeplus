import logging
logger = logging.getLogger(__name__)

"""
Fix.extracao_documento - Extração direta de documentos e helpers.

Separado de Fix.extracao para reduzir tamanho do arquivo principal.
"""

import re
import time
import pyperclip
from typing import Optional, Dict, Any, List, Union, Callable
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from Fix.log import logger, _log_info, _log_error
from Fix.selenium_base.wait_operations import wait
from Fix.selenium_base.element_interaction import safe_click

DEBUG = False


def extrair_direto(driver: WebDriver, timeout: int = 10, debug: bool = False, formatar: bool = True) -> Dict[str, Any]:
    """
    Extrai o conteúdo do documento PDF ativo na tela do processo PJe DIRETAMENTE.
    SEM CLIQUES, SEM INTERAÇÃO, apenas leitura direta.
    """
    def _checar_cabecalho_interno(passo):
        """Checagem interna do cabeçalho para debug - ROBUSTA.
        
        Verifica usando o botão 'Análise' como proxy (melhor indicador de
        cabeçalho funcional que imagem ou CSS).
        """
        try:
            # Verificar if botão "Análise" está presente e funcional
            botoes = driver.find_elements(By.CSS_SELECTOR, 'button.botao-detalhe[accesskey="t"]')
            
            if not botoes:
                if debug:
                    logger.info(f"[EXTRAIR_DIRETO][CABECALHO][{passo}] presente=False (botão não encontrado)")
                return False
            
            botao = botoes[0]
            
            try:
                is_displayed = botao.is_displayed()
            except Exception:
                is_displayed = False
            
            try:
                is_enabled = botao.is_enabled()
            except Exception:
                is_enabled = False
            
            try:
                size = botao.size
                has_size = size.get('width', 0) > 0 and size.get('height', 0) > 0
            except Exception:
                has_size = False
            
            cabecalho_ok = is_enabled and (is_displayed or has_size)
            
            if debug:
                logger.info(f"[EXTRAIR_DIRETO][CABECALHO][{passo}] presente={cabecalho_ok} displayed={is_displayed} enabled={is_enabled} tamanho={has_size}")
            
            return cabecalho_ok
            
        except Exception as e:
            if debug:
                logger.info(f"[EXTRAIR_DIRETO][CABECALHO][{passo}] erro ao checar: {str(e)[:100]}")
            return False

    resultado = {
        'conteudo': None,
        'conteudo_bruto': None,
        'info': {},
        'sucesso': False
    }
    try:
        # Checagem inicial
        _checar_cabecalho_interno('start')

        # Validar documento ativo
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.ID, "documento"))
            )
        except:
            try:
                driver.find_element(By.ID, "documento")
            except:
                _checar_cabecalho_interno('fail_documento_not_found')
                return resultado

        _checar_cabecalho_interno('documento_encontrado')

        # Tentar 3 estratégias de extração (Strategy Pattern)
        strategies = [
            lambda: _extrair_via_pdf_viewer(driver, timeout, debug),
            lambda: _extrair_via_iframe(driver, timeout, debug),
            lambda: _extrair_via_elemento_dom(driver, timeout, debug)
        ]
        metodos_nomes = ['PDF viewer direto', 'iframe', 'elemento DOM']
        for idx, strategy in enumerate(strategies):
            _checar_cabecalho_interno(f'before_strategy_{idx}_{metodos_nomes[idx]}')
            texto_bruto = strategy()
            _checar_cabecalho_interno(f'after_strategy_{idx}_{metodos_nomes[idx]}')
            if texto_bruto:
                if debug:
                    logger.info(f"[EXTRAIR_DIRETO][ESTRATEGIA] metodo='{metodos_nomes[idx]}' sucesso=True tamanho={len(texto_bruto)}")
                resultado['conteudo_bruto'] = texto_bruto
                resultado['conteudo'] = _extrair_formatar_texto(texto_bruto, debug) if formatar else texto_bruto
                resultado['metodo'] = metodos_nomes[idx]
                resultado['sucesso'] = True
                resultado['info'] = _extrair_info_documento(driver, debug)
                _checar_cabecalho_interno('sucesso_final')
                return resultado
            else:
                if debug:
                    logger.info(f"[EXTRAIR_DIRETO][ESTRATEGIA] metodo='{metodos_nomes[idx]}' falhou, tentando próxima...")
        resultado['info'] = _extrair_info_documento(driver, debug)
        _checar_cabecalho_interno('end_no_success')
        return resultado
    except Exception as e:
        if debug:
            logger.error(f'[EXTRAIR_DIRETO] Erro geral na extração: {e}')
        _checar_cabecalho_interno('exception')
        return resultado


def _normalizar_texto_decisao(texto: Optional[str]) -> str:
    if not texto:
        return ''
    return ' '.join(texto.split())


def _extrair_linha_tipo(linha: str) -> Optional[str]:
    """
    Detecta tipo de linha e aplica formatação apropriada.
    """
    linha_limpa = linha.strip()
    if not linha_limpa:
        return None

    # Detectar cabeçalhos/títulos
    eh_titulo = (len(linha_limpa) < 100 and
                (linha_limpa.isupper() or
                 any(p in linha_limpa.upper() for p in ['DECISÃO', 'DESPACHO', 'SENTENÇA', 'CONCLUSÃO', 'VISTOS'])))
    if eh_titulo:
        return f"\n=== {linha_limpa} ===\n"

    # Detectar parágrafos numerados
    if re.match(r'^\d+[\.\)]\s*', linha_limpa):
        return f"\n{linha_limpa}"

    # Detectar introduções
    eh_introducao = linha_limpa.startswith(('Ante o', 'Diante', 'Considerando', 'Tendo em vista', 'Por conseguinte'))
    if eh_introducao:
        return f"\n{linha_limpa}"

    # Detectar decisões/determinações
    eh_decisao = linha_limpa.startswith(('DEFIRO', 'INDEFIRO', 'DETERMINO', 'HOMOLOGO'))
    if eh_decisao:
        return f"\n>>> {linha_limpa}"

    # Detectar assinaturas
    eh_assinatura = any(p in linha_limpa for p in ['Servidor Responsável', 'Juiz', 'Magistrado', 'Responsável'])
    if eh_assinatura:
        return f"\n--- {linha_limpa} ---"

    # Detectar datas
    tem_data = re.search(r'\d{1,2}/\d{1,2}/\d{4}', linha_limpa) and len(linha_limpa) < 50
    if tem_data:
        return f"\n[{linha_limpa}]"

    return linha_limpa


def _extrair_formatar_texto(texto_bruto: str, debug: bool = False) -> str:
    """
    Formata o texto extraído com estrutura organizacional.
    """
    if not texto_bruto or not texto_bruto.strip():
        return ""

    try:
        texto = texto_bruto.strip()
        texto = re.sub(r'\r\n|\r', '\n', texto)
        texto = re.sub(r'[ \t]+', ' ', texto)
        texto = re.sub(r'\n\s*\n\s*\n+', '\n\n', texto)

        linhas = texto.split('\n')
        linhas_formatadas = [_extrair_linha_tipo(l) for l in linhas]
        linhas_formatadas = [l for l in linhas_formatadas if l is not None]

        texto_formatado = '\n'.join(linhas_formatadas)
        texto_formatado = re.sub(r'\n{3,}', '\n\n', texto_formatado)
        return texto_formatado.strip()

    except Exception as e:
        if debug:
            logger.error(f'[EXTRAIR_DIRETO] Erro na formatação: {e}')
        return texto_bruto


def _extrair_info_documento(driver: WebDriver, debug: bool = False) -> Dict[str, Any]:
    """Extrai informações do cabeçalho do documento."""
    try:
        info = {}

        try:
            titulo = driver.find_element(By.CSS_SELECTOR, "mat-card-title").text.strip()
            info['titulo'] = titulo
        except:
            info['titulo'] = ""

        try:
            subtitulos = driver.find_elements(By.CSS_SELECTOR, "mat-card-subtitle")
            info['subtitulos'] = [sub.text.strip() for sub in subtitulos if sub.text.strip()]
        except:
            info['subtitulos'] = []

        try:
            id_match = re.search(r'Id\s+(\w+)', info.get('titulo', ''))
            if id_match:
                info['documento_id'] = id_match.group(1)
        except:
            info['documento_id'] = ""

        return info

    except Exception as e:
        if debug:
            logger.info(f'[EXTRAIR_DIRETO] Erro ao extrair informações: {e}')
        return {}


def _extrair_via_pdf_viewer(driver: WebDriver, timeout: int, debug: bool = False) -> Optional[str]:
    """Strategy 1: Extrai texto do PDF viewer incorporado via JavaScript."""
    try:
        pdf_object = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "object.conteudo-pdf"))
        )

        WebDriverWait(driver, timeout).until(
            lambda d: pdf_object.get_attribute("data") is not None
        )

        js_script = """
        try {
            var pdfObject = document.querySelector('object[type="application/pdf"]') || document.querySelector('object.conteudo-pdf');
            if (!pdfObject) return null;
            var pdfDoc = pdfObject.contentDocument || pdfObject.contentWindow.document;
            if (!pdfDoc) return null;
            var v = pdfDoc.querySelector('#viewer');
            if (!v) return null;
            var text = v.textContent || '';
            return (text && text.trim().length > 100) ? text.trim() : null;
        } catch(e) { return null; }
        """

        resultado_js = driver.execute_script(js_script)
        if resultado_js and resultado_js.strip():
            return resultado_js.strip()

    except Exception as e:
        if debug:
            logger.error(f'[EXTRAIR_DIRETO] Erro na extração via PDF viewer: {e}')

    return None


def _extrair_via_iframe(driver: WebDriver, timeout: int, debug: bool = False) -> Optional[str]:
    """Strategy 2: Extrai texto de iframes alternativos."""
    if debug:
        logger.info('[EXTRAIR_DIRETO] Tentando extração via iframe...')

    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            try:
                driver.switch_to.frame(iframe)
                texto = driver.find_element(By.TAG_NAME, "body").text
                driver.switch_to.default_content()
                if texto and len(texto.strip()) > 100:
                    return texto.strip()
            except:
                driver.switch_to.default_content()

    except Exception as e:
        if debug:
            logger.info(f'[EXTRAIR_DIRETO] Erro na extração via iframe: {e}')
        driver.switch_to.default_content()

    return None


def _extrair_via_elemento_dom(driver: WebDriver, timeout: int, debug: bool = False) -> Optional[str]:
    """Strategy 3: Extrai texto de elemento DOM estruturado."""
    try:
        seletores = [
            "div.documento-conteudo",
            "div.conteudo-documento",
            "article",
            "main",
            "div[id*='documento']"
        ]

        for seletor in seletores:
            try:
                elemento = driver.find_element(By.CSS_SELECTOR, seletor)
                texto = elemento.text
                if texto and len(texto.strip()) > 100:
                    return texto.strip()
            except:
                pass

    except Exception as e:
        if debug:
            logger.error(f'[EXTRAIR_DIRETO] Erro na extração via DOM: {e}')

    return None


def extrair_documento(driver: WebDriver, regras_analise: Optional[Callable[[str], Any]] = None, timeout: int = 15, log: bool = False) -> Optional[str]:
    # Extrai texto do documento aberto, aplica regras se houver.
    # Retorna texto_final (str) ou None em caso de erro.
    texto_completo = None
    texto_final = None
    try:
        # Espera o botão HTML
        btn_html = wait(driver, '.fa-file-code', timeout)
        if not btn_html:
            _log_error('[EXTRAI][ERRO] Botão HTML não encontrado.')
            return None

        # Clica no botão HTML
        safe_click(driver, btn_html)
        time.sleep(1)

        # Extrai o texto do preview
        preview = wait(driver, '#previewModeloDocumento', timeout)
        if not preview:
            _log_error('[EXTRAI][ERRO] Preview do documento não encontrado.')
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            except Exception:
                pass
            return None

        texto_completo = preview.text

        # Fecha o modal ANTES de processar o texto
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            if DEBUG:
                _log_info('[EXTRAI] Modal HTML fechado.')
            time.sleep(0.5)
            # Pressiona TAB para tentar restaurar cabeçalho da aba detalhes
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.TAB)
            if DEBUG:
                _log_info('[WORKAROUND] Pressionada tecla TAB após fechar modal de documento.')
        except Exception as e_esc:
            if DEBUG:
                _log_info(f'[EXTRAI][WARN] Falha ao fechar modal com ESC: {e_esc}')

        if not texto_completo:
            _log_error('[EXTRAI][ERRO] Texto do preview vazio.')
            return None
        marcador = "Servidor Responsável"
        try:
            indice_marcador = texto_completo.rindex(marcador)
            indice_newline = texto_completo.find('\n', indice_marcador)
            if indice_newline != -1:
                texto_final = texto_completo[indice_newline:].strip()
            else:
                texto_final = texto_completo.strip()
            if DEBUG:
                _log_info(f'[EXTRAI] Conteúdo extraído abaixo de "{marcador}".')
        except ValueError:
            texto_final = texto_completo.strip()
            if DEBUG:
                _log_info(f'[EXTRAI] Marcador "{marcador}" não encontrado. Usando texto completo do documento.')

        # Aplica regras de análise se houver
        if regras_analise and callable(regras_analise):
            if DEBUG:
                _log_info('[EXTRAI] Aplicando regras de análise.')
            try:
                logger.info('[DEBUG][REGRAS] Iniciando análise de regras...')
                _ = regras_analise(texto_final)
                logger.info('[DEBUG][REGRAS] Análise de regras concluída.')
            except Exception as e_analise:
                logger.info(f'[EXTRAI][ERRO] Falha ao analisar regras: {e_analise}')

        if log:
            logger.info('[EXTRAI] Extração concluída.')
        return texto_final

    except Exception as e:
        if log:
            logger.info(f'[EXTRAI][ERRO] Falha geral ao extrair documento: {e}')
        try:
            if driver.find_elements(By.CSS_SELECTOR, '#previewModeloDocumento'):
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        except Exception:
            pass
        return None


def extrair_pdf(driver: WebDriver, log: bool = True) -> Optional[str]:
    try:
        # 1. Clicar no botão de exportar texto
        btn_export = driver.find_element(By.CSS_SELECTOR, '.fa-file-export')
        btn_export.click()
        if log:
            logger.info('[EXPORT] Botão .fa-file-export clicado.')
        # 2. Aguardar modal com título "Texto Extraído"
        for _ in range(20):
            modais = driver.find_elements(By.CSS_SELECTOR, 'pje-conteudo-documento-dialog')
            for modal in modais:
                try:
                    titulo = modal.find_element(By.CSS_SELECTOR, '.mat-dialog-title')
                    if 'Texto Extraído' in titulo.text:
                        # 2.1 Clicar no ícone de copiar texto
                        try:
                            btn_copiar = modal.find_element(By.CSS_SELECTOR, 'i.far.fa-copy')
                            btn_copiar.click()
                            time.sleep(0.3)
                            texto = pyperclip.paste()
                            if log:
                                logger.info('[EXPORT] Texto extraído do modal via copiar.')
                        except Exception as e:
                            if log:
                                logger.info(f'[EXPORT][ERRO] Falha ao copiar texto do modal: {e}')
                            # fallback: tentar pegar do <pre>
                            pre = modal.find_element(By.CSS_SELECTOR, 'pre')
                            texto = pre.text
                        # Fechar modal
                        try:
                            btn_fechar = modal.find_element(By.CSS_SELECTOR, 'button[mat-dialog-close]')
                            btn_fechar.click()
                        except Exception:
                            modal.send_keys(Keys.ESCAPE)
                        time.sleep(0.5)
                        return texto
                except Exception:
                    continue
            time.sleep(0.5)
        if log:
            logger.info('[EXPORT][ERRO] Modal de texto extraído não apareceu.')
        return None
    except Exception as e:
        if log:
            logger.info(f'[EXPORT][ERRO] {e}')
        return None