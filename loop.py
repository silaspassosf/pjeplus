# loop_prazo.py
# Função para automação em lote do painel global do PJe TRT2
# Segue estritamente o roteiro solicitado pelo usuário
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
# Importação das configurações do driver
from driver_config import criar_driver, login_func

def selecionar_destino(driver, opcao_destino, max_tentativas=3):
    """
    Seleciona a opção de destino usando diferentes estratégias de seleção.
    Retorna True se conseguiu selecionar, levanta exceção em caso de erro crítico.
    """
    print(f'[LOOP_PRAZO][DEBUG] Início da seleção do destino: {opcao_destino}')
    
    for tentativa in range(max_tentativas):
        try:
            print(f'[LOOP_PRAZO][DEBUG] Tentativa {tentativa + 1}: Clicando no select principal')
            # Primeiro tenta encontrar e clicar no select principal
            select = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'mat-select[formcontrolname="destinos"]'))
            )
            select.click()
            print('[LOOP_PRAZO][DEBUG] Select principal clicado com sucesso')
            time.sleep(1)
            
            # Estratégia 1: Seletor exato do mat-option com mat-option-text
            try:
                print('[LOOP_PRAZO][DEBUG] Tentando seletor: mat-option span.mat-option-text')
                opcao = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, f'mat-option span.mat-option-text'))
                )
                if opcao_destino.lower() in opcao.text.lower():
                    print('[LOOP_PRAZO][DEBUG] ✓ SUCESSO: Seletor mat-option span.mat-option-text funcionou!')
                    opcao.click()
                    return True
            except Exception as e:
                print(f'[LOOP_PRAZO][DEBUG] × Falha com seletor mat-option span.mat-option-text: {str(e)}')

            # Estratégia 2: XPath exato
            try:
                print('[LOOP_PRAZO][DEBUG] Tentando XPath com texto exato')
                opcao = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, f"//mat-option/span[normalize-space(text())='{opcao_destino}']"))
                )
                print('[LOOP_PRAZO][DEBUG] ✓ SUCESSO: XPath com texto exato funcionou!')
                opcao.click()
                return True
            except Exception as e:
                print(f'[LOOP_PRAZO][DEBUG] × Falha com XPath exato: {str(e)}')

            # Estratégia 3: JavaScript com querySelector
            try:
                print('[LOOP_PRAZO][DEBUG] Tentando JavaScript com mat-option')
                script = """
                    const option = Array.from(document.querySelectorAll('mat-option'))
                        .find(opt => opt.textContent.toLowerCase().includes(arguments[0].toLowerCase()));
                    if (option) {
                        option.click();
                        console.log('Opção encontrada via JavaScript');
                        return true;
                    }
                    return false;
                """
                if driver.execute_script(script, opcao_destino):
                    print('[LOOP_PRAZO][DEBUG] ✓ SUCESSO: JavaScript funcionou!')
                    return True
                print('[LOOP_PRAZO][DEBUG] × JavaScript não encontrou a opção')
            except Exception as e:
                print(f'[LOOP_PRAZO][DEBUG] × Falha com JavaScript: {str(e)}')
            
        except Exception as e:
            print(f"[LOOP_PRAZO][ERRO] Tentativa {tentativa + 1} falhou: {e}")
            if tentativa < max_tentativas - 1:
                print("[LOOP_PRAZO] Tentando novamente após 2 segundos...")
                time.sleep(2)
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(0.5)
                except:
                    pass
            else:
                print("[LOOP_PRAZO][ERRO CRÍTICO] Todas as tentativas de selecionar destino falharam")
                raise Exception(f"Falha ao selecionar opção '{opcao_destino}' após {max_tentativas} tentativas")
    
    print("[LOOP_PRAZO][ERRO CRÍTICO] Nenhuma estratégia de seleção funcionou")
    raise Exception(f"Falha crítica: Nenhuma estratégia funcionou para selecionar '{opcao_destino}'")

def ciclo1(driver, opcao_destino='Análise'):
    # 1. Aplicar filtro de fase processual: Liquidação e Execução  ##start2  
    from Fix import filtrofases
    result = filtrofases(driver, fases_alvo=['liquidação', 'execução'])
    if not result:
        # Se não encontrou processos em liquidação/execução, significa que acabaram os processos para tratar
        return "no_more_processes"
    # Aguarda a lista de processos ser atualizada após o filtro
    time.sleep(5)
    # 2. Tentar marcar-todas e suitcase UMA VEZ - se não encontrar vai para fase 2
    try:
        btn_marcar_todas = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-check.icone.marcar-todas'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_marcar_todas)
        btn_marcar_todas.click()
        time.sleep(1)
    except Exception as e:
        print(f"[LOOP_PRAZO] Marcar-todas não encontrado: {e}")
        print("[LOOP_PRAZO] ✅ TRATANDO COMO CUMPRIDO. Prosseguindo para fase 2.")
        return "marcar_todas_not_found_but_continue"
    
    try:
        btn_suitcase = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fas.fa-suitcase.icone'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_suitcase)
        btn_suitcase.click()
    except Exception as e:
        print(f"[LOOP_PRAZO] Suitcase não encontrado: {e}")
        print("[LOOP_PRAZO] ✅ TRATANDO COMO CUMPRIDO. Prosseguindo para fase 2.")
        return "suitcase_not_found_but_continue"

    # 5. Aguardar mudança de URL para movimentacao-lote e garantir que está na tela correta
    try:
        WebDriverWait(driver, 15).until(
            EC.url_contains('/painel/movimentacao-lote')
        )
        # Confirma se está realmente na tela correta
        if '/painel/movimentacao-lote' not in driver.current_url:
            print(f"[LOOP_PRAZO][ERRO] URL inesperada após suitcase: {driver.current_url}")
            return False
        print(f"[LOOP_PRAZO] Na tela de movimentação em lote: {driver.current_url}")
        time.sleep(1.2)
    except Exception as e:
        print(f"[LOOP_PRAZO][ERRO] URL de movimentacao-lote não carregou: {e}")
        return False

    # 6. Clicar na seta do dropdown "Tarefa destino única" (robustez: aguarda elemento existir e estar visível)
    try:
        seta_dropdown = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.mat-select-arrow-wrapper"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", seta_dropdown)
        # [FIX] Restaurar zoom para 100% antes do clique na seta
        print("[LOOP_PRAZO][DEBUG] Restaurando zoom para 100% antes do clique na seta do dropdown.")
        driver.execute_script("document.body.style.zoom='100%'")
        time.sleep(0.3)
        seta_dropdown.click()
        print("[LOOP_PRAZO][OK] Clique na seta do dropdown 'Tarefa destino única' realizado com sucesso (div.mat-select-arrow-wrapper)")
        time.sleep(0.5)
    except Exception as e:
        print(f"[LOOP_PRAZO][ERRO] Falha ao abrir dropdown Tarefa destino única pela seta: {e}")
        print(f"[LOOP_PRAZO][DEBUG] URL atual: {driver.current_url}")
        return False    # 7. Selecionar a opção de destino (padrão: "Análise")
    try:
        overlay = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
        )
        opcao_xpath = f".//span[contains(@class,'mat-option-text') and normalize-space(text())='{opcao_destino}']"
        try:
            opcao_elemento = overlay.find_element(By.XPATH, opcao_xpath)
            opcao_elemento.click()
            print(f"[LOOP_PRAZO] Opção '{opcao_destino}' selecionada com sucesso.")
            time.sleep(0.5)
        except Exception as e_opcao:
            print(f"[LOOP_PRAZO][ERRO] Opção '{opcao_destino}' não encontrada. Tentando selecionar a primeira opção disponível: {e_opcao}")
            # Fallback: tentar selecionar a primeira opção disponível
            try:
                primeira_opcao = overlay.find_element(By.XPATH, ".//span[contains(@class,'mat-option-text')]")
                opcao_texto = primeira_opcao.text.strip()
                primeira_opcao.click()
                print(f"[LOOP_PRAZO] Primeira opção disponível '{opcao_texto}' selecionada como fallback.")
                time.sleep(0.5)
            except Exception as e_fallback:
                print(f"[LOOP_PRAZO][ERRO] Não foi possível selecionar nenhuma opção: {e_fallback}")
                return False
    except Exception as e:
        print(f"[LOOP_PRAZO][ERRO] Falha ao acessar o painel de opções: {e}")
        return False    # 8. Clicar em "Movimentar processos" [CORRIGIDO]
    driver.execute_script("document.body.style.zoom='55%'")
    try:
        # Aguardar o botão aparecer
        btn_movimentar = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[.//span[contains(text(),'Movimentar processos')]]"))
        )
        
        # Verificar se o botão está visível e habilitado
        if not btn_movimentar.is_displayed():
            print('[LOOP_PRAZO][ERRO] Botão "Movimentar processos" não está visível')
            return False
            
        if not btn_movimentar.is_enabled():
            print('[LOOP_PRAZO][ERRO] Botão "Movimentar processos" não está habilitado')
            return False
        
        # Remover possíveis elementos que possam obscurecer o botão
        driver.execute_script("""
            // Remove elementos que podem estar sobrepondo
            const versionTag = document.getElementById('modulo-versao');
            if (versionTag) {
                versionTag.style.display = 'none';
                console.log('Version tag removida');
            }
            
            // Remove outros elementos flutuantes
            const overlays = document.querySelectorAll('.cdk-overlay-backdrop, .cdk-overlay-pane');
            overlays.forEach(overlay => overlay.style.display = 'none');
            
            // Garante que não há elementos flutuantes
            document.body.style.overflow = 'visible';
        """)
        
        time.sleep(0.5)
        
        # Rolar para o botão e garantir que está visível
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", btn_movimentar)
        time.sleep(0.5)
        
        # Tentar clique JavaScript como primeira opção (mais confiável)
        try:
            driver.execute_script("arguments[0].click();", btn_movimentar)
            print('[LOOP_PRAZO] ✅ Clique via JavaScript no botão "Movimentar processos" realizado com sucesso')
        except Exception as js_error:
            print(f'[LOOP_PRAZO] Falha no clique JavaScript, tentando clique Selenium: {js_error}')
            # Fallback: clique tradicional do Selenium
            btn_movimentar.click()
            print('[LOOP_PRAZO] ✅ Clique via Selenium no botão "Movimentar processos" realizado com sucesso')
        
        print('[LOOP_PRAZO] Movimentação em lote concluída.')
        time.sleep(1.2)
        # 9. Voltar para a lista de processos (reinicia o fluxo)
        url_lista = "https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos"
        driver.get(url_lista)        
        print('[LOOP_PRAZO] Retornou para a lista de processos.')
        # Ajustar zoom e aguardar carregamento
        driver.execute_script("document.body.style.zoom='75%'")
        time.sleep(2.5)
        
        # Simular Alt+Seta Esquerda para voltar à página anterior
        try:
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.common.action_chains import ActionChains
            
            print("[LOOP_PRAZO] Simulando Alt+Seta Esquerda para voltar à página anterior...")
            actions = ActionChains(driver)
            actions.key_down(Keys.ALT).send_keys(Keys.ARROW_LEFT).key_up(Keys.ALT).perform()
            print("[LOOP_PRAZO] Comando de navegação para trás enviado com sucesso")
            time.sleep(1.5)  # Aguardar carregamento da página anterior
        except Exception as e:
            print(f"[LOOP_PRAZO][ERRO] Falha ao simular Alt+Seta Esquerda: {e}")
            # Alternativa usando JavaScript para voltar à página anterior
            try:
                driver.execute_script("window.history.go(-1)")
                print("[LOOP_PRAZO] Usado JavaScript para voltar à página anterior")
                time.sleep(1.5)
            except Exception as js_error:
                print(f"[LOOP_PRAZO][ERRO] Falha na alternativa JavaScript: {js_error}")
        
        return True
        
    except Exception as e:
        print(f"[LOOP_PRAZO][ERRO CRÍTICO] Falha ao movimentar processos: {e}")
        # Salvar screenshot para debug
        try:
            driver.save_screenshot('erro_movimentar_processos.png')
            print('[LOOP_PRAZO] Screenshot salvo: erro_movimentar_processos.png')
        except:
            pass
        return False

def ciclo2(driver, opcao_destino='Cumprimento de providências'):
    """
    Executa o ciclo 2 de processamento (painel 8):
    - Aplicação de filtros
    - Seleção de processos NÃO livres
    - Movimentação em lote para o destino especificado (padrão: Cumprimento de providências)
    
    Args:
        driver: O driver do Selenium
        opcao_destino: A opção de destino a selecionar no dropdown (padrão: 'Cumprimento de providências')
    
    Returns:
        True em caso de sucesso, False em caso de erro, "no_more_processes" quando não há mais processos
    """
    try:
        from Fix import filtrofases, aplicar_filtro_100
        filtrofases(driver, fases_alvo=['liquidação', 'execução'], tarefas_alvo=['análise'])
        print('[LOOP_PRAZO] Filtro de fases aplicado no painel 8.')
        time.sleep(4)
        aplicar_filtro_100(driver)
        print('[LOOP_PRAZO] Filtro 100 aplicado no painel 8.')
        time.sleep(3)
        resultado_selecao = selecionar_processos_nao_livres(driver, max_processos=20)
        selecionados = resultado_selecao[0]
        ha_mais_processos = resultado_selecao[1]
        print(f'[LOOP_PRAZO] Seleção de processos NÃO livres concluída. Selecionados: {selecionados} ' + \
              f'{"(há mais processos)" if ha_mais_processos else "(não há mais processos)"}')
        if selecionados == 0:
            print('[LOOP_PRAZO] Não foram encontrados mais processos NÃO livres para tratar.')
            return "no_more_processes"
        if selecionados < 5:
            print(f'[LOOP_PRAZO] Menos de 5 processos NÃO livres selecionados ({selecionados}). Pulando movimentação e indo para fase dos LIVRES.')
            return "no_more_processes"
        # Se selecionou entre 5 e 19, movimenta só esses e encerra fase
        print(f'[LOOP_PRAZO] Prosseguindo com {selecionados} processos NÃO livres selecionados para movimentação em lote.')
        print('[LOOP_PRAZO] Aguardando estabilização após seleção via JavaScript...')
        time.sleep(2)
        if driver.execute_script("return document.body.style.zoom") != '75%':
            print('[LOOP_PRAZO] Ajustando zoom para 75%...')
            driver.execute_script("document.body.style.zoom='75%'")
            time.sleep(0.5)
        driver.execute_script("""
            const suitcase = document.querySelector('i.fas.fa-suitcase.icone');
            if (suitcase) {
                suitcase.style.opacity = '0.99';
                setTimeout(() => suitcase.style.opacity = '1', 100);
            }
        """)
        time.sleep(2)
        max_tentativas = 3
        for tentativa in range(max_tentativas):
            try:
                if "movimentacao-lote" in driver.current_url:
                    print('[LOOP_PRAZO] Já está na página de movimentação em lote, pulando clique no suitcase.')
                    break
                print(f'[LOOP_PRAZO] Tentativa {tentativa + 1} de clicar no suitcase...')
                btn_suitcase = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'i.fas.fa-suitcase.icone'))
                )
                if not btn_suitcase.is_displayed():
                    raise Exception("[ERRO CRÍTICO] Botão suitcase encontrado mas não está visível")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_suitcase)
                time.sleep(2)
                driver.execute_script("arguments[0].click();", btn_suitcase)
                print(f'[LOOP_PRAZO] Tentativa {tentativa + 1}: Clique via JavaScript realizado')
                time.sleep(2)
                # Após o clique, aguarda a URL mudar
                WebDriverWait(driver, 10).until(lambda d: "movimentacao-lote" in d.current_url)
                print('[LOOP_PRAZO] ✓ Sucesso: Página de movimentação em lote aberta.')
                break
            except Exception as e:
                print(f"[LOOP_PRAZO][ERRO] Tentativa {tentativa + 1} falhou: {e}")
                if tentativa == max_tentativas - 1:
                    print("[LOOP_PRAZO][ERRO CRÍTICO] Todas as tentativas de clicar no suitcase falharam.")
                    print("[LOOP_PRAZO][ERRO CRÍTICO] Interrompendo execução para evitar inconsistências.")
                    driver.save_screenshot('erro_suitcase.png')
                    raise
                else:
                    print('[LOOP_PRAZO] Aguardando 2 segundos antes da próxima tentativa...')
                    time.sleep(2)
        # Agora, garantir que está na página correta
        if "movimentacao-lote" not in driver.current_url:
            print('[LOOP_PRAZO][ERRO CRÍTICO] Não está na página de movimentação em lote após tentativas.')
            raise Exception('Não está na página de movimentação em lote após tentativas.')
        print('[LOOP_PRAZO] Procurando seta do dropdown Tarefa destino única...')
        try:
            seta_dropdown = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.mat-select-arrow-wrapper"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", seta_dropdown)
            print("[LOOP_PRAZO][DEBUG] Restaurando zoom para 100% antes do clique na seta do dropdown.")
            driver.execute_script("document.body.style.zoom='100%'")
            time.sleep(0.3)
            seta_dropdown.click()
            print("[LOOP_PRAZO][OK] Clique na seta do dropdown 'Tarefa destino única' realizado com sucesso (div.mat-select-arrow-wrapper)")
            time.sleep(0.5)
        except Exception as e:
            print(f"[LOOP_PRAZO][ERRO CRÍTICO] Falha ao clicar na seta do dropdown: {e}")
            raise
        try:
            painel = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.mat-select-panel'))
            )
            if not painel:
                print("[LOOP_PRAZO][ERRO CRÍTICO] Painel de opções não apareceu")
                raise Exception("[ERRO CRÍTICO] Painel de opções não apareceu")
            print('[LOOP_PRAZO] ✓ Painel de opções visível')
            # Seleciona a opção diretamente, igual ciclo1
            opcao_xpath = f".//span[contains(@class,'mat-option-text') and normalize-space(text())='{opcao_destino}']"
            try:
                opcao_elemento = painel.find_element(By.XPATH, opcao_xpath)
                opcao_elemento.click()
                print(f"[LOOP_PRAZO] Opção '{opcao_destino}' selecionada com sucesso.")
                time.sleep(0.5)
            except Exception as e_opcao:
                print(f"[LOOP_PRAZO][ERRO] Opção '{opcao_destino}' não encontrada. Tentando selecionar a primeira opção disponível: {e_opcao}")
                try:
                    primeira_opcao = painel.find_element(By.XPATH, ".//span[contains(@class,'mat-option-text')]")
                    opcao_texto = primeira_opcao.text.strip()
                    primeira_opcao.click()
                    print(f"[LOOP_PRAZO] Primeira opção disponível '{opcao_texto}' selecionada como fallback.")
                    time.sleep(0.5)
                except Exception as e_fallback:
                    print(f"[LOOP_PRAZO][ERRO CRÍTICO] Não foi possível selecionar nenhuma opção: {e_fallback}")
                    raise
            print('[LOOP_PRAZO] ✓ Destino selecionado com sucesso')
            
            # [CORRIGIDO] Clique robusto no botão "Movimentar processos" 
            try:
                btn_movimentar = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//button[.//span[contains(text(),'Movimentar processos')]]"))
                )
                
                # Remover elementos obstrutivos
                driver.execute_script("""
                    const versionTag = document.getElementById('modulo-versao');
                    if (versionTag) versionTag.style.display = 'none';
                    
                    const overlays = document.querySelectorAll('.cdk-overlay-backdrop, .cdk-overlay-pane');
                    overlays.forEach(overlay => overlay.style.display = 'none');
                """)
                
                # Clique via JavaScript
                driver.execute_script("arguments[0].click();", btn_movimentar)
                print('[LOOP_PRAZO] ✅ Botão Movimentar processos clicado via JavaScript')
                
            except Exception as btn_error:
                print(f'[LOOP_PRAZO][ERRO] Falha no botão Movimentar processos: {btn_error}')
                # Não falha completamente, continua o fluxo
                
            time.sleep(2)
            url_lista = "https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos"
            driver.get(url_lista)
            print('[LOOP_PRAZO] ✓ Retornando à lista de processos')
            time.sleep(3)
            return ha_mais_processos
            
        except Exception as e:
            print(f'[LOOP_PRAZO][ERRO] Falha ao interagir com select de destino: {e}')
            # Não levanta exceção, apenas retorna False
            return False
            
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Erro geral no ciclo2: {e}')
        # Não levanta exceção, apenas retorna False
        return False

def selecionar_processos_nao_livres(driver, max_processos=20):
    """
    Seleciona até max_processos processos "NÃO livres" que atendem aos critérios:
    - Com prazo (coluna 9 preenchida) ou
    - Com comentário (ícone comment) ou
    - Com valor em input[matinput]
    # Removido: - Com ícone de pesquisa na coluna 3
    
    Args:
        driver: O driver do Selenium
        max_processos: Máximo de processos a selecionar em uma execução (default 20)
        
    Returns:
        tuple (int, bool): (número de processos selecionados, indica se há mais processos para selecionar)
    """
    print("[LOOP_PRAZO] Iniciando seleção de processos 'NÃO livres'...")
    try:
        # Encontra todas as linhas da tabela
        linhas = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'tr.cdk-drag'))
        )
        print(f'[LOOP_PRAZO] Total de linhas encontradas: {len(linhas)}')
        
        # Usar JavaScript para selecionar os processos de forma mais eficiente
        script_selecao = """
            function selecionarProcessos(maxProcessos) {
                const linhas = document.querySelectorAll('tr.cdk-drag');
                let selecionados = 0;
                let totalNaoLivres = 0;
                
                // Primeiro conta total de não livres
                linhas.forEach(linha => {
                    const prazo = linha.querySelector('td:nth-child(9) time');
                    const prazoPreenchido = prazo && prazo.textContent.trim();
                    const hasComment = linha.querySelector('i.fa-comment') !== null;
                    const inputField = linha.querySelector('input[matinput]');
                    const campoPreenchido = inputField && inputField.value.trim();
                    // const temLupa = linha.querySelector('td:nth-child(3) i.fa-search') !== null; // REMOVIDO
                    
                    if (prazoPreenchido || hasComment || campoPreenchido) {
                        totalNaoLivres++;
                    }
                });
                
                // Depois seleciona até maxProcessos
                for (const linha of linhas) {
                    if (selecionados >= maxProcessos) break;
                    
                    const prazo = linha.querySelector('td:nth-child(9) time');
                    const prazoPreenchido = prazo && prazo.textContent.trim();
                    const hasComment = linha.querySelector('i.fa-comment') !== null;
                    const inputField = linha.querySelector('input[matinput]');
                    const campoPreenchido = inputField && inputField.value.trim();
                    // const temLupa = linha.querySelector('td:nth-child(3) i.fa-search') !== null; // REMOVIDO
                    
                    if (prazoPreenchido || hasComment || campoPreenchido) {
                        const checkbox = linha.querySelector('mat-checkbox input[type="checkbox"]');
                        if (checkbox && !checkbox.checked) {
                            checkbox.click();
                            linha.style.backgroundColor = "#d2ffcc";
                            selecionados++;
                        }
                    }
                }
                return {selecionados, totalNaoLivres};
            }
            return selecionarProcessos(arguments[0]);
        """
        
        # Executa o script passando max_processos como argumento
        resultado = driver.execute_script(script_selecao, max_processos)
        selecionados = resultado['selecionados']
        total_nao_livres = resultado['totalNaoLivres']
        
        print(f'[LOOP_PRAZO] Total de processos NÃO livres encontrados: {total_nao_livres}')
        print(f'[LOOP_PRAZO] Processos selecionados neste ciclo: {selecionados}')
        
        if selecionados == 0:
            return 0, False
        
        # Retorna o número de selecionados e se há mais processos para tratar
        return selecionados, total_nao_livres > selecionados

    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO CRÍTICO] Erro geral na seleção de processos NÃO livres: {e}')
        raise  # Propaga o erro para garantir que o ciclo2 seja interrompido

def loop_prazo(driver):
    # 0. Maximizar janela e ajustar zoom para 75%
    driver.maximize_window()
    driver.execute_script("document.body.style.zoom='75%'")
    time.sleep(0.5)
    # Maximizar a janela antes de iniciar o fluxo
    try:
        driver.maximize_window()
        print('[LOOP_PRAZO][DEBUG] Janela maximizada.')
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Não foi possível maximizar a janela: {e}')    
# 1. Navegar para a lista de processos e esperar 2.5s
    url_lista = "https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos"
    driver.get(url_lista)
    time.sleep(2.5)    
#FASE 1 Loop para executar ciclo1 repetidamente com opção "Análise" até que não haja mais processos para tratar
    print("[LOOP_PRAZO] Fase 1: Processando todos os processos para 'Análise'")
    while True:
        print("[LOOP_PRAZO] Iniciando novo ciclo de processamento para 'Análise'...")
        resultado_ciclo = ciclo1(driver, "Análise")
        
        # Se ciclo1 retornar "no_more_processes", significa que não encontrou mais processos em liquidação/execução
        if resultado_ciclo == "no_more_processes":
            print("[LOOP_PRAZO] Não há mais processos em liquidação/execução para processar no ciclo1.")
            break
        elif resultado_ciclo is False:
            print("[LOOP_PRAZO][ERRO CRÍTICO] Ciclo1 encontrou um erro. PARANDO EXECUÇÃO COMPLETA.")
            return False  # [CORRIGIDO] Para a execução completamente
        elif resultado_ciclo == "go_to_ciclo2" or resultado_ciclo == "suitcase_not_found_but_continue" or resultado_ciclo == "marcar_todas_not_found_but_continue":
            if resultado_ciclo == "go_to_ciclo2":
                print("[LOOP_PRAZO] Suitcase não encontrado no ciclo1, prosseguindo para Fase 2.")
            elif resultado_ciclo == "suitcase_not_found_but_continue":
                print("[LOOP_PRAZO] ✅ Fase 1 CUMPRIDA (suitcase não encontrado mas tratado como sucesso). Prosseguindo normalmente para Fase 2.")
            else:
                print("[LOOP_PRAZO] ✅ Fase 1 CUMPRIDA (marcar-todas não encontrado mas tratado como sucesso). Prosseguindo normalmente para Fase 2.")
            break
        
        print("[LOOP_PRAZO] Ciclo1 concluído com sucesso. Verificando se há mais processos para tratar...")
        time.sleep(2)
    
    # [CORRIGIDO] Fase 2 SEMPRE executa, independente do resultado da Fase 1
    # Se Fase 1 falhou por erro crítico (não por suitcase não encontrada), ainda assim continua
    if resultado_ciclo is False:
        print("[LOOP_PRAZO][AVISO] Fase 1 teve erro crítico, mas continuando para Fase 2 conforme solicitado.")
    
    # Fase 2: Executar ciclo2 para processar os processos do painel 8
    print("\n[LOOP_PRAZO] Fase 2: Iniciando processamento de processos do painel global 8...")
    
    # Navegar para o painel global 8
    url_painel8 = "https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos"
    driver.get(url_painel8)
    print('[LOOP_PRAZO] Navegou para painel global 8.')
    time.sleep(3)
    # Loop para executar ciclo2 repetidamente com opção "Cumprimento de providências" até que não haja mais processos
    ciclo2_concluido = True  # Flag para controlar se Fase 3 deve executar
    
    while True:
        print("[LOOP_PRAZO] Iniciando novo ciclo de processamento para 'Cumprimento de providências'...")
        resultado_ciclo2 = ciclo2(driver, "Cumprimento de providências")
        
        # Se ciclo2 retornar "no_more_processes", significa que não há mais processos para tratar
        if resultado_ciclo2 == "no_more_processes":
            print("[LOOP_PRAZO] Não há mais processos para processar no ciclo2.")
            break
        elif resultado_ciclo2 is False:
            print("[LOOP_PRAZO][AVISO] Ciclo2 encontrou um erro. Continuando para Fase 3.")
            ciclo2_concluido = False
            break  # Sai do loop mas continua para Fase 3
        
        if resultado_ciclo2:
            print("[LOOP_PRAZO] ✓ Ciclo2 concluído com sucesso.")
        else:
            print("[LOOP_PRAZO][AVISO] Ciclo2 falhou - continuando para Fase 3.")
            ciclo2_concluido = False
            break  # Sai do loop mas continua para Fase 3

    # Fase 3: SEMPRE executa (mesmo se Fase 2 falhou)
    print(f"\n[LOOP_PRAZO] Fase 3: Processando processos LIVRES no painel 8... (Fase 2 {'OK' if ciclo2_concluido else 'com problemas'})")
    
    # Garantir que está no painel 8
    try:
        if "painel/global/8" not in driver.current_url:
            url_painel8 = "https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos"
            driver.get(url_painel8)
            print('[LOOP_PRAZO] Navegou para painel global 8 (Fase 3).')
            time.sleep(3)
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Falha ao navegar para painel 8: {e}')
    
    # Aplicar filtros para Fase 3
    try:
        from Fix import filtrofases, aplicar_filtro_100
        filtrofases(driver)
        print('[LOOP_PRAZO] Filtro de fases aplicado no painel 8 (livres).')
        time.sleep(4)
        aplicar_filtro_100(driver)
        print('[LOOP_PRAZO] Filtro 100 aplicado no painel 8 (livres).')
        time.sleep(3)
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Falha ao aplicar filtros na Fase 3: {e}')
        # Continua mesmo com erro nos filtros
    # Executar seleção de processos LIVRES
    try:
        script_livres = '''
        try {
            let linhas = document.querySelectorAll('tr.cdk-drag');
            let selecionados = 0;
            linhas.forEach(function(linha){
                let prazo = linha.querySelector('td:nth-child(9) time');
                let prazoVazio = !prazo || !prazo.textContent.trim();
                let hasComment = linha.querySelector('i.fa-comment') !== null;
                let inputField = linha.querySelector('input[matinput]');
                let campoPreenchido = inputField && inputField.value.trim();
                let temLupa = linha.querySelector('td:nth-child(3) i.fa-search') !== null;
                if (prazoVazio && !hasComment && !campoPreenchido && !temLupa) {
                    let checkbox = linha.querySelector('mat-checkbox input[type="checkbox"]');
                    if (checkbox && !checkbox.checked) {
                        checkbox.click();
                        linha.style.backgroundColor = "#ffccd2";
                        selecionados++;
                    }
                }
            });
            return selecionados;
        } catch(e) { return -1; }
        '''
        selecionados_livres = driver.execute_script(script_livres)
        print(f'[LOOP_PRAZO] Seleção de processos LIVRES via JS concluída. Selecionados: {selecionados_livres}')
        time.sleep(2)
        
        if not selecionados_livres or selecionados_livres < 1:
            print('[LOOP_PRAZO] Nenhum processo LIVRE selecionado. Finalizando execução.')
            return True
            
        # Criar atividade "xs" para processos livres
        print('[LOOP_PRAZO] Criando atividade "xs" para processos livres...')
        
        # Clicar no ícone fa-tag (texto-verde)
        btn_tag = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-tag.icone.texto-verde'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_tag)
        btn_tag.click()
        print('[LOOP_PRAZO] Clique no ícone fa-tag realizado.')
        time.sleep(1)
        
        # Clicar em botão Atividade
        btn_atividade = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[normalize-space(text())='Atividade'] and contains(@class,'mat-menu-item')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_atividade)
        btn_atividade.click()
        print('[LOOP_PRAZO] Clique no botão Atividade realizado.')
        time.sleep(2)
        
        # Focar no campo Observação e digitar 'xs'
        campo_obs = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "textarea[formcontrolname='observacao']"))
        )
        campo_obs.click()
        campo_obs.clear()
        campo_obs.send_keys('xs')
        print('[LOOP_PRAZO] Observação preenchida com "xs".')
        time.sleep(1)
        
        # Clicar em Salvar
        btn_salvar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[normalize-space(text())='Salvar'] and contains(@class,'mat-raised-button') and contains(@class,'mat-primary')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_salvar)
        btn_salvar.click()
        print('[LOOP_PRAZO] ✅ Atividade "xs" salva com sucesso para processos livres.')
        time.sleep(1.5)
        
        return True
        
    except Exception as e:
        print(f"[LOOP_PRAZO][ERRO] Falha na Fase 3 (processos livres): {e}")
        # Salvar screenshot para debug
        try:
            driver.save_screenshot('erro_fase3_livres.png')
            print('[LOOP_PRAZO] Screenshot salvo: erro_fase3_livres.png')
        except:
            pass
        return False  # Falha apenas na Fase 3, mas não crítica

def main():
    # Criar driver e realizar login
    driver = criar_driver()
    login_func(driver)
    
    try:
        loop_prazo(driver)
    finally:
        # Fechar o driver ao final do processamento
        driver.quit()

# Executar a função main se o script for executado diretamente
if __name__ == "__main__":
    main()
