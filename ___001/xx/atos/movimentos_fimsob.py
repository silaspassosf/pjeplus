import logging
logger = logging.getLogger(__name__)

from .core import *


def mov_fimsob(driver, debug=False, timeout=15):
    """
    Movimento para encerrar sobrestamento.
    
    Fluxo inteligente:
    1. Verifica se já está na aba /aguardandofinal
    2. Se sim, prossegue diretamente para encerrar sobrestamento
    3. Se não, abre tarefa do processo e muda para /aguardandofinal
    4. Clica no botão "Encerrar sobrestamento"
    5. Confirma com "Sim"
    6. Fecha aba (se foi aberta)
    
    Args:
        driver: WebDriver do Selenium
        debug: Se True, exibe logs detalhados
        timeout: Timeout para aguardar elementos
    
    Returns:
        bool: True se executado com sucesso
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from Fix.core import esperar_elemento, safe_click
    import time
    
    def log_msg(msg):
        if debug:
            try:
                print(msg)
            except Exception:
                pass

    log_msg("Iniciando movimento para encerrar sobrestamento")
    
    try:
        # ===== ETAPA 1: VERIFICAR SE JÁ ESTÁ NA ABA /AGUARDANDOFINAL =====
        log_msg("1. Verificando se já está na aba /aguardandofinal...")
        
        url_atual = driver.current_url
        ja_esta_em_aguardandofinal = '/aguardandofinal' in url_atual
        
        if ja_esta_em_aguardandofinal:
            log_msg(" Já está na aba /aguardandofinal - prosseguindo diretamente")
            tarefa_aberta = False  # Não abriu tarefa, já estava na correta
        else:
            log_msg(f" Não está em /aguardandofinal (URL atual: {url_atual})")
            log_msg("Abrindo tarefa do processo...")
            
            # ===== ETAPA 1B: ABRIR TAREFA DO PROCESSO =====
            from Fix.selectors_pje import BTN_TAREFA_PROCESSO
            btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=timeout)
            if not btn_abrir_tarefa:
                log_msg(" Botão 'Abrir tarefa do processo' não encontrado!")
                return False
            
            # Captura o texto da tarefa antes do clique
            try:
                span_tarefa = btn_abrir_tarefa.find_element(By.CSS_SELECTOR, '.texto-tarefa-processo')
                tarefa_do_botao = span_tarefa.text.strip() if span_tarefa else btn_abrir_tarefa.text.strip()
                log_msg(f" Tarefa identificada: '{tarefa_do_botao}'")
            except Exception:
                log_msg(" Não foi possível capturar nome da tarefa")
            
            # Clica na tarefa e aguarda nova aba
            abas_antes = set(driver.window_handles)
            click_resultado = safe_click(driver, btn_abrir_tarefa)
            
            if not click_resultado:
                log_msg(" Falha no clique do botão da tarefa")
                return False
            
            log_msg(" Botão 'Abrir tarefa do processo' clicado")
            
            # ===== ETAPA 1C: MUDAR PARA ABA /AGUARDANDOFINAL =====
            log_msg("Mudando para aba /aguardandofinal...")
            
            # Aguarda nova aba e troca para ela
            nova_aba = None
            for _ in range(20):
                abas_depois = set(driver.window_handles)
                novas_abas = abas_depois - abas_antes
                if novas_abas:
                    nova_aba = novas_abas.pop()
                    break
                time.sleep(0.3)
            
            if nova_aba:
                driver.switch_to.window(nova_aba)
                log_msg(" Foco trocado para nova aba da tarefa")
                
                # Verifica se está na URL correta
                url_atual = driver.current_url
                if '/aguardandofinal' in url_atual:
                    log_msg(" Confirmado: aba /aguardandofinal")
                    tarefa_aberta = True
                else:
                    log_msg(f" URL atual: {url_atual} (esperado: /aguardandofinal)")
                    return False
            else:
                # Nenhuma nova aba detectada - verificar se já está na aba correta
                log_msg(" Nenhuma nova aba detectada - verificando se já está na aba /aguardandofinal...")
                url_atual = driver.current_url
                if '/aguardandofinal' in url_atual:
                    log_msg(" Já está na aba /aguardandofinal correta - prosseguindo...")
                    tarefa_aberta = False  # Não abriu nova aba, mas já estava correto
                else:
                    log_msg(f" Não está na aba /aguardandofinal. URL atual: {url_atual}")
                    return False
        
        # ===== ETAPA 2: CLICAR EM "ENCERRAR SOBRESTAMENTO" =====
        log_msg("2. Clicando no botão 'Encerrar sobrestamento'...")
        
        try:
            btn_encerrar = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 
                    'button[mattooltip="Encerrar sobrestamento"][aria-label="Encerrar todos os motivos de sobrestamento"]'))
            )
            btn_encerrar.click()
            log_msg(" Botão 'Encerrar sobrestamento' clicado")
            time.sleep(1)  # Aguarda modal de confirmação
        except Exception as e:
            log_msg(f" Erro ao clicar no botão 'Encerrar sobrestamento': {e}")
            
            # Fallback: tentar por texto do botão
            try:
                log_msg("Tentando fallback por texto do botão...")
                btn_encerrar = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, 
                        '//button[contains(.//div[@class="texto-botao-skinny"], "Encerrar sobrestamento")]'))
                )
                btn_encerrar.click()
                log_msg(" Botão 'Encerrar sobrestamento' clicado (fallback)")
                time.sleep(1)
            except Exception as e2:
                log_msg(f" Erro no fallback: {e2}")
                return False
        
        # ===== ETAPA 3: CONFIRMAR COM "SIM" =====
        log_msg("3. Confirmando com 'Sim'...")
        
        try:
            btn_sim = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 
                    'button[mat-button][color="primary"] span.mat-button-wrapper'))
            )
            
            # Verifica se é realmente o botão "Sim"
            if 'Sim' in btn_sim.text:
                btn_sim.click()
                log_msg(" Botão 'Sim' clicado")
                time.sleep(2)  # Aguarda processamento
            else:
                # Fallback por XPath
                btn_sim = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, 
                        '//button[.//span[contains(text(), "Sim")]]'))
                )
                btn_sim.click()
                log_msg(" Botão 'Sim' clicado (fallback)")
                time.sleep(2)
                
        except Exception as e:
            log_msg(f" Erro ao confirmar com 'Sim': {e}")
            return False
        
        # ===== ETAPA 4: FECHAR ABA (SOMENTE SE FOI ABERTA) =====
        if tarefa_aberta:
            log_msg("4. Fechando aba e retornando para aba /detalhe...")
            try:
                handle_atual = driver.current_window_handle
                driver.close()  # Fecha aba atual

                # Aguarda pequenas mudanças nas abas
                time.sleep(0.8)

                abas_restantes = driver.window_handles
                if not abas_restantes:
                    log_msg(" Nenhuma aba restante encontrada após fechar a aba da tarefa")
                else:
                    # Preferir uma aba cujo URL contenha '/detalhe'
                    detalhe_handle = None
                    for handle in abas_restantes:
                        try:
                            driver.switch_to.window(handle)
                            url = (driver.current_url or '').lower()
                            if '/detalhe' in url:
                                detalhe_handle = handle
                                break
                        except Exception:
                            continue

                    if detalhe_handle:
                        driver.switch_to.window(detalhe_handle)
                        log_msg(f" Trocou para aba /detalhe: {driver.current_url}")
                        try:
                            driver.refresh()
                            time.sleep(1.2)
                            log_msg(" /detalhe atualizado (refresh) após fimsob")
                        except Exception as _:
                            log_msg(" Falha ao atualizar /detalhe (refresh) — continuando")
                    else:
                        # Se não encontrou /detalhe, tenta a primeira aba disponível e força refresh
                        try:
                            driver.switch_to.window(abas_restantes[0])
                            log_msg(f" Aba /detalhe não encontrada, trocando para primeira aba disponível: {driver.current_url}")
                            try:
                                driver.refresh()
                                time.sleep(1.2)
                                log_msg(" Aba atual atualizada (refresh) após fimsob")
                            except Exception:
                                log_msg(" Falha ao dar refresh na aba atual")
                        except Exception as e_switch:
                            log_msg(f" Falha ao alternar para aba restante: {e_switch}")

            except Exception as e:
                log_msg(f" Erro ao fechar aba: {e}")
                # Não falha a função por erro no fechamento
        else:
            log_msg("4. Tarefa já estava aberta - não fechando aba")
        
        log_msg(" Movimento para encerrar sobrestamento finalizado com sucesso!")
        return True
        
    except Exception as e:
        log_msg(f" Erro geral no movimento para encerrar sobrestamento: {e}")
        return False
