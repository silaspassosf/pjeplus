import logging
logger = logging.getLogger(__name__)

# m1.py
# Fluxo automatizado de mandados PJe TRT2
###DIRETRIZES MÁXIMAS INEGOCIÁVEIS
# Priorizar edições apenas no código selecionado ou referenciado  
# Sempre validar se as alterações propostas estão estritamente alinhadas com o prompt do usuário.  
# Evitar modificações em arquivos não explicitamente mencionados.  
# Respeitar convenções de estilo definidas no projeto (ex: indentação com tabs, aspas duplas).  
# Workspace preference: NÃO altere, traduza ou reescreva NENHUMA linha do código, exceto exatamente o trecho solicitado.
# NÃO traduza palavras-chave, nomes de variáveis, comentários, strings, nem nada do código.
# NÃO faça ajustes automáticos, refatorações, nem ‘melhorias’ não solicitadas.
# Se precisar editar, use sempre o padrão # ...existing code... para indicar partes não alteradas. 
# As edições devem ser ESPECIFICAMENTE sobre erros de log ou pedidos EXPLICITOS do usuario, nada alem disso.
# tenha em mente que descumprir essas diretizes estraga o codigo e causa perda de tempo
# nao é neceasário varrer o codigo todo para cada edição pedida 
# use a busca de termos para ir diretamente à região correta e edirtar apenas o necessário, para ser mais eficiente
# ====================================================
# BLOCO 0 - GERAL
# ====================================================

# 0. Importações Padrão
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from typing import Optional, Dict, List, Union, Tuple, Callable, Any

# Selenium
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchWindowException,
    StaleElementReferenceException,
)

# Módulos Locais Fix
from Fix.core import (
    aguardar_e_clicar,
)
from Fix.drivers import criar_driver_PC
from Fix.extracao import (
    indexar_e_processar_lista,
    criar_lembrete_posit,
)
from Fix.utils import (
    navegar_para_tela,
    configurar_recovery_driver,
    handle_exception_with_recovery,
    login_pc,
)
from Fix.abas import validar_conexao_driver

# Atos Wrapper
from atos import (
    ato_judicial,
    ato_meios,
    ato_pesquisas,
    ato_crda,
    ato_crte,
    ato_bloq,
    ato_idpj,
    ato_termoE,
    ato_termoS,
    ato_edital,
    ato_idpj,
    mov_arquivar,
    ato_meiosub
)

# Módulo Mandado local
from .processamento import processar_argos, fluxo_mandados_outros

with open("log.py", "w", encoding="utf-8") as f:
    f.write(f"# Última execução: {datetime.now()}\n")
    f.write(f"# Script: {os.path.abspath(sys.argv[0])}\n")
    f.write(f"# Argumentos: {' '.join(sys.argv[1:])}\n")

# ====================================================
# CONTROLE DE SESSÃO E PROGRESSO UNIFICADO
# ====================================================

# Sistema de progresso próprio para Mandado usando o sistema unificado
from Fix.monitoramento_progresso_unificado import (
    carregar_progresso_mandado,
    salvar_progresso_mandado,
    extrair_numero_processo_mandado,
    verificar_acesso_negado_mandado,
    processo_ja_executado_mandado,
    marcar_processo_executado_mandado,
)

# Funções de compatibilidade (aliases para manter compatibilidade com código existente)
carregar_progresso = carregar_progresso_mandado
salvar_progresso = salvar_progresso_mandado
extrair_numero_processo = extrair_numero_processo_mandado
verificar_acesso_negado = verificar_acesso_negado_mandado
processo_ja_executado = processo_ja_executado_mandado
marcar_processo_executado = marcar_processo_executado_mandado


def setup_driver():
    """Setup inicial do driver"""
    driver = criar_driver_PC(headless=False)
    if not driver:
        print('[ERRO] Falha ao iniciar o driver.')
        return None
    return driver

# 2. Funções de Navegação

def navegacao(driver):
    """Navegação para a lista de documentos internos do PJe TRT2"""
    try:
        url_lista = os.getenv('URL_PJE_ESCANINHO', 'https://pje.trt2.jus.br/pjekz/escaninho/documentos-internos')
        print(f'[NAV] Iniciando navegação para: {url_lista}')

        if not navegar_para_tela(driver, url=url_lista, delay=2):
            raise Exception('Falha na navegação para a tela de documentos internos')

        # Maximizar janela e aplicar zoom reduzido para melhorar visibilidade
        try:
            try:
                driver.maximize_window()
            except Exception:
                # Alguns perfis/headless podem não suportar maximize
                pass
            try:
                driver.execute_script("document.body.style.zoom='70%';")
            except Exception:
                # Falha ao aplicar zoom via JS não é crítico
                pass
            print('[NAV] Janela maximizada e zoom aplicado (70%)')
        except Exception:
            pass

        # CONTAR PROCESSOS ANTES DO CLIQUE NO FILTRO
        try:
            processos_antes_selector = 'tr.cdk-drag'
            processos_antes = driver.find_elements(By.CSS_SELECTOR, processos_antes_selector)
            quantidade_antes = len(processos_antes)
        except Exception as count_error:
            print(f'[NAV][CONTAGEM][ERRO] Erro ao contar processos antes: {count_error}')
            quantidade_antes = 0

        print('[NAV] Verificando/ativando filtro de mandados devolvidos...')


        # IDENTIFICAR O ÍCONE ESPECÍFICO DE MANDADOS DEVOLVIDOS
        try:
            # Procurar pelo ícone com aria-label contendo "Mandados devolvidos"
            icones_mandados = driver.find_elements(By.CSS_SELECTOR, 'i[aria-label*="Mandados devolvidos"]')

            if not icones_mandados:
                print('[NAV][ERRO] Ícone de mandados devolvidos não encontrado')
                return False

            icone_mandados = icones_mandados[0]  # Deve haver apenas um

            aria_label = icone_mandados.get_attribute('aria-label')
            aria_pressed = icone_mandados.get_attribute('aria-pressed')
            print(f'[NAV][FILTRO] Ícone encontrado: aria-label="{aria_label}", aria-pressed="{aria_pressed}"')


            # VERIFICAR SE O FILTRO JÁ ESTÁ ATIVO
            if aria_pressed == 'true':
                print('[NAV][FILTRO] ✅ Filtro de mandados devolvidos já está ativo')
                # Mesmo que já esteja ativo, vamos verificar se a lista está correta
            else:
                print('[NAV][FILTRO] 🔄 Filtro não está ativo, clicando para ativar...')
                # Usar o seletor específico baseado no aria-label
                icone_selector = f'i[aria-label="{aria_label}"]'
                resultado = aguardar_e_clicar(driver, icone_selector, timeout=10, log=True)

                if not resultado:
                    print('[NAV][FILTRO] ❌ Falha ao clicar no ícone de mandados devolvidos')
                    return False

                print('[NAV][FILTRO] ✅ Ícone de mandados devolvidos clicado com sucesso')


        except Exception as icone_error:
            print(f'[NAV][FILTRO][ERRO] Erro ao identificar ícone: {icone_error}')
            return False

        # VERIFICAR PRESENÇA DO CHIP DE FILTRO "MANDADOS DEVOLVIDOS"
        try:
            print('[NAV][FILTRO] Verificando presença do filtro "Mandados devolvidos"...')
            # Seletor mais simples e confiável para o chip de filtro
            filtro_selector = 'mat-chip'

            # Aguardar até 10 segundos pela presença de QUALQUER chip de filtro
            filtro_chips = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, filtro_selector))
            )

            # Verificar se algum chip contém "Mandados devolvidos"
            filtro_encontrado = False
            for chip in filtro_chips:
                try:
                    chip_text = chip.text.strip()
                    if "mandados devolvidos" in chip_text.lower():
                        filtro_encontrado = True
                        print(f'[NAV][FILTRO] ✅ Filtro encontrado: "{chip_text}"')
                        break
                except:
                    continue

            if filtro_encontrado:
                print('[NAV][FILTRO] ✅ Filtro "Mandados devolvidos" confirmado com chip presente')
                return True
            else:
                print('[NAV][FILTRO] ❌ Chip "Mandados devolvidos" não encontrado - tentando clicar novamente...')
                # Tentar clicar novamente no ícone
                resultado_retry = aguardar_e_clicar(driver, icone_selector, timeout=10, log=True)
                if resultado_retry:
                    print('[NAV][FILTRO] ✅ Retry do clique realizado')
                    time.sleep(0.002)  # Aguardar carregamento após retry
                    return True
                else:
                    print('[NAV][FILTRO] ❌ Falha no retry do clique')
                    return False

        except TimeoutException:
            print('[NAV][FILTRO] ❌ Timeout aguardando filtro - tentando clicar novamente...')
            # Tentar clicar novamente no ícone
            resultado_retry = aguardar_e_clicar(driver, icone_selector, timeout=10, log=True)
            if resultado_retry:
                print('[NAV][FILTRO] ✅ Retry do clique realizado após timeout')
                time.sleep(0.002)
                return True
            else:
                print('[NAV][FILTRO] ❌ Falha no retry após timeout')
                return False
        except Exception as filtro_error:
            print(f'[NAV][FILTRO][ERRO] Erro na verificação: {filtro_error}')
            return False
        else:
            print('[NAV] Falha ao clicar no ícone de mandados devolvidos')
            return False

    except Exception as e:
        print(f'[NAV][ERRO] Falha na navegação: {e}')
        return False



def iniciar_fluxo_robusto(driver):
    """Função que decide qual fluxo será aplicado com controle de sessão"""
    # Carrega progresso
    progresso = carregar_progresso()
    print(f"[PROGRESSO][SESSÃO] Carregado progresso com {len(progresso['processos_executados'])} processos já executados")
    
    def fluxo_callback(driver):
        try:
            # VERIFICAÇÃO DE SESSÃO: Antes de qualquer processamento
            if verificar_acesso_negado(driver):
                print("[PROCESSAR][ALERTA] Não estamos na página da lista! URL:", driver.current_url)
                print("[RECOVERY][SESSÃO] ❌ Sessão perdida, abortando processo atual")
                return
            
            # USAR NÚMERO DA LISTA SE DISPONÍVEL (MAIS CONFIÁVEL)
            numero_processo = getattr(driver, '_numero_processo_lista', None)
            if not numero_processo:
                # Fallback: extrair da URL/página
                numero_processo = extrair_numero_processo(driver)
            
            print(f'[MANDADO] Processando: {numero_processo}')
            
            # Busca o cabeçalho do documento ativo
            try:
                # Usando aguardar_e_clicar com retornar_elemento=True
                cabecalho_selector = '.cabecalho-conteudo .mat-card-title, mat-card-title.mat-card-title'
                cabecalho = aguardar_e_clicar(driver, cabecalho_selector, timeout=10, retornar_elemento=True)
                
                if not cabecalho:
                    print('[ERRO] Cabeçalho do documento não encontrado após espera')
                    return
                    
                texto_doc = cabecalho.text
                if not texto_doc:
                    print('[ERRO] Cabeçalho do documento vazio')
                    return
            except Exception as e:
                print(f'[ERRO] Cabeçalho do documento não encontrado: {e}')
                return
                
            texto_lower = texto_doc.lower()
            # Identificação dos fluxos
            if any(termo in texto_lower for termo in ['pesquisa patrimonial', 'argos', 'devolução de ordem de pesquisa', 'certidão de devolução']):
                print(f'[ARGOS] {numero_processo}')
                processar_argos(driver, log=False)
                # VALIDAÇÃO PÓS ARGOS: Verifica se o contexto do driver ainda é válido
                try:
                    _ = driver.window_handles
                except Exception as e:
                    print(f'[ERRO] Contexto do driver perdido após processar_argos: {e}')
                    # Força exceção para interromper o fluxo normal e evitar erro na limpeza de abas
                    raise Exception(f"Driver context lost after processar_argos: {e}")
            elif any(termo in texto_lower for termo in ['oficial de justiça', 'certidão de oficial']):
                print(f'[OUTROS] {numero_processo}')
                fluxo_mandados_outros(driver, log=False)
            else:
                print(f'[AVISO] Documento não identificado: {texto_doc}')
                
        except Exception as e:
            print(f'[ERRO] Falha ao processar mandado: {str(e)}')
        finally:
            # Limpeza de abas com validação robusta de contexto
            # ATENÇÃO: Se ato_judicial criou GIGS, ele já fechou abas e voltou para /detalhe
            try:
                # Primeira validação: verifica se o contexto ainda existe
                try:
                    current_handles = driver.window_handles
                    current_handle = driver.current_window_handle
                    current_url = driver.current_url
                except Exception as context_error:
                    print(f"[LIMPEZA][ERRO] Contexto do browser perdido - abortando limpeza: {context_error}")
                    return
                
                # VERIFICAÇÃO ESPECIAL: Se já estamos na aba principal E na URL /detalhe,
                # significa que ato_judicial já fez limpeza para GIGS - não fechar novamente
                main_window = current_handles[0] if current_handles else None
                ja_na_aba_principal_com_detalhe = (
                    len(current_handles) >= 1 and 
                    current_handle == main_window and 
                    '/detalhe' in current_url
                )
                
                if ja_na_aba_principal_com_detalhe:
                    print("[LIMPEZA] Já na aba principal /detalhe - ato_judicial fez limpeza para GIGS, pulando fechamento.")
                elif len(current_handles) > 1:
                    # Se há múltiplas abas e não estamos na principal, fecha a atual
                    if main_window and current_handle != main_window:
                        try:
                            driver.close()
                            print(f"[LIMPEZA] Aba secundária fechada: {current_handle[:8]}...")
                            
                            # Troca para aba principal com validação
                            remaining_handles = driver.window_handles
                            if main_window in remaining_handles:
                                driver.switch_to.window(main_window)
                                print(f"[LIMPEZA] Retornado para aba principal: {main_window[:8]}...")
                            elif remaining_handles:
                                driver.switch_to.window(remaining_handles[0])
                                print(f"[LIMPEZA] Usando primeira aba disponível: {remaining_handles[0][:8]}...")
                            else:
                                print("[LIMPEZA][ERRO] Nenhuma aba restante após fechamento.")
                                return
                            
                            # Validação final
                            try:
                                test_url = driver.current_url
                                print(f"[LIMPEZA] Contexto validado: {test_url[:50]}...")
                            except Exception as validation_error:
                                print(f"[LIMPEZA][ERRO] Falha na validação final: {validation_error}")
                                
                        except Exception as close_error:
                            print(f"[LIMPEZA][ERRO] Falha ao fechar/trocar aba: {close_error}")
                    else:
                        print("[LIMPEZA] Já na aba principal ou aba única - nenhuma ação necessária.")
                else:
                    print("[LIMPEZA] Aba única detectada - preservando contexto.")
                    
            except Exception as cleanup_error:
                print(f"[LIMPEZA][ERRO CRÍTICO] Falha geral na limpeza: {cleanup_error}")
                print("[LIMPEZA][AVISO] Contexto do browser pode estar comprometido.")
            
            # MARCAÇÃO DE PROGRESSO: Marca processo como executado se chegou até aqui
            # USAR O NÚMERO DA LISTA (CORRETO) PARA O PROGRESSO
            if numero_processo:
                # Usar função de progresso com o número correto (da lista)
                progresso_atual = carregar_progresso()
                marcar_processo_executado(numero_processo, progresso_atual)
                print(f'[PROGRESSO] Processo {numero_processo} marcado como executado')
            
            print('[FLUXO] Processo concluído, retornando à lista')
    print('[FLUXO] Filtro de mandados devolvidos já garantido na navegação. Iniciando processamento...')
    indexar_e_processar_lista(driver, fluxo_callback)
    return True

# 3. Funções de Processamento

def main(tipo_driver='PC', tipo_login='CPF', headless=False) -> None:
    """Função principal que coordena todo o fluxo do programa com controle de sessão.
    
    Args:
        tipo_driver: Tipo de driver ('PC', 'VT', etc.)
        tipo_login: Tipo de login ('CPF', 'PC')
        headless: Executar em modo headless
    
    1. Setup inicial usando credencial() unificada
    2. Navegação para a lista de documentos internos
    3. Execução do fluxo automatizado sobre a lista com recuperação de sessão
    """
    # Verifica argumentos da linha de comando para funções utilitárias
    if len(sys.argv) > 1:
        if sys.argv[1] == "--status":
            progresso = carregar_progresso()
            print(f"[PROGRESSO][STATUS] {len(progresso)} processos executados")
            print(f"[PROGRESSO][STATUS] Sistema de progresso unificado ativo")
            return
    
    # ===== SETUP UNIFICADO COM CREDENCIAL =====
    print(f"[M1] Iniciando com driver={tipo_driver}, login={tipo_login}, headless={headless}")
    
    from Fix.core import credencial
    driver = credencial(
        tipo_driver=tipo_driver,
        tipo_login=tipo_login, 
        headless=headless
    )
    
    if not driver:
        print('[M1][ERRO] Falha ao criar driver com credencial()')
        return
        
    print('[M1] ✅ Driver criado e login realizado via credencial()')
    
    # ===== CONFIGURAR RECOVERY GLOBAL =====
    # Usar credencial() também no recovery
    def recovery_credencial():
        return credencial(tipo_driver=tipo_driver, tipo_login=tipo_login, headless=headless)
    
    configurar_recovery_driver(recovery_credencial, lambda d: True)  # Login já feito
    print("[M1] ✅ Sistema de recuperação automática configurado")

    # Navegação para a lista de documentos internos
    if not navegacao(driver):
        driver.quit()
        return

    # Processa a lista de documentos internos com controle de sessão
    iniciar_fluxo_robusto(driver)

    print("[INFO] Processamento concluído. Pressione ENTER para encerrar...")
    input()
    driver.quit()

if __name__ == "__main__":
    main()

