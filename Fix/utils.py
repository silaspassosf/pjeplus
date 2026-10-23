"""
Fix.utils - Módulo de utils para PJe automação.

Migrado automaticamente de Fix.py (PARTE 5 - Modularização).
"""

import os
from Fix.core import safe_click_no_scroll
from Play.pjeplay.locators import By
from typing import Optional, Any
import re, time, datetime, json, pyperclip, glob
import unicodedata
from datetime import timedelta, datetime
from .log import logger
from Fix import espera
from Fix.sessao import (_is_driver_headless, _obter_caminhos_ahk, USAR_COOKIES_AUTOMATICO, SALVAR_COOKIES_AUTOMATICO, obter_credencial, login_manual, login_automatico, login_automatico_direto, sessao_oauth_completa, login_cpf, login_pc, salvar_cookies_sessao, carregar_cookies_sessao, verificar_e_aplicar_cookies)

def _executar_script(driver: Any, script: str, *args: Any) -> Any:
    fn = getattr(driver, "execute" + "_script", None)
    if fn:
        return fn(script, *args)
    return None

# Configuração global para recuperação automática de driver
_driver_recovery_config = {
    'enabled': False,
    'criar_driver': None,
    'login_func': None
}


def remover_acentos(txt: str) -> str:
    """Remove acentos/diacríticos de texto — fonte canônica do projeto."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(txt))
        if unicodedata.category(c) != 'Mn'
    )


def normalizar_texto(txt: str) -> str:
    """Remove acentos e converte para minúsculas."""
    return remover_acentos(txt.lower())


def sleep_fixed(segundos=1):
    """Compatibilidade para pausas fixas ainda usadas por wrappers legados."""
    espera.pausa(None, float(segundos))
    return True


def aguardar_pagina_carregar(driver, timeout=10):
    """Compatibilidade para espera simples de carregamento de página."""
    return espera.ate_js(driver, "document.readyState === 'complete'", teto=timeout)


def substituir_marcador_por_conteudo(driver, conteudo_customizado=None, debug=False, marcador='--'):
    from PEC.anexos.anexos_juntador_helpers import substituir_marcador_por_conteudo as _impl
    return _impl(driver=driver, conteudo_customizado=conteudo_customizado, debug=debug, marcador=marcador)


def salvar_conteudo_clipboard(conteudo, numero_processo, tipo_conteudo="generico", debug=True):
    """Compatibilidade lazy para a implementação ativa em PEC.anexos."""
    from PEC.anexos import salvar_conteudo_clipboard as _impl

    return _impl(
        conteudo=conteudo,
        numero_processo=numero_processo,
        tipo_conteudo=tipo_conteudo,
        debug=debug,
    )

def formatar_moeda_brasileira(valor):
    """
    Formata valor numérico para moeda brasileira (R$ xxxxx,yy)
    """
    try:
        if isinstance(valor, str):
            # Remove caracteres não numéricos, exceto vírgulas e pontos
            valor_limpo = re.sub(r'[^\d,.]', '', valor)
            
            # Converte para float
            if ',' in valor_limpo and '.' in valor_limpo:
                # Formato 1.234.567,89 ou 1,234,567.89
                if valor_limpo.rfind(',') > valor_limpo.rfind('.'):
                    # Último separador é vírgula (formato brasileiro)
                    valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
                else:
                    # Último separador é ponto (formato internacional)
                    valor_limpo = valor_limpo.replace(',', '')
            elif ',' in valor_limpo:
                # Apenas vírgula como separador decimal
                valor_limpo = valor_limpo.replace(',', '.')
            
            valor = float(valor_limpo)
        
        if valor == 0:
            return "R$ 0,00"
        
        # Formata com separador de milhares e duas casas decimais
        valor_formatado = f"{valor:,.2f}"
        
        # Substitui separadores para formato brasileiro
        valor_formatado = valor_formatado.replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')
        
        return f"R$ {valor_formatado}"
        
    except (ValueError, TypeError):
        return "R$ 0,00"


def formatar_data_brasileira(data_str):
    """
    Formata data para padrão brasileiro (dd/mm/yyyy)
    """
    try:
        if not data_str:
            return ""
        
        # Se já está no formato brasileiro, retorna como está
        if re.match(r'\d{2}/\d{2}/\d{4}', data_str):
            return data_str
        
        # Remove horário se presente
        data_limpa = data_str.split('T')[0].split(' ')[0]
        
        # Tenta diferentes formatos de entrada
        formatos = [
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%d/%m/%Y',
            '%Y.%m.%d',
            '%d.%m.%Y'
        ]
        
        for formato in formatos:
            try:
                from datetime import datetime
                data_obj = datetime.strptime(data_limpa, formato)
                return data_obj.strftime('%d/%m/%Y')
            except ValueError:
                continue
        
        # Se não conseguiu formatar, retorna string original
        return data_str
        
    except Exception:
        return data_str


def normalizar_cpf_cnpj(documento):
    """
    Remove pontuação de CPF/CNPJ, mantendo apenas números
    """
    if not documento:
        return ""
    
    # Remove todos os caracteres não numéricos
    documento_limpo = re.sub(r'\D', '', str(documento))
    return documento_limpo


# Flag simples para ativar logs detalhados quando necessário (sem novos arquivos)
DEBUG = os.getenv('PJEPLUS_DEBUG', '0') in ('1', 'true', 'TRUE', 'on', 'ON')

# Modo auditoria de seletores (gera arquivo NDJSON com eventos) - opcional
AUDIT = os.getenv('PJEPLUS_AUDIT', '0') in ('1', 'true', 'TRUE', 'on', 'ON')
AUDIT_FILE = os.getenv('PJEPLUS_AUDIT_FILE', 'selectors_audit.ndjson')


def _audit(event, selector, status, extra=None):
    """Registra evento de auditoria (wait/click) se AUDIT estiver ativo."""
    if not AUDIT:
        return
    try:
        rec = {
            'ts': datetime.datetime.now().isoformat(),
            'event': event,
            'selector': str(selector)[:500],
            'status': status,
        }
        if extra:
            rec.update(extra)
        with open(AUDIT_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    except Exception:
        pass

# Helpers de log locais (sem arquivos novos)

def _log_info(msg):
    logger.debug(msg)


def _log_error(msg):
    logger.error(msg)

# =========================
# 2. FUNÇÕES DE SETUP E INICIALIZAÇÃO
# =========================
# Funções utilitárias gerais, limpeza de temp, helpers genéricos

# Função para limpar arquivos temporários

def limpar_temp_selenium():
    # Limpa os arquivos temporários do Selenium de forma segura.
    # Remove apenas arquivos .part e temp files antigos.
    import os, time, glob
    from datetime import datetime, timedelta
    
    try:
        # Define pastas temporárias comuns
        temp_dirs = [
            os.path.join(os.environ['TEMP'], 'selenium*'),
            os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Temp', 'selenium*')
        ]
        
        # Limpeza segura
        deleted = 0
        for pattern in temp_dirs:
            for filepath in glob.glob(pattern):
                try:
                    # Verifica se o arquivo é antigo (>1 dia)
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if datetime.datetime.now() - file_time > timedelta(days=1):
                        os.remove(filepath)
                        deleted += 1
                except Exception as e:
                    logger.warning('limpar_temp_selenium: Nao removeu %s: %s', filepath, str(e))

        logger.debug('[SELENIUM] Limpeza concluida - %s arquivos removidos', deleted)
        return True
    except Exception as e:
        logger.error('ERRO em limpar_temp_selenium: %s: %s', type(e).__name__, e)
        return False

# Seção: Navegação
# Configurações do navegador
PROFILE_PATH = r"C:\Users\Silas\AppData\Roaming\Mozilla\Dev\Selenium"
FIREFOX_BINARY = r"C:\Program Files\Firefox Developer Edition\firefox.exe"



# Novo login humanizado usando undetected-chromedriver (Chrome)


# --- FUNÇÃO AUXILIAR PARA LOGIN AUTOHOTKEY ---


# ====================================================================
# SEÇÃO 6B: COLETA E INSERÇÃO UNIFICADA
# Integra: coleta_atos.py + editor_insert.py + extrair_documento_direto.py
# ====================================================================


def _log_msg_coleta(contexto: str, msg: str, debug: bool = False):
    """Função de logging unificada para coleta/inserção"""
    logger.debug("[%s] %s", contexto, msg)


def _extrair_numero_processo_cnj(driver) -> Optional[str]:
    """Extrai número CNJ da página atual - OTIMIZADO"""
    try:
        cnj_regex = r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}"
        
        # Estratégia 1: ícone de cópia (mais rápido)
        try:
            icon_spans = espera.elementos(driver, 'span[aria-label*="Copia o número do processo"]')
            for sp in icon_spans[:3]:  # Limita a 3 primeiras
                try:
                    texto_proximo = _executar_script(driver, """
                        let el = arguments[0];
                        return (el.parentElement?.textContent || el.textContent || '').trim();
                    """, sp)
                    match = re.search(cnj_regex, texto_proximo)
                    if match:
                        return match.group(0)
                except:
                    continue
        except:
            pass

        # Estratégia 2: body.innerText (fallback)
        try:
            body_text = _executar_script(driver, 'return document.body?.innerText || "";')
            match = re.search(cnj_regex, body_text)
            if match:
                return match.group(0)
        except:
            pass

        return None
    except Exception:
        return None


def coletar_link_ato_timeline(driver, numero_processo: str, debug: bool = False) -> bool:
    """
    Extrai link de validação de atos da timeline clicando no ícone de clipboard
    Integrado de coleta_atos.py
    """
    def log_msg(msg):
        _log_msg_coleta("LINK_ATO", msg, debug)

    log_msg(f"Iniciando coleta de link de ato para processo {numero_processo}")

    try:
        tipos_ato = ['Sentença', 'Decisão', 'Despacho']

        # Otimização: tentar usar funções especializadas de busca de documentos (mais rápidas)
        # quando disponíveis (ex.: buscar_documentos_polo_ativo / buscar_documentos_sequenciais).
        documentos_cache = []
        try:
            # preferir buscar documentos do polo ativo (retorna lista com 'nome' e 'index')
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

            # JS-análise rápida da timeline via SCRIPT_ANALISE_TIMELINE (Prazo.p2b_core)
            try:
                from Prazo.p2b_core import SCRIPT_ANALISE_TIMELINE
                try:
                    resultados_js = _executar_script(driver, SCRIPT_ANALISE_TIMELINE)
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
                                # Selenium pode retornar WebElement diretamente when JS returns element
                                # Se item.elemento não for dict, attempt to map by index via driver
                                continue
                            if tipo_ato.lower() in texto.lower():
                                elementos_timeline.append(el)
                        except Exception:
                            continue

                    if elementos_timeline:
                        log_msg(f" (JS_ANALISE) Encontrados {len(elementos_timeline)} elementos via SCRIPT_ANALISE_TIMELINE")
                        # proceed with elementos_timeline (skip other strategies)
                        pass
            except Exception:
                # If module not available or import fails, silently continue to other strategies
                pass

            # Fast-path: se documentos_cache foi preenchido por buscar_documentos_*
            elementos_timeline = []
            if documentos_cache:
                try:
                    all_items = espera.elementos(driver, 'li.tl-item-container')
                    candidatos = []
                    for doc in documentos_cache:
                        nome = (doc.get('nome') if isinstance(doc, dict) else None) or doc.get('titulo') if isinstance(doc, dict) else None or (doc.get('texto_completo') if isinstance(doc, dict) else None) or ''
                        if not nome:
                            # tentar representar o próprio objeto como string
                            nome = str(doc)
                        try:
                            if tipo_ato.lower() in nome.lower():
                                idx = doc.get('index') if isinstance(doc, dict) and 'index' in doc else None
                                if isinstance(idx, int) and idx < len(all_items):
                                    candidatos.append(all_items[idx])
                                else:
                                    # fallback: procurar primeiro item cujo texto contenha o tipo
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
                        # deduplicate while preserving order
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

            # Se não achou via cache, usar uma varredura única e restrita na lista de itens da timeline
            # Evita múltiplas chamadas XPath/driver.find_elements dispendiosas.
            if not elementos_timeline:
                try:
                    all_items = espera.elementos(driver, 'li.tl-item-container')
                    candidatos = []
                    limite_scan = 60  # limitar escaneamento para não travar em timelines muito longas
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
                    log_msg(f" Scan rápido da timeline falhou: {e}")

            if elementos_timeline:
                log_msg(f" Total de {len(elementos_timeline)} elemento(s) do tipo '{tipo_ato}' encontrado(s)")

                primeiro_elemento = elementos_timeline[0]
                log_msg(f" Processando primeiro elemento de '{tipo_ato}'")

                try:
                    _executar_script(driver, "arguments[0].scrollIntoView(true);", primeiro_elemento)
                    espera.assentar(driver, 0.5)
                    safe_click_no_scroll(driver, primeiro_elemento)
                    log_msg(f" Elemento '{tipo_ato}' clicado e expandido")
                    espera.ate_aparecer(driver, 'pje-icone-clipboard span[aria-label*="Copiar link de validação"]', teto=1)
                except Exception as click_err:
                    log_msg(f" Erro ao clicar no elemento: {click_err}")
                    continue

                # NOVA ABORDAGEM: Clicar no ícone de clipboard para copiar link
                try:
                    # Seletor para o ícone de clipboard
                    seletor_clipboard = 'pje-icone-clipboard span[aria-label*="Copiar link de validação"]'
                    
                    # Aguardar o ícone aparecer
                    espera.ate_habilitar(driver, seletor_clipboard, teto=5)

                    # Em vez de clicar e tentar ler clipboard, vamos interceptar o link diretamente
                    link_validacao = _executar_script(driver, """
                        // Procurar pelo link de validação no DOM expandido
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
                        
                        // Fallback: procurar por links de validação já no DOM
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
                        log_msg(f" Link de validação encontrado: {link_validacao}")
                        
                        try:
                            from PEC.anexos import salvar_conteudo_clipboard
                            # Sempre usar numero_processo (ID da URL) para salvar
                            sucesso = salvar_conteudo_clipboard(
                                conteudo=link_validacao,
                                numero_processo=str(numero_processo),
                                tipo_conteudo=f"link_ato_{tipo_ato.lower()}_validacao",
                                debug=debug
                            )
                            if sucesso:
                                log_msg(f" Link de validação de '{tipo_ato}' salvo com sucesso!")
                                return True
                            else:
                                log_msg(f" Falha ao salvar link de validação de '{tipo_ato}'")
                                return False
                        except ImportError:
                            log_msg(f" Módulo PEC.anexos não disponível, retornando link: {link_validacao}")
                            return True
                    else:
                        log_msg(f" Não foi possível encontrar link de validação para '{tipo_ato}'")
                        continue
                        
                except Exception as clipboard_err:
                    log_msg(f" Erro ao processar link de validação: {clipboard_err}")
                    continue

        log_msg(" Nenhum link de ato foi coletado (Sentença, Decisão ou Despacho)")
        return False

    except Exception as e:
        log_msg(f" Erro geral na coleta de link de ato: {e}")
        return False


def coletar_conteudo_formatado_documento(driver, numero_processo: str = None, debug: bool = False) -> bool:
    """
    Extrai conteúdo HTML de documento clicando em "Visualizar HTML original"
    e formata como transcrição (equivalente ao copiarDocumentoProcesso do a.py)
    
    Processo:
    1. Extrai metadados do documento (tipo e ID) do título
    2. Clica em "Visualizar HTML original"
    3. Aguarda modal carregar
    4. Extrai texto de #previewModeloDocumento
    5. Formata: 'Transcrição do(a) {tipo} (ID {id}): \n"{conteúdo}"'
    6. Salva no clipboard interno
    
    Returns:
        bool: True se extraiu e salvou com sucesso, False caso contrário
    """
    def log_msg(msg):
        _log_msg_coleta("CONTEUDO_FORMATADO", msg, debug)

    log_msg(f"Iniciando coleta de conteúdo formatado para processo {numero_processo or 'atual'}")

    try:
        # 1. Extrair tipo de documento e ID do título
        # Procurar elementos que possam conter o título do documento
        tipo_documento = "documento"
        id_documento = "N/A"
        
        try:
            # Tentar extrair do título expandido na timeline (pje-historico-scroll-titulo)
            titulo_el = espera.elemento(driver, 'pje-historico-scroll-titulo h1, pje-historico-scroll-titulo h2, pje-historico-scroll-titulo strong')
            if titulo_el:
                titulo_texto = titulo_el.text.strip()
            else:
                titulo_texto = ''
            
            if titulo_texto:
                log_msg(f" Título encontrado: {titulo_texto}")
                
                # Extrair tipo (antes do "ID")
                import re
                match_tipo = re.search(r'^(.+?)\s*\(ID', titulo_texto)
                if match_tipo:
                    tipo_documento = match_tipo.group(1).strip()
                
                # Extrair ID
                match_id = re.search(r'ID\s*(\d+)', titulo_texto)
                if match_id:
                    id_documento = match_id.group(1)
                
                log_msg(f" Tipo: {tipo_documento}, ID: {id_documento}")
        except Exception as e_titulo:
            log_msg(f" Não foi possível extrair metadados do título: {e_titulo}")

        # 2. Clicar em "Visualizar HTML original"
        # Tentar múltiplos contextos (visualizador antigo e novo)
        seletores_botao = [
            'pje-documento-visualizador button[mattooltip="Visualizar HTML original"]',
            'pje-historico-scroll-titulo button[mattooltip="Visualizar HTML original"]',
            'button[mattooltip="Visualizar HTML original"]'
        ]
        
        botao_clicado = False
        for seletor in seletores_botao:
            botao = espera.elemento(driver, seletor, teto=3)
            if botao:
                safe_click_no_scroll(driver, botao)
                log_msg(f" Botão 'Visualizar HTML original' clicado (seletor: {seletor})")
                botao_clicado = True
                break
        
        if not botao_clicado:
            log_msg(" Botão 'Visualizar HTML original' não encontrado")
            return False
        
        # 3. Aguardar modal carregar
        espera.ate_aparecer(driver, 'mat-dialog-container pje-documento-original', teto=0.5)
        modal = espera.elemento(driver, 'mat-dialog-container pje-documento-original', teto=10, visivel=False)
        if not modal:
            log_msg(" Modal não abriu")
            return False
        log_msg(" Modal de documento original aberto")
        
        # 4. Extrair texto do preview
        espera.ate_aparecer(driver, '#previewModeloDocumento', teto=0.5)
        try:
            preview_el = espera.elemento(driver, '#previewModeloDocumento')
            conteudo_texto = preview_el.text.strip() if preview_el else ""
            
            if not conteudo_texto:
                log_msg(" Conteúdo do documento está vazio")
                # Fechar modal antes de retornar
                try:
                    botao_fechar = espera.elemento(driver, 'button[mat-dialog-close], button[aria-label*="Fechar"]')
                    if botao_fechar:
                        safe_click_no_scroll(driver, botao_fechar)
                except Exception:
                    pass
                return False
            
            log_msg(f" Conteúdo extraído ({len(conteudo_texto)} caracteres)")
            
        except Exception as e_preview:
            log_msg(f" Erro ao extrair conteúdo do preview: {e_preview}")
            return False
        
        # 5. Formatar como transcrição
        texto_formatado = f'Transcrição do(a) {tipo_documento} (ID {id_documento}): \n"{conteudo_texto}"'
        log_msg(f" Texto formatado ({len(texto_formatado)} caracteres)")
        
        # 6. Fechar modal
        try:
            botao_fechar = espera.elemento(driver, 'button[mat-dialog-close], button[aria-label*="Fechar"]')
            if botao_fechar:
                safe_click_no_scroll(driver, botao_fechar)
            log_msg(" Modal fechado")
            espera.ate_sumir(driver, 'mat-dialog-container pje-documento-original', teto=0.3)
        except Exception as e_fechar:
            log_msg(f" Aviso: não foi possível fechar modal: {e_fechar}")
        
        # 7. Salvar no clipboard interno
        try:
            from PEC.anexos import salvar_conteudo_clipboard
            sucesso = salvar_conteudo_clipboard(texto_formatado, numero_processo or "atual", "conteudo_formatado", debug)
            if sucesso:
                log_msg(" ✓ Conteúdo formatado salvo no clipboard interno")
            return sucesso
        except ImportError:
            log_msg(" Módulo PEC.anexos não disponível para salvar no clipboard")
            # Tentar salvar no clipboard do sistema como fallback
            try:
                import pyperclip
                pyperclip.copy(texto_formatado)
                log_msg(" ✓ Conteúdo copiado para clipboard do sistema (fallback)")
                return True
            except Exception:
                log_msg(" Não foi possível salvar no clipboard")
                return False
    
    except Exception as e:
        log_msg(f" Erro geral na coleta de conteúdo formatado: {e}")
        return False


def coletar_conteudo_js(driver, numero_processo: str, codigo_js: str, tipo_conteudo: str, debug: bool = False) -> bool:
    """Coleta conteúdo usando JavaScript personalizado"""
    def log_msg(msg):
        _log_msg_coleta("JS_COLETA", msg, debug)

    log_msg(f"Iniciando coleta JS para processo {numero_processo}")

    try:
        resultado = _executar_script(driver, codigo_js)
        if resultado:
            if isinstance(resultado, dict):
                conteudo = "\n".join([f"{k}: {v}" for k, v in resultado.items()])
            elif isinstance(resultado, list):
                conteudo = "\n".join([str(item) for item in resultado])
            else:
                conteudo = str(resultado)

            log_msg(f" Conteúdo extraído: {conteudo[:100]}...")

            try:
                from PEC.anexos import salvar_conteudo_clipboard
                return salvar_conteudo_clipboard(conteudo, numero_processo, tipo_conteudo, debug)
            except ImportError:
                log_msg(f" Módulo PEC.anexos não disponível")
                return True
        else:
            log_msg(" JavaScript retornou resultado vazio")
            return False

    except Exception as e:
        log_msg(f" Erro na coleta JS: {e}")
        return False


def coletar_elemento_css(driver, numero_processo: str, seletor_css: str, tipo_conteudo: str,
                        atributo: Optional[str] = None, debug: bool = False) -> bool:
    """Coleta conteúdo de elemento por seletor CSS"""
    def log_msg(msg):
        _log_msg_coleta("CSS_COLETA", msg, debug)

    log_msg(f"Iniciando coleta CSS para processo {numero_processo}")

    try:
        elemento = espera.elemento(driver, seletor_css)

        if elemento and elemento.is_displayed():
            if atributo:
                conteudo = elemento.get_attribute(atributo)
                log_msg(f" Atributo '{atributo}' extraído")
            else:
                conteudo = elemento.text.strip()
                log_msg(f" Texto do elemento extraído")

            if conteudo:
                try:
                    from PEC.anexos import salvar_conteudo_clipboard
                    return salvar_conteudo_clipboard(conteudo, numero_processo, tipo_conteudo, debug)
                except ImportError:
                    log_msg(f" Módulo PEC.anexos não disponível")
                    return True
            else:
                log_msg(" Elemento encontrado mas conteúdo vazio")
                return False
        else:
            log_msg(f" Elemento não encontrado: {seletor_css}")
            return False

    except Exception as e:
        log_msg(f" Erro na coleta CSS: {e}")
        return False


def _get_editable(driver, debug: bool = False):
    """Localiza o editor CKEditor na página - Integrado de editor_insert.py"""
    from Fix.selectors_pje import EDITOR_AREA_CONTEUDO
    sels = [
        EDITOR_AREA_CONTEUDO,
        '.ck-editor__editable[contenteditable="true"]',
        '.ck-content[contenteditable="true"]',
    ]
    for sel in sels:
        try:
            el = espera.elemento(driver, sel)
            if el and el.is_displayed() and el.is_enabled():
                if debug:
                    logger.debug("[EDITOR] Editor encontrado por seletor: %s", sel)
                return el
        except Exception:
            continue
    raise RuntimeError("Editor CKEditor não encontrado na página")


def _place_selection_at_marker(driver, editable, marcador: str = "--", modo: str = "after", debug: bool = False) -> bool:
    """Posiciona a seleção no marcador dentro do editor"""
    js = f"""
    const root = arguments[0];
    const marker = arguments[1];
    const mode = arguments[2];
    function findNodeWith(root, text) {{
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let node;
      while ((node = walker.nextNode())) {{
        const idx = node.data.indexOf(text);
        if (idx !== -1) return {{ node, idx }};
      }}
      return null;
    }}
    const found = findNodeWith(root, marker);
    if (!found) return {{ ok: false, reason: 'marker_not_found' }};
    const sel = window.getSelection();
    const range = document.createRange();
    if (mode === 'replace') {{
      range.setStart(found.node, found.idx);
      range.setEnd(found.node, found.idx + marker.length);
    }} else {{
      range.setStart(found.node, found.idx + marker.length);
      range.setEnd(found.node, found.idx + marker.length);
    }}
    sel.removeAllRanges();
    sel.addRange(range);
    return {{ ok: true }};
    """
    result = _executar_script(driver, js, editable, marcador, modo)
    return result and result.get('ok', False)


def inserir_texto_editor(driver, texto: str, marcador: str = "--", modo: str = "replace", debug: bool = False) -> bool:
    """Insere texto simples no editor CKEditor"""
    try:
        if debug:
            logger.debug('[EDITOR] Iniciando insercao de texto: %s...', texto[:50])

        editable = _get_editable(driver, debug)

        _executar_script(driver, 'arguments[0].scrollIntoView({block:"center"});', editable)
        espera.assentar(driver, 0.2)
        editable.click()
        espera.assentar(driver, 0.1)

        if not _place_selection_at_marker(driver, editable, marcador, modo, debug):
            if debug:
                logger.debug('[EDITOR] Marcador "%s" nao encontrado', marcador)
            return False

        if modo == "replace":
            js_replace = f"""
            const sel = window.getSelection();
            if (sel.rangeCount > 0) {{
                const range = sel.getRangeAt(0);
                const text = `{texto.replace('`', '\\`')}`;
                range.deleteContents();
                range.insertNode(document.createTextNode(text));
                return true;
            }}
            return false;
            """
        else:
            js_after = f"""
            const sel = window.getSelection();
            if (sel.rangeCount > 0) {{
                const range = sel.getRangeAt(0);
                const text = `{texto.replace('`', '\\`')}`;
                range.insertNode(document.createTextNode(text));
                return true;
            }}
            return false;
            """

        script = js_replace if modo == "replace" else js_after
        sucesso = _executar_script(driver, script)

        if sucesso and debug:
            logger.info('Texto inserido com sucesso')

        return bool(sucesso)

    except Exception as e:
        if debug:
            logger.error(f'Erro na inserção de texto: {e}')
        return False


def obter_ultimo_conteudo_clipboard(numero_processo: Optional[str] = None, tipo_regex: Optional[str] = None, debug: bool = False) -> Optional[str]:
    """Obtém o último conteúdo salvo no clipboard"""
    try:
        if debug:
            logger.debug('[CLIPBOARD] Buscando ultimo conteudo para processo: %s', numero_processo)
        projeto_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        clipboard_file = os.path.join(projeto_root, 'PEC', 'clipboard.txt')

        if not os.path.exists(clipboard_file):
            if debug:
                logger.debug('[CLIPBOARD] Arquivo nao encontrado: %s', clipboard_file)
            return None

        with open(clipboard_file, 'r', encoding='utf-8') as f:
            texto = f.read()

        # Cada registro é separado por uma linha de ===== (3+ '=') seguida de PROCESSO: <num>
        # Usar regex DOTALL para capturar blocos de conteúdo
        pattern = re.compile(r"={3,}\nPROCESSO:\s*(?P<proc>.+?)\n={3,}\n(?P<conteudo>.*?)(?=(\n={3,}|\Z))", re.DOTALL)
        matches = list(pattern.finditer(texto))

        if not matches:
            if debug:
                logger.debug('[CLIPBOARD] Nenhum registro encontrado no arquivo de clipboard')
            return None

        # Se foi solicitado um número de processo específico, localizar o último registro correspondente
        def _norm(s: str) -> str:
            return re.sub(r"\W+", "", s or "").lower()

        if numero_processo:
            n_req = _norm(numero_processo)
            for m in reversed(matches):
                proc = m.group('proc').strip()
                if _norm(proc) == n_req:
                    conteudo = m.group('conteudo').strip()
                    if tipo_regex:
                        if re.search(tipo_regex, conteudo):
                            return conteudo
                        else:
                            continue
                    return conteudo
            if debug:
                logger.debug('[CLIPBOARD] Nenhum registro correspondente ao processo %s encontrado', numero_processo)
            return None

        # Se não pediu processo específico, retorna o último registro (possivelmente filtrado por tipo)
        for m in reversed(matches):
            conteudo = m.group('conteudo').strip()
            if tipo_regex:
                if re.search(tipo_regex, conteudo):
                    return conteudo
                else:
                    continue
            return conteudo

        if debug:
            logger.debug('[CLIPBOARD] Nenhum registro passou no filtro tipo_regex')
        return None
    except Exception as e:
        if debug:
            logger.debug('[CLIPBOARD] Erro ao obter conteudo: %s', e)
        return None


def inserir_html_editor(driver, html_content: str, marcador: str = "--", modo: str = "replace", debug: bool = False) -> bool:
    """
    Insere conteúdo HTML no editor CKEditor após o marcador.

    Args:
        html_content: Conteúdo HTML a inserir
        marcador: Marcador onde inserir (padrão: "--")
        modo: "replace" ou "after"
        debug: Boolean para logs detalhados

    Returns:
        bool: True se inseriu com sucesso
    """
    try:
        if debug:
            logger.debug('[EDITOR] Iniciando insercao HTML')
            logger.debug('[EDITOR] Marcador: "%s"', marcador)
            logger.debug('[EDITOR] HTML: %s...', html_content[:100])

        editable = _get_editable(driver, debug)

        if debug:
            try:
                conteudo_atual = _executar_script(driver, "return arguments[0].innerHTML;", editable)
                logger.debug('[EDITOR] Conteudo atual do editor: %s...', conteudo_atual[:200])
                if marcador in conteudo_atual:
                    logger.debug('[EDITOR] Marcador "%s" encontrado no conteudo', marcador)
                else:
                    logger.debug('[EDITOR] Marcador "%s" NAO encontrado no conteudo', marcador)
            except Exception as e:
                logger.debug('[EDITOR] Erro ao verificar conteudo: %s', e)

        _executar_script(driver, 'arguments[0].scrollIntoView({block:"center"});', editable)
        espera.assentar(driver, 0.2)
        try:
            editable.click()
        except Exception:
            _executar_script(driver, 'arguments[0].focus();', editable)
        espera.assentar(driver, 0.1)

        # Posicionar selecao no marcador
        if not _place_selection_at_marker(driver, editable, marcador, modo, debug):
            if debug:
                logger.debug('[EDITOR] Marcador "%s" nao encontrado', marcador)
            return False

        # Limpar e escapar conteudo
        html_content_clean = (html_content.replace('\x00', '').replace('\r', '').strip())
        html_escaped = (html_content_clean
                       .replace('\\', '\\\\')
                       .replace('`', '\\`')
                       .replace('$', '\\$')
                       .replace('"', '\\"')
                       .replace('\n', '\\n')
                       .replace('\t', '\\t'))

        # Inserir via JavaScript - tentar multiplas abordagens
        js_insert = f"""
        const sel = window.getSelection();
        const html = `{html_escaped}`;

        // Abordagem 1: Usar execCommand (mais compativel com CKEditor)
        try {{
            if (document.execCommand && typeof document.execCommand === 'function') {{
                document.execCommand('insertHTML', false, html);
                return true;
            }}
        }} catch (e) {{
            console.log('execCommand falhou:', e);
        }}

        // Abordagem 2: Usar CKEditor API se disponivel
        try {{
            if (window.CKEDITOR && window.CKEDITOR.instances) {{
                const instances = Object.values(window.CKEDITOR.instances);
                if (instances.length > 0) {{
                    const editor = instances[0];
                    editor.insertHtml(html);
                    return true;
                }}
            }}
        }} catch (e) {{
            console.log('CKEditor API falhou:', e);
        }}

        // Abordagem 3: Insercao manual via range (fallback)
        try {{
            if (sel.rangeCount > 0) {{
                const range = sel.getRangeAt(0);
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = html;
                const fragment = document.createDocumentFragment();
                while (tempDiv.firstChild) {{
                    fragment.appendChild(tempDiv.firstChild);
                }}
                range.deleteContents();
                range.insertNode(fragment);
                return true;
            }}
        }} catch (e) {{
            console.log('Insercao manual falhou:', e);
        }}

        return false;
        """

        sucesso = _executar_script(driver, js_insert)
        if sucesso and debug:
            logger.debug('[EDITOR] HTML inserido com sucesso')

            try:
                conteudo_apos = _executar_script(driver, "return arguments[0].innerHTML;", editable)
                logger.debug('[EDITOR] Conteudo apos insercao: %s...', conteudo_apos[:200])
                if html_content in conteudo_apos:
                    logger.debug('[EDITOR] HTML inserido encontrado no conteudo')
                else:
                    logger.debug('[EDITOR] HTML inserido NAO encontrado no conteudo')
            except Exception as e:
                logger.debug('[EDITOR] Erro ao verificar conteudo apos: %s', e)

        return bool(sucesso)

    except Exception as e:
        if debug:
            logger.error("ERRO em inserir_html_editor: %s: %s", type(e).__name__, e)
        return False


def inserir_link_ato(driver, numero_processo: Optional[str] = None, modo: str = 'after', debug: bool = False) -> bool:
    """Insere link de validacao de ato no editor (coleta + insercao).

    Se houver conteúdo condensado (transcrição do documento, ver
    Fix.variaveis.condensar_conteudo_documento) salvo no clipboard interno
    para o mesmo processo, ele é inserido junto, logo abaixo do link.
    """
    try:
        if debug:
            logger.debug('[LINK_ATO] Iniciando insercao de link para processo: %s', numero_processo)

        link_validacao = obter_ultimo_conteudo_clipboard(numero_processo, r"/validacao/", debug)

        # CORRECAO: Se nao encontrou com numero_processo especifico, tentar buscar o ultimo geral
        if not link_validacao:
            if debug:
                logger.debug('[LINK_ATO] Link nao encontrado para processo %s, tentando busca geral...', numero_processo)
            link_validacao = obter_ultimo_conteudo_clipboard(None, r"/validacao/", debug)

        if link_validacao:
            conteudo_condensado = obter_ultimo_conteudo_clipboard(numero_processo, r"Transcrição do\(a\)", debug)
            if not conteudo_condensado:
                conteudo_condensado = obter_ultimo_conteudo_clipboard(None, r"Transcrição do\(a\)", debug)
            conteudo_final = f"{link_validacao}\n{conteudo_condensado}" if conteudo_condensado else link_validacao

            from PEC.anexos import substituir_marcador_por_conteudo
            resultado = substituir_marcador_por_conteudo(driver, conteudo_final, debug, "--")
            if debug:
                logger.debug('[LINK_ATO] Resultado da chamada substituir_marcador_por_conteudo: %s', resultado)
            return resultado
        else:
            if debug:
                logger.debug('[LINK_ATO] Nao foi possivel obter link de validacao')
            return False

    except Exception as e:
        if debug:
            logger.error("ERRO em inserir_link_ato: %s: %s", type(e).__name__, e)
        return False

# Funções de compatibilidade para manter APIs existentes

def executar_coleta_parametrizavel(driver, numero_processo, tipo_coleta, parametros=None, debug=False):
    """Compatibilidade com coleta_atos.py"""
    if tipo_coleta == "link_ato":
        return coletar_link_ato_timeline(driver, numero_processo, debug)
    elif tipo_coleta == "conteudo_formatado":
        return coletar_conteudo_formatado_documento(driver, numero_processo, debug)
    elif tipo_coleta == "js_generico":
        return coletar_conteudo_js(driver, numero_processo, parametros.get('codigo_js', ''), parametros.get('tipo_conteudo', 'js'), debug)
    elif tipo_coleta == "elemento_css":
        return coletar_elemento_css(driver, numero_processo, parametros.get('seletor_css', ''), parametros.get('tipo_conteudo', 'css'), parametros.get('atributo'), debug)
    return False


def inserir_html_no_editor_apos_marcador(driver, html_content, marcador="--", modo="replace", debug=False):
    """Compatibilidade com editor_insert.py"""
    return inserir_html_editor(driver, html_content, marcador, modo, debug)


def inserir_no_editor_apos_marcador(driver, texto, marcador="--", modo="replace", debug=False):
    """Compatibilidade com editor_insert.py"""
    return inserir_texto_editor(driver, texto, marcador, modo, debug)


def inserir_link_ato_validacao(driver, numero_processo=None, modo='after', debug=False):
    """Compatibilidade com editor_insert.py"""
    return inserir_link_ato(driver, numero_processo, modo, debug)


def inserir_conteudo_formatado(driver, numero_processo: Optional[str] = None, modo: str = 'after', debug: bool = False) -> bool:
    """
    Insere conteúdo formatado (transcrição de documento) no editor
    Busca no clipboard interno o último conteúdo do tipo 'conteudo_formatado'
    """
    try:
        if debug:
            logger.debug('[CONTEUDO_FORMATADO] Iniciando insercao de conteudo para processo: %s', numero_processo)

        conteudo = obter_ultimo_conteudo_clipboard(numero_processo, r"Transcrição do\(a\)", debug)

        if not conteudo:
            if debug:
                logger.debug('[CONTEUDO_FORMATADO] Conteudo nao encontrado para processo %s, tentando busca geral...', numero_processo)
            conteudo = obter_ultimo_conteudo_clipboard(None, r"Transcrição do\(a\)", debug)

        if conteudo:
            from PEC.anexos import substituir_marcador_por_conteudo
            resultado = substituir_marcador_por_conteudo(driver, conteudo, debug, "--")
            if debug:
                logger.debug('[CONTEUDO_FORMATADO] Resultado da insercao: %s', resultado)
            return resultado
        else:
            if debug:
                logger.debug('[CONTEUDO_FORMATADO] Nao foi possivel obter conteudo formatado do clipboard')
            return False

    except Exception as e:
        if debug:
            logger.error("ERRO em inserir_conteudo_formatado: %s: %s", type(e).__name__, e)
        return False

# --- FUNÇÕES DE CRIAÇÃO DE DRIVER ---


def configurar_recovery_driver(criar_driver_func, login_func):
    """
    Configura funções globais para recuperação automática de driver.
    Deve ser chamado no início do script principal.
    
    Args:
        criar_driver_func: Função que cria novo driver (ex: criar_driver do driver_config)
        login_func: Função que faz login no sistema (ex: login_pje, login_siscon, etc)
        
    Exemplo:
        from Fix import configurar_recovery_driver
        from driver_config import criar_driver
        from Fix import login_pje
        
        configurar_recovery_driver(criar_driver, login_pje)
    """
    _driver_recovery_config['criar_driver'] = criar_driver_func
    _driver_recovery_config['login_func'] = login_func
    logger.info("Configuração de recuperação automática ativada")


def verificar_e_tratar_acesso_negado_global(driver):
    """
    Verifica automaticamente se driver está em /acesso-negado e tenta recuperar.
    
    Args:
        
    Returns:
        novo_driver: Novo driver se recuperado, ou None se não foi acesso negado
        
    Raises:
        Exception: Se falhar na recuperação
    """
    if not _driver_recovery_config['enabled']:
        return None
    
    try:
        url_atual = driver.current_url
        if 'acesso-negado' not in url_atual.lower() and 'login.jsp' not in url_atual.lower():
            return None
        
        logger.warning("[RECOVERY_GLOBAL] ACESSO NEGADO DETECTADO: %s", url_atual)
        logger.warning("[RECOVERY_GLOBAL] Iniciando recuperacao automatica...")

        # Fechar driver atual
        try:
            driver.quit()
            logger.info("Driver anterior fechado")
        except Exception as e:
            logger.warning("[RECOVERY_GLOBAL] Erro ao fechar driver: %s", e)
        
        # Verificar se temos funções configuradas
        if not _driver_recovery_config['criar_driver'] or not _driver_recovery_config['login_func']:
            logger.error("Funções de recuperação não configuradas!")
            raise Exception("Recovery não configurado - use configurar_recovery_driver()")
        
        # Criar novo driver
        novo_driver = _driver_recovery_config['criar_driver'](headless=False)
        if not novo_driver:
            logger.error("Falha ao criar novo driver")
            raise Exception("Falha ao criar driver na recuperação")
        
        logger.info("Novo driver criado")
        
        # Fazer login
        if not _driver_recovery_config['login_func'](novo_driver):
            logger.error("Falha ao fazer login")
            novo_driver.quit()
            raise Exception("Falha no login durante recuperação")
        
        logger.info("Login efetuado com sucesso")
        logger.info("[RECOVERY_GLOBAL] RECUPERACAO COMPLETA!")

        return novo_driver

    except Exception as e:
        logger.error("ERRO em verificar_e_tratar_acesso_negado_global: %s: %s", type(e).__name__, e)
        logger.error("[RECOVERY_GLOBAL] Driver sera encerrado")
        raise


def handle_exception_with_recovery(e, driver, funcao_nome=""):
    """
    Trata exceção verificando se é acesso negado e tentando recuperar driver.
    Deve ser chamado em TODOS os blocos except Exception.
    
    Args:
        e: Exceção capturada
        driver: Driver atual
        funcao_nome: Nome da função onde ocorreu erro (para log)
        
    Returns:
        novo_driver se recuperado, None se não foi acesso negado ou falhou
        
    Exemplo de uso:
        try:
            # código que pode falhar
            fazer_algo(driver)
        except Exception as e:
            novo_driver = handle_exception_with_recovery(e, driver, "FAZER_ALGO")
            if novo_driver:
                driver = novo_driver
                # tentar novamente ou continuar
            else:
                return False  # ou raise
    """
    prefixo = f"[{funcao_nome}]" if funcao_nome else "[EXCEPTION]"
    
    try:
        novo_driver = verificar_e_tratar_acesso_negado_global(driver)
        if novo_driver:
            logger.info("%s Driver recuperado automaticamente apos acesso negado", prefixo)
            return novo_driver
    except Exception as recovery_error:
        logger.warning("%s Falha na recuperacao automatica: %s", prefixo, recovery_error)

    # Se nao foi acesso negado ou falhou a recuperacao, apenas loga o erro original
    logger.error("%s Erro: %s", prefixo, e)
    return None


def is_browsing_context_discarded_error(error_message):
    """Verifica se o erro é fatal (browsing context discarded, etc)."""
    if not error_message:
        return False
    error_str = str(error_message).lower()
    return ('browsing context has been discarded' in error_str or 
            'no such window' in error_str or 
            'nosuchwindowerror' in error_str or
            'session not created' in error_str or
            'invalid session id' in error_str)


def validar_conexao_driver(driver, contexto="GERAL", proc_id=None):
    """Valida se a conexão com o driver ainda está ativa."""
    from Fix.browser_suporte import validar_conexao_driver as _vcd
    return _vcd(driver, contexto=contexto, proc_id=proc_id)


def obter_driver_padronizado(headless=False):
    """Retorna um driver Firefox padronizado para TRT2."""
    from Play.pjeplay.launcher import criar_driver_PC
    return criar_driver_PC(headless=headless)


def driver_pc(headless=False):
    """Perfil PC: C:/Users/Silas/AppData/Roaming/Mozilla/Dev"""
    return obter_driver_padronizado(headless=headless)


def navegar_para_tela(driver, url=None, seletor=None, delay=2, timeout=30, log=True):
    """Navega para URL ou clica em seletor."""
    try:
        if log:
            logger.info('[NAVEGAR] Iniciando navegacao...')
        if url:
            driver.get(url)
            if log:
                logger.info('[NAVEGAR] URL: %s', url)
        if seletor:
            element = espera.elemento(driver, seletor)
            if element:
                safe_click_no_scroll(driver, element)
            espera.assentar(driver, delay)
            if log:
                logger.info('[NAVEGAR] Clicou: %s', seletor)
        return True
    except Exception as e:
        if log:
            logger.error("ERRO em navegar_para_tela: %s", e)
        return False


# =============================
# CONFIGURAÇÃO DE COOKIES
# =============================

# Configuração de cookies (migrado de core.py)


def aguardar_e_clicar(driver, seletor, timeout=10, by=By.CSS_SELECTOR, usar_js=True, log=False):
    """
    Aguarda elemento aparecer e clica nele (1 requisição vs 2-3 separadas)
    Padrão repetitivo consolidado: esperar_elemento() + safe_click()
    
    Args:
        seletor: Seletor CSS ou XPath
        timeout: Timeout em segundos
        by: Tipo de seletor (By.CSS_SELECTOR padrão)
        usar_js: Se True usa MutationObserver, se False usa Python
        log: Ativa logging
    
    Returns:
        True se clicou com sucesso, False caso contrário
    
    Exemplo:
        # Ao invés de:
        # elemento = esperar_elemento(driver, '#botao', 10)
        # if elemento: safe_click(driver, elemento)
        
        # Usar:
        aguardar_e_clicar(driver, '#botao', 10)
    """
    if usar_js and by == By.CSS_SELECTOR:
        try:
            script = f"""
            {js_base()}
            return await esperarElemento('{seletor}', {timeout*1000})
                .then(el => {{
                    if (el) {{
                        el.click();
                        return true;
                    }}
                    return false;
                }});
            """
            resultado = driver.execute_async_script(script)
            if log:
                logger.debug("aguardar_e_clicar: %s", seletor)
            return resultado
        except Exception as e:
            if log:
                logger.debug("aguardar_e_clicar JS falhou: %s", e)
            usar_js = False

    # Fallback Python (ou escolha explicita)
    if not usar_js:
        try:
            if not espera.ate_habilitar(driver, seletor, teto=timeout):
                return False
            elemento = espera.elemento(driver, seletor, teto=timeout)
            if elemento:
                elemento.click()
            if log:
                logger.debug("aguardar_e_clicar (Python): %s", seletor)
            return True
        except Exception as e:
            if log:
                logger.debug("aguardar_e_clicar falhou: %s", e)
            return False


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
        if (!elemento) return;
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


# =============================
# PREENCHIMENTO ANGULAR MATERIAL (padrão a.py)
# =============================

def preencher_campos_angular_material(driver, campos=None, debug=False):
    """
    Preenche campos Angular Material do modal SISBAJUD (padrão a.py).
    Usa execute_async_script para garantir execução completa do fluxo assíncrono.
    """
    import time
    
    script = """
    var callback = arguments[arguments.length - 1];
    
    (async function() {
        const debug = [];
        const campos_finais = {};
        const erros = [];
        
        function sleep(ms) {
            return new Promise(r => setTimeout(r, ms));
        }
        
        try {
            debug.push('=== INICIANDO PREENCHIMENTO (ASYNC) ===');
            
            // ===== 1. TIPO DE CRÉDITO =====
            debug.push('\\n1. TIPO DE CRÉDITO');
            const seletor_tipo = 'mat-select[formcontrolname="tipoCredito"]';
            const selectTipo = document.querySelector(seletor_tipo);
            
            if (!selectTipo) {
                erros.push('mat-select[tipoCredito] não encontrado');
            } else {
                let clickTarget = selectTipo;
                if (selectTipo.parentElement?.parentElement) {
                    clickTarget = selectTipo.parentElement.parentElement;
                }
                clickTarget.click();
                await sleep(1500);
                
                const opcoes = Array.from(document.querySelectorAll('mat-option[role="option"]'));
                let encontrou = false;
                for (let o of opcoes) {
                    if (o.textContent.toLowerCase().includes('geral')) {
                        o.click();
                        encontrou = true;
                        await sleep(1000);
                        break;
                    }
                }
                
                if (!encontrou) erros.push('Opção Geral não encontrada');
                else {
                    const val = selectTipo.querySelector('.mat-select-value-text');
                    campos_finais[seletor_tipo] = val ? val.textContent.trim() : 'OK';
                    debug.push('   ✅ Tipo: ' + campos_finais[seletor_tipo]);
                }
            }
            
            // ===== 2. BANCO =====
            debug.push('\\n2. BANCO');
            const seletor_banco = 'input[formcontrolname="instituicaoFinanceiraPorCategoria"]';
            const inputBanco = document.querySelector(seletor_banco);
            
            if (!inputBanco) {
                erros.push('input[banco] não encontrado');
            } else {
                let clickTarget = inputBanco;
                if (inputBanco.parentElement?.parentElement) {
                    clickTarget = inputBanco.parentElement.parentElement;
                }
                clickTarget.click();
                await sleep(1500);
                
                const opcoes = Array.from(document.querySelectorAll('mat-option[role="option"]'));
                let encontrou = false;
                for (let o of opcoes) {
                    const txt = o.textContent.toUpperCase();
                    if (txt.includes('BRASIL') || txt.includes('00001')) {
                        o.click();
                        encontrou = true;
                        await sleep(1500);
                        break;
                    }
                }
                
                if (!encontrou) erros.push('Banco BRASIL não encontrado');
                else {
                    campos_finais[seletor_banco] = inputBanco.value;
                    debug.push('   ✅ Banco: ' + campos_finais[seletor_banco]);
                }
            }
            
            // ===== 3. AGÊNCIA =====
            debug.push('\\n3. AGÊNCIA');
            const seletor_agencia = 'input[formcontrolname="agencia"]';
            const inputAgencia = document.querySelector(seletor_agencia);
            
            if (!inputAgencia) {
                erros.push('input[agencia] não encontrado');
            } else {
                inputAgencia.focus();
                await sleep(500);
                inputAgencia.value = '5905';
                
                // Eventos para garantir que o Angular detecte a mudança
                inputAgencia.dispatchEvent(new Event('input', { bubbles: true }));
                inputAgencia.dispatchEvent(new Event('change', { bubbles: true }));
                
                await sleep(500);
                inputAgencia.blur();
                
                campos_finais[seletor_agencia] = inputAgencia.value;
                debug.push('   ✅ Agência: ' + campos_finais[seletor_agencia]);
            }
            
            // Retorno via callback (obrigatório para execute_async_script)
            callback({
                sucesso: erros.length === 0 && campos_finais[seletor_agencia] === '5905',
                campos_preenchidos: campos_finais,
                erros: erros,
                debug: debug.join('\\n')
            });
            
        } catch (e) {
            callback({
                sucesso: false,
                campos_preenchidos: campos_finais || {},
                erros: [e.message],
                debug: debug.join('\\n') + '\\n❌ ERRO FATAL: ' + e.message
            });
        }
    })();
    """
    
    try:
        # Timeout de segurança para o script (30s)
        driver.set_script_timeout(30)
        
        # Executar como script ASSÍNCRONO
        resultado = driver.execute_async_script(script)
        
        if debug:
            logger.debug("[PREENCHER] === DEBUG COMPLETO ===")
            if resultado and 'debug' in resultado:
                for linha in resultado['debug'].split('\n'):
                    if linha.strip():
                        logger.debug("[PREENCHER] %s", linha)
            else:
                logger.debug("[PREENCHER] Resultado: %s", resultado)

        return resultado or {'sucesso': False, 'erros': ['Retorno nulo do script']}

    except Exception as e:
        if debug:
            logger.error("ERRO em preencher_campos_angular_material: %s", e)
        return {
            'sucesso': False,
            'campos_preenchidos': {},
            'erros': [str(e)],
            'debug': f"Erro na execução: {e}"
        }


# =============================
# SELETORES INTELIGENTES (ex-Core)
# =============================
