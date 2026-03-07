"""
Módulo para processamento de ofícios - fluxo de download, busca em Gmail e armazenamento de URL.

Funções:
- oficio(): Orquestra todo o fluxo de ofício
- dados(): Extrai dados do processo e faz download
- mail(): Abre Gmail e navega até a conta de ofícios
- mailVT(): Busca o email do ofício no Gmail
- minuta(): Abre o modelo de resposta e armazena URL
- info(): Cria GIGS com a URL armazenada
"""

import logging
import time
import json
import os
from typing import Optional, Dict, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)


def _carregar_storage_oficio() -> Dict[str, Any]:
    """Carrega dados armazenados de ofício do arquivo JSON."""
    try:
        if os.path.exists('oficio_storage.json'):
            with open('oficio_storage.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f'[OFICIO] Erro ao carregar storage: {e}')
    return {}


def _salvar_storage_oficio(dados: Dict[str, Any]) -> None:
    """Salva dados de ofício no arquivo JSON."""
    try:
        with open('oficio_storage.json', 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        logger.info(f'[OFICIO] Storage salvo com sucesso')
    except Exception as e:
        logger.error(f'[OFICIO] Erro ao salvar storage: {e}')


def dados(driver: WebDriver, debug: bool = False) -> bool:
    """
    ETAPA 1: Extrai dados do processo e faz download.
    
    Fluxo:
    - Executa extrair dados do processo e armazena em dadosatuais.json
    - Armazena número do processo
    - Clica no ícone de download na tela ativa
    
    Args:
        driver: WebDriver do Selenium
        debug: Se True, exibe logs detalhados
    
    Returns:
        bool: True se executado com sucesso
    """
    try:
        logger.info('[OFICIO][DADOS] Iniciando extração de dados')
        
        # 1. Executar extrair dados processo
        try:
            from Fix.extracao import extrair_dados_processo
            dados_processo = extrair_dados_processo(driver)
            if dados_processo:
                logger.info('[OFICIO][DADOS] ✓ Dados extraídos com sucesso')
                numero_processo = dados_processo.get('numero_processo', '')
            else:
                logger.error('[OFICIO][DADOS] ✗ Falha ao extrair dados')
                return False
        except ImportError:
            logger.warning('[OFICIO][DADOS] extrair_dados_processo não disponível - tentando alternativa')
            numero_processo = None
        
        # 2. Clicar no ícone de download
        try:
            download_icon = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-download.fa-lg'))
            )
            driver.execute_script('arguments[0].scrollIntoView({block: "center"});', download_icon)
            time.sleep(0.3)
            download_icon.click()
            logger.info('[OFICIO][DADOS] ✓ Download iniciado')
            time.sleep(2)
        except Exception as e:
            logger.error(f'[OFICIO][DADOS] Erro ao clicar download: {e}')
            return False
        
        # 3. Armazenar dados na storage
        storage = _carregar_storage_oficio()
        if numero_processo:
            storage['numero_processo'] = numero_processo
        storage['timestamp'] = time.time()
        _salvar_storage_oficio(storage)
        
        logger.info('[OFICIO][DADOS] ✅ Etapa 1 concluída')
        return True
        
    except Exception as e:
        logger.error(f'[OFICIO][DADOS] Erro geral: {e}')
        return False


def mail(driver: WebDriver, debug: bool = False) -> bool:
    """
    ETAPA 2: Abre Gmail e navega até a conta de ofícios.
    
    Fluxo:
    - Abre https://mail.google.com/mail/u/0/#inbox
    - Clica na conta de ofícios (EquipeSP)
    
    Args:
        driver: WebDriver do Selenium
        debug: Se True, exibe logs detalhados
    
    Returns:
        bool: True se executado com sucesso
    """
    try:
        logger.info('[OFICIO][MAIL] Abrindo Gmail')
        
        # 1. Abrir Gmail
        driver.get('https://mail.google.com/mail/u/0/#inbox')
        time.sleep(3)
        
        logger.info('[OFICIO][MAIL] ✓ Gmail aberto')
        
        # 2. Esperar carregamento
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[role="main"]'))
        )
        
        logger.info('[OFICIO][MAIL] ✅ Etapa 2 concluída')
        return True
        
    except Exception as e:
        logger.error(f'[OFICIO][MAIL] Erro: {e}')
        return False


def mailVT(driver: WebDriver, debug: bool = False) -> bool:
    """
    ETAPA 3: Busca o email do ofício no Gmail e abre resposta do cabeçalho alternativo.
    
    Fluxo:
    - Foca na aba
    - Clica na busca de email
    - Digita número do processo e pressiona enter
    - Clica no primeiro email da lista
    - Busca cabeçalho que não seja da 3ª vara (ANTES de responder)
    - Clica em Responder DAQUELE cabeçalho
    
    Args:
        driver: WebDriver do Selenium
        debug: Se True, exibe logs detalhados
    
    Returns:
        bool: True se executado com sucesso
    """
    try:
        logger.info('[OFICIO][MAILVT] Buscando email do ofício')
        
        storage = _carregar_storage_oficio()
        numero_processo = storage.get('numero_processo', '')
        
        if not numero_processo:
            logger.error('[OFICIO][MAILVT] Número do processo não encontrado na storage')
            return False
        
        # 1. Focar janela
        driver.switch_to.window(driver.current_window_handle)
        time.sleep(0.5)
        
        # 2. Clicar na barra de busca
        search_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[aria-label*="Pesquisar"]'))
        )
        search_input.click()
        time.sleep(0.3)
        
        # 3. Digitar número do processo
        search_input.send_keys(numero_processo)
        time.sleep(0.5)
        search_input.send_keys(Keys.RETURN)
        
        logger.info(f'[OFICIO][MAILVT] Buscando: {numero_processo}')
        time.sleep(3)
        
        # 4. Clicar no primeiro email
        first_email = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'tr[role="row"]'))
        )
        first_email.click()
        
        logger.info('[OFICIO][MAILVT] ✓ Email aberto')
        time.sleep(2)
        
        # 5. BUSCAR CABEÇALHO QUE NÃO É DA 3ª VARA ANTES DE RESPONDER
        # Procura por elementos de cabeçalho que não contêm "SECRETARIA DA 3ª VARA"
        target_header_element = None
        
        try:
            # Buscar todos os cabeçalhos de mensagens
            all_headers = driver.find_elements(By.CSS_SELECTOR, 'div[class*="gE"]')
            
            for header_div in all_headers:
                try:
                    # Verificar se contém "SECRETARIA DA 3ª VARA"
                    header_text = header_div.text or ''
                    
                    # Se não for da 3ª vara, este é o alvo
                    if 'SECRETARIA DA 3ª VARA' not in header_text and header_text.strip():
                        logger.info(f'[OFICIO][MAILVT] ✓ Cabeçalho alternativo encontrado')
                        logger.info(f'[OFICIO][MAILVT] Texto: {header_text[:100]}...')
                        target_header_element = header_div
                        break
                except:
                    continue
            
            if not target_header_element:
                logger.warning('[OFICIO][MAILVT] ⚠ Cabeçalho alternativo não encontrado - usando padrão')
                # Usar primeiro cabeçalho se não encontrar alternativo
                all_headers_list = driver.find_elements(By.CSS_SELECTOR, 'div[class*="gE"]')
                if all_headers_list:
                    target_header_element = all_headers_list[0]
        
        except Exception as header_error:
            logger.warning(f'[OFICIO][MAILVT] Erro ao buscar cabeçalho: {header_error}')
        
        # 6. Buscar botão Responder dentro/próximo do cabeçalho alvo
        reply_btn = None
        
        try:
            if target_header_element:
                # Tentar encontrar botão responder próximo ao cabeçalho alvo
                # Pode estar em elemento pai ou irmão
                try:
                    reply_btn = target_header_element.find_element(By.CSS_SELECTOR, 'span[role="link"][jslog*="21576"]')
                except:
                    # Se não encontrar dentro, procurar no elemento pai
                    parent = target_header_element.find_element(By.XPATH, '..')
                    try:
                        reply_btn = parent.find_element(By.CSS_SELECTOR, 'span[role="link"][jslog*="21576"]')
                    except:
                        pass
            
            # Se ainda não encontrou, usar busca geral
            if not reply_btn:
                logger.info('[OFICIO][MAILVT] Procurando botão Responder por busca geral')
                reply_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'span[role="link"][jslog*="21576"]'))
                )
        
        except Exception as reply_error:
            logger.error(f'[OFICIO][MAILVT] Erro ao encontrar botão Responder: {reply_error}')
            return False
        
        # 7. Clicar em Responder
        driver.execute_script('arguments[0].scrollIntoView({block: "center"});', reply_btn)
        time.sleep(0.3)
        reply_btn.click()
        
        logger.info('[OFICIO][MAILVT] ✓ Modo responder ativado do cabeçalho alternativo')
        time.sleep(1)
        
        logger.info('[OFICIO][MAILVT] ✅ Etapa 3 concluída')
        return True
        
    except Exception as e:
        logger.error(f'[OFICIO][MAILVT] Erro: {e}')
        import traceback
        traceback.print_exc()
        return False


def minuta(driver: WebDriver, debug: bool = False) -> bool:
    """
    ETAPA 4: Abre modelo de resposta e armazena URL.
    
    Fluxo:
    - Clica em ícone de mais opções no cabeçalho
    - Clica em "Modelos"
    - Clica em "Reitera Oficio"
    - Aguarda 4s
    - Copia URL atual para storage
    - Fecha aba
    - Descarta aba Gmail
    
    Args:
        driver: WebDriver do Selenium
        debug: Se True, exibe logs detalhados
    
    Returns:
        bool: True se executado com sucesso
    """
    try:
        logger.info('[OFICIO][MINUTA] Abrindo modelo de resposta')
        
        # 1. Clicar em "Mais opções" no cabeçalho
        more_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[aria-label="Mais opções"]'))
        )
        more_btn.click()
        
        logger.info('[OFICIO][MINUTA] ✓ Menu Mais opções aberto')
        time.sleep(1)
        
        # 2. Clicar em "Modelos"
        models_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@role="menuitem" and contains(., "Modelos")]'))
        )
        models_option.click()
        
        logger.info('[OFICIO][MINUTA] ✓ Menu Modelos aberto')
        time.sleep(1)
        
        # 3. Clicar em "Reitera Oficio"
        reitera_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@role="menuitem" and contains(., "Reitera Oficio")]'))
        )
        reitera_option.click()
        
        logger.info('[OFICIO][MINUTA] ✓ Modelo "Reitera Oficio" selecionado')
        
        # 4. Aguardar 4s para carregar
        time.sleep(4)
        
        # 5. Copiar URL para storage
        current_url = driver.current_url
        storage = _carregar_storage_oficio()
        storage['minuta_url'] = current_url
        _salvar_storage_oficio(storage)
        
        logger.info(f'[OFICIO][MINUTA] ✓ URL armazenada: {current_url}')
        
        # 6. Fechar aba minuta (voltar para aba anterior)
        driver.close()
        time.sleep(1)
        
        # 7. Mudar para aba Gmail restante
        all_windows = driver.window_handles
        if all_windows:
            driver.switch_to.window(all_windows[-1])
            logger.info('[OFICIO][MINUTA] ✓ Voltado à aba anterior')
        
        logger.info('[OFICIO][MINUTA] ✅ Etapa 4 concluída')
        return True
        
    except Exception as e:
        logger.error(f'[OFICIO][MINUTA] Erro: {e}')
        import traceback
        traceback.print_exc()
        return False


def info(driver: WebDriver, debug: bool = False) -> bool:
    """
    ETAPA 5: Cria GIGS com a URL armazenada.
    
    Fluxo:
    - Estamos em /detalhe
    - Executa criar_gigs com -1/(url armazenada)
    
    Args:
        driver: WebDriver do Selenium
        debug: Se True, exibe logs detalhados
    
    Returns:
        bool: True se executado com sucesso
    """
    try:
        logger.info('[OFICIO][INFO] Criando GIGS com URL armazenada')
        
        # 1. Carregar URL da storage
        storage = _carregar_storage_oficio()
        minuta_url = storage.get('minuta_url', '')
        
        if not minuta_url:
            logger.error('[OFICIO][INFO] URL da minuta não encontrada na storage')
            return False
        
        # 2. Executar criar_gigs
        try:
            from Fix.gigs import criar_gigs
            
            # Formato: -1/(url armazenada)
            gigs_param = f'-1/{minuta_url}'
            
            logger.info(f'[OFICIO][INFO] Criando GIGS com: {gigs_param}')
            
            # Assumindo que criar_gigs aceita dias, responsavel, observacao
            resultado = criar_gigs(driver, dias=-1, responsavel='', observacao=minuta_url)
            
            if resultado:
                logger.info('[OFICIO][INFO] ✓ GIGS criado com sucesso')
            else:
                logger.error('[OFICIO][INFO] ✗ Falha ao criar GIGS')
                return False
                
        except ImportError:
            logger.error('[OFICIO][INFO] criar_gigs não disponível')
            return False
        
        logger.info('[OFICIO][INFO] ✅ Etapa 5 concluída')
        return True
        
    except Exception as e:
        logger.error(f'[OFICIO][INFO] Erro: {e}')
        return False


def oficio(driver: WebDriver, numero_processo: Optional[str] = None, debug: bool = False) -> bool:
    """
    Orquestra fluxo completo de ofício.
    
    Ordem de execução:
    1. dados() - Extrai dados e faz download
    2. mail() - Abre Gmail
    3. mailVT() - Busca email do ofício
    4. minuta() - Abre modelo e armazena URL
    5. info() - Cria GIGS com URL
    
    Args:
        driver: WebDriver do Selenium (deve estar em /detalhe)
        numero_processo: Número do processo (obtido automaticamente se não fornecido)
        debug: Se True, exibe logs detalhados
    
    Returns:
        bool: True se fluxo completo executado com sucesso
    """
    try:
        logger.info('[OFICIO] ========== INICIANDO FLUXO DE OFÍCIO ==========')
        
        # ETAPA 1: Dados
        if not dados(driver, debug=debug):
            logger.error('[OFICIO] ✗ Falha na etapa 1 (dados)')
            return False
        
        # ETAPA 2: Gmail
        if not mail(driver, debug=debug):
            logger.error('[OFICIO] ✗ Falha na etapa 2 (mail)')
            return False
        
        # ETAPA 3: Busca no Gmail
        if not mailVT(driver, debug=debug):
            logger.error('[OFICIO] ✗ Falha na etapa 3 (mailVT)')
            return False
        
        # ETAPA 4: Minuta e URL
        if not minuta(driver, debug=debug):
            logger.error('[OFICIO] ✗ Falha na etapa 4 (minuta)')
            return False
        
        # ETAPA 5: Criar GIGS
        if not info(driver, debug=debug):
            logger.error('[OFICIO] ✗ Falha na etapa 5 (info)')
            return False
        
        logger.info('[OFICIO] ========== ✅ FLUXO DE OFÍCIO CONCLUÍDO COM SUCESSO ==========')
        return True
        
    except Exception as e:
        logger.error(f'[OFICIO] Erro geral no fluxo: {e}')
        import traceback
        traceback.print_exc()
        return False
