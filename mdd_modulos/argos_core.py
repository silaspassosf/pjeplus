"""
Módulo argos_core.py
Fluxo principal do sistema Argos.
Coordena a execução das funções de processamento de documentos, anexos e regras.
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Importações das funções auxiliares do projeto
from driver_config import sleep, wait_for_visible, wait, safe_click, validar_conexao_driver

# Importações dos módulos MDD
from mdd_modulos.argos_documentos import buscar_documento_argos
from mdd_modulos.argos_anexos import processar_anexos_argos
from mdd_modulos.argos_regras import aplicar_regras_argos
from mdd_modulos.teste_utils import testar_regra_argos_planilha

def processar_argos(driver, log=True):
    """
    Fluxo principal do processamento Argos.
    
    1. Verifica se é documento do Argos
    2. Busca e extrai documento relevante
    3. Processa anexos (sigilo e visibilidade)
    4. Aplica regras de negócio
    5. Executa ações conforme resultado
    
    Args:
        driver: Instância do WebDriver
        log: Flag para ativar/desativar logs
    
    Returns:
        bool: True se processamento foi bem-sucedido
    """
    try:
        if log:
            print('[ARGOS][CORE] Iniciando processamento Argos...')
        
        # Verifica conectividade inicial
        if not validar_conexao_driver(driver, contexto="ARGOS_INICIO"):
            if log:
                print('[ARGOS][CORE][ERRO] Driver em estado inválido')
            return False
        
        # Verifica se é documento do Argos
        if not verificar_documento_argos(driver, log):
            if log:
                print('[ARGOS][CORE] Não é documento do Argos')
            return False
        
        # Busca e extrai documento relevante
        texto_documento, tipo_documento = buscar_documento_argos(driver, log)
        
        if not texto_documento:
            if log:
                print('[ARGOS][CORE][ERRO] Não foi possível extrair documento')
            return False
        
        if log:
            print(f'[ARGOS][CORE] Documento extraído: tipo={tipo_documento}')
        
        # Processa anexos se existirem
        anexos_processados = processar_anexos_argos(driver, log)
        
        if log:
            print(f'[ARGOS][CORE] Anexos processados: {len(anexos_processados)}')
        
        # Aplica regras de negócio
        resultado_regras = aplicar_regras_argos(driver, texto_documento, tipo_documento, log)
        
        if log:
            print(f'[ARGOS][CORE] Regras aplicadas: {resultado_regras}')
        
        # Executa ações finais
        executar_acoes_finais_argos(driver, resultado_regras, log)
        
        if log:
            print('[ARGOS][CORE] Processamento Argos concluído com sucesso')
        
        return True
        
    except Exception as e:
        if log:
            print(f'[ARGOS][CORE][ERRO] Erro no processamento Argos: {e}')
        return False

def verificar_documento_argos(driver, log=True):
    """
    Verifica se o documento atual é do sistema Argos.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        bool: True se for documento do Argos
    """
    try:
        # Verifica pelo cabeçalho do documento
        try:
            cabecalho = wait_for_visible(driver, ".cabecalho-conteudo .mat-card-title", timeout=5)
            if not cabecalho:
                cabecalho = driver.find_element(By.CSS_SELECTOR, ".cabecalho-conteudo .mat-card-title")
            
            titulo_documento = cabecalho.text.lower()
            
            # Verifica se contém termos do Argos
            termos_argos = [
                "pesquisa patrimonial",
                "argos",
                "relatório de pesquisa",
                "consulta patrimonial"
            ]
            
            eh_argos = any(termo in titulo_documento for termo in termos_argos)
            
            if log:
                print(f'[ARGOS][CORE] Documento: "{cabecalho.text}" - É Argos: {eh_argos}')
            
            return eh_argos
            
        except Exception as e:
            if log:
                print(f'[ARGOS][CORE][ERRO] Erro ao verificar cabeçalho: {e}')
            return False
            
    except Exception as e:
        if log:
            print(f'[ARGOS][CORE][ERRO] Erro geral na verificação: {e}')
        return False

def executar_acoes_finais_argos(driver, resultado_regras, log=True):
    """
    Executa as ações finais baseadas no resultado das regras.
    
    Args:
        driver: Instância do WebDriver
        resultado_regras: Resultado das regras aplicadas
        log: Flag para logs
    
    Returns:
        bool: True se ações foram executadas com sucesso
    """
    try:
        if not resultado_regras:
            if log:
                print('[ARGOS][CORE] Nenhuma ação final necessária')
            return True
        
        # Ações baseadas no tipo de resultado
        if resultado_regras.get('tipo') == 'lembrete':
            return executar_lembrete_argos(driver, resultado_regras, log)
        elif resultado_regras.get('tipo') == 'andamento':
            return executar_andamento_argos(driver, resultado_regras, log)
        elif resultado_regras.get('tipo') == 'gigs':
            return executar_gigs_argos(driver, resultado_regras, log)
        else:
            if log:
                print(f'[ARGOS][CORE] Tipo de ação não reconhecido: {resultado_regras.get("tipo")}')
            return False
            
    except Exception as e:
        if log:
            print(f'[ARGOS][CORE][ERRO] Erro ao executar ações finais: {e}')
        return False

def executar_lembrete_argos(driver, resultado_regras, log=True):
    """
    Executa lembrete do Argos.
    
    Args:
        driver: Instância do WebDriver
        resultado_regras: Resultado das regras
        log: Flag para logs
    
    Returns:
        bool: True se lembrete foi executado com sucesso
    """
    try:
        if log:
            print('[ARGOS][CORE] Executando lembrete...')
        
        # Importa função de lembrete
        from mdd_modulos.argos_regras import executar_lembrete
        
        # Executa lembrete com parâmetros
        lembrete_params = resultado_regras.get('parametros', {})
        sucesso = executar_lembrete(driver, lembrete_params, log)
        
        if log:
            print(f'[ARGOS][CORE] Lembrete executado: {sucesso}')
        
        return sucesso
        
    except Exception as e:
        if log:
            print(f'[ARGOS][CORE][ERRO] Erro ao executar lembrete: {e}')
        return False

def executar_andamento_argos(driver, resultado_regras, log=True):
    """
    Executa andamento do Argos.
    
    Args:
        driver: Instância do WebDriver
        resultado_regras: Resultado das regras
        log: Flag para logs
    
    Returns:
        bool: True se andamento foi executado com sucesso
    """
    try:
        if log:
            print('[ARGOS][CORE] Executando andamento...')
        
        # Importa função de andamento
        from mdd_modulos.argos_regras import executar_andamento
        
        # Executa andamento com parâmetros
        andamento_params = resultado_regras.get('parametros', {})
        sucesso = executar_andamento(driver, andamento_params, log)
        
        if log:
            print(f'[ARGOS][CORE] Andamento executado: {sucesso}')
        
        return sucesso
        
    except Exception as e:
        if log:
            print(f'[ARGOS][CORE][ERRO] Erro ao executar andamento: {e}')
        return False

def executar_gigs_argos(driver, resultado_regras, log=True):
    """
    Executa criação de GIGS do Argos.
    
    Args:
        driver: Instância do WebDriver
        resultado_regras: Resultado das regras
        log: Flag para logs
    
    Returns:
        bool: True se GIGS foi executado com sucesso
    """
    try:
        if log:
            print('[ARGOS][CORE] Executando GIGS...')
        
        # Importa função de GIGS
        from mdd_modulos.argos_regras import criar_gigs
        
        # Executa GIGS com parâmetros
        gigs_params = resultado_regras.get('parametros', {})
        sucesso = criar_gigs(driver, gigs_params, log)
        
        if log:
            print(f'[ARGOS][CORE] GIGS executado: {sucesso}')
        
        return sucesso
        
    except Exception as e:
        if log:
            print(f'[ARGOS][CORE][ERRO] Erro ao executar GIGS: {e}')
        return False

def fluxo_argos_completo(driver, log=True):
    """
    Executa o fluxo completo do Argos, incluindo validações e fallbacks.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        bool: True se fluxo foi executado com sucesso
    """
    try:
        if log:
            print('[ARGOS][CORE] Iniciando fluxo completo do Argos...')
        
        # Validação inicial do driver
        if not validar_conexao_driver(driver, contexto="ARGOS_FLUXO_COMPLETO"):
            if log:
                print('[ARGOS][CORE][ERRO] Driver em estado inválido para fluxo completo')
            return False
        
        # Executa processamento principal
        sucesso_processamento = processar_argos(driver, log)
        
        if not sucesso_processamento:
            if log:
                print('[ARGOS][CORE] Processamento principal falhou, tentando fallback...')
            
            # Fallback: tenta processamento simplificado
            sucesso_fallback = processar_argos_fallback(driver, log)
            
            if not sucesso_fallback:
                if log:
                    print('[ARGOS][CORE][ERRO] Fallback também falhou')
                return False
            
            if log:
                print('[ARGOS][CORE] Fallback executado com sucesso')
        
        # Validação final
        if not validar_conexao_driver(driver, contexto="ARGOS_FLUXO_FINAL"):
            if log:
                print('[ARGOS][CORE][AVISO] Driver em estado questionável ao final do fluxo')
            # Não retorna False aqui pois o processamento pode ter sido bem-sucedido
        
        if log:
            print('[ARGOS][CORE] Fluxo completo do Argos concluído')
        
        return True
        
    except Exception as e:
        if log:
            print(f'[ARGOS][CORE][ERRO] Erro no fluxo completo: {e}')
        return False

def processar_argos_fallback(driver, log=True):
    """
    Processamento simplificado do Argos para casos de fallback.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        bool: True se fallback foi executado com sucesso
    """
    try:
        if log:
            print('[ARGOS][CORE] Executando fallback simplificado...')
        
        # Verifica se ainda é documento do Argos
        if not verificar_documento_argos(driver, log):
            if log:
                print('[ARGOS][CORE] Fallback: não é documento do Argos')
            return False
        
        # Tenta extrair documento de forma simplificada
        try:
            from mdd_modulos.argos_documentos import extrair_documento
            texto, _ = extrair_documento(driver)
            
            if texto:
                if log:
                    print('[ARGOS][CORE] Fallback: documento extraído com sucesso')
                
                # Aplica regras básicas
                from mdd_modulos.argos_regras import aplicar_regras_basicas
                resultado = aplicar_regras_basicas(driver, texto, log)
                
                if log:
                    print(f'[ARGOS][CORE] Fallback: regras básicas aplicadas - {resultado}')
                
                return True
            else:
                if log:
                    print('[ARGOS][CORE] Fallback: não foi possível extrair documento')
                return False
                
        except Exception as e:
            if log:
                print(f'[ARGOS][CORE][ERRO] Fallback: erro na extração: {e}')
            return False
            
    except Exception as e:
        if log:
            print(f'[ARGOS][CORE][ERRO] Erro no fallback: {e}')
        return False

def validar_estado_argos(driver, log=True):
    """
    Valida o estado atual do processamento Argos.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        dict: Informações sobre o estado do processamento
    """
    try:
        estado = {
            'documento_argos': False,
            'documento_extraido': False,
            'anexos_processados': 0,
            'regras_aplicadas': False,
            'status': 'unknown'
        }
        
        # Verifica se é documento do Argos
        estado['documento_argos'] = verificar_documento_argos(driver, log)
        
        if estado['documento_argos']:
            # Verifica se documento pode ser extraído
            try:
                from mdd_modulos.argos_documentos import extrair_documento
                texto, _ = extrair_documento(driver)
                estado['documento_extraido'] = bool(texto)
            except Exception:
                estado['documento_extraido'] = False
            
            # Verifica anexos
            try:
                from mdd_modulos.argos_anexos import verificar_estado_anexos
                anexos_info = verificar_estado_anexos(driver, log)
                estado['anexos_processados'] = anexos_info.get('total', 0)
            except Exception:
                estado['anexos_processados'] = 0
        
        # Determina status geral
        if estado['documento_argos'] and estado['documento_extraido']:
            estado['status'] = 'ready'
        elif estado['documento_argos']:
            estado['status'] = 'partial'
        else:
            estado['status'] = 'invalid'
        
        if log:
            print(f'[ARGOS][CORE] Estado validado: {estado}')
        
        return estado
        
    except Exception as e:
        if log:
            print(f'[ARGOS][CORE][ERRO] Erro na validação de estado: {e}')
        return {'status': 'error', 'erro': str(e)}

def obter_informacoes_argos(driver, log=True):
    """
    Obtém informações detalhadas sobre o documento Argos atual.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        dict: Informações detalhadas do documento
    """
    try:
        informacoes = {
            'titulo': None,
            'tipo': None,
            'texto_extraido': None,
            'anexos': [],
            'timestamp': time.time()
        }
        
        # Obtém título do documento
        try:
            cabecalho = driver.find_element(By.CSS_SELECTOR, ".cabecalho-conteudo .mat-card-title")
            informacoes['titulo'] = cabecalho.text.strip()
        except Exception:
            informacoes['titulo'] = "Título não encontrado"
        
        # Determina tipo do documento
        titulo_lower = informacoes['titulo'].lower()
        if "pesquisa patrimonial" in titulo_lower or "argos" in titulo_lower:
            informacoes['tipo'] = 'argos'
        else:
            informacoes['tipo'] = 'desconhecido'
        
        # Extrai texto do documento
        try:
            from mdd_modulos.argos_documentos import extrair_documento
            texto, _ = extrair_documento(driver)
            informacoes['texto_extraido'] = texto
        except Exception as e:
            informacoes['texto_extraido'] = f"Erro na extração: {e}"
        
        # Obtém informações dos anexos
        try:
            from mdd_modulos.argos_anexos import verificar_estado_anexos
            anexos_info = verificar_estado_anexos(driver, log)
            informacoes['anexos'] = anexos_info.get('detalhes', [])
        except Exception:
            informacoes['anexos'] = []
        
        if log:
            print(f'[ARGOS][CORE] Informações obtidas: {len(informacoes["anexos"])} anexos, texto: {len(informacoes["texto_extraido"] or "")} chars')
        
        return informacoes
        
    except Exception as e:
        if log:
            print(f'[ARGOS][CORE][ERRO] Erro ao obter informações: {e}')
        return {'erro': str(e), 'timestamp': time.time()}
