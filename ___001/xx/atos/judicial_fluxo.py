from Fix.core import aguardar_e_clicar, safe_click, logger, esperar_url_conter
from Fix.selectors_pje import BTN_TAREFA_PROCESSO
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
import time

from typing import Optional, Tuple, Dict, List, Union, Callable
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from .wrappers_utils import preparar_campo_filtro_modelo


def fluxo_cls(
    driver: WebDriver,
    conclusao_tipo: str,
    forcar_iniciar_execucao: bool = False
) -> bool:
    """
    Fluxo corrigido para CLS (Conclusão ao Magistrado → Minutar):
    
    LÓGICA SEQUENCIAL:
    1. Abrir tarefa do processo e trocar de aba
    2. Clicar em "Conclusão ao Magistrado" OU "Análise" (se o primeiro não disponível)
       - Se clicar em Análise, confirma URL /transicao e repete clique em "Conclusão ao Magistrado"
    3. Confirma URL /conclusao e escolhe o tipo de conclusão
    4. Confirma URL /minutar e inicia o fluxo de preenchimento
    
    TRATAMENTO DE ESTADOS INTERMEDIÁRIOS (ao abrir tarefa):
    - Se já em /assinar → retorna True (ato já cumprido)
    - Se já em /minutar → foca no campo e retorna True
    - Se já em /conclusao → vai direto para escolha de tipo
    
    Retorna True em caso de sucesso, False em caso de falha.
    """
    try:
        # ===== VERIFICAÇÃO INICIAL: Checar estado atual =====
        current_url = (driver.current_url or '').lower()
        
        # CASO 1: Já está em /assinar → Ato já cumprido
        if '/assinar' in current_url:
            print('[CLS] ✅ Processo já está em /assinar - ato cumprido, nada a fazer')
            return True
        
        # CASO 2: Já está em /minutar → Apenas focar no campo
        if '/minutar' in current_url:
            print('[CLS] ✅ Já estamos em /minutar - focando no campo de filtro')
            try:
                campo_filtro_modelo = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, 'input#inputFiltro'))
                )
                driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
                print('[CLS] ✅ Foco no campo #inputFiltro realizado')
            except Exception as e:
                # Silencioso - a função de modelo vai validar
                pass
            return True
        
        # CASO 3: Já está em /conclusao → Pula para escolha de tipo
        ja_em_conclusao = '/conclusao' in current_url
        
        # ===== PASSO 1: ABRIR TAREFA DO PROCESSO (se necessário) =====
        if not ja_em_conclusao:
            print('[CLS] Passo 1: Abrindo tarefa do processo...')
            abas_antes = set(driver.window_handles)
            btn_abrir_tarefa = aguardar_e_clicar(driver, BTN_TAREFA_PROCESSO, timeout=10, retornar_elemento=True)
            if not btn_abrir_tarefa:
                logger.error('[CLS] Botão "Abrir tarefa do processo" não encontrado!')
                return False

            # Verificar se já está em "Assinar"
            tarefa_do_botao = None
            try:
                span_tarefa = btn_abrir_tarefa.find_element(By.CSS_SELECTOR, '.texto-tarefa-processo')
                if span_tarefa:
                    tarefa_do_botao = span_tarefa.text.strip()
            except Exception:
                try:
                    tarefa_do_botao = btn_abrir_tarefa.text.strip()
                except Exception:
                    pass

            if tarefa_do_botao and 'assinar' in tarefa_do_botao.lower():
                print(f'[CLS] ⏭️ Tarefa "{tarefa_do_botao}" contém "assinar" — ato pronto')
                return True

            # Clicar para abrir tarefa
            if not safe_click(driver, btn_abrir_tarefa):
                logger.error('[CLS] Falha ao clicar em "Abrir tarefa do processo"')
                return False

            # Aguardar nova aba
            nova_aba = None
            try:
                WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > len(abas_antes))
                abas_depois = set(driver.window_handles)
                novas_abas = abas_depois - abas_antes
                if novas_abas:
                    nova_aba = novas_abas.pop()
            except TimeoutException:
                print('[CLS] Nenhuma nova aba detectada (continuando na mesma aba)')

            if nova_aba:
                driver.switch_to.window(nova_aba)
                print('[CLS] ✅ Foco trocado para nova aba')
                
                # Aguardar carregamento MÍNIMO (sem múltiplos F5)
                try:
                    # Apenas aguarda body estar presente - rápido
                    WebDriverWait(driver, 8).until(lambda d: d.find_element(By.TAG_NAME, 'body'))
                except Exception:
                    pass

                # Verificar URL após abertura da aba
                current_url = (driver.current_url or '').lower()
                if '/assinar' in current_url:
                    print('[CLS] ✅ Nova aba já em /assinar - ato cumprido')
                    return True
                if '/minutar' in current_url:
                    print('[CLS] ✅ Nova aba já em /minutar - focando campo')
                    try:
                        campo_filtro_modelo = WebDriverWait(driver, 10).until(
                            EC.visibility_of_element_located((By.CSS_SELECTOR, 'input#inputFiltro'))
                        )
                        driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
                        print('[CLS] ✅ Foco no campo #inputFiltro realizado')
                    except Exception as e:
                        # Silencioso - a função de modelo vai validar
                        pass
                    return True
                if '/conclusao' in current_url:
                    ja_em_conclusao = True
                    print('[CLS] Nova aba já em /conclusao - pulando navegação')
        
        # Limpeza de overlays
        try:
            overlays = driver.find_elements(By.CSS_SELECTOR, '.cdk-overlay-backdrop, .mat-dialog-container')
            if overlays:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(0.15)
        except Exception:
            pass
        
        # ===== PASSO 2: NAVEGAR PARA CONCLUSÃO AO MAGISTRADO (se necessário) =====
        if not ja_em_conclusao:
            print('[CLS] Passo 2: Navegando para Conclusão ao Magistrado...')
            
            # Aguardar que os botões de transição estejam carregados
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-botoes-transicao button'))
                )
            except Exception:
                print('[CLS][WARN] Botões de transição não carregaram')
            
            # Tentar clicar em "Conclusão ao Magistrado"
            btn_conclusao_encontrado = False
            try:
                btn_conclusao = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Conclusão ao magistrado']"))
                )
                btn_conclusao.click()
                btn_conclusao_encontrado = True
                print('[CLS] ✅ Clique em "Conclusão ao magistrado" realizado')
            except Exception as e:
                print(f'[CLS] Botão "Conclusão ao magistrado" não disponível imediatamente')
            
            # Se não encontrou, tentar "Análise" primeiro
            if not btn_conclusao_encontrado:
                print('[CLS] Tentando clicar em "Análise" primeiro...')
                try:
                    btn_analise = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Análise']"))
                    )
                    btn_analise.click()
                    print('[CLS] ✅ Clique em "Análise" realizado')
                    
                    # Aguardar transição para /transicao (aguardar URL mudar rapidamente)
                    if not esperar_url_conter(driver, '/transicao', timeout=8):
                        print(f'[CLS][WARN] URL não contém /transicao após Análise: {driver.current_url}')
                    
                    # ===== CRÍTICO: AGUARDAR E REMOVER OVERLAY APÓS ANÁLISE =====
                    print('[CLS] Aguardando e removendo overlays após Análise...')
                    max_tentativas_overlay = 5
                    for tentativa in range(max_tentativas_overlay):
                        try:
                            # Verifica se há overlay visível
                            overlays_visiveis = driver.find_elements(
                                By.CSS_SELECTOR,
                                'div.cdk-overlay-backdrop.cdk-overlay-dark-backdrop.cdk-overlay-backdrop-showing'
                            )
                            if overlays_visiveis:
                                print(f'[CLS] Overlay detectado (tentativa {tentativa + 1}/{max_tentativas_overlay}) - enviando ESC')
                                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                                time.sleep(0.3)
                            else:
                                print('[CLS] Nenhum overlay detectado - prosseguindo')
                                break
                        except Exception as overlay_err:
                            print(f'[CLS][DEBUG] Erro ao verificar overlay: {overlay_err}')
                            break
                    
                    # Pequena pausa adicional para estabilizar interface
                    time.sleep(0.5)
                    
                    # Aguardar botões de transição novamente
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-botoes-transicao button'))
                        )
                    except Exception:
                        pass
                    
                    # Agora tentar clicar em "Conclusão ao magistrado"
                    print('[CLS] Tentando clicar em "Conclusão ao magistrado" após Análise...')
                    
                    # Tenta múltiplas estratégias de clique
                    btn_conclusao_clicado = False
                    max_tentativas_clique = 3
                    
                    for tentativa_clique in range(max_tentativas_clique):
                        try:
                            btn_conclusao = WebDriverWait(driver, 8).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Conclusão ao magistrado']"))
                            )
                            
                            # Primeira tentativa: clique normal
                            if tentativa_clique == 0:
                                print(f'[CLS] Tentativa {tentativa_clique + 1}: Clique normal')
                                btn_conclusao.click()
                            # Segunda tentativa: JavaScript click
                            elif tentativa_clique == 1:
                                print(f'[CLS] Tentativa {tentativa_clique + 1}: JavaScript click')
                                driver.execute_script('arguments[0].click();', btn_conclusao)
                            # Terceira tentativa: ScrollIntoView + JavaScript click
                            else:
                                print(f'[CLS] Tentativa {tentativa_clique + 1}: ScrollIntoView + JavaScript click')
                                driver.execute_script('arguments[arguments.length - 1].scrollIntoView({block: "center"});', btn_conclusao)
                                time.sleep(0.3)
                                driver.execute_script('arguments[0].click();', btn_conclusao)
                            
                            btn_conclusao_clicado = True
                            print('[CLS] ✅ Clique em "Conclusão ao magistrado" realizado após Análise')
                            break
                            
                        except ElementClickInterceptedException as click_err:
                            print(f'[CLS][WARN] Clique interceptado na tentativa {tentativa_clique + 1}: {click_err}')
                            # Remove overlays novamente antes de próxima tentativa
                            try:
                                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                                time.sleep(0.5)
                            except Exception:
                                pass
                        except Exception as other_err:
                            print(f'[CLS][WARN] Erro na tentativa {tentativa_clique + 1}: {other_err}')
                            time.sleep(0.5)
                    
                    if not btn_conclusao_clicado:
                        print('[CLS][ERRO] Falha ao clicar em "Conclusão ao magistrado" após todas as tentativas')
                        return False
                        
                except Exception as e2:
                    print(f'[CLS][ERRO] Falha ao navegar via Análise: {e2}')
                    return False
            
            # Aguardar URL /conclusao (se não mudar, usar presença dos botões como referência)
            if not esperar_url_conter(driver, '/conclusao', timeout=15):
                current_after = (driver.current_url or '').lower()
                print(f'[CLS][ERRO] URL não mudou para /conclusao: {driver.current_url}')
                # Se já foi direto para /minutar, concluir
                if '/minutar' in current_after:
                    print('[CLS] Processo foi direto para /minutar')
                    try:
                        campo_filtro_modelo = WebDriverWait(driver, 10).until(
                            EC.visibility_of_element_located((By.CSS_SELECTOR, 'input#inputFiltro'))
                        )
                        driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
                    except Exception:
                        pass
                    return True

                # Se estamos em /transicao, validar se botões de conclusão já estão presentes
                try:
                    WebDriverWait(driver, 6).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-concluso-tarefa-botao button'))
                    )
                    print('[CLS] Botões de conclusão disponíveis em /transicao - seguindo fluxo')
                except Exception:
                    return False
        
        # ===== PASSO 3: ESCOLHER TIPO DE CONCLUSÃO =====
        print(f'[CLS] Passo 3: Escolhendo tipo de conclusão: {conclusao_tipo}')
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-concluso-tarefa-botao'))
            )
        except Exception:
            pass
        
        btn_tipo_conclusao = None
        
        # Estratégia 1: Procurar em botões estruturados (pje-concluso-tarefa-botao)
        try:
            candidatos = driver.find_elements(By.CSS_SELECTOR, 'pje-concluso-tarefa-botao button')
            for btn in candidatos:
                try:
                    txt = (btn.text or '').strip()
                    if txt and conclusao_tipo.lower() in txt.lower() and btn.is_displayed() and btn.is_enabled():
                        btn_tipo_conclusao = btn
                        break
                except Exception:
                    continue
        except Exception:
            pass

        # Estratégia 2: Procurar por texto visível
        if not btn_tipo_conclusao:
            try:
                xpath = f"//button[contains(normalize-space(text()), '{conclusao_tipo}') ]"
                btns = driver.find_elements(By.XPATH, xpath)
                for btn in btns:
                    try:
                        if btn.is_displayed() and btn.is_enabled():
                            aria = (btn.get_attribute('aria-label') or '').lower()
                            # Evitar botões de remoção/chips
                            if 'remover' not in aria and 'fechar' not in aria and 'excluir' not in aria:
                                btn_tipo_conclusao = btn
                                break
                    except Exception:
                        continue
            except Exception:
                pass

        # Estratégia 3: Procurar por aria-label
        if not btn_tipo_conclusao:
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, "button[aria-label]")
                for btn in btns:
                    try:
                        aria = (btn.get_attribute('aria-label') or '').lower()
                        if conclusao_tipo.lower() in aria:
                            if 'remover' not in aria and 'fechar' not in aria:
                                if btn.is_displayed() and btn.is_enabled():
                                    btn_tipo_conclusao = btn
                                    break
                    except Exception:
                        continue
            except Exception:
                pass
        
        if not btn_tipo_conclusao:
            print(f'[CLS][ERRO] Botão de conclusão "{conclusao_tipo}" não encontrado')
            return False
        
        driver.execute_script('arguments[0].scrollIntoView({block: "center"});', btn_tipo_conclusao)
        time.sleep(0.3)
        driver.execute_script('arguments[0].click();', btn_tipo_conclusao)
        print(f'[CLS] ✅ Botão de conclusão "{conclusao_tipo}" clicado')
        time.sleep(1)

        # ===== PASSO 4: AGUARDAR URL /MINUTAR E FOCAR NO CAMPO =====
        print('[CLS] Passo 4: Aguardando URL /minutar...')
        if not esperar_url_conter(driver, '/minutar', timeout=20):
            print(f'[CLS][ERRO] URL não mudou para /minutar: {driver.current_url}')
            return False

        print('[CLS] ✅ Chegamos em /minutar - focando no campo de filtro')
        # Foco no campo de filtro de modelos
        try:
            campo_filtro_modelo = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'input#inputFiltro'))
            )
            driver.execute_script('arguments[0].removeAttribute("disabled"); arguments[0].removeAttribute("readonly");', campo_filtro_modelo)
            driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
            driver.execute_script('arguments[0].value = arguments[1];', campo_filtro_modelo, "")  # Limpa campo
            driver.execute_script('var el=arguments[0]; el.dispatchEvent(new Event("input", {bubbles:true})); el.dispatchEvent(new Event("keyup", {bubbles:true}));', campo_filtro_modelo)
            print('[CLS][MODELO][OK] Foco e eventos JS realizados no campo de filtro de modelos (#inputFiltro).')
            time.sleep(0.3)
        except Exception as e:
            print(f'[CLS][MODELO][ERRO] Falha ao acessar/interagir com o campo de filtro de modelos: {e}')
            return False

        print('[CLS] Fluxo de CLS finalizado com sucesso.')
        return True
    except Exception as e:
        print(f'[CLS][ERRO] Falha no fluxo de CLS: {e}')
        try:
            driver.save_screenshot(f'erro_fluxo_cls_{conclusao_tipo}.png')
        except Exception as screen_err:
            print(f'[CLS][WARN] Falha ao salvar screenshot do erro: {screen_err}')
        return False # Indicate failure