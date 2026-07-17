import time
import re
from Fix.log import logger
from Fix.selenium_base import aguardar_e_clicar, safe_click
from Fix.core import wait_for_page_load
from Fix.utils import normalizar_texto
from Fix.extracao import extrair_direto
from Peticao.core.extracao.extracao import criar_gigs
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

def ativar_filtro_mandados_devolvidos(driver):
    """Ativa o filtro 'Mandados devolvidos' caso nao esteja ativo."""
    logger.info('[MANDADOS_UI] Verificando/ativando filtro de mandados devolvidos...')
    try:
        icones_mandados = driver.find_elements(By.CSS_SELECTOR, 'i[aria-label*="Mandados devolvidos"]')
        if not icones_mandados:
            logger.warning('[MANDADOS_UI] Ícone de mandados devolvidos não encontrado')
            return False
        
        icone = icones_mandados[0]
        aria_pressed = icone.get_attribute('aria-pressed')
        
        if aria_pressed == 'true':
            logger.info('[MANDADOS_UI] Filtro já ativo.')
            return True
        else:
            logger.info('[MANDADOS_UI] Clicando para ativar filtro...')
            aguardar_e_clicar(driver, 'i[aria-label*="Mandados devolvidos"]', timeout=10)
            time.sleep(2)
            return True
    except Exception as e:
        logger.error(f'[MANDADOS_UI] Erro ao ativar filtro: {e}')
        return False

def processar_mandados_escaninho_ui(driver):
    """
    Fluxo que itera pela interface do escaninho mantendo a aba aberta.
    Prioriza processos com documento "Certidão de Oficial de Justiça".
    """
    logger.info('[MANDADOS_UI] Iniciando fluxo de UI no Escaninho...')
    
    url_escaninho = "https://pje.trt2.jus.br/pjekz/escaninho/documentos-internos"
    if "escaninho/documentos-internos" not in driver.current_url:
        driver.get(url_escaninho)
        wait_for_page_load(driver, timeout=15)
        
    ativar_filtro_mandados_devolvidos(driver)
    
    # Aguarda a tabela renderizar
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table[name='Tabela de Documentos'] tbody tr")))
    except TimeoutException:
        logger.warning('[MANDADOS_UI] Tabela de documentos não carregou ou está vazia.')
        return False

    escaninho_handle = driver.current_window_handle

    while True:
        try:
            linhas = driver.find_elements(By.CSS_SELECTOR, "table[name='Tabela de Documentos'] tbody tr.cdk-drag")
            if not linhas:
                logger.info('[MANDADOS_UI] Nenhuma linha encontrada na tabela.')
                break
                
            processou_algum = False
            
            for idx in range(len(linhas)):
                # Atualizar referencias das linhas a cada iteracao para evitar stale element
                linhas_atuais = driver.find_elements(By.CSS_SELECTOR, "table[name='Tabela de Documentos'] tbody tr.cdk-drag")
                if idx >= len(linhas_atuais):
                    break
                    
                linha = linhas_atuais[idx]
                try:
                    tds = linha.find_elements(By.TAG_NAME, "td")
                    if len(tds) < 13:
                        continue
                    
                    descricao = tds[5].text.lower()
                    numero_processo = tds[1].text.strip()
                    
                    if "certidão de oficial" in descricao or "certidao de oficial" in descricao:
                        logger.info(f'[MANDADOS_UI] Processando #{numero_processo} - {tds[5].text}')
                        
                        botao_kz = tds[0].find_element(By.CSS_SELECTOR, 'button[aria-label*="Detalhes do Processo"]')
                        
                        # Pegar handles antes do clique
                        handles_antes = driver.window_handles
                        driver.execute_script("arguments[0].click();", botao_kz)
                        
                        # Aguarda nova aba abrir
                        try:
                            WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > len(handles_antes))
                        except TimeoutException:
                            logger.error(f"[MANDADOS_UI] Nova aba não abriu para {numero_processo}")
                            continue
                            
                        novo_handle = [h for h in driver.window_handles if h not in handles_antes][0]
                        driver.switch_to.window(novo_handle)
                        
                        # Processamento na nova aba
                        try:
                            wait_for_page_load(driver, timeout=8)
                            # Aguardar timeline (substitui time.sleep fixo por espera direcionada)
                            from Fix.core import aguardar_renderizacao_nativa
                            aguardar_renderizacao_nativa(driver, "li.tl-item-container", timeout=5)
                            
                            # Clica no doc mais recente que seja certidao
                            from Mandado.entrada_api import _selecionar_doc_via_timeline
                            tipo_doc = _selecionar_doc_via_timeline(driver, log=True)
                            
                            if tipo_doc == 'outros':
                                texto_result = extrair_direto(driver, timeout=6, debug=True, formatar=True)
                                texto = texto_result.get('conteudo', '') if texto_result and texto_result.get('sucesso') else ''
                                texto_norm = normalizar_texto(texto).lower()
                                
                                if "procedi a intimacao" in texto_norm or "procedi à intimação" in texto_norm:
                                    logger.info(f"[MANDADOS_UI] #{numero_processo}: Regra 'procedi à intimação' detectada. Executando ação Apagar.")
                                    # a) gigs 1, , xs2
                                    criar_gigs(driver, dias_uteis="1", responsavel="", observacao="xs2", log=True)
                                    time.sleep(1)
                                    
                                    # b) fecha aba e volta foco
                                    driver.close()
                                    driver.switch_to.window(escaninho_handle)
                                    
                                    # c) clica lixeira
                                    linhas_refresh = driver.find_elements(By.CSS_SELECTOR, "table[name='Tabela de Documentos'] tbody tr.cdk-drag")
                                    if idx < len(linhas_refresh):
                                        linha_ref = linhas_refresh[idx]
                                        lixeira = linha_ref.find_element(By.CSS_SELECTOR, "button[aria-label*='Remover documento']")
                                        driver.execute_script("arguments[0].click();", lixeira)
                                        logger.info(f"[MANDADOS_UI] Lixeira clicada para #{numero_processo}.")
                                        time.sleep(2)
                                        # Lidar com eventual modal de confirmacao do pje
                                        try:
                                            botoes_confirmacao = driver.find_elements(By.XPATH, "//button[contains(., 'Sim') or contains(., 'Confirmar') or contains(., 'Remover')]")
                                            for btn in botoes_confirmacao:
                                                if btn.is_displayed():
                                                    driver.execute_script("arguments[0].click();", btn)
                                                    logger.info(f"[MANDADOS_UI] Confirmação de lixeira aceita para #{numero_processo}.")
                                                    time.sleep(1)
                                                    break
                                        except Exception:
                                            pass # Se nao houver modal, segue em frente
                                    
                                    processou_algum = True
                                    break # Recomeca o while True pois a lista mudou (item removido)
                                else:
                                    logger.info(f"[MANDADOS_UI] #{numero_processo}: Regra não satisfeita. Pulando.")
                                    driver.close()
                                    driver.switch_to.window(escaninho_handle)
                            else:
                                logger.info(f"[MANDADOS_UI] #{numero_processo}: Não é certidão ou não carregou timeline. Pulando.")
                                driver.close()
                                driver.switch_to.window(escaninho_handle)
                                
                        except Exception as e:
                            logger.error(f"[MANDADOS_UI] Erro ao processar detalhes de #{numero_processo}: {e}")
                            if len(driver.window_handles) > 1:
                                driver.close()
                                driver.switch_to.window(escaninho_handle)
                                
                except StaleElementReferenceException:
                    logger.warning("[MANDADOS_UI] Stale element ao acessar linha. Reiniciando iteração.")
                    processou_algum = True # forca recarregar linhas
                    break
                except Exception as e:
                    logger.error(f"[MANDADOS_UI] Erro não tratado na iteracao de linhas: {e}")
                    
            if not processou_algum:
                logger.info("[MANDADOS_UI] Fim da lista de Certidão de Oficial. Parando iteração para o primeiro passo.")
                break
                
        except Exception as e:
            logger.error(f"[MANDADOS_UI] Erro geral no loop: {e}")
            break
            
    logger.info('[MANDADOS_UI] Fluxo de Mandados UI concluído.')
    return True
