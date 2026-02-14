from .loop_base import *


def _ciclo1_marcar_todas(driver: WebDriver) -> str:
    """Seleciona todos os processos via botão marcar-todas."""
    from Fix.core import com_retry

    def _tentar_marcar():
        # Usar XPath mais robusto para encontrar o botão marcar-todas
        print("[DEBUG] Procurando botão marcar-todas...")
        btn_marcar_todas = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//i[contains(@class, 'marcar-todas')]"))
        )
        print(f"[DEBUG] Botão marcar-todas encontrado: {btn_marcar_todas.get_attribute('outerHTML')}")
        # Usar JavaScript click para evitar obstrução
        result = driver.execute_script("""
        arguments[0].scrollIntoView(true);
        arguments[0].click();
        return true;
        """, btn_marcar_todas)
        if result:
            print("[DEBUG] Clique em marcar-todas executado com sucesso.")
        time.sleep(1)
        return result

    try:
        if com_retry(_tentar_marcar, max_tentativas=5, backoff_base=1.5, log=True):
            print("[DEBUG] Marcar-todas clicado com sucesso após retry.")
            return "success"
        else:
            print("[LOOP_PRAZO] Todas as tentativas de marcar-todas falharam")
            return "marcar_todas_not_found_but_continue"
    except Exception as e:
        print(f"[LOOP_PRAZO] Erro geral em marcar-todas: {e}")
        return "error"


def _ciclo1_abrir_suitcase(driver: WebDriver) -> bool:
    """Abre suitcase para movimentação em lote usando JavaScript click."""
    from Fix.core import com_retry

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'i.fas.fa-suitcase.icone'))
        )
    except Exception as e:
        return False
    elements = driver.find_elements(By.CSS_SELECTOR, 'i.fas.fa-suitcase.icone')
    def _tentar_abrir_suitcase():
        # Usar JavaScript para encontrar e clicar
        script = '''
        try {
            let suitcase = document.querySelector('i.fas.fa-suitcase.icone');
            if (suitcase) {
                console.log('Suitcase encontrado:', suitcase.outerHTML);
                suitcase.scrollIntoView({block: 'center'});
                suitcase.click();
                return true;
            } else {
                console.log('Suitcase não encontrado');
                return false;
            }
        } catch(e) {
            console.error('Erro ao clicar suitcase:', e);
            return false;
        }
        '''
        result = driver.execute_script(script)
        if result:
            pass
        return result

    try:
        if com_retry(_tentar_abrir_suitcase, max_tentativas=3, backoff_base=1.5, log=True):
            time.sleep(1)
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"[LOOP_PRAZO] Erro geral em abrir suitcase: {e}")
        return False


def _ciclo1_aguardar_movimentacao_lote(driver: WebDriver) -> bool:
    """Aguarda carregamento da página de movimentação em lote."""
    print("[DEBUG] Aguardando URL /painel/movimentacao-lote...")
    try:
        WebDriverWait(driver, 15).until(
            EC.url_contains('/painel/movimentacao-lote')
        )
        print(f"[DEBUG] URL atual: {driver.current_url}")
        if '/painel/movimentacao-lote' not in driver.current_url:
            print(f"[LOOP_PRAZO][ERRO] URL inesperada após suitcase: {driver.current_url}")
            return False
        print(f"[LOOP_PRAZO] Na tela de movimentação em lote: {driver.current_url}")
        time.sleep(1.2)
        return True
    except Exception as e:
        print(f"[LOOP_PRAZO][ERRO] URL de movimentacao-lote não carregou: {e}")
        return False


def _ciclo1_movimentar_destino_providencias(driver: WebDriver) -> bool:
    """Abordagem especial para 'Cumprimento de providências' no ciclo 2."""
    opcao_destino = 'Cumprimento de providências'
    print(f"[LOOP_PRAZO] Abordagem especial para '{opcao_destino}'")

    # Aumentar tentativas para abrir dropdown
    max_tentativas_abrir = 8
    dropdown_aberto = False

    for tent_abrir in range(1, max_tentativas_abrir + 1):
        try:
            print(f"[LOOP_PRAZO] Tentativa {tent_abrir}/{max_tentativas_abrir} de abrir dropdown para providências")

            # Aguardar mais tempo para o elemento estar pronto
            seta_dropdown = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.mat-select-arrow-wrapper"))
            )
            time.sleep(1.5)  # Mais tempo
            driver.execute_script("arguments[0].scrollIntoView(true);", seta_dropdown)
            driver.execute_script("document.body.style.zoom='100%'")
            time.sleep(0.5)

            # Múltiplos cliques se necessário
            for click_attempt in range(3):
                try:
                    driver.execute_script("arguments[0].click();", seta_dropdown)
                    print(f"[LOOP_PRAZO] Clique {click_attempt + 1} executado")
                    time.sleep(2.0)  # Mais tempo para overlay aparecer

                    # Verificar se overlay apareceu
                    overlay = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
                    )
                    opcoes_elementos = overlay.find_elements(By.XPATH, ".//span[contains(@class,'mat-option-text')]")
                    opcoes_textos = [opt.text.strip() for opt in opcoes_elementos if opt.text.strip()]

                    if len(opcoes_textos) > 0:
                        print(f"[LOOP_PRAZO] ✅ Dropdown aberto com {len(opcoes_textos)} opções após clique {click_attempt + 1}")
                        print(f"[LOOP_PRAZO] Opções: {opcoes_textos}")
                        dropdown_aberto = True
                        break
                except:
                    time.sleep(1.0)

            if dropdown_aberto:
                break

        except Exception as e:
            print(f"[LOOP_PRAZO] ⚠️ Erro na tentativa {tent_abrir}: {e}")
            time.sleep(1.0)

    if not dropdown_aberto:
        print(f"[LOOP_PRAZO][ERRO] Falha ao abrir dropdown para providências após {max_tentativas_abrir} tentativas")
        return False

    # Selecionar a opção com mais tentativas
    max_tentativas = 8
    for tentativa in range(1, max_tentativas + 1):
        try:
            print(f"[LOOP_PRAZO] Tentativa {tentativa}/{max_tentativas} de selecionar '{opcao_destino}'")

            overlay = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
            )

            # Busca mais flexível para "Cumprimento de providências"
            opcao_elemento = None
            try:
                # Tentar exato primeiro
                opcao_xpath = f".//span[contains(@class,'mat-option-text') and normalize-space(text())='{opcao_destino}']"
                opcao_elemento = overlay.find_element(By.XPATH, opcao_xpath)
            except:
                try:
                    # Tentar parcial
                    opcao_xpath_parcial = f".//span[contains(@class,'mat-option-text') and contains(text(),'Cumprimento')]"
                    opcao_elemento = overlay.find_element(By.XPATH, opcao_xpath_parcial)
                except:
                    try:
                        # Tentar ainda mais parcial
                        opcao_xpath_muito_parcial = f".//span[contains(@class,'mat-option-text') and contains(text(),'providências')]"
                        opcao_elemento = overlay.find_element(By.XPATH, opcao_xpath_muito_parcial)
                    except:
                        pass

            if opcao_elemento:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", opcao_elemento)
                time.sleep(0.5)
                # Tentar clique normal primeiro
                try:
                    opcao_elemento.click()
                    print(f"[LOOP_PRAZO] ✅ Opção '{opcao_destino}' selecionada com clique normal na tentativa {tentativa}.")
                except:
                    # Fallback para JavaScript click
                    driver.execute_script("arguments[0].click();", opcao_elemento)
                    print(f"[LOOP_PRAZO] ✅ Opção '{opcao_destino}' selecionada com JS click na tentativa {tentativa}.")
                time.sleep(1.5)
                break
            else:
                print(f"[LOOP_PRAZO][AVISO] Tentativa {tentativa}: Opção '{opcao_destino}' não encontrada")

                # Se não encontrou, tentar reabrir dropdown
                if tentativa < max_tentativas:
                    try:
                        driver.execute_script("document.body.click();")
                        time.sleep(0.5)
                        seta_dropdown = driver.find_element(By.CSS_SELECTOR, "div.mat-select-arrow-wrapper")
                        seta_dropdown.click()
                        time.sleep(1.5)
                    except:
                        pass

        except Exception as e:
            print(f"[LOOP_PRAZO][ERRO] Tentativa {tentativa}: Falha geral: {e}")
            if tentativa == max_tentativas:
                return False
            time.sleep(1)

    # Aguardar botão aparecer e clicar
    time.sleep(3)
    seletor_movimentar = "button.mat-raised-button[color='primary']"
    try:
        btn_movimentar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_movimentar))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_movimentar)
        result = driver.execute_script("arguments[0].click(); return true;", btn_movimentar)
        if result:
            print('[LOOP_PRAZO] ✅ Botão "Movimentar processos" clicado com sucesso')
            time.sleep(2)
            return True
        else:
            print('[LOOP_PRAZO][ERRO] Falha no JavaScript click em "Movimentar processos"')
            return False
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Botão "Movimentar processos" não encontrado: {e}')
        return False


def _ciclo1_movimentar_destino(driver: WebDriver, opcao_destino: str) -> bool:
    """Seleciona destino usando abordagem direta inline (como no original) com retry."""

    # Para "Cumprimento de providências" no ciclo 2, usar abordagem mais robusta
    if opcao_destino == 'Cumprimento de providências':
        print("[LOOP_PRAZO] Usando abordagem especial para 'Cumprimento de providências'")
        return _ciclo1_movimentar_destino_providencias(driver)

    # INSISTIR até dropdown abrir e mostrar opções reais
    max_tentativas_abrir = 5
    dropdown_aberto = False

    for tent_abrir in range(1, max_tentativas_abrir + 1):
        try:

            seta_dropdown = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.mat-select-arrow-wrapper"))
            )
            time.sleep(1.0)
            driver.execute_script("arguments[0].scrollIntoView(true);", seta_dropdown)
            driver.execute_script("document.body.style.zoom='100%'")
            time.sleep(0.3)

            # Clicar e aguardar overlay aparecer COM OPÇÕES
            driver.execute_script("arguments[0].click();", seta_dropdown)
            time.sleep(1.2)

            # VERIFICAR se overlay tem opções reais (não apenas vazio)
            try:
                overlay = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
                )
                opcoes_elementos = overlay.find_elements(By.XPATH, ".//span[contains(@class,'mat-option-text')]")
                opcoes_textos = [opt.text.strip() for opt in opcoes_elementos if opt.text.strip()]

                if len(opcoes_textos) > 0:
                    dropdown_aberto = True
                    break
                else:
                    time.sleep(0.5)
            except Exception:
                time.sleep(0.5)

        except Exception as e:
            logger.error(f"[LOOP_PRAZO]  Erro na tentativa {tent_abrir}: {e}")
            time.sleep(0.5)

    if not dropdown_aberto:
        logger.error(f"[LOOP_PRAZO][ERRO] Falha ao abrir dropdown após {max_tentativas_abrir} tentativas")
        return False

    # Selecionar a opção de destino com RETRY
    max_tentativas = 5
    for tentativa in range(1, max_tentativas + 1):
        try:

            overlay = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
            )

            # Listar todas as opções disponíveis para debug
            opcoes_elementos = overlay.find_elements(By.XPATH, ".//span[contains(@class,'mat-option-text')]")
            opcoes_disponiveis = [opt.text.strip() for opt in opcoes_elementos if opt.text.strip()]

            # Tentar encontrar e clicar na opção exata
            opcao_xpath = f".//span[contains(@class,'mat-option-text') and normalize-space(text())='{opcao_destino}']"
            try:
                opcao_elemento = overlay.find_element(By.XPATH, opcao_xpath)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", opcao_elemento)
                time.sleep(0.3)
                opcao_elemento.click()
                time.sleep(0.8)
                break  # Sucesso, sair do loop

            except Exception as e_opcao:

                # Tentar busca case-insensitive e parcial
                opcao_xpath_parcial = f".//span[contains(@class,'mat-option-text') and contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{opcao_destino.lower()}')]"
                try:
                    opcao_elemento_parcial = overlay.find_element(By.XPATH, opcao_xpath_parcial)
                    opcao_texto = opcao_elemento_parcial.text.strip()
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", opcao_elemento_parcial)
                    time.sleep(0.3)
                    opcao_elemento_parcial.click()
                    time.sleep(0.8)
                    break  # Sucesso, sair do loop

                except Exception as e_parcial:
                    logger.error(f"[LOOP_PRAZO][ERRO] Tentativa {tentativa}: Busca parcial também falhou: {e_parcial}")

                    # Se não é última tentativa, fechar e reabrir dropdown
                    if tentativa < max_tentativas:
                        try:
                            # Fechar clicando fora
                            driver.execute_script("document.body.click();")
                            time.sleep(0.5)
                            # Reabrir
                            seta_dropdown = driver.find_element(By.CSS_SELECTOR, "div.mat-select-arrow-wrapper")
                            seta_dropdown.click()
                            time.sleep(0.8)
                        except Exception:
                            pass
                    else:
                        # Última tentativa falhou
                        logger.error(f"[LOOP_PRAZO][ERRO] Todas as {max_tentativas} tentativas falharam para '{opcao_destino}'")
                        return False

        except Exception as e:
            logger.error(f"[LOOP_PRAZO][ERRO] Tentativa {tentativa}: Falha ao acessar painel de opções: {e}")
            if tentativa == max_tentativas:
                return False
            time.sleep(1)

    # Aguardar botão aparecer após seleção
    time.sleep(2)

    # Procurar o botão "Movimentar processos" com seletor específico
    seletor_movimentar = "button.mat-raised-button[color='primary']"
    elements = driver.find_elements(By.CSS_SELECTOR, seletor_movimentar)
    if elements:
        btn_movimentar = elements[0]
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_movimentar)
        result = driver.execute_script("arguments[0].click(); return true;", btn_movimentar)
        if result:
            time.sleep(1.2)
            return True
        else:
            logger.error('[LOOP_PRAZO][ERRO] Falha no JavaScript click em "Movimentar processos"')
            return False
    else:
        logger.error('[LOOP_PRAZO][ERRO] Botão "Movimentar processos" não encontrado')
        return False


def _ciclo1_retornar_lista(driver: WebDriver) -> None:
    """Retorna para lista de processos e ajusta navegação."""
    url_lista = "https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos"
    driver.get(url_lista)
    print('[LOOP_PRAZO] Retornou para a lista de processos.')

    # Ajustar zoom e aguardar carregamento
    driver.execute_script("document.body.style.zoom='75%'")
    time.sleep(2.5)

    # Simular Alt+Seta Esquerda para voltar à página anterior
    try:
        print("[LOOP_PRAZO] Simulando Alt+Seta Esquerda para voltar à página anterior...")
        actions = ActionChains(driver)
        actions.key_down(Keys.ALT).send_keys(Keys.ARROW_LEFT).key_up(Keys.ALT).perform()
        print("[LOOP_PRAZO] Comando de navegação para trás enviado com sucesso")
        time.sleep(1.5)
    except Exception as e:
        print(f"[LOOP_PRAZO][ERRO] Falha ao simular Alt+Seta Esquerda: {e}")
        # Alternativa usando JavaScript para voltar à página anterior
        try:
            driver.execute_script("window.history.go(-1)")
            print("[LOOP_PRAZO] Usado JavaScript para voltar à página anterior")
            time.sleep(1.5)
        except Exception as js_error:
            print(f"[LOOP_PRAZO][ERRO] Falha na alternativa JavaScript: {js_error}")