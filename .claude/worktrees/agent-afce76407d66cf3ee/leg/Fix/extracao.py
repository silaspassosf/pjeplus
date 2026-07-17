"""
Fix.extracao - Módulo de extracao para PJe automação.

Migrado automaticamente de Fix.py (PARTE 5 - Modularização).
"""

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException,
    WebDriverException, NoSuchWindowException, ElementClickInterceptedException, 
    ElementNotInteractableException
)
from typing import Optional, Dict, Any, List, Union, Callable
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import re, time, datetime, json, pyperclip, logging

# Importar funções de verificação de carregamento
try:
    from atos.core import verificar_carregamento_detalhe, aguardar_e_verificar_detalhe
    _ATOS_CORE_AVAILABLE = True
except ImportError:
    _ATOS_CORE_AVAILABLE = False
import requests
from urllib.parse import urlparse
from pathlib import Path
from Fix.log import logger
from .core import aguardar_e_clicar, safe_click, preencher_multiplos_campos, wait, sleep, smart_sleep
from .abas import validar_conexao_driver, forcar_fechamento_abas_extras
from .utils import normalizar_cpf_cnpj, formatar_moeda_brasileira, formatar_data_brasileira

def extrair_direto(driver, timeout=10, debug=False, formatar=True):
    """
    Extrai o conteúdo do documento PDF ativo na tela do processo PJe DIRETAMENTE.
    SEM CLIQUES, SEM INTERAÇÃO, apenas leitura direta.
    
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
    
    resultado = {
        'conteudo': None,
        'conteudo_bruto': None,
        'info': {},
        'sucesso': False
    }
    try:
        # Validar documento ativo
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.ID, "documento"))
            )
        except:
            try:
                driver.find_element(By.ID, "documento")
            except:
                return resultado
        # Tentar 3 estratégias de extração (Strategy Pattern)
        strategies = [
            lambda: _extrair_via_pdf_viewer(driver, timeout, debug),
            lambda: _extrair_via_iframe(driver, timeout, debug),
            lambda: _extrair_via_elemento_dom(driver, timeout, debug)
        ]
        metodos_nomes = ['PDF viewer direto', 'iframe', 'elemento DOM']
        for idx, strategy in enumerate(strategies):
            texto_bruto = strategy()
            if texto_bruto:
                resultado['conteudo_bruto'] = texto_bruto
                resultado['conteudo'] = _extrair_formatar_texto(texto_bruto, debug) if formatar else texto_bruto
                resultado['metodo'] = metodos_nomes[idx]
                resultado['sucesso'] = True
                resultado['info'] = _extrair_info_documento(driver, debug)
                if debug:
                    print(f'[EXTRAIR_DIRETO] Extração bem-sucedida via {resultado["metodo"]}')
                return resultado
        resultado['info'] = _extrair_info_documento(driver, debug)
        if debug:
            print('[EXTRAIR_DIRETO] Nenhuma estratégia de extração funcionou')
        return resultado
    except Exception as e:
        if debug:
            print(f'[EXTRAIR_DIRETO] Erro geral na extração: {e}')
        return resultado


# =========================
# SISTEMA GLOBAL DE RECUPERAÇÃO DE DRIVER (ACESSO NEGADO)
# =========================

# Variável global para armazenar referências de driver e funções de recuperação
_driver_recovery_config = {
    'criar_driver': None,
    'login_func': None,
    'enabled': True
}


def extrair_documento(driver, regras_analise=None, timeout=15, log=False):
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
                print('[DEBUG][REGRAS] Iniciando análise de regras...')
                _ = regras_analise(texto_final)
                print('[DEBUG][REGRAS] Análise de regras concluída.')
            except Exception as e_analise:
                print(f'[EXTRAI][ERRO] Falha ao analisar regras: {e_analise}')

        if log: print('[EXTRAI] Extração concluída.')
        return texto_final

    except Exception as e:
        if log: print(f'[EXTRAI][ERRO] Falha geral ao extrair documento: {e}')
        try:
            if driver.find_elements(By.CSS_SELECTOR, '#previewModeloDocumento'):
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        except Exception:
            pass
        return None


def extrair_pdf(driver, log=True):
    import time
    from selenium.webdriver.common.keys import Keys
    import pyperclip
    try:
        # 1. Clicar no botão de exportar texto
        btn_export = driver.find_element(By.CSS_SELECTOR, '.fa-file-export')
        btn_export.click()
        if log:
            print('[EXPORT] Botão .fa-file-export clicado.')
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
                                print('[EXPORT] Texto extraído do modal via copiar.')
                        except Exception as e:
                            if log:
                                print(f'[EXPORT][ERRO] Falha ao copiar texto do modal: {e}')
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
            print('[EXPORT][ERRO] Modal de texto extraído não apareceu.')
        return None
    except Exception as e:
        if log:
            print(f'[EXPORT][ERRO] {e}')
        return None
## Função para extrair dados do processo

def extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False):
    """
    Extrai dados do processo via API do PJe (TRT2), seguindo a mesma lógica da extensão MaisPje.
    Função completa auto-contida.
    """
    # Funções auxiliares internas
    def get_cookies_dict(driver):
        try:
            cookies = driver.get_cookies()
            return {c['name']: c['value'] for c in cookies}
        except Exception as e:
            print(f"[ERRO] Falha ao obter cookies: {e}")
            return {}

    def extrair_numero_processo_url(driver):
        """Extrai número do processo da URL ou do elemento clipboard"""
        url = driver.current_url
        # Primeiro tenta extrair da URL
        m = re.search(r'processo/(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', url)
        if m:
            return m.group(1)
        
        # Se não encontrar na URL, tenta extrair do elemento clipboard do PJE
        try:
            xpath_clipboard = "//pje-icone-clipboard//span[contains(@aria-label, 'Copia o número do processo')]"
            elemento_clipboard = driver.find_element(By.XPATH, xpath_clipboard)
            aria_label = elemento_clipboard.get_attribute("aria-label")
            if aria_label:
                match_clipboard = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})", aria_label)
                if match_clipboard:
                    return match_clipboard.group(1)
        except:
            pass
        
        return None

    def extrair_trt_host(driver):
        url = driver.current_url
        parsed = urlparse(url)
        return parsed.netloc

    def obter_id_processo_via_api(numero_processo, sess, trt_host):
        """Replica a função obterIdProcessoViaApi do gigs-plugin.js"""
        url = f'https://{trt_host}/pje-comum-api/api/agrupamentotarefas/processos?numero={numero_processo}'
        try:
            resp = sess.get(url, timeout=10)
            if resp.ok:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0].get('idProcesso')
        except Exception as e:
            if debug:
                print(f'[extrair.py] Erro ao obter ID via API: {e}')
        return None

    def obter_dados_processo_via_api(id_processo, sess, trt_host):
        """Replica a função obterDadosProcessoViaApi do gigs-plugin.js"""
        url = f'https://{trt_host}/pje-comum-api/api/processos/id/{id_processo}'
        try:
            resp = sess.get(url, timeout=10)
            if resp.ok:
                return resp.json()
        except Exception as e:
            if debug:
                print(f'[extrair.py] Erro ao obter dados via API: {e}')
        return None
    
    cookies = get_cookies_dict(driver)
    numero_processo = extrair_numero_processo_url(driver)
    trt_host = extrair_trt_host(driver)
    
    sess = requests.Session()
    for k, v in cookies.items():
        sess.cookies.set(k, v)
    sess.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "X-Grau-Instancia": "1"  # Adiciona header usado pela extensão
    })
    
    if not numero_processo:
        if debug:
            print('[extrair.py] Não foi possível extrair o número do processo.')
        return {}

    # 1. Obter ID do processo usando o número (como na extensão MaisPje)
    id_processo = obter_id_processo_via_api(numero_processo, sess, trt_host)
    if not id_processo:
        if debug:
            print('[extrair.py] Não foi possível obter o ID do processo via API.')
        return {}

    # 2. Obter dados completos do processo usando o ID
    dados_processo = obter_dados_processo_via_api(id_processo, sess, trt_host)
    if not dados_processo:
        if debug:
            print('[extrair.py] Não foi possível obter dados do processo via API.')
        return {}
    
    processo_memoria = {
        "numero": [dados_processo.get("numero", numero_processo)], 
        "id": id_processo, 
        "autor": [], 
        "reu": [], 
        "terceiro": [],
        "divida": {}, 
        "justicaGratuita": [], 
        "transito": "", 
        "custas": "", 
        "dtAutuacao": "",
        "classeJudicial": dados_processo.get("classeJudicial", {}),
        "labelFaseProcessual": dados_processo.get("labelFaseProcessual", ""),
        "orgaoJuizo": dados_processo.get("orgaoJuizo", {}),
        "dataUltimo": dados_processo.get("dataUltimo", "")
    }

    # Extrai data de autuação dos dados principais
    dt = dados_processo.get("autuadoEm")
    if dt:
        from datetime import datetime
        try:
            dtobj = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            processo_memoria["dtAutuacao"] = dtobj.strftime('%d/%m/%Y')
        except:
            processo_memoria["dtAutuacao"] = dt
    
    # 2. Partes (formato limpo)
    def criar_pessoa_limpa(parte):
        nome = parte.get("nome", "").strip()
        doc_original = parte.get("documento", "")
        
        # Normaliza documento (remove pontuação)
        doc_normalizado = normalizar_cpf_cnpj(doc_original)
        
        pessoa = {"nome": nome, "cpfcnpj": doc_normalizado}
        
        reps = parte.get("representantes", [])
        if reps:
            adv = reps[0]
            # Normaliza também o CPF do advogado
            cpf_advogado = normalizar_cpf_cnpj(adv.get("documento", ""))
            pessoa["advogado"] = {
                "nome": adv.get("nome", "").strip(),
                "cpf": cpf_advogado,
                "oab": adv.get("numeroOab", "")
            }
        return pessoa
          # 2. Partes usando API separada (como na extensão)
    try:
        url_partes = f"https://{trt_host}/pje-comum-api/api/processos/id/{id_processo}/partes"
        resp = sess.get(url_partes, timeout=10)
        if resp.ok:
            j = resp.json()
            for parte in j.get("ATIVO", []):
                processo_memoria["autor"].append(criar_pessoa_limpa(parte))
            for parte in j.get("PASSIVO", []):
                processo_memoria["reu"].append(criar_pessoa_limpa(parte))
            for parte in j.get("TERCEIROS", []):
                processo_memoria["terceiro"].append({"nome": parte.get("nome", "").strip()})
    except Exception as e:
        if debug:
            print('[extrair.py] Erro ao buscar partes:', e)
    
    # 3. Divida
    try:
        url_divida = f"https://{trt_host}/pje-comum-api/api/calculos/processo?pagina=1&tamanhoPagina=10&ordenacaoCrescente=false&idProcesso={id_processo}"
        resp = sess.get(url_divida, timeout=10)
        if resp.ok:
            j = resp.json()
            if j and j.get("resultado"):
                # Pega o PRIMEIRO elemento (mais recente)
                mais_recente = j["resultado"][0]
                
                # Aplica formatação aos dados antes de salvar
                valor_raw = mais_recente.get("total", 0)
                data_raw = mais_recente.get("dataLiquidacao", "")
                
                processo_memoria["divida"] = {
                    "valor": formatar_moeda_brasileira(valor_raw),
                    "data": formatar_data_brasileira(data_raw)
                }
    except Exception as e:
        if debug:
            print('[extrair.py] Erro ao buscar divida:', e)


      # Salva JSON
    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(processo_memoria, f, ensure_ascii=False, indent=2)
    return processo_memoria


# =========================
# 4.1 FUNÇÕES PARA DESTINATÁRIOS EXTRAÍDOS DE DECISÕES
# =========================

DESTINATARIOS_CACHE_PATH = Path('destinatarios_argos.json')



def extrair_destinatarios_decisao(texto_decisao, dados_processo=None, debug=False):
    """Extrai possíveis destinatários (nome + CPF/CNPJ) a partir do texto completo da decisão."""
    if not texto_decisao:
        if debug:
            print('[DEST][WARN] Texto da decisão vazio. Nenhum destinatário extraído.')
        return []

    texto_compacto = _normalizar_texto_decisao(texto_decisao)
    texto_upper = texto_compacto.upper()
    resultados = []
    vistos = set()

    padrao_doc = re.compile(r'(CPF|CNPJ)\s*[:\-]?\s*([\d\.\-/]+)')

    for match in padrao_doc.finditer(texto_upper):
        tipo_doc = match.group(1)
        documento_bruto = match.group(2)
        doc_normalizado = normalizar_cpf_cnpj(documento_bruto)
        if len(doc_normalizado) not in (11, 14):
            continue

        inicio_procura = max(0, match.start() - 160)
        prefixo = texto_upper[inicio_procura:match.start()]
        match_nome = re.search(r"([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ\s'\.-]{2,})[,\s]*$", prefixo)
        if not match_nome:
            continue

        nome_inicio = inicio_procura + match_nome.start(1)
        nome_fim = inicio_procura + match_nome.end(1)
        nome_bruto = texto_compacto[nome_inicio:nome_fim].strip()
        nome_upper_ref = nome_bruto.upper()
        marcadores = [
            ' SÓCIO ', ' SOCIO ', ' SÓCIA ', ' SOCIA ', ' EMPRESA ', ' PARTE ',
            ' EXECUTADA ', ' EXECUTADO ', ' INCLUIR ', ' INCLUSÃO ', ' INCLUSAO ',
            ' SECRETARIA ', ' RETIFICAÇÃO ', ' RETIFICACAO ', ' PARA INCLUIR ',
            ' PARA INCLUSAO '
        ]
        for marcador in marcadores:
            idx = nome_upper_ref.rfind(marcador)
            if idx != -1:
                corte = idx + len(marcador)
                nome_bruto = nome_bruto[corte:].strip(' ,.-')
                nome_upper_ref = nome_upper_ref[corte:]
                break

        nome_bruto = nome_bruto.lstrip('.- ').strip()
        if nome_bruto.upper().startswith(('O ', 'A ', 'OS ', 'AS ')):
            partes_nome = nome_bruto.split(' ', 1)
            if len(partes_nome) > 1:
                nome_bruto = partes_nome[1]
        nome_bruto = nome_bruto.strip()
        chave = (doc_normalizado, nome_bruto.strip().upper())
        if chave in vistos:
            continue
        vistos.add(chave)

        registro = {
            'nome_identificado': nome_bruto.strip(),
            'documento': documento_bruto.strip(),
            'documento_normalizado': doc_normalizado,
            'tipo_documento': 'CPF' if len(doc_normalizado) == 11 else 'CNPJ',
            'polo': None,
            'nome_oficial': None
        }

        if dados_processo:
            partes_passivas = dados_processo.get('reu', []) or []
            for parte in partes_passivas:
                doc_cadastrado = normalizar_cpf_cnpj(parte.get('cpfcnpj'))
                if doc_cadastrado and doc_cadastrado == doc_normalizado:
                    registro['polo'] = 'reu'
                    registro['nome_oficial'] = parte.get('nome', '').strip() or registro['nome_identificado']
                    break

        resultados.append(registro)

    if debug:
        print(f'[DEST][DEBUG] Destinatários identificados: {json.dumps(resultados, ensure_ascii=False, indent=2)}')

    return resultados



def salvar_destinatarios_cache(chave_simples, destinatarios, origem=''):  # noqa: D401
    """
     VERSÃO SIMPLIFICADA - Salva destinatários sem depender do número do processo
    Sempre usa uma chave simples como "ATUAL" para facilitar o acesso
    """
    payload = {
        'numero_processo': chave_simples,  # Mantém compatibilidade mas usa chave simples
        'destinatarios': destinatarios,
        'origem': origem,
        'timestamp': datetime.datetime.now().isoformat()
    }
    try:
        DESTINATARIOS_CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'[DEST][CACHE] Cache salvo com chave: {chave_simples} ({len(destinatarios)} destinatários)')
    except Exception as exc:
        print(f'[DEST][WARN] Falha ao salvar cache de destinatários: {exc}')



def carregar_destinatarios_cache():
    """
     VERSÃO SIMPLIFICADA - Carrega destinatários sem depender do número do processo
    Retorna sempre o último cache salvo (chave única)
    """
    try:
        if DESTINATARIOS_CACHE_PATH.exists():
            cache = json.loads(DESTINATARIOS_CACHE_PATH.read_text(encoding='utf-8'))
            print(f'[DEST][CACHE] Cache carregado: {len(cache.get("destinatarios", []))} destinatários')
            return cache
    except Exception as exc:
        print(f'[DEST][WARN] Falha ao carregar cache de destinatários: {exc}')
    return {}

# =========================
# 5. FUNÇÕES DE MANIPULAÇÃO DE DOCUMENTOS
# =========================

# Seção: Manipulaçao de intimações
# Função para preencher campos de prazo

def _normalizar_texto_decisao(texto):
    if not texto:
        return ''
    return ' '.join(texto.split())



def _extrair_linha_tipo(linha: str) -> Optional[str]:
    """
    Detecta tipo de linha e aplica formatação apropriada.
    
    Args:
        linha: String com texto da linha
    
    Returns:
        Linha formatada ou None se vazia
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
    
    Args:
        texto_bruto: Texto bruto extraído do documento
        debug: Se True, exibe logs de debug (padrão False)
    
    Returns:
        Texto formatado com estrutura ou texto bruto se falhar formatação
    """
    # Guard clause: texto vazio
    if not texto_bruto or not texto_bruto.strip():
        return ""
    
    try:
        # Limpeza
        texto = texto_bruto.strip()
        texto = re.sub(r'\r\n|\r', '\n', texto)
        texto = re.sub(r'[ \t]+', ' ', texto)
        texto = re.sub(r'\n\s*\n\s*\n+', '\n\n', texto)
        
        # Formatar linhas
        linhas = texto.split('\n')
        linhas_formatadas = [_extrair_linha_tipo(l) for l in linhas]
        linhas_formatadas = [l for l in linhas_formatadas if l is not None]
        
        texto_formatado = '\n'.join(linhas_formatadas)
        texto_formatado = re.sub(r'\n{3,}', '\n\n', texto_formatado)
        return texto_formatado.strip()
        
    except Exception as e:
        if debug:
            print(f'[EXTRAIR_DIRETO] Erro na formatação: {e}')
        return texto_bruto



def _extrair_info_documento(driver, debug=False):
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
            print(f'[EXTRAIR_DIRETO] Erro ao extrair informações: {e}')
        return {}



def _extrair_via_pdf_viewer(driver, timeout, debug=False):
    """Strategy 1: Extrai texto do PDF viewer incorporado via JavaScript."""
    if debug:
        print('[EXTRAIR_DIRETO] Tentando extração via PDF viewer...')
    
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
            print(f'[EXTRAIR_DIRETO] Erro na extração via PDF viewer: {e}')
    
    return None



def _extrair_via_iframe(driver, timeout, debug=False):
    """Strategy 2: Extrai texto de iframes alternativos."""
    if debug:
        print('[EXTRAIR_DIRETO] Tentando extração via iframe...')
    
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
            print(f'[EXTRAIR_DIRETO] Erro na extração via iframe: {e}')
        driver.switch_to.default_content()
    
    return None



def _extrair_via_elemento_dom(driver, timeout, debug=False):
    """Strategy 3: Extrai texto de elemento DOM estruturado."""
    if debug:
        print('[EXTRAIR_DIRETO] Tentando extração via elemento DOM...')
    
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
            print(f'[EXTRAIR_DIRETO] Erro na extração via DOM: {e}')
    
    return None



def _gigs_responsavel_valido(responsavel: Optional[str]) -> bool:
    """
    Verifica se responsável é válido (não vazio, não '-').
    
    Args:
        responsavel: String com nome do responsável ou None
    
    Returns:
        True se responsável é válido, False caso contrário
    """
    return responsavel is not None and responsavel.strip() and responsavel.strip() != '-'


# ===== LEMBRETE GENÉRICO (JUNTO COM GIGS) =====
def criar_lembrete_posit(driver, titulo, conteudo, debug=False):
    """
    Cria lembrete/post-it genérico com título e conteúdo customizáveis.
    Reutilizável em diferentes contextos (Bloqueio, Acompanhamento, etc).
    
    Args:
        driver: WebDriver Selenium
        titulo: Texto do título (ex: "Bloqueio pendente")
        conteudo: Texto do conteúdo (ex: "processar após IDPJ")
        debug: Log detalhado (default: False)
    
    Returns:
        bool: True se sucesso, False caso contrário
    """
    try:
        if debug:
            print(f'[LEMBRETE][POSIT]  Criando: "{titulo}" / "{conteudo}"')
        
        # 1. ABRIR MENU
        menu_clicked = aguardar_e_clicar(driver, '.fa-bars', log=debug)
        time.sleep(0.8)
        
        # 2. PROCURAR ÍCONE DE LEMBRETE
        seletores_lembrete = [
            'button[aria-label*="Lembrete"]',
            'button[title*="Lembrete"]',
            'pje-icone-post-it button',
            '.lista-itens-menu li:nth-child(16) button',
        ]
        
        lembrete_clicked = False
        for seletor in seletores_lembrete:
            try:
                lembrete_clicked = aguardar_e_clicar(driver, seletor, timeout=3, log=False)
                if lembrete_clicked:
                    if debug:
                        print(f'[LEMBRETE][POSIT] ✓ Ícone: {seletor}')
                    break
            except:
                continue
        
        time.sleep(0.8)
        
        # 3. FOCAR DIÁLOGO
        aguardar_e_clicar(driver, '.mat-dialog-content', log=False)
        time.sleep(0.8)
        
        # 4. PREENCHER TÍTULO
        titulo_elem = aguardar_e_clicar(driver, '#tituloPostit', timeout=5)
        if titulo_elem:
            preencher_campo(titulo_elem, titulo)
        
        # 5. PREENCHER CONTEÚDO
        conteudo_elem = aguardar_e_clicar(driver, '#conteudoPostit', timeout=5)
        if conteudo_elem:
            preencher_campo(conteudo_elem, conteudo)
        
        # 6. SALVAR
        seletores_salvar = [
            'button[color="primary"]',
            '.mat-raised-button:not([disabled])',
            'button[type="submit"]',
        ]
        
        for seletor in seletores_salvar:
            try:
                if aguardar_e_clicar(driver, seletor, timeout=3, log=False):
                    break
            except:
                continue
        
        time.sleep(0.8)
        if debug:
            print(f'[LEMBRETE][POSIT] ✅ "{titulo}"')
        return True
        
    except Exception as e:
        if debug:
            print(f'[LEMBRETE][POSIT][ERRO] {e}')
        return False


def _parse_gigs_string(string):
    """
    Parseia string de teste GIGS automaticamente.
    
    Regras:
    - sem / = OBSERVACAO
    - uma / ou // juntas = prazo/observacao ou prazo//observacao (sem responsável)
    - duas / entre parâmetros = prazo/responsável/observacao
    """
    if '/' not in string:
        # Apenas observação
        return {'dias_uteis': None, 'responsavel': None, 'observacao': string.strip()}
    
    # Verificar se há duas barras consecutivas
    if '//' in string:
        partes = string.split('//', 1)
        if len(partes) == 2:
            prazo_str, obs = partes
            try:
                dias_uteis = int(prazo_str.strip())
            except ValueError:
                dias_uteis = None
            return {'dias_uteis': dias_uteis, 'responsavel': None, 'observacao': obs.strip()}
    
    # Split por /
    partes = string.split('/')
    if len(partes) == 2:
        # prazo/observacao
        prazo_str, obs = partes
        try:
            dias_uteis = int(prazo_str.strip())
        except ValueError:
            dias_uteis = None
        return {'dias_uteis': dias_uteis, 'responsavel': None, 'observacao': obs.strip()}
    elif len(partes) == 3:
        # prazo/responsavel/observacao
        prazo_str, resp, obs = partes
        try:
            dias_uteis = int(prazo_str.strip())
        except ValueError:
            dias_uteis = None
        return {'dias_uteis': dias_uteis, 'responsavel': resp.strip(), 'observacao': obs.strip()}
    
    # Fallback: apenas observação
    return {'dias_uteis': None, 'responsavel': None, 'observacao': string.strip()}


def criar_gigs(driver, dias_uteis=None, responsavel=None, observacao=None, timeout=10, log=True):
    """
    Cria atividade GIGS na aba /detalhe - VERSÃO OTIMIZADA baseada em a.py
    
    Suporta múltiplas assinaturas:
    - criar_gigs(driver, "observacao simples") -> apenas observação
    - criar_gigs(driver, "7/xs carta") -> prazo/observacao
    - criar_gigs(driver, "7/xs/carta urgente") -> prazo/responsavel/observacao
    - criar_gigs(driver, 7, "xs", "carta") -> parâmetros separados
    
    Fluxo simplificado:
    1. Clica "Nova Atividade"
    2. Preenche campos (dias, responsável, observação)
    3. Salva e confirma
    """
    # Parse string unificada se necessário
    if isinstance(dias_uteis, str) and responsavel is None and observacao is None:
        parsed = _parse_gigs_string(dias_uteis)
        dias_uteis = parsed['dias_uteis']
        responsavel = parsed['responsavel']
        observacao = parsed['observacao']
    
    # Compatibilidade: 2 params = dias_uteis + observacao
    if observacao is None and responsavel is not None:
        observacao = responsavel
        responsavel = None
    
    try:
        if log:
            info = f"{dias_uteis or '-'}/{responsavel or '-'}/{observacao or '-'}"
            print(f"[GIGS] Criando: {info}")
        
        # 1. Clicar Nova Atividade (seletor específico para evitar editar atividade existente)
        if log:
            print('[GIGS] Clicando Nova Atividade...')
        btn_nova = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH,
                "//button[.//span[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nova atividade')] "
                "or contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nova atividade')]")
            )
        )
        btn_nova.click()
        time.sleep(1)  # Aguardar modal abrir
        
        # 2. Aguardar formulário
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]'))
        )
        if log:
            print('[GIGS] Formulário aberto')
        
        # 3. Preencher dias úteis
        if dias_uteis:
            campo_dias = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="dias"]')
            campo_dias.clear()
            campo_dias.send_keys(str(dias_uteis))
            time.sleep(0.3)
            if log:
                print(f'[GIGS] Prazo: {dias_uteis} dias')
        
        # 4. Preencher responsável (com autocomplete)
        if responsavel:
            campo_resp = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="responsavel"]')
            campo_resp.clear()
            campo_resp.send_keys(responsavel)
            time.sleep(0.5)
            campo_resp.send_keys(Keys.ARROW_DOWN)
            time.sleep(0.2)
            campo_resp.send_keys(Keys.ENTER)
            if log:
                print(f'[GIGS] Responsável: {responsavel}')
        
        # 5. Preencher observação
        if observacao:
            campo_obs = driver.find_element(By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]')
            campo_obs.clear()
            campo_obs.send_keys(observacao)
            # Forçar evento para Angular detectar
            driver.execute_script(
                "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
                campo_obs
            )
            time.sleep(0.3)
            if log:
                print(f'[GIGS] Observação: {observacao[:50]}...' if len(observacao) > 50 else f'[GIGS] Observação: {observacao}')
        
        # 6. Salvar
        if log:
            print('[GIGS] Salvando...')
        btn_salvar = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Salvar')]"))
        )
        btn_salvar.click()
        
        # 7. Aguardar confirmação (não esperar sumir)
        time.sleep(0.3)
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, "//snack-bar-container//span[contains(normalize-space(.), 'Atividade salva com sucesso')]"))
            )
            if log:
                print('[GIGS] ✅ Atividade criada com sucesso')
            return True
        except TimeoutException:
            if log:
                print('[GIGS] ⚠️ Confirmação não detectada, assumindo sucesso')
            return True
        
    except Exception as e:
        if log:
            print(f'[GIGS][ERRO] {e}')
        return False


def criar_comentario(driver, observacao, visibilidade='LOCAL', timeout=10, log=True):
    """
    Cria comentário GIGS na aba /detalhe - baseado em lancarComentario do a.py
    
    Args:
        driver: WebDriver do Selenium
        observacao: Texto do comentário
        visibilidade: 'LOCAL' (padrão), 'RESTRITA' ou 'GLOBAL'
        timeout: Timeout para operações (default 10s)
        log: Habilitar logs (default True)
    
    Returns:
        True se comentário criado com sucesso, False caso contrário
    
    Exemplos:
        criar_comentario(driver, "Aguardando retorno da parte")
        criar_comentario(driver, "Informação sigilosa", visibilidade='RESTRITA')
        criar_comentario(driver, "Comentário geral", visibilidade='GLOBAL')
    """
    try:
        if log:
            print(f"[COMENTARIO] Criando: {observacao[:50]}..." if len(observacao) > 50 else f"[COMENTARIO] Criando: {observacao}")
        
        # 1. Clicar "Novo Comentário"
        if log:
            print('[COMENTARIO] Clicando Novo Comentário...')
        btn_novo = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Novo Comentário') or contains(., 'Novo comentário')]"))
        )
        btn_novo.click()
        time.sleep(1)
        
        # 2. Aguardar formulário
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[formcontrolname="descricao"], textarea[name="descricao"]'))
        )
        if log:
            print('[COMENTARIO] Formulário aberto')
        
        # 3. Preencher observação/descrição
        campo_obs = driver.find_element(By.CSS_SELECTOR, 'textarea[formcontrolname="descricao"], textarea[name="descricao"]')
        campo_obs.clear()
        campo_obs.send_keys(observacao)
        # Forçar evento para Angular
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
            campo_obs
        )
        time.sleep(0.3)
        if log:
            print(f'[COMENTARIO] Descrição preenchida')
        
        # 4. Selecionar visibilidade (radio buttons)
        visibilidade_upper = visibilidade.upper()
        if log:
            print(f'[COMENTARIO] Visibilidade: {visibilidade_upper}')
        
        try:
            radio_buttons = driver.find_elements(By.CSS_SELECTOR, 'pje-gigs-comentarios-cadastro mat-radio-button, mat-radio-button')
            if len(radio_buttons) >= 3:
                index_map = {'LOCAL': 0, 'RESTRITA': 1, 'GLOBAL': 2}
                idx = index_map.get(visibilidade_upper, 0)
                radio_buttons[idx].find_element(By.CSS_SELECTOR, 'input').click()
                time.sleep(0.3)
                
                # Se RESTRITA, pode ter campo adicional (usuários)
                if visibilidade_upper == 'RESTRITA':
                    if log:
                        print('[COMENTARIO] Visibilidade RESTRITA - pode requerer seleção de usuários')
                    time.sleep(0.5)  # Aguardar campo adicional
        except Exception as e:
            if log:
                print(f'[COMENTARIO][AVISO] Não foi possível selecionar visibilidade: {e}')
        
        # 5. Salvar
        if log:
            print('[COMENTARIO] Salvando...')
        btn_salvar = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Salvar')]"))
        )
        btn_salvar.click()
        time.sleep(1)
        
        # 6. Comentário não dá confirmação explícita, apenas fecha
        # Verificar se modal fechou
        time.sleep(1)
        try:
            modals = driver.find_elements(By.CSS_SELECTOR, 'mat-dialog-container')
            modal_aberto = any(m.is_displayed() for m in modals)
            if not modal_aberto:
                if log:
                    print('[COMENTARIO] ✅ Comentário criado com sucesso')
                return True
            else:
                # Forçar fechar com ESC
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(0.5)
                if log:
                    print('[COMENTARIO] ✅ Comentário criado (modal fechado manualmente)')
                return True
        except Exception:
            if log:
                print('[COMENTARIO] ✅ Comentário criado')
            return True
            
    except Exception as e:
        if log:
            print(f'[COMENTARIO][ERRO] {e}')
        return False



def bndt(driver, inclusao=False, debug=False, **kwargs):
    """
    Executa rotinas BNDT - versão refatorada processando ambos os polos.
    Orquestrador principal que coordena as etapas.

    Nota: aceita `debug` e `**kwargs` para compatibilidade com chamadas
    que possam passar parâmetros extras (ex: via executor genérico).
    """
    # Log explícito do valor recebido para diagnosticar chamadas incorretas
    try:
        logger.info(f'BNDT: parâmetro inclusao recebido: {inclusao!r} (tipo: {type(inclusao)})')
    except Exception:
        pass
    operacao = "Inclusão" if inclusao else "Exclusão"
    logger.info(f'Iniciando operação BNDT: {operacao}')
    
    main_window = driver.current_window_handle
    nova_aba = None
    erro_classe = False
    
    try:
        # Etapa 1: Validar localização
        _bndt_validar_localizacao(driver)
        
        # Etapa 2: Abrir menu e ícone
        _bndt_abrir_menu(driver)
        _bndt_clicar_icone(driver)
        
        # Etapa 3: Abrir nova aba
        main_window, nova_aba = _bndt_abrir_nova_aba(driver)
        
        # PROCESSAR APENAS POLO PASSIVO
        polo = 'Passivo'
        logger.info(f'============ Processando Polo {polo} ============')
        
        # 1. Clicar no botão do polo Passivo
        logger.info(f'Procurando botão de polo {polo}...')
        try:
            btn_polo = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, f"//input[@value='{polo}']/ancestor::mat-radio-button | //mat-radio-button[@value='{polo}']"))
            )
            btn_polo.click()
            logger.info(f'Polo {polo} selecionado')
            time.sleep(0.5)
        except Exception as e:
            logger.error(f'Erro ao selecionar polo {polo}: {e}')
            raise

        # 2. Selecionar operação (Inclusão ou Exclusão)
        if not _bndt_selecionar_operacao_para_polo(driver, inclusao, polo):
            driver.close()
            driver.switch_to.window(main_window)
            return False

        # 3. Verificar se existe mensagem "Não existem partes a serem selecionadas"
        try:
            no_reg_elems = driver.find_elements(By.CSS_SELECTOR, '#tabela-registros-bndt div[class*="mensagem"], pje-bndt-partes-sem-registro .mensagem, mat-card .mensagem, div.mensagem.ng-star-inserted')
            for elem in no_reg_elems:
                texto_no_reg = (elem.text or '').strip().lower()
                if ('não há registros' in texto_no_reg or 
                    'não há registros disponíveis' in texto_no_reg or 
                    'não existem partes a serem selecionadas' in texto_no_reg):
                    logger.info(f'Polo {polo}: "{elem.text}" — nada a fazer')
                    driver.close()
                    driver.switch_to.window(main_window)
                    return True
        except Exception:
            pass

        # 4. Verificar se há mensagem de classe não permitida
        try:
            msg_classe_elems = driver.find_elements(By.XPATH, "//*[contains(text(),'A classe judicial do processo não pode acessar')]")
            if msg_classe_elems:
                logger.warning(f'Polo {polo}: Classe judicial do processo não permite cadastro no BNDT')
                erro_classe = True
                driver.close()
                driver.switch_to.window(main_window)
                return False
        except Exception:
            pass

        # 5. Processar seleções (marcar checkboxes)
        _bndt_processar_selecoes_polo(driver, polo)
        
        # 6. Gravar e confirmar
        _bndt_gravar_e_confirmar_polo(driver, polo)
        
        logger.info(f'============ Finalizando operação {operacao} ============')
        
        if erro_classe:
            logger.warning('ATENÇÃO: Classe do processo não suporta BNDT!')
        
        # Fechar aba BNDT
        driver.close()
        driver.switch_to.window(main_window)
        logger.info(f'Operação {operacao} concluída no polo {polo}')
        return True
    
    except Exception as e:
        logger.error(f'ERRO na operação {operacao}: {e}')
        # Fechar apenas a aba BNDT (se aberta) para não encerrar o driver principal
        if nova_aba and nova_aba in driver.window_handles:
            try:
                driver.switch_to.window(nova_aba)
                driver.close()
            except Exception:
                pass

        # Garantir retorno para a aba principal original
        if main_window and main_window in driver.window_handles:
            try:
                driver.switch_to.window(main_window)
            except Exception:
                pass
        return False



def _bndt_validar_localizacao(driver):
    """Valida se está em /detalhe."""
    current_url = driver.current_url
    if '/detalhe' not in current_url:
        raise Exception(f'bndt deve ser executado a partir de /detalhe. URL atual: {current_url}')
    logger.info('Confirmado: Estamos na página /detalhe')
    return True



def _bndt_abrir_menu(driver: WebDriver) -> bool:
    """
    Abre o menu hambúrguer com validação robusta.
    
    Args:
        driver: Instância do WebDriver Selenium
    
    Returns:
        True se menu aberto com sucesso, False caso contrário
    """
    try:
        btn_menu = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa-bars.icone-botao-menu'))
        )
        btn_menu.click()
        logger.info('Menu hambúrguer clicado')
        time.sleep(0.2)  # ⚡ Otimizado: validação já feita pelo wait
        return True
    except TimeoutException:
        logger.error('Menu hambúrguer não encontrado')
        return False
    except Exception as e:
        logger.error(f'Erro ao abrir menu: {e}')
        return False



def _bndt_clicar_icone(driver: WebDriver) -> bool:
    """
    Clica no ícone BNDT com validação robusta.
    
    Args:
        driver: Instância do WebDriver Selenium
    
    Returns:
        True se ícone clicado com sucesso, False caso contrário
    """
    try:
        btn_bndt = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fas.fa-money-check-alt.icone-padrao'))
        )
        btn_bndt.click()
        logger.info('Ícone BNDT clicado')
        time.sleep(0.3)  # ⚡ Otimizado: nova aba será aguardada no próximo wait
        return True
    except TimeoutException:
        logger.error('Ícone BNDT não encontrado')
        return False
    except Exception as e:
        logger.error(f'Erro ao clicar ícone BNDT: {e}')
        return False



def _bndt_abrir_nova_aba(driver):
    """Abre nova aba BNDT e retorna seu handle."""
    main_window = driver.current_window_handle
    WebDriverWait(driver, 15).until(lambda d: len(d.window_handles) > 1)
    
    all_windows = driver.window_handles
    nova_aba = [w for w in all_windows if w != main_window]
    if not nova_aba:
        raise Exception('Nova aba BNDT não foi criada')
    
    nova_aba = nova_aba[-1]
    driver.switch_to.window(nova_aba)
    WebDriverWait(driver, 15).until(lambda d: '/bndt' in d.current_url)
    
    time.sleep(0.5)  # ⚡ Otimizado: URL já validada, elementos serão aguardados
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-card, mat-radio-group, button'))
        )
        logger.info('Elementos da página BNDT detectados')
    except Exception as e:
        logger.warning(f'AVISO: Elementos podem não ter carregado: {e}')
    
    logger.info(f'Nova aba BNDT aberta: {driver.current_url}')
    return main_window, nova_aba



def _bndt_selecionar_operacao(driver, inclusao):
    """Seleciona Inclusão ou Exclusão."""
    operacao = "Inclusão" if inclusao else "Exclusão"

    try:
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception as e:
        logger.warning(f'AVISO: Página pode não ter carregado: {e}')

    # IMPORTANT: the BNDT page normally opens with 'Inclusão' already selected.
    # When inclusao=True we should NOT attempt to switch radios — simply assume
    # the default is correct (and return success). Only when inclusao=False
    # (Exclusão) we search and click the Exclusão radio.
    if inclusao:
        try:
            # Try to detect that Inclusão is selected to be explicit, but if
            # detection fails, still assume the default selection is Inclusão
            # and do nothing (avoid clicking 'Exclusão' accidentally).
            try:
                inp = driver.find_element(By.XPATH, "//input[@name='mat-radio-group-1' and @value='INCLUSAO']")
                checked = False
                try:
                    checked = inp.is_selected() or inp.get_attribute('checked') or inp.get_attribute('aria-checked') == 'true'
                except Exception:
                    checked = False
                if checked:
                    logger.info('BNDT: Inclusão já selecionada — sem ação necessária')
                    return True
                else:
                    # If found but not checked, attempt to click the inclusive radio safely
                    try:
                        parent = inp.find_element(By.XPATH, 'ancestor::mat-radio-button')
                        parent.click()
                        logger.info('BNDT: Radio Inclusão clicado (detected unchecked -> clicked)')
                        time.sleep(0.5)
                        return True
                    except Exception:
                        logger.info('BNDT: Inclusão requisitada — assumindo opção padrão já selecionada')
                        return True
            except Exception:
                # Could not find the input explicitly; assume default is Inclusão
                logger.info('BNDT: Inclusão requisitada — assumindo opção padrão já selecionada')
                return True
        except Exception as e:
            logger.warning(f'BNDT: Falha ao verificar radio Inclusão, mas prosseguindo sem clique: {e}')
            return True

    # exclusão flow: find and click the exclusão radio
    selectors = [
        (By.XPATH, "//mat-radio-button[@id='mat-radio-7']"),
        (By.XPATH, "//mat-radio-button[contains(@id,'mat-radio-')][.//input[@value='EXCLUSAO'] ]"),
        (By.XPATH, "//mat-radio-button[.//span[contains(text(),'Exclusão')]]"),
        (By.XPATH, "//input[@name='mat-radio-group-1'][@value='EXCLUSAO']/ancestor::mat-radio-button")
    ]

    radio_operacao = None
    for by, selector in selectors:
        try:
            radio_operacao = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, selector)))
            logger.info(f'Radio {operacao} encontrado')
            break
        except Exception:
            continue

    if not radio_operacao:
        raise Exception(f'Não foi possível encontrar o radio button de {operacao}')

    radio_operacao.click()
    logger.info(f'Radio {operacao} clicado')
    time.sleep(0.5)

    # Após selecionar o radio, verificar se existe a mensagem "Não existem partes a serem selecionadas"
    # Se existir, significa que não há partes para selecionar, então a operação está cumprida
    try:
        mensagem_nao_existem_partes = driver.find_elements(By.XPATH, "//div[contains(@class, 'mensagem') and contains(text(), 'Não existem partes a serem selecionadas')]")
        if mensagem_nao_existem_partes:
            logger.info('BNDT: Não existem partes a serem selecionadas — operação cumprida sem seleções')
            return True
    except Exception as e:
        logger.warning(f'BNDT: Erro ao verificar mensagem de partes não existentes: {e}')
        # Prosseguir normalmente se a verificação falhar


def _bndt_selecionar_operacao_para_polo(driver, inclusao, polo):
    """Seleciona Inclusão ou Exclusão para um polo específico."""
    operacao = "Inclusão" if inclusao else "Exclusão"
    tipo_operacao = "INCLUSAO" if inclusao else "EXCLUSAO"
    
    logger.info(f'Selecionando operação: {operacao} para polo {polo}')
    
    try:
        btn_operacao = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, f"//input[@value='{tipo_operacao}']/ancestor::mat-radio-button | //mat-radio-button[@value='{tipo_operacao}']"))
        )
        btn_operacao.click()
        logger.info(f'Operação {operacao} selecionada para polo {polo}')
        time.sleep(0.5)
        return True
    except Exception as e:
        logger.warning(f'Erro ao selecionar operação {operacao} no polo {polo}: {e}')
        return False



def _bndt_processar_selecoes(driver):
    """Seleciona o checkbox de "Selecionar todos" se disponível."""
    selectors = [
        (By.XPATH, "//mat-checkbox[.//span[contains(text(),'Selecionar todos')]]//label"),
        (By.XPATH, "//mat-checkbox[.//span[contains(text(),'Selecionar todos')]]//input[@type='checkbox']"),
        (By.XPATH, "//span[contains(@class,'mat-checkbox-label')][contains(text(),'Selecionar todos')]/ancestor::mat-checkbox//label"),
        (By.XPATH, "//input[@type='checkbox'][@aria-label='Selecionar todos']/ancestor::mat-checkbox//label")
    ]

    for by, selector in selectors:
        try:
            chk_todos = driver.find_element(by, selector)
            driver.execute_script('arguments[0].click();', chk_todos)
            logger.info('Checkbox "Selecionar todos" clicado (sem aguardar elementos extras)')
            time.sleep(0.25)
            return
        except Exception:
            continue

    logger.warning('Checkbox "Selecionar todos" não encontrado — ação concluída sem seleção adicional')


def _bndt_processar_selecoes_polo(driver, polo):
    """Procurar e clicar em todos os checkboxes de débito/crédito para um polo específico."""
    logger.info(f'Procurando checkboxes para marcar no polo {polo}...')
    try:
        labels = driver.find_elements(By.CSS_SELECTOR, 'pje-bndt-exclusao label[for*="debito"][for*="-input"], pje-bndt-inclusao label[for*="debito"][for*="-input"]')
        if not labels:
            logger.warning(f'Nenhum checkbox encontrado no polo {polo}')
            return
        
        for label in labels:
            try:
                label.click()
                time.sleep(0.1)
            except Exception as e:
                logger.warning(f'Erro ao clicar checkbox: {e}')
        
        logger.info(f'{len(labels)} checkbox(es) marcados no polo {polo}')
        time.sleep(0.5)
    except Exception as e:
        logger.warning(f'Erro ao marcar checkboxes no polo {polo}: {e}')


def _bndt_gravar_e_confirmar(driver, main_window, nova_aba):
    """Clica Gravar, confirma e fecha aba."""
    selectors_gravar = [
        (By.XPATH, "//button[.//span[contains(text(),'Gravar')]]"),
        (By.XPATH, "//button[contains(@class,'mat-raised-button')][contains(text(),'Gravar')]"),
        (By.CSS_SELECTOR, "button[mat-raised-button]:contains('Gravar')"),
        (By.XPATH, "//button[@type='submit'][contains(text(),'Gravar')]")
    ]
    
    btn_gravar = None
    for by, selector in selectors_gravar:
        try:
            btn_gravar = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, selector)))
            logger.info('Botão Gravar encontrado')
            break
        except Exception:
            continue
    
    if not btn_gravar:
        raise Exception('Botão Gravar não encontrado')
    
    btn_gravar.click()
    logger.info('Botão Gravar clicado')
    time.sleep(1)
    
    # Verificar confirmação final
    try:
        btn_sim = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(),'Sim')]]"))
        )
        btn_sim.click()
        logger.info('Confirmação clicada')
        time.sleep(1)
    except Exception:
        pass
    
    # Fechar aba
    driver.close()
    driver.switch_to.window(main_window)
    logger.info('Aba BNDT fechada')


def _bndt_gravar_e_confirmar_polo(driver, polo):
    """Clica Gravar e confirma para um polo específico."""
    logger.info(f'Procurando botão Gravar para polo {polo}...')
    btn_gravar = None
    selectors_gravar = [
        (By.XPATH, "//button[.//span[contains(text(),'Gravar')]]"),
        (By.XPATH, "//button[contains(@class,'mat-raised-button')][contains(text(),'Gravar')]"),
        (By.XPATH, "//pje-bndt-exclusao//button[contains(text(),'Gravar')] | //pje-bndt-inclusao//button[contains(text(),'Gravar')]")
    ]
    for by, selector in selectors_gravar:
        try:
            btn_gravar = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((by, selector)))
            logger.info('Botão Gravar encontrado')
            break
        except Exception:
            continue
    
    if not btn_gravar:
        logger.warning(f'Botão Gravar não encontrado no polo {polo}')
        return

    try:
        btn_gravar.click()
        logger.info('Botão Gravar clicado')
        time.sleep(0.5)
    except Exception as e:
        logger.warning(f'Erro ao clicar no botão Gravar: {e}')
        return

    # Confirmar ação (botão Sim)
    try:
        btn_sim = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'cdk-overlay-pane')]//button[contains(.,'Sim')]"))
        )
        btn_sim.click()
        logger.info('Confirmação "Sim" clicada')
        time.sleep(0.5)
    except Exception:
        logger.warning('Botão "Sim" não encontrado (pode não ser necessário)')

    # Aguardar desaparecer loading
    try:
        WebDriverWait(driver, 10).until_not(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class*="container-loading"] mat-progress-spinner'))
        )
        time.sleep(0.5)
    except Exception:
        pass

    # Verificar mensagem de sucesso ou erro
    try:
        aviso = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'simple-snack-bar'))
        )
        if aviso:
            texto_aviso = aviso.text
            logger.info(f'Aviso: {texto_aviso}')
            
            if 'Excluído registro de' in texto_aviso or 'Partes excluídas' in texto_aviso or 'Incluído registro de' in texto_aviso or 'Partes incluídas' in texto_aviso:
                logger.info(f'Operação no polo {polo} concluída com sucesso')
                # Fechar aviso
                try:
                    btn_close = aviso.find_element(By.CSS_SELECTOR, 'button')
                    btn_close.click()
                except Exception:
                    pass
            elif 'A classe judicial do processo não pode acessar' in texto_aviso:
                logger.warning('Classe judicial não permite BNDT')
            else:
                logger.warning(f'Mensagem inesperada: {texto_aviso}')
    except Exception:
        logger.warning('Nenhum aviso detectado')



def filtrofases(driver, fases_alvo=['liquidação', 'execução'], tarefas_alvo=None, seletor_tarefa='Tarefa do processo'):
    print(f'Filtrando fase processual: {", ".join(fases_alvo).title()}...')
    try:
        fase_element = None
        try:
            fase_element = driver.find_element(By.XPATH, "//span[contains(text(), 'Fase processual')]")
        except Exception:
            try:
                seletor_fase = 'span.ng-tns-c82-22.ng-star-inserted'
                for elem in driver.find_elements(By.CSS_SELECTOR, seletor_fase):
                    if 'Fase processual' in elem.text:
                        fase_element = elem
                        break
            except Exception:
                print('[ERRO] Não encontrou o seletor de fase processual.')
                return False
        if not fase_element:
            print('[ERRO] Não encontrou o seletor de fase processual.')
            return False
        driver.execute_script("arguments[0].click();", fase_element)
        time.sleep(1)
        painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
        painel = None
        for _ in range(10):
            try:
                painel = driver.find_element(By.CSS_SELECTOR, painel_selector)
                if painel.is_displayed():
                    break
            except Exception:
                time.sleep(0.3)
        if not painel or not painel.is_displayed():
            print('[ERRO] Painel de opções não apareceu.')
            return False
        fases_clicadas = set()
        opcoes = painel.find_elements(By.XPATH, ".//mat-option")
        for fase in fases_alvo:
            for opcao in opcoes:
                try:
                    texto = opcao.text.strip().lower()
                    if fase in texto and opcao.is_displayed():
                        driver.execute_script("arguments[0].click();", opcao)
                        fases_clicadas.add(fase)
                        print(f'[OK] Fase "{fase}" selecionada.')
                        time.sleep(0.5)
                        break
                except Exception:
                    continue
        if len(fases_clicadas) == 0:
            print(f'[ERRO] Não encontrou opções {fases_alvo} no painel.')
            return False
        try:
            botao_filtrar = driver.find_element(By.CSS_SELECTOR, 'i.fas.fa-filter')
            driver.execute_script('arguments[0].click();', botao_filtrar)
            print('[OK] Fases selecionadas e filtro aplicado (botão filtrar).')
            time.sleep(1)
        except Exception as e:
            print(f'[ERRO] Não conseguiu clicar no botão de filtrar: {e}')
        # Generalização da seleção de tarefa
        if tarefas_alvo:
            print(f'Filtrando tarefa: {", ".join(tarefas_alvo).title()}...')
            tarefa_element = None
            try:
                tarefa_element = driver.find_element(By.XPATH, f"//span[contains(text(), '{seletor_tarefa}')]")
            except Exception:
                try:
                    seletor = 'span.ng-tns-c82-22.ng-star-inserted'
                    for elem in driver.find_elements(By.CSS_SELECTOR, seletor):
                        if seletor_tarefa in elem.text:
                            tarefa_element = elem
                            break
                except Exception:
                    print(f'[ERRO] Não encontrou o seletor de tarefa: {seletor_tarefa}.')
                    return False
            if not tarefa_element:
                print(f'[ERRO] Não encontrou o seletor de tarefa: {seletor_tarefa}.')
                return False
            driver.execute_script("arguments[0].click();", tarefa_element)
            time.sleep(1)
            painel = None
            painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
            for _ in range(10):
                try:
                    painel = driver.find_element(By.CSS_SELECTOR, painel_selector)
                    if painel.is_displayed():
                        break
                except Exception:
                    time.sleep(0.3)
            if not painel or not painel.is_displayed():
                print('[ERRO] Painel de opções de tarefa não apareceu.')
                return False
            tarefas_clicadas = set()
            opcoes = painel.find_elements(By.XPATH, ".//mat-option")
            for tarefa in tarefas_alvo:
                for opcao in opcoes:
                    try:
                        texto = opcao.text.strip().lower()
                        if tarefa.lower() in texto and opcao.is_displayed():
                            driver.execute_script("arguments[0].click();", opcao)
                            tarefas_clicadas.add(tarefa)
                            print(f'[OK] Tarefa "{tarefa}" selecionada.')
                            time.sleep(0.5)
                            break
                    except Exception:
                        continue
            if len(tarefas_clicadas) == 0:
                print(f'[ERRO] Não encontrou opções {tarefas_alvo} no painel de tarefas.')
                return False
            try:
                botao_filtrar = driver.find_element(By.CSS_SELECTOR, 'i.fas.fa-filter')
                driver.execute_script('arguments[0].click();', botao_filtrar)
                print('[OK] Tarefas selecionadas e filtro aplicado (botão filtrar).')
                time.sleep(1)
            except Exception as e:
                print(f'[ERRO] Não conseguiu clicar no botão de filtrar para tarefas: {e}')
    except Exception as e:
        print(f'[ERRO] Erro no filtro de fase: {e}')
        return False
    return True

def indexar_processos(driver):
    """
    Indexa processos de forma mais robusta, evitando problemas de stale elements
    """
    padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
    processos = []
    
    # Buscar elementos frescos a cada iteração para evitar stale elements
    def obter_linhas_frescas():
        return driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
    
    linhas = obter_linhas_frescas()
    print(f'[INDEXAR] Encontradas {len(linhas)} linhas para processar')
    
    for idx in range(len(linhas)):
        try:
            # Sempre obter elementos frescos para evitar stale references
            linhas_atuais = obter_linhas_frescas()
            
            # Verificar se o índice ainda é válido
            if idx >= len(linhas_atuais):
                print(f'[INDEXAR][SKIP] Linha {idx+1}: DOM mudou, menos linhas disponíveis')
                continue
                
            linha = linhas_atuais[idx]
            
            # Extrair texto do processo
            links = linha.find_elements(By.CSS_SELECTOR, 'a')
            texto = ''
            
            if links:
                texto = links[0].text.strip()
            else:
                tds = linha.find_elements(By.TAG_NAME, 'td')
                if tds:
                    texto = tds[0].text.strip()
            
            # Buscar número do processo
            match = padrao_proc.search(texto)
            num_proc = match.group(0) if match else '[sem número]'
            
            processos.append((num_proc, linha))
            
        except Exception as e:
            print(f'[INDEXAR][ERRO] Linha {idx+1}: {e} (elemento pode ter ficado stale)')
            # Não tentar reindexar - apenas continuar
            continue
    
    print(f'[INDEXAR] Processamento concluído: {len(processos)} processos indexados')
    return processos


def reindexar_linha(driver, proc_id):
    """
    Reindexar linha quando elemento fica stale.
    Agora com verificação de acesso negado e melhor tratamento de erros.
    NÃO navega automaticamente - respeita a página atual do módulo.
    """
    try:
        # Verificar se ainda estamos em uma página válida do PJE
        url_atual = driver.current_url
        if 'acesso-negado' in url_atual.lower() or 'access-denied' in url_atual.lower():
                logger.error(f'ACESSO NEGADO detectado na URL: {url_atual}')
                return None
        
        # Verificar se é uma URL válida do PJE
        if 'pje.trt2.jus.br' not in url_atual:
            logger.error(f'URL não é do PJE: {url_atual}')
            return None
        
        # REMOVIDO: Navegação automática para atividades
        # Cada módulo deve gerenciar sua própria navegação
        print(f'[REINDEXAR] Tentando reindexar na página atual: {url_atual}')
        
        # Buscar linhas na página atual (diferentes seletores dependendo do módulo)
        possible_selectors = [
            'tr.cdk-drag',           # Atividades (PEC)
            'tr',                    # Documentos internos (M1) 
            'tbody tr',              # Outras tabelas
            '.linha-processo',       # Seletor alternativo
        ]
        
        linhas_atuais = []
        for selector in possible_selectors:
            try:
                linhas_temp = driver.find_elements(By.CSS_SELECTOR, selector)
                if linhas_temp:
                    linhas_atuais = linhas_temp
                    print(f'[REINDEXAR] Usando seletor {selector}: {len(linhas_atuais)} linhas encontradas')
                    break
            except:
                continue
        
        if not linhas_atuais:
            logger.error(f'Nenhuma linha encontrada na página com os seletores testados')
            return None
        
        print(f'[REINDEXAR] Buscando {proc_id} entre {len(linhas_atuais)} linhas...')
        
        for idx, linha_temp in enumerate(linhas_atuais):
            try:
                # Verificar se a linha ainda é válida
                if not linha_temp.is_displayed():
                    continue
                    
                # Buscar número do processo na linha (diferentes estratégias)
                texto_linha = ""
                
                # Estratégia 1: Links
                links = linha_temp.find_elements(By.CSS_SELECTOR, 'a')
                if links:
                    texto_linha = links[0].text.strip()
                else:
                    # Estratégia 2: Células td
                    tds = linha_temp.find_elements(By.TAG_NAME, 'td')
                    if tds:
                        # Procurar em várias células (processo pode estar em diferentes colunas)
                        for td in tds[:3]:  # Verificar as 3 primeiras colunas
                            td_text = td.text.strip()
                            if proc_id in td_text:
                                texto_linha = td_text
                                break
                        if not texto_linha:
                            texto_linha = tds[0].text.strip()
                    else:
                        # Estratégia 3: Texto geral da linha
                        texto_linha = linha_temp.text.strip()
                
                if proc_id in texto_linha:
                    logger.info(f'Processo {proc_id} encontrado na linha {idx+1}')
                    return linha_temp
                    
            except Exception as e:
                # Não logar erros individuais para não poluir - linha pode estar stale mesmo
                continue
        
        logger.error(f'Processo {proc_id} não encontrado nas {len(linhas_atuais)} linhas da página atual')
        return None
        
    except Exception as e:
        logger.error(f'Erro geral na reindexação: {e}')
        return None



def abrir_detalhes_processo(driver, linha):
    try:
        btn = linha.find_element(By.CSS_SELECTOR, '[mattooltip*="Detalhes do Processo"]')
    except Exception:
        try:
            btn = linha.find_element(By.CSS_SELECTOR, 'button, a')
        except Exception:
            return False
    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
    driver.execute_script("arguments[0].click();", btn)
    return True


def trocar_para_nova_aba(driver, aba_lista_original):
    """
    Troca para uma nova aba diferente da aba original da lista.
    Inclui tratamento robusto de erros, verificações adicionais e verificação de carregamento.
    
    Args:
        driver: O driver Selenium
        aba_lista_original: O handle da aba original da lista
        
    Returns:
        str: O handle da nova aba se foi bem-sucedido, None caso contrário
    """
    try:
        # Verificar se o driver está conectado
        if not validar_conexao_driver(driver, "ABAS"):
            print('[ABAS][ERRO] Driver não está conectado ao tentar trocar de aba')
            return None
            
        # Obter lista atual de abas
        try:
            abas = driver.window_handles
            if not abas:
                print('[ABAS][ERRO] Nenhuma aba disponível')
                return None
                
            if len(abas) == 1 and abas[0] == aba_lista_original:
                print('[ABAS][ERRO] Apenas a aba original está disponível, nenhuma nova aba foi aberta')
                return None
                
            # Log melhorado - mostrar apenas a quantidade, não os IDs longos
            print(f'[ABAS] Detectadas {len(abas)} abas')
        except Exception as e:
            print(f'[ABAS][ERRO] Falha ao obter lista de abas: {e}')
            return None
            
        # Tentar trocar para uma aba diferente da original
        for h in abas:
            if h != aba_lista_original:
                try:
                    driver.switch_to.window(h)
                    # Verificar se realmente trocamos de aba
                    atual_handle = driver.current_window_handle
                    if atual_handle == h:
                        # Log com URL útil em vez de ID longo
                        try:
                            url_atual = driver.current_url
                            from urllib.parse import urlparse
                            parsed = urlparse(url_atual)
                            path_parts = parsed.path.strip('/').split('/')
                            if len(path_parts) >= 2:
                                url_legivel = f"{path_parts[-2]}/{path_parts[-1]}"
                            else:
                                url_legivel = parsed.path or url_atual[-30:]
                            print(f'[ABAS] ✅ Trocou para: {url_legivel}')
                        except:
                            print(f'[ABAS] ✅ Trocou para nova aba')
                        
                        # VERIFICAÇÃO DE CARREGAMENTO: Se for página /detalhe, verificar se carregou
                        try:
                            current_url = driver.current_url or ''
                            if '/detalhe' in current_url.lower() and _ATOS_CORE_AVAILABLE:
                                print('[ABAS] Verificando carregamento da página /detalhe...')
                                if not verificar_carregamento_detalhe(driver, timeout_inicial=2.0, max_tentativas=3, log=True):
                                    print('[ABAS][ALERTA] Falha no carregamento da página /detalhe, mas continuando...')
                                else:
                                    print('[ABAS] ✅ Página /detalhe carregada corretamente')
                        except Exception as e:
                            print(f'[ABAS][ALERTA] Erro na verificação de carregamento: {e}')
                        
                        return h
                    else:
                        print(f'[ABAS][ALERTA] Troca para aba {h} falhou, handle atual é: {atual_handle}')
                except Exception as e:
                    print(f'[ABAS][ERRO] Erro ao trocar para aba {h}: {e}')
                    continue
                    
        # Se chegou aqui, não conseguiu trocar para nenhuma nova aba
        print('[ABAS][ERRO] Não foi possível trocar para nenhuma nova aba')
        return None
    except Exception as e:
        print(f'[ABAS][ERRO] Erro geral ao tentar trocar de aba: {e}')
        return None


def _indexar_preparar_contexto(driver, max_processos=None):
    """Valida conexão e indexa processos, retornando (aba_original, lista_processos) ou (None, None)."""
    import time
    
    conexao_inicial = validar_conexao_driver(driver, "FLUXO")
    if conexao_inicial == "FATAL":
        print('[FLUXO][FATAL] Driver inutilizável no início do processamento!')
        return None, None
    elif not conexao_inicial:
        print('[FLUXO][ERRO] Driver não está conectado no início do processamento!')
        return None, None
    
    try:
        aba_lista_original = driver.current_window_handle
        print(f'[FLUXO] Aba da lista capturada: {aba_lista_original}')
    except Exception as e:
        print(f'[FLUXO][ERRO] Falha ao capturar aba da lista: {e}')
        return None, None
    
    try:
        processos = indexar_processos(driver)
        if not processos:
            print('[FLUXO][ALERTA] Nenhum processo encontrado para indexação')
            return None, None
    except Exception as e:
        print(f'[FLUXO][ERRO] Falha ao indexar processos: {e}')
        return None, None
    
    if max_processos and max_processos > 0 and max_processos < len(processos):
        processos = processos[:max_processos]
        print(f'[FLUXO] Limitando processamento a {max_processos} processos')
    
    return aba_lista_original, processos



def _indexar_tentar_reindexar(driver: WebDriver, proc_id: str, max_tentativas: int = 3) -> Optional[WebElement]:
    """
    Tenta reindexar linha com múltiplas tentativas.
    
    Args:
        driver: Instância do WebDriver Selenium
        proc_id: ID do processo a reindexar
        max_tentativas: Número máximo de tentativas (padrão 3)
    
    Returns:
        WebElement da linha reindexada ou None se falhar
    """
    import time
    for tent in range(max_tentativas):
        try:
            linha = reindexar_linha(driver, proc_id)
            if linha:
                return linha
            print(f'[PROCESSAR] Tentativa {tent+1}/{max_tentativas} - Reindexando')
            time.sleep(1)
        except Exception as e:
            print(f'[PROCESSAR][ERRO] Falha na tentativa {tent+1}: {e}')
            time.sleep(1)
    return None



def _indexar_tentar_trocar_aba(driver: WebDriver, aba_original: str, max_tentativas: int = 3) -> Optional[str]:
    """
    Tenta trocar para nova aba com múltiplas tentativas.
    
    Args:
        driver: Instância do WebDriver Selenium
        aba_original: Handle da aba original
        max_tentativas: Número máximo de tentativas (padrão 3)
    
    Returns:
        Handle da nova aba ou None se falhar
    """
    import time
    for tent in range(max_tentativas):
        try:
            nova_aba = trocar_para_nova_aba(driver, aba_original)
            if nova_aba:
                # Log melhorado - mostrar URL em vez de ID
                try:
                    url_atual = driver.current_url
                    from urllib.parse import urlparse
                    parsed = urlparse(url_atual)
                    path_parts = parsed.path.strip('/').split('/')
                    if len(path_parts) >= 2:
                        url_legivel = f"{path_parts[-2]}/{path_parts[-1]}"
                    else:
                        url_legivel = parsed.path or url_atual[-30:]
                    print(f'[PROCESSAR] Trocado para nova aba: {url_legivel}')
                except:
                    print(f'[PROCESSAR] Trocado para nova aba')
                time.sleep(0.5)
                return nova_aba
            print(f'[PROCESSAR] Tentativa {tent+1}/{max_tentativas} - Aguardando aba')
            time.sleep(1)
        except Exception as e:
            print(f'[PROCESSAR][ERRO] Falha ao trocar aba (tent {tent+1}): {e}')
            time.sleep(1)
    return None



def _indexar_processar_item(driver, proc_id, linha, aba_lista_original, callback):
    """Processa um item individual da lista: abre, executa callback, limpa abas."""
    import time
    
    print(f'[PROCESSAR] Processando {proc_id}...', flush=True)
    
    # Validar conexão
    conexao_status = validar_conexao_driver(driver, "PROCESSAR")
    if conexao_status == "FATAL":
        print(f'[PROCESSAR][FATAL] Contexto descartado - interrompendo')
        return "FATAL"
    elif not conexao_status:
        print(f'[PROCESSAR][ERRO] Conexão perdida para {proc_id}')
        return "ERRO"
    
    # Verificar URL e recuperar se necessário
    try:
        atual_url = driver.current_url
        if 'acesso-negado' in atual_url.lower() or 'login.jsp' in atual_url.lower():
            print(f'[PROCESSAR][ALERTA] Acesso negado detectado. Reiniciando driver...')
            novo_driver = reiniciar_driver_e_logar_pje(driver, log=True)
            if not novo_driver:
                print('[PROCESSAR][ERRO] Falha ao reiniciar driver')
                return "ERRO"
            driver = novo_driver
            aba_lista_original = driver.window_handles[0] if driver.window_handles else None
        
        # Guard clause: URL inválida
        if "escaninho" not in atual_url and "documentos" not in atual_url:
            if not aba_lista_original or aba_lista_original not in driver.window_handles:
                return "ERRO"
            driver.switch_to.window(aba_lista_original)
            print('[PROCESSAR] Voltado para aba da lista')
    except Exception as e:
        print(f'[PROCESSAR][ERRO] Falha ao verificar URL: {e}')
        return "ERRO"
    
    # Reindexar com tentativas (extraído em função)
    linha_atual = _indexar_tentar_reindexar(driver, proc_id)
    if not linha_atual:
        print(f'[PROCESSAR][ERRO] Não reindexado após 3 tentativas')
        return "ERRO"
    
    # Abrir detalhes
    try:
        if not abrir_detalhes_processo(driver, linha_atual):
            print(f'[PROCESSAR][ERRO] Botão de detalhes não encontrado')
            return "ERRO"
    except Exception as e:
        print(f'[PROCESSAR][ERRO] Falha ao abrir detalhes: {e}')
        return "ERRO"
    
    time.sleep(1)
    
    # Trocar para nova aba com tentativas (extraído em função)
    nova_aba = _indexar_tentar_trocar_aba(driver, aba_lista_original)
    if not nova_aba:
        print(f'[PROCESSAR][ERRO] Nova aba não aberta após 3 tentativas')
        return "ERRO"
    
    # Executar callback COM O NÚMERO DA LISTA
    try:
        time.sleep(1)
        # CRIAR UM WRAPPER QUE PASSA O NÚMERO DA LISTA PARA O CALLBACK
        def callback_wrapper(driver_inner):
            # Adicionar o número da lista como atributo temporário do driver
            driver_inner._numero_processo_lista = proc_id
            return callback(driver_inner)
        
        if callback_wrapper(driver):
            print(f'[PROCESSAR] Callback OK para {proc_id}')
            conexao_pos = validar_conexao_driver(driver, "POS-CALLBACK")
            if conexao_pos == "FATAL":
                print(f'[PROCESSAR][FATAL] Contexto perdido durante callback')
                return "FATAL"
        else:
            print(f'[PROCESSAR][ERRO] Callback retornou False')
            return "ERRO"
    except Exception as e:
        print(f'[PROCESSAR][ERRO] Falha inesperada em callback: {e}')
        return "ERRO"
    finally:
        # Limpar atributo temporário
        if hasattr(driver, '_numero_processo_lista'):
            delattr(driver, '_numero_processo_lista')
    
    # Limpar abas
    limpeza = forcar_fechamento_abas_extras(driver, aba_lista_original)
    if limpeza == "FATAL":
        print(f'[PROCESSAR][FATAL] Contexto perdido durante limpeza')
        return "FATAL"
    elif not limpeza:
        print(f'[PROCESSAR][ALERTA] Limpeza de abas falhou (não é fatal)')
    
    return "SUCESSO"



def indexar_e_processar_lista(driver, callback, seletor_btn=None, modo='tabela', max_processos=None, log=True):
    """
    Processa lista de processos com tratamento robusto de conexão e abas.
    Estratégia: reindexa a lista completa antes de cada processamento para lidar com listas dinâmicas.
    """
    print('[FLUXO] Iniciando indexação da lista de processos...', flush=True)

    aba_original, processos_iniciais = _indexar_preparar_contexto(driver, max_processos)
    if not aba_original or not processos_iniciais:
        return False

    # Indexar uma vez no início (não a cada iteração)
    try:
        processos_iniciais = indexar_processos(driver)
        if not processos_iniciais:
            print('[FLUXO] Nenhum processo encontrado para processar')
            return False
        print(f'[FLUXO] {len(processos_iniciais)} processos encontrados para processamento')
    except Exception as e:
        print(f'[FLUXO][ERRO] Falha ao indexar lista inicial: {e}')
        return False

    processados = 0
    erros = 0
    fatal = False
    
    # Processar lista indexada (sem reindexar a cada item)
    for idx, (proc_id, linha_original) in enumerate(processos_iniciais):
        if max_processos and processados >= max_processos:
            print(f'[FLUXO] Limite de {max_processos} processos atingido')
            break

        print(f'[FLUXO] Processando item {idx+1}/{len(processos_iniciais)}: {proc_id}')

        resultado = _indexar_processar_item(driver, proc_id, linha_original, aba_original, callback)

        if resultado == "SUCESSO":
            processados += 1
        elif resultado == "FATAL":
            fatal = True
            print(f'[FLUXO][FATAL] Interrompendo processamento')
            break
        else:
            erros += 1
            # Em caso de erro, tentar o próximo da lista atual
            idx += 1

    # Relatório final
    print(f'[FLUXO] ✅ Processamento concluído: {processados} sucesso, {erros} erros')
    return processados > 0


def analise_argos(driver):
    # Fluxo robusto para análise de mandados do tipo Argos (Pesquisa Patrimonial).
    print('[ARGOS] Iniciando análise Argos...')
    try:
        # Placeholder para lógica Argos adicional
        print('[ARGOS] Análise Argos concluída.')
    except Exception as e:
        print(f'[ARGOS][ERRO] Falha na análise Argos: {e}')


# NOTE: `buscar_documento_argos` is implemented centrally in `Fix.core` to avoid
# duplicate implementations across the package. The prior implementation in
# this module was removed to keep a single authoritative version inside
# `Fix/core.py` as requested.


def tratar_anexos_argos(driver, log=True):
    # Função placeholder, lógica removida conforme solicitado.
    if log:
        print('[ARGOS][ANEXOS] Tratando anexos...')
    if log:
        print('[ARGOS][ANEXOS] Anexos tratados com sucesso.')

# =========================
# 8. FUNÇÕES DE UI E INTERFACE
# =========================

# Seção: Mandados Outros


def analise_outros(driver):
    # Fluxo robusto para análise de mandados do tipo Outros (Oficial de Justiça).
    # - Extrai certidão do documento.
    # - Cria GIGS sempre como tipo 'prazo', 0 dias, nome 'Pz mdd'.
    print('[OUTROS] Iniciando análise Outros...')
    texto = extrair_documento(driver, regras_analise=lambda texto: criar_gigs(driver, 0, 'Pz mdd'))
    if not texto:
        print("[OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
    print('[OUTROS] Análise Outros concluída.')
