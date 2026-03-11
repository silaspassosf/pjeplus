from Fix.core import aguardar_e_clicar, esperar_elemento, safe_click, logger, esperar_url_conter, preencher_multiplos_campos
from Fix.selectors_pje import BTN_TAREFA_PROCESSO
from Fix.utils import executar_coleta_parametrizavel, inserir_link_ato_validacao
from Fix.extracao import bndt, criar_gigs
from Fix.movimento_helpers import selecionar_movimento_auto
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
import time
import logging

from typing import Optional, Tuple, Dict, List, Union, Callable
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from .wrappers_utils import executar_visibilidade_sigilosos_se_necessario
from .core import verificar_carregamento_pagina, aguardar_e_verificar_aba


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
                                driver.execute_script('arguments[0].scrollIntoView({block: "center"});', btn_conclusao)
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
                xpath = f"//button[contains(normalize-space(text()), '{conclusao_tipo}')]"
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


# ====================================================
# HELPERS PARA ATO_JUDICIAL (14 funções)
# ====================================================


def esperar_insercao_modelo(driver, timeout=8000):
    """
    Aguarda a inserção do modelo monitorando a aparição do dialog e snackbar.
    Versão simplificada baseada nos padrões do a.py - usa MutationObserver + setTimeout.
    """
    try:
        # JavaScript simplificado baseado no padrão do a.py
        js_monitor = f"""
        return new Promise((resolve) => {{
            console.log('maisPje: esperar_insercao_modelo() - iniciando com timeout {timeout}ms');

            let startTime = Date.now();
            let timeoutId = setTimeout(() => {{
                console.log('maisPje: esperar_insercao_modelo() - timeout esgotado após ' + (Date.now() - startTime) + ' ms');
                resolve(false);
            }}, {timeout});

            // Função para verificar se a inserção foi bem-sucedida
            function verificarInsercao() {{
                try {{
                    // Verifica dialog de visualização
                    let dialog = document.querySelector('pje-dialogo-visualizar-modelo');
                    let dialogVisivel = dialog && dialog.offsetParent !== null;

                    // Verifica snackbar de confirmação
                    let snackbar = document.querySelector('simple-snack-bar');
                    let snackbarVisivel = snackbar && snackbar.offsetParent !== null;

                    if (dialogVisivel && snackbarVisivel) {{
                        console.log('maisPje: esperar_insercao_modelo() - inserção confirmada');
                        clearTimeout(timeoutId);
                        resolve(true);
                        return true;
                    }}
                }} catch (e) {{
                    console.warn('maisPje: esperar_insercao_modelo() - erro na verificação:', e);
                }}
                return false;
            }}

            // Verificação inicial (se já está inserido, não precisa observar)
            if (!verificarInsercao()) {{
                // Monitora mudanças no DOM (como no a.py)
                let observer = new MutationObserver((mutations) => {{
                if (verificarInsercao()) {{
                    observer.disconnect();
                }}
            }});

            observer.observe(document.body, {{
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['style', 'class']
            }});

            // Verificação periódica como backup
            let checkInterval = setInterval(() => {{
                if (verificarInsercao()) {{
                    clearInterval(checkInterval);
                    observer.disconnect();
                }}
            }}, 500);

                // Cleanup no timeout
                setTimeout(() => {{
                    clearInterval(checkInterval);
                    observer.disconnect();
                }}, {timeout});
            }}
        }});
        """

        # Executa o JavaScript e aguarda resultado
        resultado = driver.execute_async_script(f"""
        var callback = arguments[arguments.length - 1];
        ({js_monitor}).then(callback);
        """)

        if resultado:
            print(f'[ATO][ESPERAR_MODELO] ✅ Inserção confirmada')
        else:
            print(f'[ATO][ESPERAR_MODELO] ⚠️ Timeout aguardando inserção ({timeout}ms)')

        return resultado

    except Exception as e:
        print(f'[ATO][ESPERAR_MODELO][ERRO] Falha no monitoramento: {e}')
        return False


def ato_judicial(
    driver: WebDriver,
    conclusao_tipo=None,
    modelo_nome=None,
    prazo=None,
    marcar_pec=None,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=None,
    debug=False,
    sigilo=None,
    descricao=None,  # NOVO: parâmetro para descrição
    perito=False,     # NOVO: parâmetro para ativar peritos
    Assinar=False,    # NOVO: parâmetro para ativar assinatura
    coleta_conteudo=None,  # NOVO: parâmetro para coleta de conteúdo parametrizável
    inserir_conteudo=None,  # NOVO: função opcional para inserção no editor (ex: editor_insert.inserir_link_ato_validacao)
    intimar=None,     # NOVO: parâmetro para controlar intimações automáticas
    **kwargs
):
    """
    Fluxo generalizado para qualquer ato judicial, seguindo a ordem:
    0. Coleta de conteúdo parametrizável (PRIMEIRO PASSO - na aba /detalhe)
    1. Modelo (fluxo_cls)
    2. Descrição
    3. Sigilo
    4. Intimar
    5. PEC
    6. Prazo
    7. Movimento
    8. Assinar
    9. Função extra de sigilo (NOTA: não executada aqui, deve ser feita externamente)
    
    NOVO COMPORTAMENTO DE SIGILO:
    - A função visibilidade_sigilosos não é mais executada automaticamente
    - Deve ser executada externamente após fechar a aba e estar na URL /detalhe
    - Use executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado)
    
    :return: (sucesso: bool, sigilo_ativado: bool)
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    
    try:
        # 0. PRIMEIRO: Executar coleta de conteúdo parametrizável na aba /detalhe (se especificado)
        if coleta_conteudo:
            print('[ATO][COLETA] Executando coleta de conteúdo parametrizável ANTES do fluxo principal...')
            try:
                # Verifica se está na aba /detalhe
                current_url = driver.current_url
                if '/detalhe' not in current_url:
                    print(f'[ATO][COLETA][WARN] URL atual não contém /detalhe: {current_url}')
                    print('[ATO][COLETA][WARN] Coleta deve ser executada na aba /detalhe')
                    
                # Importa a função do módulo de coleta
                
                # Se coleta_conteudo for string, converte para dict simples
                if isinstance(coleta_conteudo, str):
                    config_coleta = {'tipo': coleta_conteudo}
                else:
                    config_coleta = coleta_conteudo
                
                # Extrai parâmetros
                tipo_coleta = config_coleta.get('tipo', '')
                parametros = config_coleta.get('parametros', None)
                
                # Tenta extrair número do processo da URL atual
                try:
                    from PEC.anexos import extrair_numero_processo_da_url
                    numero_processo = extrair_numero_processo_da_url(driver)  # Passa o driver, não a URL
                    if not numero_processo:
                        print('[ATO][COLETA][WARN] Número do processo não encontrado na URL')
                        numero_processo = "PROCESSO_DESCONHECIDO"
                except Exception as e:
                    print(f'[ATO][COLETA][ERRO] Erro na extração do número do processo: {e}')
                    numero_processo = "PROCESSO_DESCONHECIDO"
                
                # Executa a coleta
                sucesso_coleta = executar_coleta_parametrizavel(
                    driver, numero_processo, tipo_coleta, parametros, debug
                )
                
                if sucesso_coleta:
                    print(f'[ATO][COLETA] ✓ Coleta de "{tipo_coleta}" executada com sucesso ANTES do fluxo!')
                else:
                    print(f'[ATO][COLETA] ⚠ Falha na coleta de "{tipo_coleta}" (mas continua o fluxo)')
                    
            except Exception as coleta_err:
                print(f'[ATO][COLETA][ERRO] Erro na coleta de conteúdo: {coleta_err}')
                print('[ATO][COLETA] Continuando com o fluxo principal mesmo com erro na coleta...')
                # Não falha o fluxo principal por erro na coleta

        print('[ATO][DEBUG] ==========================================')
        print('[ATO][DEBUG] Iniciando fluxo principal do ato judicial...')
        
        # ===== VERIFICAÇÃO DE URL ATUAL =====
        # Detecta se já estamos em /conclusao ou /minutar para pular etapas
        current_url = (driver.current_url or '').lower()
        ja_em_conclusao = '/conclusao' in current_url
        ja_em_minutar = '/minutar' in current_url
        
        if ja_em_minutar:
            print('[ATO][DEBUG] ✅ Já estamos em /minutar - pulando fluxo_cls completamente')
        elif ja_em_conclusao:
            print('[ATO][DEBUG] ✅ Já estamos em /conclusao - fluxo_cls pulará navegação inicial')
        
        # 1. Modelo (fluxo_cls) - EXECUTADO APENAS SE NÃO ESTIVER JÁ EM /minutar
        sigilo_ativado = False
        print('[ATO][DEBUG] Etapa: Modelo (fluxo_cls)')
        resultado_cls = False
        
        # Se já estamos em /minutar, pular completamente o fluxo_cls
        if ja_em_minutar:
            resultado_cls = True  # Considera sucesso pois já estamos onde precisamos
            print('[ATO][DEBUG] ✅ Pulando fluxo_cls (já em /minutar)')
        elif conclusao_tipo and modelo_nome:
            try:
                resultado_cls = fluxo_cls(driver, conclusao_tipo, forcar_iniciar_execucao=False)
                if not resultado_cls:
                    # Verificar se mesmo com falha estamos em /minuta (pode ter navegado parcialmente)
                    current_url_check = (driver.current_url or '').lower()
                    if '/minutar' in current_url_check or '/minuta' in current_url_check:
                        print('[ATO][WARN] Fluxo CLS retornou False, mas estamos em /minuta - continuando')
                        resultado_cls = True
                    else:
                        print('[ATO][ERRO] Fluxo CLS falhou e NÃO estamos em /minuta - abortando')
                        return False, False
                else:
                    print('[ATO][DEBUG] ✅ Fluxo CLS executado com sucesso')
            except Exception as e:
                print(f'[ATO][ERRO] Falha no fluxo CLS: {e}')
                return False, False
        
        # 5. PEC
        print('[ATO][DEBUG] Etapa: PEC')
        # LOGS INICIAIS DE DEBUG
        print(f'[ATO][ENTRADA] ================== INÍCIO ato_judicial ==================')
        print(f'[ATO][ENTRADA] conclusao_tipo: {conclusao_tipo!r}')
        print(f'[ATO][ENTRADA] modelo_nome: {modelo_nome!r}')
        print(f'[ATO][ENTRADA] prazo: {prazo!r}')
        print(f'[ATO][ENTRADA] marcar_pec: {marcar_pec!r}')
        print(f'[ATO][ENTRADA] movimento: {movimento!r}')
        print(f'[ATO][ENTRADA] descricao: {descricao!r}')
        print(f'[ATO][ENTRADA] sigilo: {sigilo!r}')
        print(f'[ATO][ENTRADA] intimar: {intimar!r}')
        print(f'[ATO][ENTRADA] debug: {debug!r}')
        print(f'[ATO][ENTRADA] =======================================================')
        
        # 2. Digitação do modelo e prosseguimento (padrão MaisPje/gigs-plugin.js)
        # NOTA: Só executa se fluxo_cls foi bem-sucedido OU se devemos tentar mesmo com falha
        if resultado_cls or conclusao_tipo:  # Tenta mesmo se CLS falhou
            print(f'[ATO][MODELO] Tentando preencher modelo: {modelo_nome}')
            
            try:
                from selenium.webdriver.common.by import By
                # Verifica se já estamos na tela de minuta (campo #inputFiltro existe)
                try:
                    campo_filtro_modelo = driver.find_element(By.CSS_SELECTOR, '#inputFiltro')
                    print('[ATO][MODELO] ✅ Campo #inputFiltro encontrado - já na tela de minuta')
                except:
                    print('[ATO][MODELO] ❌ Campo #inputFiltro não encontrado - não estamos na tela de minuta')
                    if not resultado_cls:
                        print('[ATO][ERRO] Fluxo CLS falhou e não estamos na tela de minuta')
                        return False, False
                    return False, False
                
                # VERIFICAÇÃO: Editor já tem conteúdo? (caso "elaborar")
                try:
                    editor = driver.find_element(By.CSS_SELECTOR, 'div.ck-content[contenteditable="true"]')
                    conteudo_editor = editor.text.strip()
                    
                    if conteudo_editor:
                        print(f'[ATO][MODELO] ⚠️ Editor já contém texto ({len(conteudo_editor)} caracteres)')
                        print(f'[ATO][MODELO]  Primeiras 100 chars: {conteudo_editor[:100]}...')
                        print('[ATO][MODELO] ⏭️ Pulando inserção de modelo - usando conteúdo existente')
                        
                        # Pular para etapa de PEC (não inserir modelo)
                        # Mas continuar o fluxo normalmente (não retornar aqui)
                        skip_modelo_insert = True
                    else:
                        print('[ATO][MODELO] Editor vazio - prosseguindo com inserção de modelo')
                        skip_modelo_insert = False
                except Exception as e:
                    print(f'[ATO][MODELO][DEBUG] Não foi possível verificar editor: {e}')
                    skip_modelo_insert = False
                
                # Se não deve pular, insere o modelo
                if not skip_modelo_insert:
                    # Preenche o modelo
                    driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
                    driver.execute_script('arguments[0].value = arguments[1];', campo_filtro_modelo, modelo_nome)
                    # Dispara eventos como no gigs-plugin.js
                    for ev in ['input', 'change', 'keyup']:
                        driver.execute_script('var evt = new Event(arguments[1], {bubbles:true}); arguments[0].dispatchEvent(evt);', campo_filtro_modelo, ev)
                    # Simula Enter
                    from selenium.webdriver.common.keys import Keys
                    campo_filtro_modelo.send_keys(Keys.ENTER)
                    print(f'[ATO][MODELO][OK] Modelo "{modelo_nome}" preenchido via JS e ENTER pressionado no filtro.')
                    
                    # Aguarda carregamento da tela após filtro
                    import time
                    time.sleep(2)
                else:
                    # Se pulou inserção, apenas aguarda um pouco
                    import time
                    time.sleep(0.5)
                
            except Exception as modelo_err:
                print(f'[ATO][MODELO][ERRO] Erro ao preencher modelo: {modelo_err}')
                return False, False
        else:
            print('[ATO][MODELO] Pulando preenchimento - fluxo CLS falhou e não há conclusao_tipo')
            return False, False
            
        # 3. Seleciona o modelo filtrado destacado (fundo amarelo)
        # NOTA: Só executa se não pulamos a inserção (skip_modelo_insert)
        if not skip_modelo_insert:
            try:
                seletor_item_filtrado = '.nodo-filtrado'
                nodo = aguardar_e_clicar(driver, seletor_item_filtrado, timeout=15)
                if not nodo:
                    print('[ATO][ERRO] Nodo do modelo não encontrado!')
                    return False, False
                print('[ATO] Clique em nodo-filtrado realizado!')

                # Aguarda modal de visualização abrir
                modal_aberto = False
                for tentativa in range(5):  # Reduzido para 5 tentativas
                    try:
                        modal = driver.find_element(By.CSS_SELECTOR, 'pje-dialogo-visualizar-modelo')
                        if modal.is_displayed():
                            modal_aberto = True
                            break
                    except:
                        pass
                    time.sleep(0.5)

                if not modal_aberto:
                    print('[ATO][WARN] Modal não abriu, tentando inserir mesmo assim...')

                # Localiza botão inserir
                seletor_btn_inserir = 'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button'
                btn_inserir = aguardar_e_clicar(driver, seletor_btn_inserir, timeout=10, retornar_elemento=True)
                if not btn_inserir:
                    print('[ATO][ERRO] Botão inserir não encontrado!')
                    return False, False

                # Insere modelo
                time.sleep(0.5)
                btn_inserir.send_keys(Keys.SPACE)
                print('[ATO][MODELO] Aguardando inserção do modelo...')
                
                sucesso_modelo = esperar_insercao_modelo(driver, timeout=8000)
                if sucesso_modelo:
                    print('[ATO][MODELO] ✅ Modelo inserido com sucesso!')
                else:
                    print('[ATO][MODELO] ⚠️ Timeout ao inserir modelo (8s), continuando...')
                
                time.sleep(1.5)

            except Exception as modelo_insert_err:
                print(f'[ATO][MODELO][ERRO] Erro ao inserir modelo: {modelo_insert_err}')
                return False, False
        else:
            print('[ATO][MODELO] ⏭️ Pulando seleção/inserção de modelo (editor já preenchido)')

        # NOVO: Hook de inserção de conteúdo (após inserir modelo, antes do Salvar)
        try:
            if inserir_conteudo:
                print('[ATO][INSERIR] Executando função de inserção de conteúdo no editor...')
                # Resolver função caso venha como string conhecida
                inserir_fn = inserir_conteudo
                if isinstance(inserir_conteudo, str):
                    try:
                        if inserir_conteudo.lower() in ('link_ato', 'link_ato_validacao'):
                            inserir_fn = inserir_link_ato_validacao
                    except Exception as _e:
                        print(f"[ATO][INSERIR][WARN] Não foi possível resolver função por string: {inserir_conteudo} -> {_e}")
                # Obter número do processo da URL
                try:
                    from PEC.anexos import extrair_numero_processo_da_url
                    numero_processo_atual = extrair_numero_processo_da_url(driver)
                    if debug and numero_processo_atual:
                        print(f"[ATO][INSERIR] Número do processo extraído da URL: {numero_processo_atual}")
                    
                    # Se for apenas ID numérico (ex: 6094959), não usar
                    # Clipboard precisa de número formatado (ex: 0010644-31.2024.5.02.0472)
                    if numero_processo_atual and numero_processo_atual.isdigit():
                        if debug:
                            print(f"[ATO][INSERIR] ID numérico detectado, ignorando para busca no clipboard")
                        numero_processo_atual = None
                        
                except Exception:
                    numero_processo_atual = None
                
                # Se conteudo_relatorio foi fornecido, tentar extrair numero_processo dele ou usar kwargs
                if 'conteudo_relatorio' in kwargs and 'numero_processo' in kwargs:
                    numero_processo_atual = kwargs.get('numero_processo', numero_processo_atual)
                    if debug:
                        print(f"[ATO][INSERIR] Usando número do processo dos kwargs: {numero_processo_atual}")
                
                # Chamar função de forma resiliente
                ok = False
                try:
                    # Tentar com todos os parâmetros incluindo conteudo_relatorio se estiver em kwargs
                    if 'conteudo_relatorio' in kwargs:
                        if debug:
                            print(f"[ATO][INSERIR] Chamando inserir_fn com conteudo_relatorio fornecido")
                        ok = inserir_fn(driver=driver, numero_processo=numero_processo_atual, conteudo_relatorio=kwargs['conteudo_relatorio'], debug=debug)
                    else:
                        ok = inserir_fn(driver=driver, numero_processo=numero_processo_atual, debug=debug)
                except TypeError:
                    try:
                        ok = inserir_fn(driver, numero_processo_atual)
                    except Exception:
                        ok = inserir_fn(driver)
                print(f"[ATO][INSERIR] Resultado da inserção: {'✓' if ok else '✗'}")
            else:
                if debug:
                    print('[ATO][INSERIR] Nenhuma função de inserção fornecida (pulando)')
        except Exception as e:
            print(f"[ATO][INSERIR][WARN] Erro ao executar inserção: {e}")

        # NOVO: Clica no botão Salvar (mat-raised-button mat-primary) e aguarda 1s para ativar aba de prazos
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        try:
            btn_salvar = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'mat-raised-button') and contains(@class, 'mat-primary') and contains(., 'Salvar') and @aria-label='Salvar']"))
            )
            safe_click(driver, btn_salvar)
            print('[ATO] Clique no botão Salvar realizado!')
            time.sleep(1)
        except Exception as e:
            print(f'[ATO][ERRO] Botão Salvar não encontrado ou não clicável: {e}')
            return False, False

        # SIGILO E INTIMAR - EXECUTADOS APÓS SALVAR O MODELO
        # 2. Sigilo (executa apenas se explicitamente True)
        sigilo_ativado = False
        if str(sigilo).lower() in ("sim", "true", "1"):
            print('[ATO][SIGILO] Etapa: Sigilo - Ativando sigilo...')
            try:
                # Localizar e clicar no toggle "Sigiloso" se estiver desativado
                toggle_sigilo = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'label.mat-slide-toggle-label'))
                )
                parent_toggle = toggle_sigilo.find_element(By.XPATH, './ancestor::mat-slide-toggle[1]')
                if not 'mat-checked' in parent_toggle.get_attribute('class'):
                    driver.execute_script("arguments[0].click();", toggle_sigilo)
                    print('[ATO][SIGILO] Toggle "Sigiloso" ativado.')
                    sigilo_ativado = True
                else:
                    print('[ATO][SIGILO] Toggle "Sigiloso" já estava ativado.')
                    sigilo_ativado = True
            except Exception as e:
                print(f'[ATO][SIGILO] Erro ao ativar sigilo: {e}')
                sigilo_ativado = False
        
        print('[ATO][DEBUG] ==========================================')
        
        # 3. Intimar (controla intimações automáticas)
        print('[ATO][DEBUG] Etapa: Intimar')
        intimar_ativado = True if intimar is None else str(intimar).lower() in ("sim", "true", "1")
        if not intimar_ativado:
            print('[ATO][INTIMAR] Desativando intimações automáticas...')
            try:
                # Ativar aba de intimações se não estiver ativa
                guia_intimacoes = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-editor-lateral div[aria-posinset="1"]'))
                )
                if guia_intimacoes.get_attribute('aria-selected') == "false":
                    guia_intimacoes.click()
                    time.sleep(0.5)
                
                # Localizar e clicar no toggle "Intimar?" se estiver ativado
                toggle_intimar = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-intimacao-automatica label.mat-slide-toggle-label'))
                )
                parent_toggle = toggle_intimar.find_element(By.XPATH, '..')
                if 'mat-checked' in parent_toggle.get_attribute('class'):
                    toggle_intimar.click()
                    print('[ATO][INTIMAR] Toggle "Intimar?" desativado.')
                else:
                    print('[ATO][INTIMAR] Toggle "Intimar?" já estava desativado.')
            except Exception as e:
                print(f'[ATO][INTIMAR] Erro ao desativar intimações: {e}')
        
        print('[ATO][DEBUG] ==========================================')

        # LOGS DETALHADOS DE FLUXO
        print(f'[ATO] Processando etapas: Descrição → PEC → Prazo → Movimento → Assinar')
        
        # 1. DESCRIÇÃO
        if descricao:
            try:
                campo_desc = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Descrição"]')
                campo_desc.clear()
                campo_desc.send_keys(descricao)
                for ev in ['input', 'change', 'keyup']:
                    driver.execute_script('var evt = new Event(arguments[1], {bubbles:true}); arguments[0].dispatchEvent(evt);', campo_desc, ev)
                if campo_desc.get_attribute('value') == descricao:
                    print(f'[ATO][DESCRICAO] Preenchida com sucesso')
                else:
                    print(f'[ATO][DESCRICAO][WARN] Valor não confere')
            except Exception as e:
                print(f'[ATO][DESCRICAO][ERRO] Falha: {e}')
        
        # 5. PEC
        if marcar_pec is not None:
            try:
                pec_checkbox = None
                pec_input = None
                
                try:
                    pec_checkbox = driver.find_element(By.CSS_SELECTOR, 'mat-checkbox[aria-label="Enviar para PEC"]')
                    pec_input = pec_checkbox.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
                except:
                    try:
                        pec_checkbox = driver.find_element(By.CSS_SELECTOR, 'div.checkbox-pec mat-checkbox')
                        pec_input = pec_checkbox.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
                    except:
                        pec_input = driver.find_element(By.CSS_SELECTOR, 'input[type="checkbox"][aria-label="Enviar para PEC"]')
                        pec_checkbox = pec_input.find_element(By.XPATH, './ancestor::mat-checkbox[1]')
                
                if not pec_checkbox or not pec_input:
                    raise Exception("Checkbox PEC não encontrado")
                
                checked = False
                try:
                    if pec_input.get_attribute('aria-checked') == 'true' or pec_input.get_attribute('checked') == 'true' or pec_input.is_selected() or 'mat-checkbox-checked' in pec_checkbox.get_attribute('class'):
                        checked = True
                except:
                    checked = False
                
                if marcar_pec and not checked:
                    driver.execute_script('arguments[0].scrollIntoView({block: "center"});', pec_checkbox)
                    time.sleep(0.2)
                    try:
                        label = pec_checkbox.find_element(By.CSS_SELECTOR, 'label.mat-checkbox-layout')
                        driver.execute_script('arguments[0].click();', label)
                    except:
                        driver.execute_script('arguments[0].click();', pec_checkbox)
                    print('[ATO][PEC] Marcado')
                    time.sleep(0.3)
                elif not marcar_pec and checked:
                    driver.execute_script('arguments[0].scrollIntoView({block: "center"});', pec_checkbox)
                    time.sleep(0.2)
                    try:
                        label = pec_checkbox.find_element(By.CSS_SELECTOR, 'label.mat-checkbox-layout')
                        driver.execute_script('arguments[0].click();', label)
                    except:
                        driver.execute_script('arguments[0].click();', pec_checkbox)
                    print('[ATO][PEC] Desmarcado')
                    time.sleep(0.3)
                    
            except Exception as e:
                print(f'[ATO][ERRO] Falha PEC: {e}')        # 4. Prazo
        if prazo is not None and intimar_ativado:
            try:
                print('[ATO][PRAZO] Preenchendo prazos...')
                preencher_prazos_destinatarios(driver, prazo, apenas_primeiro=marcar_primeiro_destinatario, perito=perito)
                
                driver.execute_script("""
                    const overlays = document.querySelectorAll('.cdk-overlay-backdrop, .mat-dialog-container, .cdk-overlay-pane');
                    overlays.forEach(overlay => {
                        if (overlay.style) overlay.style.display = 'none';
                    });
                    
                    const snackbars = document.querySelectorAll('snack-bar-container, simple-snack-bar');
                    snackbars.forEach(snack => {
                        if (snack.style) snack.style.display = 'none';
                    });
                    
                    document.body.style.overflow = 'visible';
                """)
                
                btn_gravar_prazo = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[.//span[normalize-space(text())='Gravar'] and contains(@class, 'mat-raised-button') and not(contains(@aria-label, 'movimentos'))]"))
                )
                
                if not btn_gravar_prazo.is_displayed() or not btn_gravar_prazo.is_enabled():
                    print('[ATO][PRAZO][ERRO] Botão Gravar inválido')
                    return False, False
                    
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", btn_gravar_prazo)
                time.sleep(0.5)
                
                try:
                    driver.execute_script("arguments[0].click();", btn_gravar_prazo)
                    print('[ATO][PRAZO] Gravado via JS')
                except Exception as js_error:
                    btn_gravar_prazo.click()
                    print('[ATO][PRAZO] Gravado via Selenium')
                
                time.sleep(1)
                print('[ATO][PRAZO] Concluído')
                
            except Exception as e:
                print(f'[ATO][PRAZO][ERRO] Falha: {e}')
                return False, False
               # 5. Movimento
        if movimento:
            try:
                # Decide between checkbox flow (single-token) or two-stage combobox flow (multi-stage with '/' or '-')
                if '/' in movimento or '-' in movimento:
                    try:
                        sucesso = selecionar_movimento_auto(driver, movimento)
                    except Exception as e:
                        print(f'[ATO][MOVIMENTO][ERRO] selecionar_movimento_auto exception: {e}')
                        return False, False
                    if not sucesso:
                        print('[ATO][MOVIMENTO][ERRO] selecionar_movimento_auto não conseguiu selecionar o movimento')
                        return False, False
                    print('[ATO][MOVIMENTO] Selecionado via fluxo de dois estágios (combobox)')
                else:
                    js_mov = f'''
                (function() {{
                    var tentativas = 0, abaMov = null;
                    while (tentativas < 3 && !abaMov) {{
                        var abas = Array.from(document.querySelectorAll('.mat-tab-label'));
                        abaMov = abas.find(a => a.textContent && a.textContent.normalize('NFD').replace(/[\\W_]/g, '').toLowerCase().includes('movimentos'));
                        if (abaMov && abaMov.getAttribute('aria-selected') !== 'true') {{
                            abaMov.click();
                            break;
                        }}
                        tentativas++;
                    }}
                    
                    setTimeout(function() {{
                        var textoMov = '{movimento}'.trim().toLowerCase().replace(/\\s+/g, ' ');
                        var checkboxes = Array.from(document.querySelectorAll('mat-checkbox.mat-checkbox.movimento'));
                        var selecionado = false;
                        
                        function normalizarTexto(texto) {{
                            return texto.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase().trim();
                        }}
                        
                        var termoPesquisa = normalizarTexto(textoMov);
                          
                        for (var cb of checkboxes) {{
                            try {{
                                var label = cb.querySelector('label.mat-checkbox-layout .mat-checkbox-label');
                                var labelText = label && label.textContent ? label.textContent : '';
                                var labelNorm = labelText.trim().toLowerCase().replace(/\\s+/g, ' ');
                                var labelSemAcento = normalizarTexto(labelText);
                                
                                var encontrado = labelNorm.includes(textoMov) || 
                                                labelSemAcento.includes(termoPesquisa) ||
                                                (textoMov === 'frustrada' && (labelSemAcento.includes('execucao frustrada') || labelSemAcento.includes('276'))) ||
                                                (textoMov.match(/^\\d+$/) && labelText.includes('(' + textoMov + ')'));
                                
                                if (encontrado) {{
                                    var input = cb.querySelector('input[type="checkbox"]');
                                    if (input && !input.checked) {{
                                        var inner = cb.querySelector('.mat-checkbox-inner-container');
                                        if(inner) {{
                                            inner.click();
                                        }} else {{
                                            input.click();
                                        }}
                                    }}
                                    window.selecionadoMovimento = true;
                                    window.labelSelecionadoMovimento = labelText;
                                    selecionado = true;
                                    break;
                                }}
                            }} catch (e) {{
                                console.warn('[ATO][MOVIMENTO] Erro ao processar checkbox:', e);
                            }}
                        }}
                        
                        if (!selecionado) {{
                            console.warn('[ATO][MOVIMENTO] Movimento não encontrado');
                            window.selecionadoMovimento = false;
                        }} else {{
                            console.log('[ATO][MOVIMENTO] Movimento marcado');
                        }}
                    }}, 800);
                }})();
                '''
                    driver.execute_script(js_mov)
                    time.sleep(1.5)

                    movimento_selecionado = driver.execute_script('return window.selecionadoMovimento === true;')
                    if not movimento_selecionado:
                        print('[ATO][MOVIMENTO][ERRO] Não selecionado')
                        return False, False

                    print(f'[ATO][MOVIMENTO] Selecionado: {driver.execute_script("return window.labelSelecionadoMovimento || \"desconhecido\";")}')
                
                btn_gravar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Gravar os movimentos a serem lançados']"))
                )
                btn_gravar.click()
                time.sleep(1.5)
                
                btn_sim = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'mat-button') and contains(@class, 'mat-primary') and .//span[text()='Sim']]"))
                )
                btn_sim.click()
                time.sleep(1)
                
                btn_salvar_mov = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Salvar'][color='primary']"))
                )
                btn_salvar_mov.click()
                print('[ATO][MOVIMENTO] Concluído')
                time.sleep(1)
            except Exception as e:
                print(f'[ATO][MOVIMENTO][ERRO] Falha: {e}')
                return False, False
        # 6. Assinar
        if Assinar:
            time.sleep(3)
            try:
                btn_assinar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.mat-fab[aria-label="Enviar para assinatura"]'))
                )
                btn_assinar.click()
                print('[ATO][ASSINAR] Enviado para assinatura')
                time.sleep(1)
            except Exception as e:
                print(f'[ATO][ASSINAR][ERRO] Falha: {e}')
                return False, False
        
        # 7. GIGS
        if gigs:
            try:
                current_handle = driver.current_window_handle
                abas_antes_gigs = list(driver.window_handles)
                current_url = driver.current_url
                
                if isinstance(gigs, dict):
                    dias = gigs.get('dias', '1')
                    responsavel = gigs.get('responsavel', '')
                    observacao = gigs.get('observacao', '')
                    detalhe = gigs.get('detalhe', True)
                else:
                    partes = gigs.split('/')
                    dias = partes[0] if len(partes) > 0 else '1'
                    if len(partes) >= 3:
                        responsavel = partes[1]
                        observacao = partes[2]
                    elif len(partes) == 2:
                        responsavel = ''
                        observacao = partes[1]
                    else:
                        responsavel = ''
                        observacao = ''
                    detalhe = True
                
                if detalhe:
                    import re
                    match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', current_url)
                    if match:
                        numero_processo = match.group(1)
                        url_detalhe = f'https://pje.trt2.jus.br/primeirograu/Processo/ConsultaDocumento/listView.seam?np={numero_processo}'
                        try:
                            driver.get(url_detalhe)
                            time.sleep(2)
                        except Exception as eget:
                            print(f'[ATO][GIGS][WARN] Falha navegação: {eget}')
                
                resultado_gigs = criar_gigs(driver, dias, responsavel, observacao)
                
                if resultado_gigs:
                    print('[ATO][GIGS] Criado com sucesso')
                else:
                    print('[ATO][GIGS][ERRO] Falha na criação')
                    
                try:
                    if not detalhe:
                        try:
                            driver.close()
                        except Exception as eclose:
                            print(f'[ATO][GIGS][WARN] Erro fechamento: {eclose}')
                        abas_restantes = driver.window_handles
                        if abas_restantes:
                            try:
                                driver.switch_to.window(abas_restantes[0])
                                time.sleep(0.5)
                            except Exception as eswitch:
                                print(f'[ATO][GIGS][WARN] Erro troca: {eswitch}')
                    else:
                        try:
                            if current_handle in driver.window_handles:
                                driver.switch_to.window(current_handle)
                                time.sleep(0.5)
                            else:
                                for h in driver.window_handles:
                                    try:
                                        driver.switch_to.window(h)
                                        if '/minutar' in (driver.current_url or ''):
                                            break
                                    except Exception:
                                        continue
                        except Exception as ere:
                            print(f'[ATO][GIGS][WARN] Erro retorno: {ere}')
                except Exception as epost:
                    print(f'[ATO][GIGS][WARN] Erro pós-criação: {epost}')
                    
            except Exception as gigs_err:
                print(f'[ATO][GIGS][ERRO] Exceção: {gigs_err}')
        
        print(f'[ATO] Finalizado: {conclusao_tipo}, {modelo_nome}')
        if sigilo_ativado:
            print('[ATO][SIGILO] Ativado - executar visibilidade_sigilosos em /detalhe')
            # Executar visibilidade para sigilosos após o ato judicial
            executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado, debug=debug)
        
        return True, sigilo_ativado
    except Exception as e:
        print(f'[ATO][ERRO] Falha no fluxo do ato judicial ({conclusao_tipo}, {modelo_nome}): {e}')
        try:
            driver.save_screenshot(f'erro_ato_{conclusao_tipo}_{modelo_nome}.png')
        except Exception as screen_err:
            print(f'[ATO][WARN] Falha ao salvar screenshot do erro: {screen_err}')
        # RETORNA: (falha, sigilo_nao_ativado)
        return False, False


def make_ato_wrapper(conclusao_tipo, modelo_nome, prazo=None, marcar_pec=None, movimento=None, gigs=None, marcar_primeiro_destinatario=None, descricao=None, sigilo=None, perito=False, Assinar=False, coleta_conteudo=None, inserir_conteudo=None, intimar=None):
    def wrapper(driver, debug=False, sigilo_=None, movimento_=None, descricao_=None, perito_=None, Assinar_=None, coleta_conteudo_=None, inserir_conteudo_=None, **kwargs):
        call_args = dict(
            driver=driver,
            conclusao_tipo=conclusao_tipo,
            modelo_nome=modelo_nome,
            prazo=prazo,
            marcar_pec=marcar_pec,
            movimento=movimento_ if movimento_ is not None else movimento,
            gigs=gigs,
            marcar_primeiro_destinatario=marcar_primeiro_destinatario,
            debug=debug,
            sigilo=sigilo_ if sigilo_ is not None else sigilo,
            descricao=descricao_ if descricao_ is not None else descricao,
            perito=perito_ if perito_ is not None else perito,
            Assinar=Assinar_ if Assinar_ is not None else Assinar,
            coleta_conteudo=coleta_conteudo_ if coleta_conteudo_ is not None else coleta_conteudo,
            inserir_conteudo=inserir_conteudo_ if inserir_conteudo_ is not None else inserir_conteudo,
            intimar=intimar,
        )
        # Adicionar kwargs ao call_args para propagar parametros extras (ex: conteudo_relatorio)
        call_args.update(kwargs)
        
        sucesso, sigilo_ativado = ato_judicial(**call_args)
        
        # Para compatibilidade com código existente, retorna apenas sucesso
        # mas armazena sigilo_ativado como atributo para acesso posterior
        wrapper.ultimo_sigilo_ativado = sigilo_ativado
        return sucesso
    return wrapper

# Wrappers centralizados em wrappers_ato.py
from .wrappers_ato import (
    ato_meios,
    ato_100,
    ato_crda,
    ato_crte,
    ato_bloq,
    ato_idpj,
    ato_termoE,
    ato_termoS,
    ato_edital,
    ato_sobrestamento,
    ato_prov,
    ato_180,
    ato_x90,
    ato_pesqliq_original,
    ato_pesqliq,
    ato_calc2,
    ato_meiosub,
    ato_presc,
    ato_fal,
    ato_parcela,
)

# Wrapper customizado para pesquisas com lógica especial de "Iniciar a execução"
def ato_pesquisas(driver, debug=False, gigs=None, **kwargs):
    """
    Wrapper para ato de pesquisas com lógica especial.
    Verifica e clica em 'Iniciar a execução' antes de executar o ato judicial.
    IMPORTANTE: Retorna (sucesso, sigilo_ativado) para aplicação de visibilidade posterior.
    """
    try:
        # 1. Lógica especial: Se existir botão 'Iniciar a execução', clicar antes de seguir
        try:
            from selenium.webdriver.common.by import By
            btn_iniciar = driver.find_element(By.CSS_SELECTOR, "button[aria-label*='Iniciar a execução'], button[mattooltip*='Iniciar a execução']")
            if btn_iniciar and btn_iniciar.is_displayed() and btn_iniciar.is_enabled():
                safe_click(driver, btn_iniciar)
                print('[ATO_PESQUISAS] Clique em "Iniciar a execução" realizado.')
                import time
                time.sleep(1)
        except Exception:
            print('[ATO_PESQUISAS] Botão "Iniciar a execução" não encontrado ou não clicável, seguindo fluxo normal.')
        
        # 2. Segue fluxo padrão do ato judicial com parâmetros fixos
        sucesso, sigilo_ativado = ato_judicial(
            driver,
            conclusao_tipo='BACEN',
            modelo_nome='xsbacen',
            prazo=30,
            marcar_pec=False,
            movimento='bloqueio',
            gigs=gigs,
            marcar_primeiro_destinatario=True,
            debug=debug,
            sigilo=True,
            descricao='Pesquisas para execução',
            intimar=False
        )
        
        # Para compatibilidade, armazena sigilo_ativado como atributo
        ato_pesquisas.ultimo_sigilo_ativado = sigilo_ativado
        
        # CORREÇÃO: Retorna tupla (sucesso, sigilo_ativado) para visibilidade externa
        if debug:
            print(f'[ATO_PESQUISAS] Retornando: sucesso={sucesso}, sigilo_ativado={sigilo_ativado}')
        return sucesso, sigilo_ativado
        
    except Exception as e:
        print(f'[ATO_PESQUISAS][ERRO] Falha no fluxo do ato de pesquisas: {e}')
        try:
            driver.save_screenshot('erro_ato_pesquisas.png')
        except Exception:
            pass
        return False, False  # CORREÇÃO: Retorna tupla mesmo em erro


# ====================================================
# FUNÇÃO IDPJ - Nova regra para "instaurado em face"
# ====================================================


def idpj(
    driver: WebDriver,
    debug: bool = False
) -> bool:
    """
    Função IDPJ para casos "instaurado em face"
    
    Fluxo:
    0. Executa BNDT inclusão (nova etapa)
    1. Verifica lembretes de bloqueio na seção de post-its
    2. Se tem bloqueio com data não superior a 100 dias: executa ato_bloq
    3. Se não tem: executa ato_meios
    
    Returns:
        bool: True se executou com sucesso, False caso contrário
    """
    try:
        if debug:
            print('[IDPJ] Iniciando fluxo IDPJ...')
        
        # 0. Executar BNDT inclusão
        if debug:
            print('[IDPJ] Etapa 0: Executando BNDT inclusão...')
        try:
            resultado_bndt = bndt(driver, inclusao=True)
            if resultado_bndt:
                if debug:
                    print('[IDPJ] ✅ BNDT inclusão executada com sucesso')
            else:
                if debug:
                    print('[IDPJ] ⚠️ BNDT inclusão retornou False, continuando fluxo')
        except Exception as e:
            if debug:
                print(f'[IDPJ] ❌ Erro no BNDT inclusão: {e}')
            # Continua mesmo com erro no BNDT
        
        # 1. Verificar se há lembretes de bloqueio
        if debug:
            print('[IDPJ] Etapa 1: Verificando lembretes de bloqueio...')
        
        tem_bloqueio_recente = verificar_bloqueio_recente(driver, debug=debug)
        
        if tem_bloqueio_recente:
            if debug:
                print('[IDPJ] ✅ Bloqueio recente encontrado - executando ato_bloq')
            return ato_bloq(driver)
        else:
            if debug:
                print('[IDPJ] ⚠️ Nenhum bloqueio recente - executando ato_meios')
            return ato_meios(driver)
            
    except Exception as e:
        if debug:
            print(f'[IDPJ] ❌ Erro na função idpj: {e}')
        return False


def preencher_prazos_destinatarios(driver, prazo, apenas_primeiro=False, perito=False, perito_nomes=None):
    """
    Preenche prazos para destinatários em uma tabela específica.
    Versão simplificada baseada na função original, usando apenas funções de Fix.
    """
    from selenium.webdriver.common.by import By
    
    # Lista fixa de nomes de peritos
    nomes_peritos_padrao = [
        'ROGERIO APARECIDO ROSA',
        # Adicione outros nomes fixos aqui se necessário
    ]
    if perito_nomes is None:
        perito_nomes = nomes_peritos_padrao
    
    try:
        # Encontra todas as linhas da tabela de destinatários
        linhas = driver.find_elements(By.CSS_SELECTOR, 'table.t-class tr.ng-star-inserted')
        if not linhas:
            print('[ATO][PRAZO][ERRO] Nenhuma linha de destinatário encontrada!')
            return False
        
        ativos = []
        for tr in linhas:
            try:
                checkbox = tr.find_element(By.CSS_SELECTOR, 'input[type="checkbox"][aria-label="Intimar parte"]')
                nome_elem = tr.find_element(By.CSS_SELECTOR, '.destinario')
                nome = nome_elem.text.strip().upper()
                
                # Verifica se já está marcado
                if checkbox.get_attribute('aria-checked') == 'true':
                    ativos.append((tr, checkbox, nome))
                # Se está desmarcado e é perito e perito=True e nome na lista
                elif perito and nome in [n.upper() for n in perito_nomes]:
                    driver.execute_script("arguments[0].click();", checkbox)
                    print(f'[ATO][PRAZO][PERITO] Checkbox do perito {nome} ativado.')
                    ativos.append((tr, checkbox, nome))
            except Exception as e:
                print(f'[ATO][PRAZO][WARN] Erro ao localizar checkbox/nome: {e}')
        
        if not ativos:
            print('[ATO][PRAZO][ERRO] Nenhum destinatário ativo!')
            return False
        
        if apenas_primeiro:
            # Desmarca todos exceto o primeiro
            for i, (tr, checkbox, nome) in enumerate(ativos):
                if i == 0:
                    continue
                try:
                    driver.execute_script("arguments[0].click();", checkbox)
                    print(f'[ATO][PRAZO][INFO] Checkbox do destinatário {i+1} desmarcado.')
                except Exception as e:
                    print(f'[ATO][PRAZO][WARN] Erro ao desmarcar checkbox: {e}')
            ativos = [ativos[0]]
        
        # Preenche prazos usando JavaScript para múltiplos campos
        campos_prazo = {}
        for i, (tr, checkbox, nome) in enumerate(ativos):
            try:
                input_prazo = tr.find_element(By.CSS_SELECTOR, 'mat-form-field.prazo input[type="text"].mat-input-element')
                campo_id = f'prazo_destinatario_{i}'
                # Atribui um ID único ao campo se não tiver
                driver.execute_script("arguments[0].id = arguments[1];", input_prazo, campo_id)
                campos_prazo[f'#{campo_id}'] = str(prazo)
                print(f'[ATO][PRAZO][OK] Preparado prazo {prazo} para destinatário {nome}.')
            except Exception as e:
                print(f'[ATO][PRAZO][WARN] Erro ao preparar campo de prazo: {e}')
        
        # Preenche todos os campos de uma vez
        if campos_prazo:
            from Fix.core import preencher_multiplos_campos
            resultado = preencher_multiplos_campos(driver, campos_prazo, log=True)
            if all(resultado.values()):
                print(f'[ATO][PRAZO][OK] Todos os {len(campos_prazo)} campos de prazo preenchidos com sucesso.')
                return True
            else:
                print(f'[ATO][PRAZO][WARN] Alguns campos de prazo podem não ter sido preenchidos corretamente.')
                return False
        
        return True
        
    except Exception as e:
        print(f'[ATO][PRAZO][ERRO] Falha geral ao preencher prazos: {e}')
        return False


def verificar_bloqueio_recente(driver, debug=False):
    """
    Verifica se existe lembrete de bloqueio com data não superior a 100 dias.
    Versão simplificada baseada na função original.
    
    Returns:
        bool: True se encontrou bloqueio recente, False caso contrário
    """
    try:
        import re
        from datetime import datetime, timedelta
        
        if debug:
            print('[IDPJ][BLOQUEIO] Buscando seção de lembretes...')
        
        # Procurar pela seção de lembretes (post-it-set)
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            lembretes_section = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.post-it-set'))
            )
        except:
            if debug:
                print('[IDPJ][BLOQUEIO] ⚠️ Seção de lembretes não encontrada')
            return False
        
        # Encontrar todos os lembretes expandidos
        lembretes = lembretes_section.find_elements(By.CSS_SELECTOR, 'mat-expansion-panel.mat-expanded')
        
        if debug:
            print(f'[IDPJ][BLOQUEIO] {len(lembretes)} lembrete(s) encontrado(s)')
        
        data_limite = datetime.now() - timedelta(days=100)
        
        for lembrete in lembretes:
            try:
                # Verificar título do lembrete
                titulo_element = lembrete.find_element(By.CSS_SELECTOR, 'mat-panel-title')
                titulo = titulo_element.text.strip().lower()
                
                # Verificar conteúdo do lembrete
                conteudo_element = lembrete.find_element(By.CSS_SELECTOR, 'div.post-it-conteudo')
                conteudo = conteudo_element.text.strip().lower()
                
                if debug:
                    print(f'[IDPJ][BLOQUEIO] Analisando - Título: "{titulo}" | Conteúdo: "{conteudo[:50]}..."')
                
                # Verificar se é um lembrete de bloqueio
                if ('bloq' in titulo or 'bloq' in conteudo or 
                    'bloqueio' in titulo or 'bloqueio' in conteudo):
                    
                    if debug:
                        print('[IDPJ][BLOQUEIO]  Lembrete de bloqueio encontrado - verificando data...')
                    
                    # Extrair data do rodapé
                    try:
                        rodape = lembrete.find_element(By.CSS_SELECTOR, 'div.rodape-post-it-usuario span')
                        rodape_texto = rodape.text.strip()
                        
                        # Buscar padrão de data (formato DD/MM/AA HH:MM)
                        match_data = re.search(r'(\d{2}/\d{2}/\d{2})\s+(\d{2}:\d{2})', rodape_texto)
                        
                        if match_data:
                            data_str = match_data.group(1)
                            # Converter para formato completo (assumindo 20XX)
                            dia, mes, ano = data_str.split('/')
                            ano_completo = f"20{ano}"
                            
                            data_lembrete = datetime.strptime(f"{dia}/{mes}/{ano_completo}", "%d/%m/%Y")
                            
                            if debug:
                                print(f'[IDPJ][BLOQUEIO] Data do lembrete: {data_lembrete.strftime("%d/%m/%Y")}')
                                print(f'[IDPJ][BLOQUEIO] Data limite (100 dias): {data_limite.strftime("%d/%m/%Y")}')
                            
                            # Verificar se a data é dentro dos últimos 100 dias
                            if data_lembrete >= data_limite:
                                if debug:
                                    print('[IDPJ][BLOQUEIO] ✅ Bloqueio recente (≤ 100 dias) encontrado!')
                                return True
                            else:
                                if debug:
                                    print('[IDPJ][BLOQUEIO] ⚠️ Bloqueio antigo (> 100 dias)')
                        else:
                            if debug:
                                print('[IDPJ][BLOQUEIO] ⚠️ Não foi possível extrair data do lembrete')
                    
                    except Exception as e:
                        if debug:
                            print(f'[IDPJ][BLOQUEIO] ❌ Erro ao extrair data: {e}')
                        continue
                
            except Exception as e:
                if debug:
                    print(f'[IDPJ][BLOQUEIO] ❌ Erro ao analisar lembrete: {e}')
                continue
        
        if debug:
            print('[IDPJ][BLOQUEIO] ⚠️ Nenhum bloqueio recente encontrado')
        return False
        
    except Exception as e:
        if debug:
            print(f'[IDPJ][BLOQUEIO] ❌ Erro na verificação de bloqueio: {e}')
        return False
