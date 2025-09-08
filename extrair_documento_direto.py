# extrair_documento_direto.py - Extrai conteúdo do documento ativo na tela do processo
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import time
import re

def extrair_direto(driver, timeout=10, debug=False, formatar=True):
    """
    Extrai o conteúdo do documento PDF ativo na tela do processo PJe DIRETAMENTE.
    SEM CLIQUES, SEM INTERAÇÃO, apenas leitura direta.
    Função única e completa com todas as funcionalidades integradas.
    
    Args:
        driver: WebDriver do Selenium
        timeout: Timeout para operações
        debug: Se True, exibe logs detalhados
        formatar: Se True, aplica formatação organizacional ao texto
    
    Returns:
        dict: {
            'conteudo': str,           # Texto formatado (se formatar=True)
            'conteudo_bruto': str,     # Texto original
            'info': dict,              # Metadados do documento
            'sucesso': bool,           # Se extração foi bem-sucedida
            'metodo': str              # Método que funcionou
        }
    """
    
    def log_debug(msg):
        """Função auxiliar para logs de debug"""
        if debug:
            print(f'[EXTRAIR_DIRETO] {msg}')
    
    def formatar_texto(texto_bruto):
        """Função auxiliar para organizar e formatar o texto extraído"""
        if not texto_bruto or not texto_bruto.strip():
            return ""
        
        try:
            log_debug("Aplicando formatação ao texto...")
            
            # 1. Limpeza inicial
            texto = texto_bruto.strip()
            
            # 2. Normalizar quebras de linha
            texto = re.sub(r'\r\n|\r', '\n', texto)
            
            # 3. Remover espaços excessivos
            texto = re.sub(r'[ \t]+', ' ', texto)
            
            # 4. Normalizar múltiplas quebras de linha
            texto = re.sub(r'\n\s*\n\s*\n+', '\n\n', texto)
            
            # 5. Organizar estrutura do documento
            linhas = texto.split('\n')
            linhas_formatadas = []
            
            for linha in linhas:
                linha = linha.strip()
                if not linha:
                    continue
                
                # Detectar cabeçalhos/títulos
                if (len(linha) < 100 and 
                    (linha.isupper() or 
                     any(palavra in linha.upper() for palavra in ['DECISÃO', 'DESPACHO', 'SENTENÇA', 'CONCLUSÃO', 'VISTOS']))):
                    linhas_formatadas.append(f"\n=== {linha} ===\n")
                    
                # Detectar parágrafos numerados
                elif re.match(r'^\d+[\.\)]\s*', linha):
                    linhas_formatadas.append(f"\n{linha}")
                    
                elif linha.startswith(('Ante o', 'Diante', 'Considerando', 'Tendo em vista', 'Por conseguinte')):
                    linhas_formatadas.append(f"\n{linha}")
                    
                elif linha.startswith(('DEFIRO', 'INDEFIRO', 'DETERMINO', 'HOMOLOGO')):
                    linhas_formatadas.append(f"\n>>> {linha}")
                    
                # Detectar assinaturas
                elif any(palavra in linha for palavra in ['Servidor Responsável', 'Juiz', 'Magistrado', 'Responsável']):
                    linhas_formatadas.append(f"\n--- {linha} ---")
                    
                # Detectar datas
                elif re.search(r'\d{1,2}/\d{1,2}/\d{4}', linha) and len(linha) < 50:
                    linhas_formatadas.append(f"\n[{linha}]")
                    
                else:
                    linhas_formatadas.append(linha)
            
            # 6. Juntar e fazer limpeza final
            texto_formatado = '\n'.join(linhas_formatadas)
            texto_formatado = re.sub(r'\n{3,}', '\n\n', texto_formatado)
            return texto_formatado.strip()
            
        except Exception as e:
            log_debug(f"❌ Erro na formatação: {e}")
            return texto_bruto
    
    def extrair_info_documento():
        """Função auxiliar para extrair informações do cabeçalho"""
        try:
            info = {}
            
            # Buscar título do documento
            try:
                titulo = driver.find_element(By.CSS_SELECTOR, "mat-card-title").text.strip()
                info['titulo'] = titulo
                log_debug(f"Título: {titulo}")
            except:
                info['titulo'] = ""
            
            # Buscar subtítulos
            try:
                subtitulos = driver.find_elements(By.CSS_SELECTOR, "mat-card-subtitle")
                info['subtitulos'] = [sub.text.strip() for sub in subtitulos if sub.text.strip()]
                log_debug(f"Subtítulos encontrados: {len(info['subtitulos'])}")
            except:
                info['subtitulos'] = []
            
            # Extrair ID do documento
            try:
                id_match = re.search(r'Id\s+(\w+)', info.get('titulo', ''))
                if id_match:
                    info['documento_id'] = id_match.group(1)
                    log_debug(f"ID extraído: {info['documento_id']}")
            except:
                info['documento_id'] = ""
            
            return info
            
        except Exception as e:
            log_debug(f"❌ Erro ao extrair informações: {e}")
            return {}
    
    # ===== INÍCIO DA FUNÇÃO PRINCIPAL =====
    resultado = {
        'conteudo': None,
        'conteudo_bruto': None,
        'info': {},
        'sucesso': False,
        'metodo': None
    }
    
    try:
        log_debug("Iniciando extração DIRETA do documento ativo...")
        
        # 1. Aguardar e verificar documento ativo
        try:
            documento_wrapper = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.ID, "documento"))
            )
            log_debug("✅ Elemento #documento encontrado")
            
        except Exception as timeout_error:
            log_debug(f"❌ Timeout aguardando #documento: {timeout_error}")
            try:
                documento_wrapper = driver.find_element(By.ID, "documento")
                log_debug("✅ Elemento #documento encontrado (busca direta)")
            except:
                log_debug("❌ Elemento #documento não encontrado")
                return resultado
        
        # 2. Buscar object PDF ativo
        try:
            pdf_object = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "object.conteudo-pdf"))
            )
            
            WebDriverWait(driver, timeout).until(
                lambda d: pdf_object.get_attribute("data") is not None
            )
            
            pdf_url = pdf_object.get_attribute("data")
            log_debug(f"✅ PDF Object encontrado com URL: {pdf_url}")
            
        except Exception as pdf_error:
            log_debug(f"❌ Erro ao encontrar PDF object: {pdf_error}")
            return resultado
        
        # 3. Extrair ID do documento
        object_id = pdf_object.get_attribute("id")
        doc_id = None
        if object_id:
            doc_id_match = re.search(r'obj(\d+)', object_id)
            doc_id = doc_id_match.group(1) if doc_id_match else None
            log_debug(f"📄 ID do documento extraído: {doc_id}")
        
        # 4. MÉTODO 1: PDF.js viewer (prioritário)
        try:
            log_debug("Tentando extrair do PDF.js viewer...")
            
            # Aguardar iframe carregar
            try:
                WebDriverWait(driver, 5).until(
                    lambda d: d.execute_script("""
                        var obj = document.querySelector('object.conteudo-pdf');
                        return obj && obj.contentWindow && obj.contentWindow.document;
                    """)
                )
            except:
                pass
            
            js_script = """
            try {
                var pdfFrame = document.querySelector('object[data*="viewer.html"], iframe[src*="viewer.html"]');
                if (pdfFrame) {
                    try {
                        var frameDoc = pdfFrame.contentDocument || pdfFrame.contentWindow.document;
                        
                        // Aguardar textLayers carregarem
                        var maxAttempts = 10;
                        var attempt = 0;
                        
                        while (attempt < maxAttempts) {
                            var textLayers = frameDoc.querySelectorAll('.textLayer, .page .textLayer');
                            
                            if (textLayers.length > 0) {
                                var fullText = '';
                                var hasValidText = false;
                                
                                for (var i = 0; i < textLayers.length; i++) {
                                    var pageText = textLayers[i].textContent || textLayers[i].innerText;
                                    if (pageText && pageText.trim().length > 10) {
                                        fullText += pageText + '\\n';
                                        hasValidText = true;
                                    }
                                }
                                
                                if (hasValidText) {
                                    return fullText.trim();
                                }
                            }
                            
                            var start = Date.now();
                            while (Date.now() - start < 100) {}
                            attempt++;
                        }
                        
                        var viewer = frameDoc.querySelector('#viewer');
                        if (viewer) {
                            var pages = viewer.querySelectorAll('.page');
                            var fullText = '';
                            for (var i = 0; i < pages.length; i++) {
                                var pageText = pages[i].textContent || pages[i].innerText;
                                if (pageText && pageText.trim().length > 10) {
                                    fullText += pageText + '\\n';
                                }
                            }
                            if (fullText.trim()) {
                                return fullText.trim();
                            }
                        }
                    } catch (e) {
                        console.log('Cross-origin restriction:', e);
                    }
                }
                
                // Buscar na janela principal
                var mainViewer = document.querySelector('#viewer');
                if (mainViewer) {
                    var pages = mainViewer.querySelectorAll('.page');
                    var fullText = '';
                    for (var i = 0; i < pages.length; i++) {
                        var pageText = pages[i].textContent || pages[i].innerText;
                        if (pageText && pageText.trim().length > 10) {
                            fullText += pageText + '\\n';
                        }
                    }
                    if (fullText.trim()) {
                        return fullText.trim();
                    }
                }
                
                var textLayers = document.querySelectorAll('.textLayer, .page .textLayer');
                if (textLayers.length > 0) {
                    var fullText = '';
                    for (var i = 0; i < textLayers.length; i++) {
                        var pageText = textLayers[i].textContent || textLayers[i].innerText;
                        if (pageText && pageText.trim().length > 10) {
                            fullText += pageText + '\\n';
                        }
                    }
                    if (fullText.trim()) {
                        return fullText.trim();
                    }
                }
                
                return null;
            } catch(e) {
                return null;
            }
            """
            
            resultado_js = driver.execute_script(js_script)
            if resultado_js and resultado_js.strip():
                log_debug(f"✅ Conteúdo extraído do PDF.js viewer ({len(resultado_js)} caracteres)")
                resultado['conteudo_bruto'] = resultado_js.strip()
                resultado['conteudo'] = formatar_texto(resultado_js) if formatar else resultado_js.strip()
                resultado['metodo'] = 'PDF.js viewer'
                resultado['sucesso'] = True
                resultado['info'] = extrair_info_documento()
                return resultado
                
        except Exception as js_error:
            log_debug(f"❌ Erro no PDF.js viewer: {js_error}")
        
        # 5. MÉTODO 2: Elementos DOM
        try:
            log_debug("Procurando texto em elementos DOM...")
            
            text_selectors = [
                f"#acess{doc_id}",
                "[id*='acess']",
                "[aria-label*='Conteúdo']",
                "[class*='texto-documento']",
                "[class*='conteudo-texto']",
                ".pdf-text-content",
                "[data-text]"
            ]
            
            for selector in text_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip() or element.get_attribute('textContent')
                        if text and len(text) > 50:
                            log_debug(f"✅ Texto encontrado via seletor DOM: {selector}")
                            resultado['conteudo_bruto'] = text.strip()
                            resultado['conteudo'] = formatar_texto(text) if formatar else text.strip()
                            resultado['metodo'] = f'DOM selector: {selector}'
                            resultado['sucesso'] = True
                            resultado['info'] = extrair_info_documento()
                            return resultado
                except:
                    continue
                    
        except Exception as dom_error:
            log_debug(f"❌ Erro na busca DOM: {dom_error}")
        
        # 6. MÉTODO 3: Download direto do PDF
        if pdf_url and "blob:" not in pdf_url:
            try:
                log_debug("Tentando extrair via download direto do PDF...")
                
                cookies = {c['name']: c['value'] for c in driver.get_cookies()}
                headers = {
                    'User-Agent': driver.execute_script("return navigator.userAgent;"),
                    'Referer': driver.current_url
                }
                
                response = requests.get(pdf_url, cookies=cookies, headers=headers, timeout=timeout)
                if response.status_code == 200:
                    log_debug(f"✅ PDF baixado ({len(response.content)} bytes)")
                    
                    # Tentar pdfplumber primeiro
                    try:
                        import pdfplumber
                        import io
                        
                        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
                            texto_completo = ""
                            for page in pdf.pages:
                                page_text = page.extract_text()
                                if page_text:
                                    texto_completo += page_text + "\n"
                        
                        if texto_completo.strip():
                            log_debug(f"✅ PDF extraído via pdfplumber ({len(texto_completo)} caracteres)")
                            resultado['conteudo_bruto'] = texto_completo.strip()
                            resultado['conteudo'] = formatar_texto(texto_completo) if formatar else texto_completo.strip()
                            resultado['metodo'] = 'pdfplumber download'
                            resultado['sucesso'] = True
                            resultado['info'] = extrair_info_documento()
                            return resultado
                            
                    except ImportError:
                        log_debug("⚠️ pdfplumber não disponível, tentando PyPDF2...")
                        
                        try:
                            import PyPDF2
                            import io
                            
                            pdf_file = io.BytesIO(response.content)
                            pdf_reader = PyPDF2.PdfReader(pdf_file)
                            
                            texto_completo = ""
                            for page in pdf_reader.pages:
                                texto_completo += page.extract_text() + "\n"
                            
                            if texto_completo.strip():
                                log_debug(f"✅ PDF extraído via PyPDF2 ({len(texto_completo)} caracteres)")
                                resultado['conteudo_bruto'] = texto_completo.strip()
                                resultado['conteudo'] = formatar_texto(texto_completo) if formatar else texto_completo.strip()
                                resultado['metodo'] = 'PyPDF2 download'
                                resultado['sucesso'] = True
                                resultado['info'] = extrair_info_documento()
                                return resultado
                                
                        except ImportError:
                            log_debug("⚠️ PyPDF2 também não disponível")
                        except Exception as pdf_error:
                            log_debug(f"❌ Erro ao processar PDF com PyPDF2: {pdf_error}")
                            
                    except Exception as pdf_error:
                        log_debug(f"❌ Erro ao processar PDF: {pdf_error}")
                        
            except Exception as url_error:
                log_debug(f"❌ Erro ao baixar PDF: {url_error}")
        
        log_debug("❌ Nenhum método de extração funcionou")
        resultado['info'] = extrair_info_documento()  # Pelo menos extrair info
        return resultado
        
    except Exception as e:
        log_debug(f"❌ Erro geral na extração: {e}")
        return resultado

if __name__ == "__main__":
    print("extrair_documento_direto.py - Função única para extração direta de documentos do PJe")
    print("Uso: from extrair_documento_direto import extrair_direto")
