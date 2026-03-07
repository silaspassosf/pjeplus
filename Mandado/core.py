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
    indexar_processos,
    criar_lembrete_posit,
)
from Fix.utils import (
    navegar_para_tela,
    configurar_recovery_driver,
    handle_exception_with_recovery,
    login_pc,
)
from Fix.abas import validar_conexao_driver
from Fix.abas import forcar_fechamento_abas_extras

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


def _aguardar_estabilizacao_pos_processo(driver: WebDriver, timeout: float = 6.0) -> bool:
    """Aguarda estado estável após fechar abas antes de abrir próximo processo."""
    inicio = time.time()

    while (time.time() - inicio) < timeout:
        try:
            status = validar_conexao_driver(driver, "MANDADO_POS_PROCESSO")
            if status == "FATAL":
                logger.error('[FLUXO][POS] Contexto fatal detectado durante estabilização')
                return False

            abas = driver.window_handles
            url_atual = (driver.current_url or '').lower()

            # Estado esperado: uma aba na lista/painel global
            if len(abas) == 1 and ('/lista-processos' in url_atual or '/painel/global/' in url_atual):
                # Pequeno buffer para render da lista/chips antes do próximo clique
                try:
                    _ = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class, tr.cdk-drag')
                except Exception:
                    pass
                time.sleep(0.35)
                return True
        except Exception:
            pass

        time.sleep(0.25)

    # fallback não-bloqueante: pequena pausa extra para reduzir corrida
    time.sleep(0.5)
    logger.warning('[FLUXO][POS] Timeout de estabilização pós-processo; seguindo com buffer de segurança')
    return True


def setup_driver() -> Optional[WebDriver]:
    """Setup inicial do driver"""
    driver = criar_driver_PC(headless=False)
    if not driver:
        logger.info('[ERRO] Falha ao iniciar o driver.')
        return None
    return driver

# 2. Funções de Navegação

def navegacao(driver: WebDriver) -> bool:
    """Navegação para a lista de documentos internos do PJe TRT2"""
    try:
        url_lista = os.getenv('URL_PJE_ESCANINHO', 'https://pje.trt2.jus.br/pjekz/escaninho/documentos-internos')
        logger.info(f'[NAV] Iniciando navegação para: {url_lista}')

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
            logger.info('[NAV] Janela maximizada e zoom aplicado (70%)')
        except Exception:
            pass

        # CONTAR PROCESSOS ANTES DO CLIQUE NO FILTRO
        try:
            processos_antes_selector = 'tr.cdk-drag'
            processos_antes = driver.find_elements(By.CSS_SELECTOR, processos_antes_selector)
            quantidade_antes = len(processos_antes)
        except Exception as count_error:
            logger.info(f'[NAV][CONTAGEM][ERRO] Erro ao contar processos antes: {count_error}')
            quantidade_antes = 0

        logger.info('[NAV] Verificando/ativando filtro de mandados devolvidos...')


        # IDENTIFICAR O ÍCONE ESPECÍFICO DE MANDADOS DEVOLVIDOS
        try:
            # Procurar pelo ícone com aria-label contendo "Mandados devolvidos"
            icones_mandados = driver.find_elements(By.CSS_SELECTOR, 'i[aria-label*="Mandados devolvidos"]')

            if not icones_mandados:
                logger.info('[NAV][ERRO] Ícone de mandados devolvidos não encontrado')
                return False

            icone_mandados = icones_mandados[0]  # Deve haver apenas um

            aria_label = icone_mandados.get_attribute('aria-label')
            aria_pressed = icone_mandados.get_attribute('aria-pressed')
            logger.info(f'[NAV][FILTRO] Ícone encontrado: aria-label="{aria_label}", aria-pressed="{aria_pressed}"')


            # VERIFICAR SE O FILTRO JÁ ESTÁ ATIVO
            if aria_pressed == 'true':
                logger.info('[NAV][FILTRO]  Filtro de mandados devolvidos já está ativo')
                # Mesmo que já esteja ativo, vamos verificar se a lista está correta
            else:
                logger.info('[NAV][FILTRO]  Filtro não está ativo, clicando para ativar...')
                # Usar o seletor específico baseado no aria-label
                icone_selector = f'i[aria-label="{aria_label}"]'
                resultado = aguardar_e_clicar(driver, icone_selector, timeout=10, log=True)

                if not resultado:
                    logger.info('[NAV][FILTRO]  Falha ao clicar no ícone de mandados devolvidos')
                    return False

                logger.info('[NAV][FILTRO]  Ícone de mandados devolvidos clicado com sucesso')


        except Exception as icone_error:
            logger.info(f'[NAV][FILTRO][ERRO] Erro ao identificar ícone: {icone_error}')
            return False

        # VERIFICAR PRESENÇA DO CHIP DE FILTRO "MANDADOS DEVOLVIDOS"
        try:
            logger.info('[NAV][FILTRO] Verificando presença do filtro "Mandados devolvidos"...')
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
                        logger.info(f'[NAV][FILTRO]  Filtro encontrado: "{chip_text}"')
                        break
                except:
                    continue

            if filtro_encontrado:
                logger.info('[NAV][FILTRO]  Filtro "Mandados devolvidos" confirmado com chip presente')
                return True
            else:
                logger.info('[NAV][FILTRO]  Chip "Mandados devolvidos" não encontrado - tentando clicar novamente...')
                # Tentar clicar novamente no ícone
                resultado_retry = aguardar_e_clicar(driver, icone_selector, timeout=10, log=True)
                if resultado_retry:
                    logger.info('[NAV][FILTRO]  Retry do clique realizado')
                    time.sleep(0.002)  # Aguardar carregamento após retry
                    return True
                else:
                    logger.info('[NAV][FILTRO]  Falha no retry do clique')
                    return False

        except TimeoutException:
            logger.info('[NAV][FILTRO]  Timeout aguardando filtro - tentando clicar novamente...')
            # Tentar clicar novamente no ícone
            resultado_retry = aguardar_e_clicar(driver, icone_selector, timeout=10, log=True)
            if resultado_retry:
                logger.info('[NAV][FILTRO]  Retry do clique realizado após timeout')
                time.sleep(0.002)
                return True
            else:
                logger.info('[NAV][FILTRO]  Falha no retry após timeout')
                return False
        except Exception as filtro_error:
            logger.info(f'[NAV][FILTRO][ERRO] Erro na verificação: {filtro_error}')
            return False
        else:
            logger.info('[NAV] Falha ao clicar no ícone de mandados devolvidos')
            return False

    except Exception as e:
        logger.info(f'[NAV][ERRO] Falha na navegação: {e}')
        return False



def iniciar_fluxo_robusto(driver: WebDriver) -> Dict[str, Any]:
    """Função que decide qual fluxo será aplicado com controle de sessão"""
    # Carrega progresso
    progresso = carregar_progresso()
    logger.info(f"[PROGRESSO][SESSÃO] Carregado progresso com {len(progresso['processos_executados'])} processos já executados")
    
    def fluxo_callback(driver):
        numero_processo = None
        processado_com_sucesso = False
        try:
            # VERIFICAÇÃO DE SESSÃO: Antes de qualquer processamento
            if verificar_acesso_negado(driver):
                logger.info(f"[PROCESSAR][ALERTA] Não estamos na página da lista! URL: {driver.current_url}")
                logger.info("[RECOVERY][SESSÃO]  Sessão perdida, abortando processo atual")
                return False
            
            # USAR NÚMERO DA LISTA SE DISPONÍVEL (MAIS CONFIÁVEL)
            numero_processo = getattr(driver, '_numero_processo_lista', None)
            if not numero_processo:
                # Fallback: extrair da URL/página
                numero_processo = extrair_numero_processo(driver)
            
            logger.info(f'[MANDADO][CALLBACK] invoked for {numero_processo}')
            logger.info(f'[MANDADO] Processando: {numero_processo}')

            # Busca o cabeçalho do documento ativo sem clicar (detalhes já abertos pelo indexador)
            try:
                cabecalho_selector = '.cabecalho-conteudo .mat-card-title, mat-card-title.mat-card-title'
                cabecalhos = driver.find_elements(By.CSS_SELECTOR, cabecalho_selector)
                cabecalho = cabecalhos[0] if cabecalhos else None

                if not cabecalho:
                    logger.info('[ERRO] Cabeçalho do documento não encontrado na aba de detalhes')
                    return False

                texto_doc = cabecalho.text if cabecalho else ''
                if not texto_doc:
                    logger.info('[ERRO] Cabeçalho do documento vazio')
                    return False
            except Exception as e:
                logger.info(f'[ERRO] Exceção ao localizar cabeçalho: {e}')
                return False
                
            texto_lower = texto_doc.lower()
            # Identificação dos fluxos
            if any(termo in texto_lower for termo in ['pesquisa patrimonial', 'argos', 'devolução de ordem de pesquisa', 'certidão de devolução']):
                logger.info(f'[ARGOS] {numero_processo}')
                # processar_argos retorna status; propagar falha para o indexador
                if not processar_argos(driver, log=False):
                    logger.info(f'[ERRO] processar_argos retornou falsy para {numero_processo}')
                    return False
                # VALIDAÇÃO PÓS ARGOS: Verifica se o contexto do driver ainda é válido
                try:
                    _ = driver.window_handles
                except Exception as e:
                    logger.info(f'[ERRO] Contexto do driver perdido após processar_argos: {e}')
                    # Força exceção para interromper o fluxo normal e evitar erro na limpeza de abas
                    raise Exception(f"Driver context lost after processar_argos: {e}")
            elif any(termo in texto_lower for termo in ['oficial de justiça', 'certidão de oficial']):
                logger.info(f'[OUTROS] {numero_processo}')
                fluxo_mandados_outros(driver, log=False)
            else:
                logger.info(f'[AVISO] Documento não identificado: {texto_doc}')
                return False

            processado_com_sucesso = True
            # Sucesso explícito do callback
            return True
        except Exception as e:
            logger.info(f'[ERRO] Falha ao processar mandado: {str(e)}')
            return False
        finally:
            # Limpeza padronizada via Fix (alinhada ao fluxo de indexação)
            try:
                aba_lista_original = None
                try:
                    handles = driver.window_handles
                    aba_lista_original = handles[0] if handles else None
                except Exception:
                    aba_lista_original = None

                if aba_lista_original:
                    forcar_fechamento_abas_extras(driver, aba_lista_original)
                    _aguardar_estabilizacao_pos_processo(driver)
            except Exception as cleanup_error:
                logger.info(f"[LIMPEZA][ERRO] Falha na limpeza padronizada de abas: {cleanup_error}")
            
            # Marcar progresso APENAS quando o callback concluir com sucesso
            if processado_com_sucesso and numero_processo:
                # Usar função de progresso com o número correto (da lista)
                progresso_atual = carregar_progresso()
                marcar_processo_executado(numero_processo, progresso_atual)
                logger.info(f'[PROGRESSO] Processo {numero_processo} marcado como executado')
            
            logger.info('[FLUXO] Processo concluído, retornando à lista')
    logger.info('[FLUXO] Filtro de mandados devolvidos já garantido na navegação. Iniciando processamento...')

    # Capturar progresso antes/depois para computar quantos processos foram executados
    progresso_before = carregar_progresso()
    count_before = len(progresso_before.get('processos_executados', []))

    # 1) Checar se há processos na lista antes de iniciar o indexador
    try:
        processos_indexados = indexar_processos(driver)
        logger.info(f'[FLUXO] Lista inicial contém {len(processos_indexados)} linhas (indexar_processos)')
    except Exception as e:
        logger.warning(f'[FLUXO][ALERTA] Falha ao indexar lista inicialmente: {e}')
        processos_indexados = []

    # 2) Se lista vazia, tentar recarregar e reindexar (2 tentativas) — evita concluir silenciosamente
    if not processos_indexados:
        logger.warning('[FLUXO][ALERTA] Nenhum processo encontrado após aplicar filtro; tentando reindexar/recarregar (2 tentativas)')
        for attempt in range(2):
            try:
                time.sleep(1 + attempt)  # backoff leve
                try:
                    driver.refresh()
                except Exception:
                    pass
                processos_indexados = indexar_processos(driver)
                logger.info(f'[FLUXO] Tentativa {attempt+1}: encontrou {len(processos_indexados)} linhas')
                if processos_indexados:
                    break
            except Exception as e:
                logger.warning(f'[FLUXO][ALERTA] Reindex tentativa {attempt+1} falhou: {e}')

    if not processos_indexados:
        logger.warning('[FLUXO][ERRO] Lista de mandados está vazia após tentativas — abortando processamento de Mandado')
        progresso_after = carregar_progresso()
        count_after = len(progresso_after.get('processos_executados', []))
        processed = max(0, count_after - count_before)
        return {
            'sucesso': False,
            'processos': processed
        }

    # 3) Executar indexador normalmente
    success = False
    try:
        result_indexador = indexar_e_processar_lista(driver, fluxo_callback)
        logger.info(f'[FLUXO] indexar_e_processar_lista returned: {result_indexador}')
        success = bool(result_indexador)
    except Exception as e:
        logger.info(f'[FLUXO][ERRO] indexar_e_processar_lista falhou: {e}')
        success = False

    progresso_after = carregar_progresso()
    count_after = len(progresso_after.get('processos_executados', []))
    processed = max(0, count_after - count_before)

    return {
        'sucesso': success,
        'processos': processed
    }

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
            logger.info(f"[PROGRESSO][STATUS] {len(progresso)} processos executados")
            logger.info(f"[PROGRESSO][STATUS] Sistema de progresso unificado ativo")
            return
    
    # ===== SETUP UNIFICADO COM CREDENCIAL =====
    logger.info(f"[M1] Iniciando com driver={tipo_driver}, login={tipo_login}, headless={headless}")
    
    from Fix.core import credencial
    driver = credencial(
        tipo_driver=tipo_driver,
        tipo_login=tipo_login, 
        headless=headless
    )
    
    if not driver:
        logger.info('[M1][ERRO] Falha ao criar driver com credencial()')
        return
        
    logger.info('[M1]  Driver criado e login realizado via credencial()')
    
    # ===== CONFIGURAR RECOVERY GLOBAL =====
    # Usar credencial() também no recovery
    def recovery_credencial():
        return credencial(tipo_driver=tipo_driver, tipo_login=tipo_login, headless=headless)
    
    configurar_recovery_driver(recovery_credencial, lambda d: True)  # Login já feito
    logger.info("[M1]  Sistema de recuperação automática configurado")

    # Navegação para a lista de documentos internos
    if not navegacao(driver):
        driver.quit()
        return

    # Processa a lista de documentos internos com controle de sessão
    iniciar_fluxo_robusto(driver)

    logger.info("[INFO] Processamento concluído. Pressione ENTER para encerrar...")
    driver.quit()

if __name__ == "__main__":
    main()

