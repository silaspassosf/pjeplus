"""
Módulo outros_core.py
Fluxo principal dos mandados Outros (Oficial de Justiça).
Processa certidões de oficial e aplica regras de negócio.
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
from mdd_modulos.outros_analise import analise_padrao_outros, ultimo_mdd

def fluxo_mandados_outros(driver, log=True):
    """
    Processa o fluxo de mandados não-Argos (Oficial de Justiça).
    1. Verifica se é certidão de oficial através do cabeçalho
    2. Extrai e analisa o texto da certidão
    3. Verifica padrões de mandado positivo/negativo
    4. Cria GIGS ou executa atos conforme resultado
    """
    if log:
        print('[MANDADOS][OUTROS] Iniciando fluxo Mandado (Outros)')
    
    try:
        # Verifica conectividade inicial
        if not validar_conexao_driver(driver, contexto="OUTROS_INICIO"):
            if log:
                print('[MANDADOS][OUTROS][ERRO] Driver em estado inválido')
            return False
        
        # Verifica se é certidão de oficial através do cabeçalho
        if not verificar_certidao_oficial(driver, log):
            if log:
                print('[MANDADOS][OUTROS] Não é certidão de oficial, criando GIGS fallback')
            # criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
            return True
        
        # Extrai e analisa o texto da certidão
        resultado_analise = extrair_e_analisar_certidao(driver, log)
        
        if not resultado_analise:
            if log:
                print('[MANDADOS][OUTROS][ERRO] Falha na análise da certidão')
            return False
        
        # Executa ações baseadas na análise
        sucesso_acoes = executar_acoes_outros(driver, resultado_analise, log)
        
        if log:
            print(f'[MANDADOS][OUTROS] Fluxo concluído: {sucesso_acoes}')
        
        return sucesso_acoes
        
    except Exception as e:
        if log:
            print(f'[MANDADOS][OUTROS][ERRO] Erro no fluxo: {e}')
        return False

def verificar_certidao_oficial(driver, log=True):
    """
    Verifica se é certidão de oficial através do cabeçalho.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        bool: True se for certidão de oficial
    """
    try:
        # Usa wait_for_visible mais robusto ao invés de find_element direto
        cabecalho = wait_for_visible(driver, ".cabecalho-conteudo .mat-card-title", timeout=5)
        if not cabecalho:
            if log:
                print('[MANDADOS][OUTROS][ALERTA] Cabeçalho não encontrado. Tentando fallback.')
            cabecalho = driver.find_element(By.CSS_SELECTOR, ".cabecalho-conteudo .mat-card-title")
        
        titulo_documento = cabecalho.text.lower()
        
        # Verifica padrões de certidão de oficial
        padroes_oficial = [
            "certidão de oficial",
            "certidão de oficial de justiça"
        ]
        
        eh_certidao_oficial = any(padrao in titulo_documento for padrao in padroes_oficial)
        
        if log:
            print(f"[MANDADOS][OUTROS] Documento '{cabecalho.text}' - É certidão de oficial: {eh_certidao_oficial}")
        
        return eh_certidao_oficial
        
    except Exception as e:
        if log:
            print(f"[MANDADOS][OUTROS][ERRO] Erro ao verificar cabeçalho: {e}")
        return False

def extrair_e_analisar_certidao(driver, log=True):
    """
    Extrai o texto da certidão e executa análise de padrões.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        dict: Resultado da análise ou None se falhou
    """
    try:
        # Extrai texto do documento
        from mdd_modulos.outros_analise import extrair_documento
        
        # Função de análise que será passada para extrair_documento
        def analise_callback(texto):
            return analise_padrao_outros(driver, texto, log)
        
        texto, resultado = extrair_documento(driver, regras_analise=analise_callback)
        
        if not texto:
            if log:
                print("[MANDADOS][OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
            return None
        
        # Retorna resultado da análise
        return {
            'texto': texto,
            'resultado_analise': resultado,
            'timestamp': time.time()
        }
        
    except Exception as e:
        if log:
            print(f"[MANDADOS][OUTROS][ERRO] Erro na extração e análise: {e}")
        return None

def executar_acoes_outros(driver, resultado_analise, log=True):
    """
    Executa ações baseadas no resultado da análise.
    
    Args:
        driver: Instância do WebDriver
        resultado_analise: Resultado da análise do texto
        log: Flag para logs
    
    Returns:
        bool: True se ações foram executadas com sucesso
    """
    try:
        if not resultado_analise:
            if log:
                print('[MANDADOS][OUTROS] Nenhuma ação a executar')
            return True
        
        resultado = resultado_analise.get('resultado_analise')
        
        if not resultado:
            if log:
                print('[MANDADOS][OUTROS] Análise não retornou resultado válido')
            return True
        
        # Executa ações baseadas no tipo de resultado
        if resultado.get('tipo') == 'cancelamento_total':
            return executar_cancelamento_total(driver, log)
        elif resultado.get('tipo') == 'mandado_positivo':
            return executar_mandado_positivo(driver, resultado, log)
        elif resultado.get('tipo') == 'mandado_negativo':
            return executar_mandado_negativo(driver, resultado, log)
        else:
            if log:
                print(f'[MANDADOS][OUTROS] Tipo de ação não reconhecido: {resultado.get("tipo")}')
            return True
            
    except Exception as e:
        if log:
            print(f'[MANDADOS][OUTROS][ERRO] Erro ao executar ações: {e}')
        return False

def executar_cancelamento_total(driver, log=True):
    """
    Executa ordem de cancelamento total.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        bool: True se executado com sucesso
    """
    try:
        if log:
            print("[MANDADOS][OUTROS] Executando ordem de cancelamento total")
        
        # Executa BNDT_apagar
        try:
            from isolar import BNDT_apagar
            BNDT_apagar(driver)
        except ImportError:
            if log:
                print("[MANDADOS][OUTROS][AVISO] Módulo isolar não encontrado")
        
        # Executa def_arq
        try:
            from atos import def_arq
            def_arq(driver)
        except ImportError:
            if log:
                print("[MANDADOS][OUTROS][AVISO] Módulo atos não encontrado")
        
        if log:
            print("[MANDADOS][OUTROS] Cancelamento total executado")
        
        return True
        
    except Exception as e:
        if log:
            print(f"[MANDADOS][OUTROS][ERRO] Erro no cancelamento total: {e}")
        return False

def executar_mandado_positivo(driver, resultado, log=True):
    """
    Executa ações para mandado positivo.
    
    Args:
        driver: Instância do WebDriver
        resultado: Resultado da análise
        log: Flag para logs
    
    Returns:
        bool: True se executado com sucesso
    """
    try:
        if log:
            print("[MANDADOS][OUTROS] Executando ações para mandado positivo")
        
        # Criar GIGS com observação específica
        # criar_gigs(driver, dias_uteis=0, observacao='xx positivo', tela='principal')
        
        if log:
            print("[MANDADOS][OUTROS] Mandado positivo processado")
        
        return True
        
    except Exception as e:
        if log:
            print(f"[MANDADOS][OUTROS][ERRO] Erro no mandado positivo: {e}")
        return False

def executar_mandado_negativo(driver, resultado, log=True):
    """
    Executa ações para mandado negativo.
    
    Args:
        driver: Instância do WebDriver
        resultado: Resultado da análise
        log: Flag para logs
    
    Returns:
        bool: True se executado com sucesso
    """
    try:
        if log:
            print("[MANDADOS][OUTROS] Executando ações para mandado negativo")
        
        texto = resultado.get('texto', '').lower()
        
        # Verifica se contém "penhora de bens"
        if "penhora de bens" in texto:
            if log:
                print("[MANDADOS][OUTROS] Texto contém 'penhora de bens' - chamando ato_meios")
            return executar_ato_meios(driver, log)
        
        # Verifica se contém "deixei de penhorar"
        elif "deixei de penhorar" in texto:
            if log:
                print("[MANDADOS][OUTROS] Texto contém 'deixei de penhorar' - chamando ato_meios")
            return executar_ato_meios(driver, log)
        
        else:
            # Verifica mandado anterior na timeline
            return processar_mandado_anterior(driver, log)
        
    except Exception as e:
        if log:
            print(f"[MANDADOS][OUTROS][ERRO] Erro no mandado negativo: {e}")
        return False

def executar_ato_meios(driver, log=True):
    """
    Executa ato_meios.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        bool: True se executado com sucesso
    """
    try:
        if log:
            print("[MANDADOS][OUTROS] Executando ato_meios...")
        
        # Importa e executa ato_meios
        from atos import ato_meios
        ato_meios(driver)
        
        if log:
            print("[MANDADOS][OUTROS] ato_meios executado com sucesso")
        
        return True
        
    except Exception as e:
        if log:
            print(f"[MANDADOS][OUTROS][ERRO] Erro ao executar ato_meios: {e}")
        return False

def processar_mandado_anterior(driver, log=True):
    """
    Processa o mandado anterior na timeline.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        bool: True se processado com sucesso
    """
    try:
        # Busca último mandado na timeline
        autor, elemento = ultimo_mdd(driver, log=log)
        
        if not autor:
            if log:
                print("[MANDADOS][OUTROS] Não encontrado último mandado na timeline")
            # criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
            return True
        
        # Verifica se é Silas Passos
        if 'silas passos' in autor.lower():
            if log:
                print("[MANDADOS][OUTROS] Último mandado assinado por Silas Passos - chamando ato_edital")
            return executar_ato_edital(driver, log)
        else:
            if log:
                print("[MANDADOS][OUTROS] Último mandado assinado por outro autor - não faz nada")
            return True
            
    except Exception as e:
        if log:
            print(f"[MANDADOS][OUTROS][ERRO] Erro ao processar mandado anterior: {e}")
        return False

def executar_ato_edital(driver, log=True):
    """
    Executa ato_edital.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        bool: True se executado com sucesso
    """
    try:
        if log:
            print("[MANDADOS][OUTROS] Executando ato_edital...")
        
        # Importa e executa ato_edital
        from atos import ato_edital
        ato_edital(driver)
        
        if log:
            print("[MANDADOS][OUTROS] ato_edital executado com sucesso")
        
        return True
        
    except Exception as e:
        if log:
            print(f"[MANDADOS][OUTROS][ERRO] Erro ao executar ato_edital: {e}")
        return False

def processar_mandado_anterior_penhora(driver, log=True):
    """
    Processa mandado anterior verificando se contém 'penhora'.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        bool: True se processado com sucesso
    """
    try:
        if log:
            print("[MANDADOS][OUTROS] Verificando mandado anterior para penhora...")
        
        # Localiza mandado anterior na timeline
        autor_ant, elemento_ant = ultimo_mdd(driver, log=log)
        
        if not elemento_ant:
            if log:
                print("[MANDADOS][OUTROS] Mandado anterior não encontrado")
            return False
        
        # Clica no mandado anterior
        try:
            link_ant = elemento_ant.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            safe_click(driver, link_ant)
            time.sleep(1)
            
            # Extrai texto do mandado anterior
            from mdd_modulos.outros_analise import extrair_documento
            texto_mandado_ant, _ = extrair_documento(driver)
            
            if texto_mandado_ant and 'penhora' in texto_mandado_ant.lower():
                if log:
                    print("[MANDADOS][OUTROS] Mandado anterior contém 'penhora' - chamando ato_meios")
                return executar_ato_meios(driver, log)
            else:
                if log:
                    print("[MANDADOS][OUTROS] Mandado anterior não contém 'penhora'")
                return True
                
        except Exception as e:
            if log:
                print(f"[MANDADOS][OUTROS][ERRO] Falha ao processar mandado anterior: {e}")
            return False
            
    except Exception as e:
        if log:
            print(f"[MANDADOS][OUTROS][ERRO] Erro no processamento de mandado anterior: {e}")
        return False

def validar_estado_outros(driver, log=True):
    """
    Valida o estado atual do processamento Outros.
    
    Args:
        driver: Instância do WebDriver
        log: Flag para logs
    
    Returns:
        dict: Informações sobre o estado do processamento
    """
    try:
        estado = {
            'certidao_oficial': False,
            'texto_extraido': False,
            'mandado_anterior_encontrado': False,
            'status': 'unknown'
        }
        
        # Verifica se é certidão de oficial
        estado['certidao_oficial'] = verificar_certidao_oficial(driver, log)
        
        if estado['certidao_oficial']:
            # Verifica se texto pode ser extraído
            try:
                from mdd_modulos.outros_analise import extrair_documento
                texto, _ = extrair_documento(driver)
                estado['texto_extraido'] = bool(texto)
            except Exception:
                estado['texto_extraido'] = False
            
            # Verifica se há mandado anterior
            try:
                autor, elemento = ultimo_mdd(driver, log=log)
                estado['mandado_anterior_encontrado'] = bool(elemento)
            except Exception:
                estado['mandado_anterior_encontrado'] = False
        
        # Determina status geral
        if estado['certidao_oficial'] and estado['texto_extraido']:
            estado['status'] = 'ready'
        elif estado['certidao_oficial']:
            estado['status'] = 'partial'
        else:
            estado['status'] = 'invalid'
        
        if log:
            print(f'[MANDADOS][OUTROS] Estado validado: {estado}')
        
        return estado
        
    except Exception as e:
        if log:
            print(f'[MANDADOS][OUTROS][ERRO] Erro na validação de estado: {e}')
        return {'status': 'error', 'erro': str(e)}
