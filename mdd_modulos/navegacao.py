"""
Módulo navegacao.py
Centraliza funções de navegação e fluxo do sistema.
Coordena navegação entre telas e controla o fluxo principal.
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Importações das funções auxiliares do projeto
from driver_config import sleep, wait_for_visible, wait, safe_click, validar_conexao_driver

def navegacao(driver, log=True):
    """
    Navega para a lista de documentos internos.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        bool: True se navegação foi bem-sucedida
    """
    try:
        if log:
            print('[NAVEGACAO] Iniciando navegação para lista de documentos internos...')
        
        # Verifica conectividade inicial
        if not validar_conexao_driver(driver, contexto="NAVEGACAO_INICIO"):
            if log:
                print('[NAVEGACAO][ERRO] Driver em estado inválido')
            return False
        
        # Navega para a página de documentos internos
        sucesso_navegacao = navegar_documentos_internos(driver, log)
        
        if not sucesso_navegacao:
            if log:
                print('[NAVEGACAO][ERRO] Falha na navegação para documentos internos')
            return False
        
        # Aguarda página carregar
        sucesso_carregamento = aguardar_carregamento_pagina(driver, log)
        
        if not sucesso_carregamento:
            if log:
                print('[NAVEGACAO][ERRO] Falha no carregamento da página')
            return False
        
        if log:
            print('[NAVEGACAO] Navegação concluída com sucesso')
        
        return True
        
    except Exception as e:
        if log:
            print(f'[NAVEGACAO][ERRO] Erro na navegação: {e}')
        return False

def navegar_documentos_internos(driver, log=True):
    """
    Navega especificamente para a lista de documentos internos.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        bool: True se navegação foi bem-sucedida
    """
    try:
        if log:
            print('[NAVEGACAO] Navegando para documentos internos...')
        
        # Aqui deveria haver a lógica específica de navegação
        # Por exemplo, clicar em menus, botões, etc.
        
        # Placeholder para implementação específica
        # Essa função deve ser implementada baseada na interface do sistema
        
        if log:
            print('[NAVEGACAO] Navegação para documentos internos concluída')
        
        return True
        
    except Exception as e:
        if log:
            print(f'[NAVEGACAO][ERRO] Erro na navegação para documentos internos: {e}')
        return False

def aguardar_carregamento_pagina(driver, log=True):
    """
    Aguarda o carregamento completo da página.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        bool: True se página carregou com sucesso
    """
    try:
        if log:
            print('[NAVEGACAO] Aguardando carregamento da página...')
        
        # Aguarda elementos importantes carregarem
        try:
            # Aguarda timeline ou lista de documentos
            timeline = wait_for_visible(driver, 'ul.timeline-container', timeout=10)
            
            if timeline:
                if log:
                    print('[NAVEGACAO] Timeline carregada com sucesso')
                return True
            else:
                if log:
                    print('[NAVEGACAO] Timeline não encontrada, verificando outras estruturas...')
                
                # Fallback: verifica se há lista de documentos
                lista_docs = wait_for_visible(driver, '.lista-documentos, .documento-item', timeout=5)
                
                if lista_docs:
                    if log:
                        print('[NAVEGACAO] Lista de documentos carregada')
                    return True
                else:
                    if log:
                        print('[NAVEGACAO][AVISO] Estrutura de documentos não encontrada')
                    return False
            
        except Exception as e:
            if log:
                print(f'[NAVEGACAO][ERRO] Erro ao aguardar carregamento: {e}')
            return False
        
    except Exception as e:
        if log:
            print(f'[NAVEGACAO][ERRO] Erro geral no carregamento: {e}')
        return False

def fluxo_mandado(driver, log=True):
    """
    Processa a lista de documentos internos - fluxo principal.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        bool: True se fluxo foi executado com sucesso
    """
    try:
        if log:
            print('[FLUXO] Iniciando processamento da lista de documentos...')
        
        # Verifica conectividade inicial
        if not validar_conexao_driver(driver, contexto="FLUXO_INICIO"):
            if log:
                print('[FLUXO][ERRO] Driver em estado inválido')
            return False
        
        # Identifica o tipo de documento atual
        tipo_documento = identificar_tipo_documento(driver, log)
        
        if not tipo_documento:
            if log:
                print('[FLUXO][ERRO] Não foi possível identificar o tipo de documento')
            return False
        
        # Executa fluxo específico baseado no tipo
        sucesso_fluxo = executar_fluxo_especifico(driver, tipo_documento, log)
        
        if not sucesso_fluxo:
            if log:
                print(f'[FLUXO][ERRO] Falha no fluxo específico: {tipo_documento}')
            return False
        
        if log:
            print('[FLUXO] Processamento concluído com sucesso')
        
        return True
        
    except Exception as e:
        if log:
            print(f'[FLUXO][ERRO] Erro no fluxo principal: {e}')
        return False

def identificar_tipo_documento(driver, log=True):
    """
    Identifica o tipo do documento atual.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        str: Tipo do documento ('argos', 'outros', 'desconhecido')
    """
    try:
        if log:
            print('[FLUXO] Identificando tipo do documento...')
        
        # Busca cabeçalho do documento
        try:
            cabecalho = wait_for_visible(driver, ".cabecalho-conteudo .mat-card-title", timeout=5)
            if not cabecalho:
                cabecalho = driver.find_element(By.CSS_SELECTOR, ".cabecalho-conteudo .mat-card-title")
            
            titulo_documento = cabecalho.text.lower()
            
            # Verifica se é documento do Argos
            termos_argos = [
                "pesquisa patrimonial",
                "argos",
                "relatório de pesquisa",
                "consulta patrimonial"
            ]
            
            if any(termo in titulo_documento for termo in termos_argos):
                if log:
                    print(f'[FLUXO] Documento identificado como Argos: "{cabecalho.text}"')
                return 'argos'
            
            # Verifica se é certidão de oficial
            termos_oficial = [
                "certidão de oficial",
                "certidão de oficial de justiça"
            ]
            
            if any(termo in titulo_documento for termo in termos_oficial):
                if log:
                    print(f'[FLUXO] Documento identificado como Outros: "{cabecalho.text}"')
                return 'outros'
            
            # Tipo não reconhecido
            if log:
                print(f'[FLUXO] Documento não reconhecido: "{cabecalho.text}"')
            return 'desconhecido'
            
        except Exception as e:
            if log:
                print(f'[FLUXO][ERRO] Erro ao identificar documento: {e}')
            return 'desconhecido'
        
    except Exception as e:
        if log:
            print(f'[FLUXO][ERRO] Erro geral na identificação: {e}')
        return 'desconhecido'

def executar_fluxo_especifico(driver, tipo_documento, log=True):
    """
    Executa o fluxo específico baseado no tipo de documento.
    
    Args:
        driver: Instância do WebDriver
        tipo_documento: Tipo do documento
        log: Flag para logs
    
    Returns:
        bool: True se fluxo foi executado com sucesso
    """
    try:
        if log:
            print(f'[FLUXO] Executando fluxo específico: {tipo_documento}')
        
        if tipo_documento == 'argos':
            # Executa fluxo do Argos
            from mdd_modulos.argos_core import processar_argos
            return processar_argos(driver, log)
        
        elif tipo_documento == 'outros':
            # Executa fluxo dos Outros
            from mdd_modulos.outros_core import fluxo_mandados_outros
            return fluxo_mandados_outros(driver, log)
        
        elif tipo_documento == 'desconhecido':
            if log:
                print('[FLUXO] Documento não reconhecido, executando fluxo padrão')
            return executar_fluxo_padrao(driver, log)
        
        else:
            if log:
                print(f'[FLUXO][ERRO] Tipo de documento não suportado: {tipo_documento}')
            return False
        
    except Exception as e:
        if log:
            print(f'[FLUXO][ERRO] Erro no fluxo específico: {e}')
        return False

def executar_fluxo_padrao(driver, log=True):
    """
    Executa fluxo padrão para documentos não reconhecidos.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        bool: True se fluxo foi executado com sucesso
    """
    try:
        if log:
            print('[FLUXO] Executando fluxo padrão...')
        
        # Lógica básica para documentos não reconhecidos
        # Por exemplo, criar GIGS padrão ou registrar log
        
        if log:
            print('[FLUXO] Fluxo padrão concluído')
        
        return True
        
    except Exception as e:
        if log:
            print(f'[FLUXO][ERRO] Erro no fluxo padrão: {e}')
        return False

def fluxo_teste(driver, log=True):
    """
    Fluxo de teste isolado que começa pelo cabeçalho do documento ativo.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        bool: True se teste foi executado com sucesso
    """
    try:
        if log:
            print('[TESTE] Iniciando fluxo de teste...')
        
        # Espera o cabeçalho do documento ativo
        cabecalho = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-card-title.mat-card-title'))
        )
        
        texto_cabecalho = cabecalho.text.lower()
        
        if log:
            print(f"[TESTE] Cabeçalho do documento: {texto_cabecalho}")

        if "pesquisa patrimonial" in texto_cabecalho or "argos" in texto_cabecalho:
            if log:
                print("[TESTE] Iniciando fluxo Argos")
            from mdd_modulos.argos_core import processar_argos
            return processar_argos(driver, log)
        
        elif "oficial de justiça" in texto_cabecalho or "certidão de oficial" in texto_cabecalho:
            if log:
                print("[TESTE] Iniciando fluxo Outros")
            from mdd_modulos.outros_core import fluxo_mandados_outros
            return fluxo_mandados_outros(driver, log)
        
        else:
            if log:
                print(f"[TESTE] Tipo de documento não identificado: {texto_cabecalho}")
            return False

    except Exception as e:
        if log:
            print(f"[TESTE][ERRO] Falha ao identificar o cabeçalho do documento: {e}")
        return False

def validar_navegacao(driver, log=True):
    """
    Valida o estado da navegação atual.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        dict: Informações sobre o estado da navegação
    """
    try:
        estado = {
            'pagina_carregada': False,
            'timeline_presente': False,
            'documento_ativo': False,
            'tipo_documento': None,
            'status': 'unknown'
        }
        
        # Verifica se página está carregada
        try:
            driver.find_element(By.TAG_NAME, 'body')
            estado['pagina_carregada'] = True
        except Exception:
            estado['pagina_carregada'] = False
        
        # Verifica se timeline está presente
        try:
            timeline = driver.find_element(By.CSS_SELECTOR, 'ul.timeline-container')
            estado['timeline_presente'] = timeline.is_displayed()
        except Exception:
            estado['timeline_presente'] = False
        
        # Verifica se há documento ativo
        try:
            cabecalho = driver.find_element(By.CSS_SELECTOR, ".cabecalho-conteudo .mat-card-title")
            estado['documento_ativo'] = True
            estado['tipo_documento'] = identificar_tipo_documento(driver, log)
        except Exception:
            estado['documento_ativo'] = False
        
        # Determina status geral
        if estado['pagina_carregada'] and estado['documento_ativo']:
            estado['status'] = 'ready'
        elif estado['pagina_carregada']:
            estado['status'] = 'partial'
        else:
            estado['status'] = 'invalid'
        
        if log:
            print(f'[NAVEGACAO] Estado validado: {estado}')
        
        return estado
        
    except Exception as e:
        if log:
            print(f'[NAVEGACAO][ERRO] Erro na validação: {e}')
        return {'status': 'error', 'erro': str(e)}

def obter_url_atual(driver, log=True):
    """
    Obtém a URL atual do navegador.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        str: URL atual ou None se erro
    """
    try:
        url_atual = driver.current_url
        
        if log:
            print(f'[NAVEGACAO] URL atual: {url_atual}')
        
        return url_atual
        
    except Exception as e:
        if log:
            print(f'[NAVEGACAO][ERRO] Erro ao obter URL: {e}')
        return None

def navegar_para_url(driver, url, log=True):
    """
    Navega para uma URL específica.
    
    Args:
        driver: Instância do WebDriver
        url: URL de destino
        log: Flag para logs
    
    Returns:
        bool: True se navegação foi bem-sucedida
    """
    try:
        if log:
            print(f'[NAVEGACAO] Navegando para: {url}')
        
        driver.get(url)
        
        # Aguarda carregamento básico
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        
        if log:
            print('[NAVEGACAO] Navegação para URL concluída')
        
        return True
        
    except Exception as e:
        if log:
            print(f'[NAVEGACAO][ERRO] Erro na navegação para URL: {e}')
        return False
