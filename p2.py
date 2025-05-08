from Fix import login_automatico, driver_notebook, obter_driver_padronizado, aplicar_filtro_100, processar_lista_processos, pz_minuta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import logging
import os
from Fix import esperar_elemento, safe_click
from Fix import indexar_e_processar_lista, criar_gigs, obter_driver_padronizado, login_notebook, aplicar_filtro_100
from Fix import extrair_documento, esperar_elemento, safe_click, criar_gigs, indexar_e_processar_lista, obter_driver_padronizado, login_notebook, aplicar_filtro_100
from atos import ato_pesquisas, ato_sobrestamento
from mov import def_arq
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.keys import Keys

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler('pje_automacao.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AutomacaoPJe')

def fluxo_pz(driver):
    """
    Processa prazos detalhados em processos abertos.
    Usa extrair_documento para obter texto, analisa regras,
    cria GIGS parametrizadas, executa atos sequenciais e fecha aba.
    """
    logger.info('[FLUXO_PZ] Iniciando análise de prazo detalhado...')
    acao_secundaria = None
    texto = None # Initialize texto as None
    try:
        # 1. Seleciona documento relevante (decisão, despacho ou sentença)
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        doc_encontrado = None
        doc_link = None
        for item in itens:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                if not re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                    continue
                mag_icons = item.find_elements(By.CSS_SELECTOR, 'div.tl-icon[aria-label*="Magistrado"]')
                mag_ok = any('otavio' in mag.get_attribute('aria-label').lower() or 'mariana' in mag.get_attribute('aria-label').lower() for mag in mag_icons)
                if mag_ok:
                    doc_encontrado = item
                    doc_link = link
                    break
            except Exception:
                continue
        if not doc_encontrado or not doc_link:
            logger.warning('[FLUXO_PZ] Nenhum documento relevante encontrado.')
            return

        logger.info('[FLUXO_PZ] Documento relevante encontrado, abrindo painel...')
        doc_link.click()
        time.sleep(2) # Wait for panel/URL to load

        # 2. Extrair texto usando a função de Fix.py
        import datetime
        t_inicio_extrair = datetime.datetime.now()
        logger.info(f'[FLUXO_PZ][PERF] Início extrair_documento: {t_inicio_extrair.strftime("%H:%M:%S.%f")[:-3]}')
        texto_tuple = None # Initialize tuple variable
        try:
            texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=True) # timeout reduzido
            if texto_tuple and texto_tuple[0]:
                texto = texto_tuple[0].lower()
                t_fim_extrair = datetime.datetime.now()
                logger.info(f'[FLUXO_PZ][PERF] Fim extrair_documento: {t_fim_extrair.strftime("%H:%M:%S.%f")[:-3]} (duração: {(t_fim_extrair-t_inicio_extrair).total_seconds():.2f}s)')
            else:
                logger.warning('[FLUXO_PZ] extrair_documento retornou None ou texto vazio.')
                texto = None
        except Exception as e_extrair:
            logger.error(f'[FLUXO_PZ] Erro ao chamar/processar extrair_documento: {e_extrair}')
            texto = None
        if not texto:
            logger.warning('[FLUXO_PZ] Não foi possível extrair o texto do documento via extrair_documento.')
            try:
                driver.save_screenshot(f'screenshot_erro_extracao_texto_{time.strftime("%Y%m%d_%H%M%S")}.png')
                logger.info('[FLUXO_PZ] Screenshot de erro de extração salvo.')
            except Exception as screen_err:
                logger.error(f'[FLUXO_PZ][ERRO] Falha ao tirar screenshot de erro de extração: {screen_err}')
            return
        # 3. Log the extracted text (if successful)
        log_texto = texto[:500] + '...' if len(texto) > 500 else texto
        logger.info(f'[FLUXO_PZ] Texto extraído para análise (início):\n---\n{log_texto}\n---')
        logger.info('[FLUXO_PZ] Analisando regras...')

        # 4. Define as regras com parâmetros e ações sequenciais
        regras = [
            (['concede-se 05 dias', 'visibilidade aos advogados', 'início da fluência', 'indicar meios', 'oito dias para apresentação', 'oito dias para apresentacao'],
             'gigs', (1, 'Guilherme - Sobrestamento'), ato_sobrestamento),
            (['revel', 'concorda com homologação', 'concorda com homologacao', 'tomarem ciência dos esclarecimentos apresentados'],
             'gigs', (1, 'Silvia - Homologação'), None),
            (['hasta', 'saldo devedor', 'prescrição', 'prescricao'],
             'gigs', (1, 'xs - pec'), None),
            (['impugnações apresentadas', 'impugnacoes apresentadas', 'fixando o crédito do autor em'],
             'gigs', (1, 'SILVIA - Argos'), ato_pesquisas),
            # Add the new phrase to the keywords for def_arq
            (['cumprido o acordo homologado', 'julgo extinta a presente execução, nos termos do art. 924'],
             'movimentar', def_arq, None),
            (['bloqueio realizado, ora convertido'], 'gigs', (1, 'xs pec bloqueio'), None),
        ]

        # Regra especial: bloqueio de valores realizado, ora
        if 'bloqueio de valores realizado, ora' in texto:
            itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
            datas = []
            idx_despacho = None
            idx_ultima = None
            for idx, item in enumerate(itens):
                try:
                    data_el = item.find_element(By.CSS_SELECTOR, 'time')
                    data_txt = data_el.text.strip()
                    datas.append(data_txt)
                    if 'despacho' in item.text.lower() and idx_despacho is None:
                        idx_despacho = idx
                except Exception:
                    datas.append('')
            idx_ultima = 0 if not datas else max(range(len(datas)), key=lambda i: datas[i])
            if idx_despacho is not None and idx_despacho == idx_ultima:
                logger.info('[FLUXO_PZ] Despacho é o último documento. Criando GIGS 1/xs pec bloqueio.')
                criar_gigs(driver, 1, 'xs pec bloqueio')
            else:
                logger.info('[FLUXO_PZ] Há intimações após despacho. Chamando catya e criando GIGS 1/Bruna - Liberação.')
                from carta import catya
                catya(driver)
                criar_gigs(driver, 1, 'Bruna - Liberação')
            return

        # 5. Iterate through rules and keywords to find the first match
        acao_definida = None
        parametros_acao = None
        termo_encontrado = None
        acao_secundaria = None # Reset before checking rules

        for keywords, tipo_acao, params, acao_sec in regras:
            for keyword in keywords:
                if keyword in texto:
                    acao_definida = tipo_acao
                    parametros_acao = params
                    acao_secundaria = acao_sec
                    termo_encontrado = keyword
                    logger.info(f'[FLUXO_PZ] Regra encontrada pelo termo: "{termo_encontrado}". Ação Primária: {acao_definida}, Secundária: {acao_secundaria.__name__ if acao_secundaria else "Nenhuma"}')
                    break
            if acao_definida:
                break

        # 6. Perform action(s) based on the matched rule (or default)
        import datetime
        t_inicio_gigs = datetime.datetime.now()
        if acao_definida == 'gigs':
             dias, obs = parametros_acao
             logger.info(f'[FLUXO_PZ][PERF] Início criação GIGS: {t_inicio_gigs.strftime("%H:%M:%S.%f")[:-3]}')
             try:
                 criar_gigs(driver, dias, obs)
                 t_fim_gigs = datetime.datetime.now()
                 logger.info(f'[FLUXO_PZ][PERF] Fim criação GIGS: {t_fim_gigs.strftime("%H:%M:%S.%f")[:-3]} (duração: {(t_fim_gigs-t_inicio_gigs).total_seconds():.2f}s)')
                 # ...existing code...
                 if acao_secundaria:
                     logger.info(f'[FLUXO_PZ] Executando Ação Secundária: {acao_secundaria.__name__}')
                     # Monta dicionário de parâmetros para o ato secundário
                     parametros_ato = {
                         'conclusao_tipo': None,
                         'modelo_nome': None,
                         'prazo': None,
                         'marcar_pec': None,
                         'movimento': None,
                         'gigs': None,
                         'marcar_primeiro_destinatario': None,
                         'debug': False
                     }
                     # Preenche com valores se disponíveis na regra
                     if isinstance(parametros_acao, tuple) and len(parametros_acao) == 2:
                         parametros_ato['prazo'] = dias
                         parametros_ato['gigs'] = {'dias_uteis': dias, 'observacao': obs}
                     acao_secundaria(driver, **parametros_ato)
                     logger.info(f'[FLUXO_PZ] Ação Secundária {acao_secundaria.__name__} concluída.')
                     time.sleep(1)
             except Exception as gigs_error:
                 logger.error(f'[FLUXO_PZ][ERRO] Falha ao criar GIGS "{obs}" ou na ação secundária: {gigs_error}')
        elif acao_definida == 'movimentar':
             func_movimento = parametros_acao
             logger.info(f'[FLUXO_PZ] Executando Ação Primária: Movimentar Processo ({func_movimento.__name__})')
             try:
                 func_movimento(driver)
                 time.sleep(1) # Pause after movement
             except Exception as mov_error:
                  logger.error(f'[FLUXO_PZ][ERRO] Falha ao executar movimentação {func_movimento.__name__}: {mov_error}')
        else:
             # Default action if no rule matched
             logger.info('[FLUXO_PZ] Nenhuma regra aplicável encontrada no texto. Aplicando ação padrão: Criar GIGS "Pz".')
             try:
                 criar_gigs(driver, 0, 'Pz')
                 time.sleep(1) # Pause after default GIGS
             except Exception as default_gigs_error:
                  logger.error(f'[FLUXO_PZ][ERRO] Falha ao criar GIGS padrão "Pz": {default_gigs_error}')


        logger.info('[FLUXO_PZ] Análise de prazo detalhado e ações concluídas.')

    except Exception as e:
        logger.error(f'[FLUXO_PZ][ERRO] Erro durante a análise de prazo detalhado: {str(e)}')
        # Consider adding screenshot on error
        try:
            driver.save_screenshot(f'screenshot_erro_fluxo_pz_{time.strftime("%Y%m%d_%H%M%S")}.png')
        except Exception as screen_err:
             logger.error(f'[FLUXO_PZ][ERRO] Falha ao tirar screenshot: {screen_err}')

    finally:
        # ADDED: Close the current tab as the last action
        try:
            all_windows = driver.window_handles
            # This assumes the main list is always the first handle. Be cautious.
            main_window = all_windows[0]
            current_window = driver.current_window_handle

            if current_window != main_window and len(all_windows) > 1:
                logger.info('[FLUXO_PZ] Fechando aba do processo...')
                driver.close()
                # Ensure switch happens even if close fails somehow, or if already closed
                if main_window in driver.window_handles:
                     driver.switch_to.window(main_window)
                     logger.info('[FLUXO_PZ] Foco retornado para a aba principal.')
                else:
                     # This case might indicate the main window was closed unexpectedly
                     logger.warning('[FLUXO_PZ] Aba principal não encontrada após fechar aba do processo.')
                     # May need to re-acquire handles or handle error state
                     if driver.window_handles: # Switch to first available if main is gone
                          driver.switch_to.window(driver.window_handles[0])

            elif len(all_windows) <= 1:
                 logger.info('[FLUXO_PZ] Apenas uma aba aberta ou já na aba principal, não fechando/trocando.')
            else: # Already on main window
                 logger.info('[FLUXO_PZ] Já na aba principal, nenhuma ação de fechamento/troca necessária.')

        except Exception as close_err:
            logger.error(f'[FLUXO_PZ][ERRO] Falha ao tentar fechar/trocar aba no finally: {close_err}')

def fluxo_prazo(driver):
    """
    Executa o fluxo de prazo: Itera processos, chama fluxo_pz para cada um.
    """
    from Fix import indexar_e_processar_lista # Keep this import

    logger.info('[FLUXO_PRAZO] Iniciando fluxo de prazo.')

    def callback_processo(driver_processo):
        """
        Callback para executar fluxo_pz no processo aberto.
        fluxo_pz handles analysis, actions (primary & secondary), and tab closing.
        """
        logger.info(f'[FLUXO_PRAZO][CALLBACK] Iniciando fluxo_pz para o processo atual.')
        fluxo_pz(driver_processo) # Call the main function for the process tab
        logger.info(f'[FLUXO_PRAZO][CALLBACK] fluxo_pz concluído para o processo atual.')
        # The callback finishes when fluxo_pz finishes (including secondary actions)

    # Chama indexar_e_processar_lista com o callback definido
    indexar_e_processar_lista(driver, callback_processo) # Use the correct processing function

    logger.info('[FLUXO_PRAZO] Fluxo de prazo concluído.')

def navegar_para_atividades(driver):
    """
    Navega para a tela de atividades do GIGS clicando no ícone .fa-tags.
    """
    try:
        # Navegação por clique no ícone .fa-tags
        print("[NAVEGAR] Procurando ícone .fa-tags...")
        tag_icon = esperar_elemento(driver, ".fa-tags", timeout=20)
        if not tag_icon:
            print("[ERRO] Ícone .fa-tags não encontrado!")
            return
        safe_click(driver, tag_icon)
        print("[NAVEGAR] Ícone .fa-tags clicado.")

        # Aguarda o carregamento da tela de atividades
        esperar_elemento(driver, ".classe-unica-da-tela-atividades", timeout=20)
        print("[OK] Na tela de atividades do GIGS. Continue o fluxo normalmente...")
    except Exception as e:
        print(f"[ERRO] Falha ao navegar para a tela de atividades: {e}")

# Updated to use driver_notebook and login_notebook from Fix.py.
from Fix import login_notebook, driver_notebook

def esperar_url(driver, url_esperada, timeout=30):
    """
    Espera até a URL do driver ser igual à url_esperada ou até o timeout.
    Retorna True se a URL for atingida, False caso contrário.
    """
    import time
    start = time.time()
    while time.time() - start < timeout:
        if driver.current_url == url_esperada:
            return True
        time.sleep(0.5)
    return False

# Updated the executar_fluxo function to use the new driver and login function.
def executar_fluxo():
    """
    Executa o fluxo completo de login, navegação, filtro e processamento.
    """
    driver = driver_notebook()
    try:
        # 1. Login
        if not login_notebook(driver):
            raise Exception('Falha no login')
        logger.info('[LOGIN] Login realizado com sucesso.')

        # Maximizar a janela do navegador
        logger.info('[NAVEGAR] Maximizar a janela do navegador.')
        driver.maximize_window()

        # 2. Navegar diretamente para a página de atividades
        url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
        logger.info(f'[NAVEGAR] Navegando diretamente para {url_atividades}...')
        driver.get(url_atividades)

        # Verificar se a página foi carregada corretamente
        if not esperar_url(driver, url_atividades, timeout=30):
            logger.error(f'[NAVEGAR] Timeout aguardando URL {url_atividades}. URL atual: {driver.current_url}')
            raise Exception(f'Timeout aguardando URL {url_atividades}')
        logger.info('[NAVEGAR] Página de atividades carregada com sucesso.')

        # 3. Aplicar filtro de 100 itens por página
        if not aplicar_filtro_100(driver):
            raise Exception('Falha ao aplicar filtro de 100 itens por página')

        # 4. Filtro de atividade sem prazo e descrição "xs"
        try:
            logger.info('[FILTRO] Aplicando filtro de atividade sem prazo e descrição "xs"...')
            # Remover chip "Vencidas" se existir
            chip_remove_button = esperar_elemento(driver, '.mat-chip-remove', timeout=5)
            if chip_remove_button and chip_remove_button.is_displayed():
                safe_click(driver, chip_remove_button)
                logger.info('[FILTRO] Chip "Vencidas" removido.')
                time.sleep(0.5)

            # Clicar em Atividade sem prazo
            btn_atividade_sem_prazo = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa-pen:nth-child(1)'))
            )
            safe_click(driver, btn_atividade_sem_prazo)
            logger.info('[FILTRO] Atividade sem prazo selecionada.')
            time.sleep(1)

            # Aplicar descrição "xs"
            campo_descricao = WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[aria-label*="Descrição"]'))
            )
            campo_descricao.clear()
            campo_descricao.send_keys('xs')
            campo_descricao.send_keys(Keys.ENTER)
            logger.info('[FILTRO] Descrição da atividade "xs" aplicada.')
            time.sleep(2)

        except Exception as e:
            logger.error(f'[FILTRO][ERRO] Erro ao aplicar filtro de atividade: {e}')
            raise

        # 5. Executar fluxo de prazo
        fluxo_prazo(driver)

    except Exception as e:
        logger.error(f'[EXECUCAO][ERRO] {e}')
    finally:
        driver.quit()

if __name__ == "__main__":
    try:
        executar_fluxo()
    except Exception as e:
        logger.error(f"[MAIN][ERRO] {e}")
