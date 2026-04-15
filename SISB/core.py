import logging
logger = logging.getLogger(__name__)

"""
SISB/core.py - Módulo Core do SISBAJUD

Este módulo contém as funções essenciais para inicialização e autenticação no SISBAJUD:
- driver_sisbajud(): Cria driver Firefox configurado para SISBAJUD
- login_automatico_sisbajud(): Login automatizado com simulação humana
- login_manual_sisbajud(): Login manual aguardando usuário
- salvar_dados_processo_temp(): Salva dados temporários do processo
- iniciar_sisbajud(): Função unificada de inicialização completa

E as funções orquestradoras principais:
- minuta_bloqueio(): Orquestra criação de minuta de bloqueio
- processar_ordem_sisbajud(): Orquestra processamento de ordens
- processar_bloqueios(): Orquestra processamento de bloqueios
- processar_endereco(): Orquestra processamento de endereços

Criado durante refatoração modular do sisb.py (275KB → 4 módulos)
"""

import os
import json
import time
import random
import traceback
from datetime import datetime, timedelta

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# Imports do projeto
try:
    from driver_config import criar_driver_sisb
except Exception:
    try:
        from Fix.drivers.lifecycle import criar_driver_sisb_pc as criar_driver_sisb
    except Exception:
        criar_driver_sisb = None
from . import helpers
# Importar função diretamente do módulo de campos para evitar depender
# do namespace `processamento` em tempo de execução.
from .processamento_campos import _configurar_valor
from . import utils

# Função auxiliar para simulação humana (extraída de sisb.py)
def simular_movimento_humano(driver, elemento):
    """
    Simula movimento de mouse humano antes de clicar em elemento
    """
    try:
        actions = ActionChains(driver)
        
        # Movimento com curva (não linear)
        if random.random() < 0.7:  # 70% chance de movimento curvo
            # Primeiro move para uma posição próxima (não exata)
            offset_x = random.randint(-10, 10)
            offset_y = random.randint(-10, 10)
            actions.move_to_element_with_offset(elemento, offset_x, offset_y)
            actions.pause(random.uniform(0.1, 0.3))
        
        # Move para o elemento final
        actions.move_to_element(elemento)
        actions.pause(random.uniform(0.1, 0.5))
        actions.perform()
        
    except Exception as e:
        _ = e

# Variável global para armazenar dados do processo
processo_dados_extraidos = None


def driver_sisbajud():
    """Cria o driver para SISBAJUD usando a fábrica definida em driver_config."""
    try:
        if not criar_driver_sisb:
            logger.info('[SISBAJUD][DRIVER]  criar_driver_sisb indisponível (driver_config ausente)')
            return None
        logger.info('[SISBAJUD][DRIVER] Iniciando criação do driver Firefox SISBAJUD...')
        # A fábrica criar_driver_sisb devolve um WebDriver configurado para SISBAJUD
        driver = criar_driver_sisb()
        if driver:
            logger.info('[SISBAJUD][DRIVER]  Driver criado com sucesso')
        else:
            logger.info('[SISBAJUD][DRIVER]  criar_driver_sisb retornou None')
        return driver
    except Exception as e:
        logger.info(f"[SISBAJUD][DRIVER]  Erro ao criar driver SISBAJUD via driver_config: {e}")
        import traceback
        logger.exception("Erro detectado")
        return None


def login_automatico_sisbajud(driver):
    """
    Login automatizado humanizado no SISBAJUD com simulação de comportamento humano
    """
    try:
        logger.info('[SISBAJUD][LOGIN] Navegando para SISBAJUD...')
        driver.get('https://sisbajud.cnj.jus.br/')

        # Aguardar carregamento otimizado
        time.sleep(random.uniform(1.0, 1.5))  # Reduzido de 2.5-4.0 para 1.0-1.5

        # Verificar se já está logado
        current_url = driver.current_url
        if not any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms']):
            logger.info('[SISBAJUD][LOGIN]  Já está logado!')
            return True

        # 1. Clicar no campo de login e digitar CPF como humano
        logger.info('[SISBAJUD][LOGIN] 1. Clicando no campo de login e digitando CPF como humano...')
        try:
            username_field = driver.find_element(By.ID, "username")
            simular_movimento_humano(driver, username_field)
            username_field.click()
            time.sleep(random.uniform(0.3, 0.7))
            cpf = os.environ.get('BP_SISB', '')
            for i, char in enumerate(cpf):
                # Simular erro de digitação (5% chance)
                if random.random() < 0.05:
                    erro_char = str(random.randint(0,9))
                    username_field.send_keys(erro_char)
                    time.sleep(random.uniform(0.08, 0.18))
                    username_field.send_keys(Keys.BACKSPACE)
                    time.sleep(random.uniform(0.08, 0.18))
                username_field.send_keys(char)
                time.sleep(random.uniform(0.09, 0.22))
            logger.info('[SISBAJUD][LOGIN]  CPF digitado como humano')
        except Exception as e:
            logger.info(f'[SISBAJUD][LOGIN]  Erro ao digitar CPF: {e}')
            return False

        # 2. Clicar no campo de senha e digitar senha como humano
        logger.info('[SISBAJUD][LOGIN] 2. Clicando no campo de senha e digitando senha como humano...')
        try:
            password_field = driver.find_element(By.ID, "password")
            simular_movimento_humano(driver, password_field)
            password_field.click()
            time.sleep(random.uniform(0.3, 0.7))
            senha = os.environ.get('BP_PASS', '')
            for i, char in enumerate(senha):
                # Simular erro de digitação (5% chance)
                if random.random() < 0.05:
                    erro_char = chr(random.randint(33,126))
                    password_field.send_keys(erro_char)
                    time.sleep(random.uniform(0.08, 0.18))
                    password_field.send_keys(Keys.BACKSPACE)
                    time.sleep(random.uniform(0.08, 0.18))
                password_field.send_keys(char)
                time.sleep(random.uniform(0.09, 0.22))
            logger.info('[SISBAJUD][LOGIN]  Senha digitada como humano')
        except Exception as e:
            logger.info(f'[SISBAJUD][LOGIN]  Erro ao digitar senha: {e}')
            return False

        # 3. Clicar no botão de login "Entrar"
        logger.info('[SISBAJUD][LOGIN] 3. Clicando no botão de login "Entrar"...')
        try:
            btn_entrar = driver.find_element(By.ID, "kc-login")
            simular_movimento_humano(driver, btn_entrar)
            btn_entrar.click()
            logger.info('[SISBAJUD][LOGIN]  Botão "Entrar" clicado')
        except Exception as e:
            logger.info(f'[SISBAJUD][LOGIN]  Erro ao clicar no botão de login: {e}')
            return False

        # Aguardar redirecionamento com verificação inteligente
        logger.info('[SISBAJUD][LOGIN] Aguardando redirecionamento...')
        max_tentativas = 20  # 20 tentativas x 0.5s = 10 segundos máximo
        for tentativa in range(max_tentativas):
            time.sleep(0.5)
            try:
                current_url = driver.current_url.lower()
                
                # Sucesso: redirecionou para SISBAJUD sem indicadores de login
                if 'sisbajud.cnj.jus.br' in current_url and not any(ind in current_url for ind in ['login', 'auth', 'realms']):
                    logger.info('[SISBAJUD][LOGIN]  Login realizado com sucesso!')
                    
                    # Maximizar a janela imediatamente após o login para garantir visibilidade dos elementos
                    try:
                        driver.maximize_window()
                        logger.info('[SISBAJUD][LOGIN]  Janela maximizada após login automático')
                    except Exception as e:
                        _ = e
                    return True
                
                # Verificação manual necessária: ainda em página de auth mas não na tela inicial de login
                if any(ind in current_url for ind in ['auth', 'realms']) and 'kc-login' not in driver.page_source:
                    logger.info('[SISBAJUD][LOGIN]  Login automático não concluído - pode necessitar verificação manual')
                    logger.info('[SISBAJUD][LOGIN]  URL atual:', driver.current_url)
                    return 'manual_needed'
                    
            except Exception as e:
                _ = e
        
        # Timeout: verificar estado final
        current_url = driver.current_url.lower()
        if 'sisbajud.cnj.jus.br' in current_url and not any(ind in current_url for ind in ['login', 'auth', 'realms']):
            logger.info('[SISBAJUD][LOGIN]  Login realizado com sucesso (após timeout)')
            return True
        else:
            logger.info('[SISBAJUD][LOGIN]  Login não concluído automaticamente - pode precisar de verificação')
            logger.info('[SISBAJUD][LOGIN]  URL final:', driver.current_url)
            return 'manual_needed'

    except Exception as e:
        logger.info(f'[SISBAJUD][LOGIN]  Erro durante login: {e}')
        logger.exception("Erro detectado")
        return False


def login_manual_sisbajud(driver, aguardar_url_final=True):
    """
    Login manual para SISBAJUD: navega até a página de login e aguarda o usuário completar o login.
    """
    try:
        logger.info('[SISBAJUD][LOGIN_MANUAL] Navegando para SISBAJUD e aguardando login manual...')
        
        # Verificar se já está na página de login/auth (não navegar de novo se já estiver)
        current_url = driver.current_url
        if not any(ind in current_url.lower() for ind in ['sisbajud', 'login', 'auth', 'realms']):
            driver.get('https://sisbajud.cnj.jus.br/')
        else:
            logger.info('[SISBAJUD][LOGIN_MANUAL] Já está na página de autenticação, aguardando conclusão...')
        
        # Aguarda o usuário completar o login
        target_indicator = 'sisbajud.cnj.jus.br'
        import time
        timeout = 300  # ⏰ 5 minutos para login manual (tempo suficiente para código de verificação)
        inicio = time.time()
        while True:
            try:
                current = driver.current_url.lower()
                # Verificar se está em SISBAJUD E não está em página de autenticação
                if target_indicator in current and not any(ind in current for ind in ['login', 'auth', 'realms']):
                    logger.info('[SISBAJUD][LOGIN_MANUAL] Login detectado manualmente (URL mudou).')
                    
                    # Tentar salvar cookies via driver_config helper para persistência
                    try:
                        from driver_config import salvar_cookies_sessao, salvar_cookies_sisbajud, SALVAR_COOKIES_AUTOMATICO
                        if SALVAR_COOKIES_AUTOMATICO:
                            try:
                                salvar_cookies_sisbajud(driver, info_extra='login_manual_sisbajud')
                                logger.info('[SISBAJUD][LOGIN_MANUAL] Cookies salvos após login manual SISBAJUD')
                            except Exception as e:
                                logger.info(f"[SISBAJUD][LOGIN_MANUAL] Falha ao salvar cookies: {e}")
                    except Exception:
                        # driver_config pode não estar disponível neste contexto
                        _ = None
                    return True
            except Exception as e:
                _ = e
            if not aguardar_url_final:
                return False
            if time.time() - inicio > timeout:
                logger.info('[SISBAJUD][LOGIN_MANUAL] Timeout aguardando login manual.')
                return False
            time.sleep(0.5)  #  REDUZIDO: 1s → 0.5s (resposta mais rápida ao timeout)
    except Exception as e:
        logger.info(f'[SISBAJUD][LOGIN_MANUAL] Erro durante login manual: {e}')
        return False


def salvar_dados_processo_temp(params_adicionais=None):
    """
    Salva dados do processo no arquivo do projeto (dadosatuais.json) para integração entre janelas
    """
    try:
        # Usa caminho do projeto ao invés de pasta temporária
        project_path = os.path.dirname(os.path.abspath(__file__))  # Pasta onde está o sisbajud.py
        dados_path = os.path.join(project_path, 'dadosatuais.json')

        # Adicionar parâmetros de automação aos dados do processo
        dados_para_salvar = processo_dados_extraidos.copy()
        if params_adicionais:
            dados_para_salvar['parametros_automacao'] = params_adicionais
            logger.info(f'[SISBAJUD] Parâmetros de automação adicionados: {params_adicionais}')

        # Sempre sobrescreve o arquivo para não acumular dados de múltiplos processos
        with open(dados_path, 'w', encoding='utf-8') as f:
            json.dump(dados_para_salvar, f, ensure_ascii=False, indent=2)
        logger.info(f'[SISBAJUD] Dados do processo salvos em: {dados_path}')
    except Exception as e:
        logger.info(f'[SISBAJUD][ERRO] Falha ao salvar dados do processo: {e}')


def iniciar_sisbajud(driver_pje=None, extrair_dados=False):
    """
    Função unificada de inicialização do SISBAJUD:
    1. [OPCIONAL] Extrai dados do processo PJe (somente se extrair_dados=True E processo aberto)
    2. Cria driver Firefox SISBAJUD
    3. Realiza login automatizado
    4. Retorna o driver SISBAJUD logado

    IMPORTANTE: Para uso em lote, chamar com extrair_dados=False.
    A extração de dados deve ser feita DEPOIS de abrir cada processo individual.
    """
    global processo_dados_extraidos

    try:
        logger.info('[SISBAJUD] ============================================')
        logger.info('[SISBAJUD] Iniciando sessão SISBAJUD...')
        logger.info(f'[SISBAJUD][DEBUG] extrair_dados={extrair_dados}, driver_pje presente={driver_pje is not None}')
        logger.info('[SISBAJUD] ============================================')

        # 1. Extrair dados do processo PJe (SOMENTE se solicitado explicitamente E driver fornecido)
        if extrair_dados and driver_pje:
            logger.info('[SISBAJUD] Extraindo dados do processo PJe...')
            from Fix.extracao import extrair_dados_processo
            processo_dados_extraidos = extrair_dados_processo(driver_pje)
            if processo_dados_extraidos:
                # Corrigir para usar o campo correto do dadosatuais.json
                numero_lista = processo_dados_extraidos.get("numero", [])
                numero_display = numero_lista[0] if numero_lista else "N/A"
                logger.info(f'[SISBAJUD]  Dados extraídos: {numero_display}')
                salvar_dados_processo_temp()
            else:
                logger.info('[SISBAJUD]  Não foi possível extrair dados do processo')
        elif extrair_dados and not driver_pje:
            logger.info('[SISBAJUD]  Driver PJE não fornecido, não é possível extrair dados')

        # 2. Criar driver Firefox SISBAJUD
        logger.info('[SISBAJUD] Criando driver Firefox SISBAJUD...')
        driver = driver_sisbajud()
        
        if not driver:
            logger.info('[SISBAJUD]  Falha ao criar driver - driver_sisbajud() retornou None')
            return None
        
        logger.info(f'[SISBAJUD][DEBUG] Driver criado com sucesso: {type(driver)}')
        # Tentativa: recarregar cookies específicos do SISBAJUD (implementado em bacen.py)
        cookie_restored = False
        try:
            from bacen import carregar_cookies_sisbajud
            try:
                if carregar_cookies_sisbajud(driver):
                    logger.info('[SISBAJUD]  Cookies SISBAJUD carregados com sucesso; pulando etapa de login.')
                    cookie_restored = True
            except Exception:
                # falha ao carregar cookies SISBAJUD - continuar para o fluxo de login
                cookie_restored = False
        except Exception:
            # módulo bacen pode não existir em todos os contextos; ignorar
            cookie_restored = False

        if not driver:
            logger.info('[SISBAJUD]  Falha ao criar driver')
            return None

        # Realizar login: priorizar cookies SISBAJUD, depois tentar login automático SISBAJUD
        try:
            from driver_config import criar_driver_sisb, criar_driver_sisb_notebook, salvar_cookies_sessao, salvar_cookies_sisbajud, SALVAR_COOKIES_AUTOMATICO
        except Exception:
            criar_driver_sisb = None
            criar_driver_sisb_notebook = None
            salvar_cookies_sessao = None
            SALVAR_COOKIES_AUTOMATICO = False

        try:
            from bacen import carregar_cookies_sisbajud
        except Exception:
            carregar_cookies_sisbajud = None

        # Se os cookies SISBAJUD foram restaurados anteriormente, já temos sessão válida
        login_ok = False
        if cookie_restored:
            login_ok = True

        # Tentar carregar cookies específicos do SISBAJUD (formato do módulo bacen)
        if not login_ok and carregar_cookies_sisbajud:
            try:
                if carregar_cookies_sisbajud(driver):
                    logger.info('[SISBAJUD]  Cookies SISBAJUD (bacen) carregados com sucesso; pulando etapa de login.')
                    login_ok = True
            except Exception as e:
                _ = e

        # Se ainda não temos sessão, tentar login automático SISBAJUD (função local)
        if not login_ok:
            try:
                logger.info('[SISBAJUD] Tentando login automático SISBAJUD (função interna)...')
                resultado_login = login_automatico_sisbajud(driver)
                logger.info(f'[SISBAJUD][DEBUG] Resultado do login_automatico_sisbajud: {resultado_login}')
                
                if resultado_login == True:
                    login_ok = True
                    logger.info('[SISBAJUD]  Login automático bem-sucedido')
                    # Salvar cookies gerados pelo login automático, se configurado
                    try:
                        if SALVAR_COOKIES_AUTOMATICO and salvar_cookies_sisbajud:
                            salvar_cookies_sisbajud(driver, info_extra='login_automatico_sisbajud')
                    except Exception as e:
                        _ = e
                elif resultado_login == 'manual_needed':
                    logger.info('[SISBAJUD]  Login automático requer intervenção manual (código de verificação)')
                    logger.info('[SISBAJUD]  Por favor, complete o login manualmente (insira código de verificação se necessário)...')
                    # Aguardar conclusão manual sem timeout curto
                    if login_manual_sisbajud(driver, aguardar_url_final=True):
                        login_ok = True
                        logger.info('[SISBAJUD]  Login completado manualmente com sucesso')
                        # Salvar cookies após conclusão manual
                        try:
                            if SALVAR_COOKIES_AUTOMATICO and salvar_cookies_sisbajud:
                                salvar_cookies_sisbajud(driver, info_extra='login_manual_pos_automatico')
                        except Exception as e:
                            _ = e
                    else:
                        logger.info('[SISBAJUD]  Login manual não foi concluído')
                else:
                    logger.info(f'[SISBAJUD]  Login automático retornou: {resultado_login}')
                    logger.info('[SISBAJUD] Login automático SISBAJUD falhou, seguindo para login manual...')
            except Exception as e:
                logger.info(f'[SISBAJUD]  Erro no login automático SISBAJUD: {e}')
                import traceback
                logger.exception("Erro detectado")

        # Se ainda não logado, fallback para login manual SISBAJUD
        if not login_ok:
            try:
                logger.info('[SISBAJUD] Aguardando login MANUAL SISBAJUD...')
                if login_manual_sisbajud(driver):
                    login_ok = True
                    # Salvar cookies após login manual SISBAJUD (se permitido)
                    try:
                        if SALVAR_COOKIES_AUTOMATICO and salvar_cookies_sisbajud:
                            salvar_cookies_sisbajud(driver, info_extra='login_manual_sisbajud')
                            logger.info('[SISBAJUD]  Cookies SISBAJUD salvos após login manual')
                    except Exception as e:
                        logger.info(f'[SISBAJUD]  Falha ao salvar cookies SISBAJUD: {e}')
                else:
                    logger.info('[SISBAJUD]  Login manual SISBAJUD falhou ou expirou')
            except Exception as e:
                logger.info(f'[SISBAJUD] Erro durante login manual SISBAJUD: {e}')

        if not login_ok:
            logger.info('[SISBAJUD]  Não foi possível autenticar no SISBAJUD')
            try:
                driver.quit()
            except Exception as e:
                _ = e
            return None

        # Se chegou aqui, o login foi bem-sucedido — agora AGUARDAR explicitamente pela URL /minuta
        minuta_indicator = 'sisbajud.cnj.jus.br/minuta'
        url_timeout = 120
        inicio_url = time.time()
        url_ready = False
        while time.time() - inicio_url < url_timeout:
            try:
                current = driver.current_url.lower()
                if minuta_indicator in current:
                    logger.info('[SISBAJUD]  URL /minuta detectada')
                    url_ready = True
                    break
            except Exception as e:
                _ = e
            time.sleep(0.5)

        if not url_ready:
            logger.info('[SISBAJUD]  Timeout aguardando a URL https://sisbajud.cnj.jus.br/minuta após login')
            return None

        # Após detectar a URL específica, aguardar 2 segundos
        logger.info('[SISBAJUD]  URL /minuta confirmada, aguardando 2 segundos...')
        time.sleep(2)

        # Maximizar janela rapidamente
        try:
            driver.maximize_window()
            logger.info('[SISBAJUD]  Janela maximizada')
        except Exception as e:
            logger.info(f'[SISBAJUD]  Não foi possível maximizar a janela: {e}')

        logger.info('[SISBAJUD]  Sessão SISBAJUD inicializada com sucesso - login realizado, aguardando próxima ação')
        return driver
# exceção externa para toda inicialização
    except Exception as e:
        logger.info(f'[SISBAJUD][ERRO] Falha ao iniciar sessão SISBAJUD: {e}')
        try:
            logger.exception("Erro detectado")
        except Exception as trace_err:
            _ = trace_err

    return None


def minuta_bloqueio(driver, dados_processo=None, driver_pje=None, log=True, fechar_driver=True, prazo_dias=None, protocolar=False):
    """
    Orquestra a criação de minuta de bloqueio no SISBAJUD:
    0. Extrair dados do processo (se necessário) e verificar valor
    1. Se não houver valor: criar GIGS -1/xs valor e retornar
    2. Se houver valor: prosseguir com criação da minuta
    3. Validar dados do processo
    4. Preencher campos iniciais
    5. Processar REUs otimizado
    6. Salvar minuta
    7. Gerar relatório
    
    Args:
        fechar_driver: Se True, fecha o driver SISBAJUD ao final. Use False para processamento em lote.
        prazo_dias: Prazo em dias (30 ou 60). Se None, solicita ao usuário via diálogo.
    """
    resultado = {
        'status': 'pendente',
        'reus_processados': 0,
        'erros': [],
        'detalhes': {}
    }

    try:
        logger.info('\n[SISBAJUD] INICIANDO CRIAÇÃO DE MINUTA DE BLOQUEIO')
        logger.info('=' * 60)

        # 0. EXTRAIR DADOS DO PROCESSO (se necessário) e VERIFICAR VALOR
        if dados_processo is None:
            if log:
                logger.info('[SISBAJUD] Extraindo dados do processo do PJe...')
            try:
                from Fix.extracao import extrair_dados_processo
                if driver_pje:
                    dados_processo = extrair_dados_processo(driver_pje)
                else:
                    # Fallback: carregar do arquivo
                    from .utils import carregar_dados_processo
                    dados_processo = carregar_dados_processo()
                
                if not dados_processo:
                    if log:
                        logger.info('[SISBAJUD]  Falha ao extrair/carregar dados do processo')
                    resultado['status'] = 'erro'
                    resultado['erros'].append('Falha ao extrair/carregar dados do processo')
                    return resultado
                    
                if log:
                    logger.info('[SISBAJUD]  Dados do processo extraídos/carregados com sucesso')
            except Exception as e:
                if log:
                    logger.info(f'[SISBAJUD]  Erro ao extrair dados do processo: {e}')
                resultado['status'] = 'erro'
                resultado['erros'].append(f'Erro ao extrair dados: {e}')
                return resultado

        # VERIFICAR SE HÁ VALOR DE BLOQUEIO (validação final - normalmente já verificado antes no lote)
        divida = dados_processo.get('divida', {}) if dados_processo else {}
        valor = divida.get('valor')
        
        if not valor:
            if log:
                logger.info('[SISBAJUD]  Sem valor de bloqueio - função deveria ter sido chamada apenas com valor')
            resultado['status'] = 'erro'
            resultado['erros'].append('Sem valor de bloqueio')
            return resultado
        
        if log:
            logger.info(f'[SISBAJUD]  Valor encontrado: {valor} - prosseguindo com minuta')

        # 1. Clicar em "Nova Minuta" para iniciar criação de minuta
        logger.info('[SISBAJUD] Clicando em "Nova Minuta" para iniciar criação...')
        script_nova_minuta = """
        var botaoNova = document.querySelector('button.mat-fab.mat-primary .fa-plus');
        if (!botaoNova) {
            botaoNova = document.querySelector('button.mat-fab.mat-primary');
        }
        if (botaoNova) {
            // Se for ícone, clica no botão pai
            if (botaoNova.tagName === 'MAT-ICON') {
                botaoNova = botaoNova.closest('button');
            }
            botaoNova.click();
            return true;
        }
        return false;
        """

        sucesso_nova_minuta = driver.execute_script(script_nova_minuta)
        if sucesso_nova_minuta:
            logger.info('[SISBAJUD]  Botão "Nova Minuta" clicado automaticamente')
            time.sleep(2)  # Aguardar navegação
        else:
            logger.info('[SISBAJUD]  Botão "Nova Minuta" não encontrado')
            return {
                'status': 'erro',
                'erros': ['Botão "Nova Minuta" não encontrado'],
                'reus_processados': 0,
                'detalhes': {}
            }

        # 2. Validar dados do processo
        dados_validos, numero_processo = helpers._validar_dados(dados_processo)
        if not dados_validos:
            resultado['status'] = 'erro'
            resultado['erros'].append('Dados do processo inválidos ou insuficientes')
            return resultado

        # 2.1 Usar prazo_dias fornecido ou padrão 30
        if prazo_dias is None:
            prazo_dias = 30

        # 3. Preencher campos iniciais (com o prazo selecionado)
        campos_preenchidos = helpers._preencher_campos_iniciais(driver, dados_processo, prazo_dias)
        if not campos_preenchidos:
            resultado['status'] = 'erro'
            resultado['erros'].append('Falha ao preencher campos iniciais')
            return resultado

        # 4. Processar REUs otimizado
        reus_processados = helpers._processar_reus_otimizado(driver, dados_processo.get('reu', []))
        resultado['reus_processados'] = reus_processados

        # 5. Configurar valor da execução
        _configurar_valor(driver, dados_processo)

        # 6. Salvar minuta
        minuta_salva = helpers._salvar_minuta(driver)
        if not minuta_salva:
            resultado['status'] = 'erro'
            resultado['erros'].append('Falha ao salvar minuta')
            return resultado

        # 6.1 PROTOCOLAR/ASSINAR MINUTA
        # REMOVIDO: passo de protocolar/assinar foi desativado (pulamos essa fase)
        minuta_protocolada = False
        resultado['minuta_protocolada'] = False
        if log:
            logger.info('[SISBAJUD]  Passo 6.1 (protocolar/assinar) foi removido - continuando fluxo')

        # 6.2 Gerar relatório (para juntada posterior manual/automática)
        relatorio_gerado = helpers._gerar_relatorio_minuta(driver, numero_processo)
        if not relatorio_gerado:
            if log:
                logger.info('[SISBAJUD]  Falha ao gerar relatório da minuta')
            # Prosseguir com fechamento e retorno com status de erro parcial

        # 6.5 Se o relatório foi gerado e um driver PJE foi passado, executar a juntada
        # (usa relatório da PRIMEIRA minuta)
        juntada_executada = False
        if relatorio_gerado:
            if log:
                logger.info(f'[SISBAJUD][DEBUG] relatorio_gerado: {bool(relatorio_gerado)}, driver_pje presente: {driver_pje is not None}')
            # Debug: mostrar tipo/representação do driver_pje
            if driver_pje is not None and log:
                try:
                    logger.info(f'[SISBAJUD][DEBUG] driver_pje type: {type(driver_pje)}')
                except Exception as e:
                    _ = e
        if relatorio_gerado and driver_pje:
            try:
                # A juntada da minuta de bloqueio deve usar o próprio modelo da minuta
                # (modelo 'xteim') — não usar os wrappers de ordem genéricos.
                if log:
                    logger.info('[SISBAJUD] ▶ Executando juntada DA MINUTA no PJe (modelo xteim)...')

                # Importar wrapper específico que insere conteúdo do relatório SISBAJUD
                try:
                    from PEC.anexos import consulta_wrapper
                except Exception:
                    consulta_wrapper = None

                if consulta_wrapper:
                    # chamar consulta_wrapper com modelo correto
                    juntada_executada = consulta_wrapper(driver_pje, numero_processo, debug=log, modelo='xteim')
                    resultado['juntada_executada'] = bool(juntada_executada)
                    if juntada_executada and log:
                        logger.info('[SISBAJUD]  Juntada da minuta realizada no PJe')
                    elif log:
                        logger.info('[SISBAJUD]  Juntada da minuta pode não ter sido executada corretamente')

                    # Após a juntada, retornar para /detalhe e aplicar visibilidade para certidão sigilosa
                    if juntada_executada and driver_pje:
                        from atos.wrappers_utils import executar_visibilidade_sigilosos_se_necessario
                        if log:
                            logger.info('[SISBAJUD] ▶ Aplicando visibilidade para certidão sigilosa no PJe (/detalhe)...')
                        vis_ok = executar_visibilidade_sigilosos_se_necessario(driver_pje, True, debug=log)
                        resultado['visibilidade_certidao_sigilosa'] = bool(vis_ok)
                        if vis_ok and log:
                            logger.info('[SISBAJUD]  Visibilidade para certidão sigilosa aplicada')
                        elif log:
                            logger.info('[SISBAJUD]  Falha ao aplicar visibilidade para certidão sigilosa')
                        
                        # Criar GIGS 22/xs resultado (após visibilidade, ainda em /detalhe)
                        from Fix.extracao import criar_gigs
                        if log:
                            logger.info('[SISBAJUD] ▶ Criando GIGS 22/xs resultado...')
                        resultado_gigs = criar_gigs(driver_pje, '22/xs resultado', log=log)
                        if resultado_gigs and log:
                            logger.info('[SISBAJUD]  GIGS 22/xs resultado criado')
                        elif log:
                            logger.info('[SISBAJUD]  GIGS 22/xs resultado não foi criado')
                else:
                    resultado['erros'].append('consulta_wrapper não disponível')
                    if log:
                        logger.info('[SISBAJUD]  consulta_wrapper não disponível para executar juntada da minuta')
            except Exception as e:
                resultado['erros'].append(f'Erro na juntada PJE (minuta): {e}')
                if log:
                    logger.info(f'[SISBAJUD]  Erro ao executar juntada da minuta: {e}')

        # 7. Fechar driver SISBAJUD (minuta salva e relatório gerado/parcial)
        if fechar_driver:
            try:
                driver.quit()
                if log:
                    logger.info('[SISBAJUD]  Driver SISBAJUD fechado')
            except Exception as e:
                if log:
                    logger.info(f'[SISBAJUD]  Erro ao fechar driver: {e}')
        else:
            if log:
                logger.info('[SISBAJUD] ℹ Driver SISBAJUD mantido aberto (modo lote)')

        resultado['status'] = 'concluido'
        if log:
            logger.info(f'[SISBAJUD]  Minuta de bloqueio concluída: {resultado["reus_processados"]} REUs processados')

        return resultado

    except Exception as e:
        erro = f"Erro geral na criação de minuta: {str(e)}"
        if log:
            logger.info(f'[SISBAJUD]  {erro}')
        resultado['status'] = 'erro'
        resultado['erros'].append(erro)

        if fechar_driver:
            try:
                driver.quit()
            except Exception as e:
                _ = e

        return resultado


def processar_ordem_sisbajud(driver, dados_processo, driver_pje=None, log=True, fechar_driver=True):
    """
    Processamento completo de ordens no SISBAJUD:
    1. Carregar dados do processo
    2. Filtrar séries válidas
    3. Processar séries e ordens
    4. Gerar relatório
    5. Executar juntada no PJE
    
    Args:
        fechar_driver: Se True, fecha o driver SISBAJUD ao final. Use False para processamento em lote.
    """
    resultado = {
        'status': 'pendente',
        'tipo_fluxo': None,
        'series_processadas': 0,
        'ordens_processadas': 0,
        'erros': [],
        'detalhes': {}
    }

    try:
        logger.info('\n[SISBAJUD] INICIANDO PROCESSAMENTO DE ORDENS')
        logger.info('=' * 60)

        # 1. Carregar dados do processo (usa parâmetro se passado, senão carrega do arquivo)
        if dados_processo:
            # Usar dados passados por parâmetro (processamento em lote)
            numero_processo = dados_processo.get('numero_processo') or dados_processo.get('numero')
            # Garantir que numero_processo seja string (pode vir como lista)
            if isinstance(numero_processo, list):
                numero_processo = numero_processo[0] if numero_processo else None
            if log:
                logger.info(f'[SISBAJUD] Usando dados do processo passados por parâmetro: {numero_processo}')
        else:
            # Fallback: carregar do arquivo (modo standalone)
            dados_processo, numero_processo = helpers._carregar_dados_ordem()
        
        if not dados_processo or not numero_processo:
            resultado['status'] = 'erro'
            resultado['erros'].append('Falha ao carregar dados do processo')
            return resultado

        # 1.5. Navegar para teimosinha e inserir número do processo
        if log:
            logger.info(f'[SISBAJUD] Navegando para teimosinha com processo: {numero_processo}')

        try:
            # Navegar para a URL da teimosinha
            driver.get("https://sisbajud.pdpj.jus.br/teimosinha")
            if log:
                logger.info('[SISBAJUD]  Navegação para teimosinha realizada')

            # Aguardar carregamento da página e campo de processo
            campo_processo = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Número do Processo"]'))
            )

            # Limpar, inserir o número do processo e pressionar ENTER
            campo_processo.clear()
            campo_processo.send_keys(numero_processo + Keys.RETURN)

            if log:
                logger.info('[SISBAJUD]  Processo inserido e ENTER pressionado')

            # Aguardar carregamento da série
            from Fix.utils_sleep import aguardar_pagina_carregar
            aguardar_pagina_carregar(driver, timeout=15)

            if log:
                logger.info('[SISBAJUD]  Processo inserido no SISBAJUD e série aberta')

        except Exception as e:
            erro = f'Erro ao navegar/inserir processo no SISBAJUD: {str(e)}'
            if log:
                logger.info(f'[SISBAJUD]  {erro}')
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado

        # 2. Calcular data limite para filtro (10/12/2025 devido a recesso)
        data_limite = datetime(2025, 12, 10)  # Aceitar desde 10/12/2025
        if log:
            logger.info(f'[SISBAJUD] Data limite para filtro: {data_limite.strftime("%d/%m/%Y")} (recesso)')

        # 3. Filtrar séries válidas
        series_validas = helpers._filtrar_series(driver, data_limite)
        if not series_validas:
            resultado['status'] = 'concluido'
            resultado['erros'].append('Não há séries válidas para processar')
            return resultado

        # 4. Determinar tipo de fluxo baseado nos valores das séries
        total_bloqueado = sum(float(s.get('valor_bloqueado', 0)) for s in series_validas)
        total_bloquear = sum(float(s.get('valor_bloquear', 0)) for s in series_validas)

        if total_bloqueado == 0.0:
            tipo_fluxo = 'NEGATIVO'
        elif total_bloqueado < 100.0 and total_bloquear >= 1000.0:
            tipo_fluxo = 'DESBLOQUEIO'
        else:
            tipo_fluxo = 'POSITIVO'

        resultado['tipo_fluxo'] = tipo_fluxo
        if log:
            logger.info(f'[SISBAJUD] Tipo de fluxo determinado: {tipo_fluxo}')

        # 4.5 Calcular estratégia de bloqueio (apenas para POSITIVO)
        estrategia = None
        if tipo_fluxo == 'POSITIVO':
            estrategia = helpers._calcular_estrategia_bloqueio(series_validas, dados_processo, log)
            resultado['estrategia'] = estrategia
            
            # Ordenar séries por valor de bloqueio (decrescente) para otimizar transferências
            if estrategia.get('tipo') == 'TRANSFERIR_PARCIAL':
                series_validas_ordenadas = sorted(series_validas, key=lambda s: float(s.get('valor_bloqueado', 0)), reverse=True)
                if log:
                    logger.info(f'[SISBAJUD]  Séries ordenadas por valor (maior primeiro) para otimizar transferências')
                series_validas = series_validas_ordenadas

        # 5. Processar séries e ordens (APENAS se houver algo para processar)
        if tipo_fluxo in ['POSITIVO', 'DESBLOQUEIO']:
            resultado_processamento = helpers._processar_series(driver, series_validas, tipo_fluxo, log, estrategia=estrategia)
            resultado.update(resultado_processamento)
        else:
            # NEGATIVO: sem bloqueios, pular processamento de séries
            if log:
                logger.info('[SISBAJUD] ⏭ Fluxo NEGATIVO: pulando processamento de séries')
            resultado['series_processadas'] = 0
            resultado['ordens_processadas'] = 0

        # 6. Gerar relatório (incluindo dados das séries e estratégia)
        # Para fluxo POSITIVO, passar o driver para extrair dados dos bloqueios da página
        relatorio_gerado = helpers._gerar_relatorio_ordem(
            tipo_fluxo,
            resultado['series_processadas'],
            resultado['ordens_processadas'],
            resultado['detalhes'],
            series_validas,  # Passar séries para o relatório
            driver if tipo_fluxo == 'POSITIVO' else None,  # Driver para extrair bloqueios
            log,
            numero_processo=numero_processo,  # Passar número do processo para o clipboard
            estrategia=estrategia  # Passar estratégia para o relatório
        )

        # 7. Executar juntada no PJE
        if relatorio_gerado and driver_pje:
            juntada_executada = helpers._executar_juntada_pje(driver_pje, tipo_fluxo, numero_processo, log)
            resultado['juntada_executada'] = juntada_executada
            
            # 7.1 Executar ato apropriado após juntada
            if juntada_executada:
                try:
                    from atos.wrappers_ato import ato_meios, ato_bloq
                    
                    if tipo_fluxo == 'POSITIVO':
                        # Fluxo POSITIVO: executar ato_bloq
                        if log:
                            logger.info('[SISBAJUD] Executando ato_bloq (fluxo POSITIVO)...')
                        ato_bloq(driver_pje)
                        if log:
                            logger.info('[SISBAJUD]  ato_bloq executado com sucesso')
                        
                        # Fechar aba da minuta após salvar e voltar para /detalhe
                        try:
                            # Fechar aba atual (minuta)
                            driver_pje.close()
                            if log:
                                logger.info('[SISBAJUD]  Aba da minuta fechada')
                            
                            # Procurar aba /detalhe e focar nela
                            abas_disponiveis = driver_pje.window_handles
                            aba_detalhe_encontrada = False
                            
                            for aba in abas_disponiveis:
                                try:
                                    driver_pje.switch_to.window(aba)
                                    url_atual = driver_pje.current_url
                                    if '/detalhe' in url_atual:
                                        aba_detalhe_encontrada = True
                                        if log:
                                            logger.info(f'[SISBAJUD]  Foco na aba /detalhe: {url_atual}')
                                        break
                                except Exception:
                                    continue
                            
                            if not aba_detalhe_encontrada:
                                if log:
                                    logger.info('[SISBAJUD]  Aba /detalhe não encontrada, usando primeira aba disponível')
                                # Fallback: usar primeira aba
                                driver_pje.switch_to.window(driver_pje.window_handles[0])
                                
                        except Exception as e_fechar:
                            if log:
                                logger.info(f'[SISBAJUD]  Erro ao fechar aba: {e_fechar}')
                        
                        # Criar GIGS após ato_bloq (voltando para aba detalhe)
                        try:
                            if log:
                                logger.info('[SISBAJUD] Criando GIGS "1/xs pec dec"...')
                            from Fix.extracao import criar_gigs
                            criar_gigs(driver_pje, "1/xs pec dec", log=log)
                            if log:
                                logger.info('[SISBAJUD]  GIGS criado com sucesso')
                        except Exception as e_gigs:
                            if log:
                                logger.info(f'[SISBAJUD]  Erro ao criar GIGS: {e_gigs}')
                    else:
                        # Fluxo NEGATIVO ou DESBLOQUEIO: executar ato_meios
                        if log:
                            logger.info(f'[SISBAJUD] Executando ato_meios (fluxo {tipo_fluxo})...')
                        ato_meios(driver_pje)
                        if log:
                            logger.info('[SISBAJUD]  ato_meios executado com sucesso')
                            
                    resultado['ato_executado'] = True
                except Exception as e_ato:
                    if log:
                        logger.info(f'[SISBAJUD]  Erro ao executar ato: {e_ato}')
                    resultado['ato_executado'] = False

        # 8. Fechar driver SISBAJUD
        if fechar_driver:
            try:
                driver.quit()
                if log:
                    logger.info('[SISBAJUD]  Driver SISBAJUD fechado')
            except Exception as e:
                if log:
                    logger.info(f'[SISBAJUD]  Erro ao fechar driver: {e}')
        else:
            if log:
                logger.info('[SISBAJUD] ℹ Driver SISBAJUD mantido aberto (modo lote)')

        resultado['status'] = 'concluido'
        if log:
            logger.info(f'[SISBAJUD]  Processamento concluído: {resultado["series_processadas"]} séries, {resultado["ordens_processadas"]} ordens')

        return resultado

    except Exception as e:
        erro = f"Erro geral no processamento: {str(e)}"
        if log:
            logger.info(f'[SISBAJUD]  {erro}')
        resultado['status'] = 'erro'
        resultado['erros'].append(erro)

        if fechar_driver:
            try:
                driver.quit()
            except Exception as e:
                _ = e

        return resultado


def processar_bloqueios(driver_pje=None):
    """
    Processa bloqueios no SISBAJUD usando a função processar_ordem_sisbajud
    SEMPRE carrega dados de dadosatuais.json - nenhum parâmetro necessário
    """
    try:
        logger.info('\n[SISBAJUD] INICIANDO PROCESSAMENTO DE BLOQUEIOS')
        logger.info('=' * 60)

        # 1. Inicializar SISBAJUD
        driver_sisbajud = iniciar_sisbajud(driver_pje=driver_pje)
        if not driver_sisbajud:
            logger.info('[SISBAJUD]  Falha ao inicializar SISBAJUD')
            return None

        # 2. Carregar dados do processo do arquivo (ÚNICA FONTE)
        dados_processo = utils.carregar_dados_processo()
        if not dados_processo:
            logger.info('[SISBAJUD]  Arquivo dadosatuais.json não encontrado. Execute extrair_dados_processo NO PJE antes!')
            return None

        # 3. Processar ordens SISBAJUD
        resultado = processar_ordem_sisbajud(driver_sisbajud, dados_processo, driver_pje=driver_pje)

        # 4. Retornar resultado para o PJe
        if resultado['status'] == 'concluido':
            logger.info('[SISBAJUD]  Processamento de bloqueios concluído com sucesso!')

            return {
                'status': 'sucesso',
                'dados_processamento': resultado,
                'acao_posterior': {
                    'tipo': 'atualizar_pje_bloqueios',
                    'parametros': {
                        'id_processo': dados_processo.get('id_processo'),
                        'tipo_fluxo': resultado.get('tipo_fluxo'),
                        'series_processadas': resultado.get('series_processadas', 0),
                        'ordens_processadas': resultado.get('ordens_processadas', 0)
                    }
                }
            }
        else:
            logger.info('[SISBAJUD]  Falha no processamento de bloqueios')
            return {
                'status': 'erro',
                'erros': resultado.get('erros', []),
                'acao_posterior': None
            }

    except Exception as e:
        logger.info(f'[SISBAJUD][ERRO] Falha no processamento de bloqueios: {e}')
        logger.exception("Erro detectado")
        return None


def processar_endereco(driver_pje=None):
    """
    Processa endereços no SISBAJUD (placeholder)
    SEMPRE carrega dados de dadosatuais.json - nenhum parâmetro necessário
    """
    try:
        logger.info('\n[SISBAJUD] INICIANDO PROCESSAMENTO DE ENDEREÇO')
        logger.info('=' * 60)

        # 1. Inicializar SISBAJUD
        driver_sisbajud = iniciar_sisbajud(driver_pje=driver_pje)
        if not driver_sisbajud:
            logger.info('[SISBAJUD]  Falha ao inicializar SISBAJUD')
            return None

        # 2. Carregar dados do processo do arquivo (ÚNICA FONTE)
        dados_processo = utils.carregar_dados_processo()
        if not dados_processo:
            logger.info('[SISBAJUD]  Arquivo dadosatuais.json não encontrado. Execute extrair_dados_processo NO PJE antes!')
            driver_sisbajud.quit()
            return None

        # Placeholder para implementação futura
        logger.info('[SISBAJUD]  Função processar_endereco ainda não implementada')

        # Fechar driver
        driver_sisbajud.quit()

        return {
            'status': 'pendente',
            'mensagem': 'Função processar_endereco ainda não implementada',
            'acao_posterior': None
        }

    except Exception as e:
        logger.info(f'[SISBAJUD][ERRO] Falha no processamento de endereço: {e}')
        logger.exception("Erro detectado")
        return None


def coletar_dados_minuta_sisbajud(driver):
    """
    Executa JavaScript para coletar dados da minuta SISBAJUD e retorna o texto formatado
    Baseado na implementação do 123.py, adaptado para o módulo SISB
    """
    try:
        logger.info('[SISBAJUD] Executando script de coleta de dados da minuta...')

        # JavaScript fornecido pelo usuário (decodificado) - versão adaptada para SISB
        script_coleta = """
        function getCleanText(selector) {
            const element = document.querySelector(selector);
            if (element) {
                return element.textContent.trim();
            }
            return null;
        }

        function getValueByLabel(labelText) {
            // Buscar no novo formato HTML do SISBAJUD
            const labels = Array.from(document.querySelectorAll('.sisbajud-label'));
            const targetLabel = labels.find(label => label.textContent.trim().includes(labelText));
            if (targetLabel) {
                // Buscar o valor na mesma div pai usando o novo formato
                const parentDiv = targetLabel.closest('.col-md-3') || targetLabel.parentElement;
                if (parentDiv) {
                    const valueElement = parentDiv.querySelector('.sisbajud-label-valor');
                    if (valueElement) {
                        return valueElement.textContent.trim();
                    }
                }
            }
            return null;
        }

        try {
            // Extrair dados usando o novo formato HTML
            const numeroProcesso = getValueByLabel('Número do processo:');
            const numeroProtocolo = getValueByLabel('Número do protocolo:');
            const repeticaoProgramada = getValueByLabel('Repetição programada?');
            const limiteRepeticao = getValueByLabel('Data limite da repetição:');
            const valorBloqueio = getCleanText('td[data-label="valorBloquear:"]');

            const executados = [];
            const rowsExecutados = document.querySelectorAll('tr.element-row');
            rowsExecutados.forEach(row => {
                const nomeElement = row.querySelector('.col-reu-dados-nome-pessoa');
                const documentoElement = row.querySelector('.col-reu-dados a');
                if (nomeElement && documentoElement) {
                    const nome = nomeElement.textContent.trim();
                    const documento = documentoElement.textContent.trim();
                    executados.push(`${nome} - [${documento}]`);
                }
            });

            const pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"';

            let resultado = `<p ${pStyle}><strong>Dados da Teimosinha protocolada:</strong></p>`;
            resultado += `<p ${pStyle}>Número do processo: <strong>${numeroProcesso || 'Não encontrado'}</strong></p>`;
            resultado += `<p ${pStyle}>Número do protocolo: <strong>${numeroProtocolo || 'Não encontrado'}</strong></p>`;
            resultado += `<p ${pStyle}>Repetição programada? <strong>${repeticaoProgramada || 'Não encontrado'}</strong></p>`;
            resultado += `<p ${pStyle}>Limite da repetição: <strong>${limiteRepeticao || 'Não encontrado'}</strong></p>`;
            resultado += `<p ${pStyle}>Valor do bloqueio: <strong>${valorBloqueio ? valorBloqueio.split('\\n')[0] : 'Não encontrado'}</strong></p>`;
            resultado += `<p ${pStyle}><strong>Partes alvo do bloqueio:</strong></p>`;

            if (executados.length > 0) {
                executados.forEach(executado => {
                    resultado += `<p ${pStyle}><strong>${executado}</strong></p>`;
                });
            } else {
                resultado += `<p ${pStyle}><strong>Nenhum executado encontrado</strong></p>`;
            }

            resultado += `<p ${pStyle}>Notas:</p>`;
            resultado += `<p ${pStyle}>-Por padrão é consultado CNPJ raiz.</p>`;
            resultado += `<p ${pStyle}>-Eventuais partes faltantes se referem a CPF ou CNPJ sem relacionamento bancário.</p>`;

            return resultado;

        } catch (error) {
            return 'ERRO: ' + error.message;
        }
        """

        # Executar o script e obter o resultado
        resultado = driver.execute_script(script_coleta)

        if resultado and not resultado.startswith('ERRO:'):
            logger.info('[SISBAJUD]  Dados da minuta coletados com sucesso')
            return resultado
        else:
            logger.info(f'[SISBAJUD]  Erro na coleta de dados: {resultado}')
            return None

    except Exception as e:
        logger.info(f'[SISBAJUD]  Falha ao executar script de coleta: {e}')
        return None


def minuta_bloqueio_60(driver, dados_processo=None, driver_pje=None, log=True, fechar_driver=True):
    """
    Wrapper para minuta_bloqueio com prazo de 60 dias.
    Chama minuta_bloqueio com prazo_dias=60.

    Args:
        Mesmos argumentos de minuta_bloqueio

    Returns:
        Mesmo retorno de minuta_bloqueio
    """
    return minuta_bloqueio(
        driver=driver,
        dados_processo=dados_processo,
        driver_pje=driver_pje,
        log=log,
        fechar_driver=fechar_driver,
        prazo_dias=60,
        protocolar=False
    )