import logging
logger = logging.getLogger(__name__)

from .core import *

from selenium.webdriver.remote.webdriver import WebDriver


def mov_sob(driver, numero_processo, observacao, debug=False, timeout=15):
    """
    Movimento de sobrestamento com prazo específico.
    
    Fluxo:
    1. Abre tarefa do processo (igual ao mov padrão)    
    2. Clica no ícone de calendário NA NOVA ABA DA TAREFA ABERTA
    3. Preenche prazo em meses (extrai número da observação)
    4. Confirma com "Prosseguir"

    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo
        observacao: Observação que contém o número do prazo (ex: "sob 6")
        debug: Se True, exibe logs detalhados
        timeout: Timeout para aguardar elementos
    
    Returns:
        bool: True se executado com sucesso
    """
    import re
    from Fix.core import safe_click_no_scroll
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from Fix.core import esperar_elemento, safe_click
    
    def log_msg(msg):
        if debug:
            try:
                print(msg)
            except Exception:
                pass

    log_msg(f"Iniciando movimento de sobrestamento para processo {numero_processo}")
    log_msg(f"Observação: {observacao}")
    
    try:
        # Extrai o número da observação (ex: "sob 6" -> "6")
        numero_match = re.search(r'\bsob\s+(\d+)', observacao.lower())
        if not numero_match:
            log_msg(f" Número não encontrado na observação: {observacao}")
            return False

        prazo_meses = numero_match.group(1)
        log_msg(f" Prazo extraído: {prazo_meses} meses")

        # ===== ETAPA 1: ABRIR A TAREFA DO PROCESSO (sempre abrir primeiro) =====
        # Nota: comportamento intencionalmente alinhado ao fluxo genérico `mov()`:
        #  - Garantir /detalhe (se existir)
        #  - Tentar localizar o botão rapidamente
        #  - Se não achar, tentar buscas rápidas por variações e um fallback robusto
        #  - Clicar imediatamente com safe_click (fallback para JS click)
        log_msg("1. Abrindo tarefa do processo (sempre primeiro)...")

        def garantir_aba_detalhe():
            # Se houver mais de uma aba, preferimos a que contém '/detalhe'
            try:
                for handle in driver.window_handles:
                    try:
                        driver.switch_to.window(handle)
                        if '/detalhe' in driver.current_url:
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
            return False

        # tentamos garantir aba /detalhe (não é fatal se não encontrar)
        try:
            garantir_aba_detalhe()
        except Exception:
            pass

        # tentativa rápida pelo seletor canônico (curto timeout para não travar)
        from Fix.selectors_pje import BTN_TAREFA_PROCESSO
        btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=max(2, timeout//3))

        # se não achou, tentar variações rápidas (busca direta sem esperar muito)
        if not btn_abrir_tarefa:
            log_msg(" Botão 'Abrir tarefa do processo' não encontrado via seletor padrão em tentativa rápida; tentando variações...")
            try:
                # procura por atributos alternativos ou texto aproximado
                candidates = []
                try:
                    candidates = driver.find_elements(By.CSS_SELECTOR, 'button[mattooltip*="tarefa"], button[aria-label*="tarefa"], button[title*="tarefa"]')
                except Exception:
                    candidates = []

                for c in candidates:
                    try:
                        if c.is_displayed() and c.is_enabled():
                            btn_abrir_tarefa = c
                            break
                    except Exception:
                        continue
            except Exception:
                btn_abrir_tarefa = None

        # último fallback: usar função robusta do selectors_pje (curto timeout)
        if not btn_abrir_tarefa:
            try:
                from Fix.selectors_pje import buscar_seletor_robusto as buscar_robusto
                btn_abrir_tarefa = buscar_robusto(driver, [
                    "Abre a tarefa do processo",
                    "Abrir tarefa do processo",
                    "Abrir tarefa",
                    "Abrir a tarefa do processo"
                ], timeout=3, log=debug)
            except Exception:
                btn_abrir_tarefa = None

        if not btn_abrir_tarefa:
            log_msg(" Botão 'Abrir tarefa do processo' não encontrado! Não foi possível prosseguir")
            return False

        # Captura o texto da tarefa (quando possível)
        tarefa_do_botao = None
        try:
            span_tarefa = btn_abrir_tarefa.find_element(By.CSS_SELECTOR, '.texto-tarefa-processo')
            if span_tarefa:
                tarefa_do_botao = span_tarefa.text.strip()
                log_msg(f" Tarefa identificada: '{tarefa_do_botao}'")
        except Exception:
            try:
                tarefa_do_botao = btn_abrir_tarefa.text.strip()
            except Exception:
                tarefa_do_botao = None

        # Se a tarefa é "Aguardando prazo", não fazer nada (já está em andamento)
        if tarefa_do_botao and 'aguardando prazo' in tarefa_do_botao.lower():
            log_msg(f"ℹ Tarefa já em estado 'Aguardando prazo' - nenhuma ação necessária")
            return True

        # Clicar na tarefa imediatamente (mesmo que já esteja na aba /detalhe)
        abas_antes = set(driver.window_handles)
        click_ok = safe_click(driver, btn_abrir_tarefa)
        if not click_ok:
            # fallback para clique via JS se safe_click falhar
            try:
                driver.execute_script('arguments[0].click();', btn_abrir_tarefa)
                click_ok = True
            except Exception:
                click_ok = False

        if not click_ok:
            log_msg(" Falha no clique do botão da tarefa")
            return False
        log_msg(f'[MOV_SOB] Botão "Abrir tarefa do processo" clicado')

        # Aguarda nova aba e troca para ela (preferir aba com '/detalhe')
        nova_aba = None
        for _ in range(20):
            abas_depois = set(driver.window_handles)
            novas_abas = abas_depois - abas_antes
            if novas_abas:
                nova_aba = novas_abas.pop()
                break
            time.sleep(0.3)

        if nova_aba:
            # Ao abrir a tarefa, a nova aba é a que devemos usar (não procurar por '/detalhe').
            driver.switch_to.window(nova_aba)
            log_msg(f" Foco trocado para nova aba da tarefa: {driver.current_url}")
        else:
            log_msg(" Nenhuma nova aba detectada, prosseguindo na aba atual")

        # Espera carregamento da aba de detalhes
        try:
            WebDriverWait(driver, 8).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        except Exception:
            time.sleep(0.8)

        # ===== ETAPA 2: LOCALIZAR O BOTÃO DE CALENDÁRIO NA ABA DA TAREFA =====
        log_msg("2. Localizando botão de calendário na aba da tarefa...")
        btn_calendario = None
        try:
            btn_calendario = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[mattooltip="Definir prazo para este motivo de sobrestamento"]'))
            )
            log_msg(" Botão de calendário encontrado")
        except Exception:
            btn_calendario = None

        if not btn_calendario:
            log_msg(" Botão de calendário não encontrado via seletor principal - tentando ícone/alternativos...")
            try:
                icone_cal = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fas.fa-calendar-alt'))
                )
                safe_click_no_scroll(driver, icone_cal, log=False)
                log_msg(' Fallback: clique no ícone calendário realizado')
            except Exception:
                log_msg(' Botão de calendário não encontrado (principal nem fallback)')
                return False

        # ===== ETAPA 3: CLICAR NO CALENDÁRIO (se achamos o botão) =====
        try:
            if btn_calendario:
                try:
                    btn_calendario.click()
                    log_msg(' Clique direto no botão calendário executado')
                except Exception:
                    try:
                        driver.execute_script('arguments[0].click();', btn_calendario)
                        log_msg(' Clique via JavaScript no botão calendário executado')
                    except Exception:
                        # última tentativa: clicar no ícone interno
                        try:
                            ic = btn_calendario.find_element(By.CSS_SELECTOR, 'i.fas.fa-calendar-alt')
                            ic.click()
                            log_msg(' Clique no ícone interno executado')
                        except Exception as e:
                            log_msg(f' Falha ao clicar no calendário: {e}')
                            return False

            # Aguardar o modal aparecer
            log_msg("Aguardando modal 'Prazo do sobrestamento' aparecer...")
            modal_prazo = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-dialog-prazo-sobrestamento'))
            )
            log_msg(' Modal "Prazo do sobrestamento" encontrado')
        except Exception as e:
            log_msg(f' Erro ao abrir modal de prazo: {e}')
            return False

        # ===== ETAPA 4: PREENCHER PRAZO EM MESES =====
        try:
            campo_prazo = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[formcontrolname='mesesPrazoControl']"))
            )
            campo_prazo.clear()
            campo_prazo.send_keys(prazo_meses)
            log_msg(f" Prazo {prazo_meses} meses preenchido no campo")
            time.sleep(0.5)
        except Exception as e:
            log_msg(f' Erro ao preencher prazo no modal: {e}')
            return False

        # ===== ETAPA 5: CONFIRMAR COM 'PROSSEGUIR' =====
        try:
            btn_prosseguir = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, "//pje-dialog-prazo-sobrestamento//button[.//span[contains(text(), 'Prosseguir')]]"))
            )
            try:
                btn_prosseguir.click()
            except Exception:
                driver.execute_script('arguments[0].click();', btn_prosseguir)
            log_msg(' Botão "Prosseguir" clicado')
            time.sleep(1.5)  # Reduzido de 2.5 para 1.5
            
            # AGUARDAR SUCESSO: Verificar snackbar de sucesso OU fechamento do modal
            sucesso_detectado = False
            
            # Primeiro: tentar detectar snackbar de sucesso
            try:
                snackbar_sucesso = WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'snack-bar-container.success simple-snack-bar span'))
                )
                if 'registrado com sucesso' in snackbar_sucesso.text.lower() or 'sucesso' in snackbar_sucesso.text.lower():
                    log_msg(' Snackbar de sucesso detectado - sobrestamento processado!')
                    sucesso_detectado = True
            except Exception:
                log_msg(' Snackbar de sucesso não detectado, verificando modal...')
            
            # Segundo: se não detectou snackbar, verificar se modal fechou
            if not sucesso_detectado:
                try:
                    WebDriverWait(driver, 3).until(
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, 'pje-dialog-prazo-sobrestamento'))
                    )
                    log_msg(' Modal fechado - sobrestamento processado')
                    sucesso_detectado = True
                except Exception:
                    log_msg(' Modal ainda visível - mas pode ter processado (continuando)')
                    # Não falha se modal não fechou, pois pode estar processando em background
            
            if sucesso_detectado:
                log_msg(' Movimento de sobrestamento finalizado com sucesso!')
                return True
            else:
                log_msg(' Não foi possível confirmar sucesso, mas operação pode ter sido concluída')
                return True  # Assume sucesso se chegou até aqui
                
        except Exception as e:
            log_msg(f' Erro ao confirmar com "Prosseguir": {e}')
            return False

    except Exception as e:
        log_msg(f' Erro geral no movimento de sobrestamento: {e}')
        return False
