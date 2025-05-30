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


from Fix import login_pc, driver_notebook, aplicar_filtro_100, indexar_e_processar_lista, extrair_dados_processo
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import logging
import os
from Fix import esperar_elemento, safe_click
from Fix import criar_gigs, login_pc, aplicar_filtro_100
from Fix import extrair_documento, esperar_elemento, safe_click, criar_gigs, indexar_e_processar_lista, login_notebook, aplicar_filtro_100
from atos import ato_pesquisas, ato_sobrestamento
from mov import def_arq
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from Fix import driver_pc, login_pc

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
        def remover_acentos(txt):
            import unicodedata
            return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

        def normalizar_texto(txt):
            return remover_acentos(txt.lower())

        texto_normalizado = normalizar_texto(texto)

        def gerar_regex_geral(termo):
            # Remove acentos e deixa minúsculo para o termo
            termo_norm = normalizar_texto(termo)
            # Divide termo em palavras
            palavras = termo_norm.split()
            # Monta regex permitindo pontuação, vírgula, etc. entre as palavras
            partes = [re.escape(p) for p in palavras]
            # Entre cada palavra, aceita qualquer quantidade de espaços, pontuação, vírgula, etc.
            regex = r''
            for i, parte in enumerate(partes):
                regex += parte
                if i < len(partes) - 1:
                    regex += r'[\s\.,;:!\-–—]*'            # Permite o trecho em qualquer lugar do texto (texto antes/depois)
            return re.compile(rf"{regex}", re.IGNORECASE)

        regras = [            ([gerar_regex_geral(k) for k in [
                '05 dias para a apresentação',
                '05 dias para oferta',
                'concede-se 05 dias para oferta',
                'cinco dias para apresentação',
                'cinco dias para oferta',
                'cinco dias para apresentacao',
                'concedo cinco dias',
                'concedo o prazo de oito dias',
                'oito dias para apresentacao',
                'visibilidade aos advogados',
                'início da fluência',
                'oito dias para apresentação',
                'oito dias para apresentacao',
            ]],
             'gigs', (1, 'Guilherme - Sobrestamento'), ato_sobrestamento),
            ([gerar_regex_geral(k) for k in ['revel', 'concorda com homologação', 'concorda com homologacao', 'tomarem ciência dos esclarecimentos apresentados', 'oito dias impugnar os']],
             'gigs', (1, 'Silvia - Homologação'), None),
            ([gerar_regex_geral(k) for k in ['Se revê o novo sobrestamento']],
             'movimentar', def_arq, None),
            ([gerar_regex_geral(k) for k in ['hasta', 'saldo devedor']],
             'gigs', (1, 'xs - pec'), None),
            ([gerar_regex_geral(k) for k in ['impugnações apresentadas', 'impugnacoes apresentadas', 'fixando o crédito do autor em', 'referente ao principal']],
             'gigs', (1, 'SILVIA - Argos'), ato_pesquisas),            ([gerar_regex_geral(k) for k in ['cumprido o acordo homologado', 'julgo extinta a presente execução, nos termos do art. 924']],
             'movimentar', def_arq, None),
            ([gerar_regex_geral(k) for k in ['A pronúncia da prescrição intercorrente se trata']],
             'movimentar', def_arq, None),
            ([gerar_regex_geral(k) for k in ['bloqueio realizado, ora convertido']], 'gigs', (1, 'xs pec bloqueio'), None),
            # NOVA REGRA SOLICITADA
            ([gerar_regex_geral(k) for k in ['sobre o preenchimento dos pressupostos legais para concessão do parcelamento']],
             'gigs', (1, 'Bruna - Liberação'), None),
        ] # Regra especial: bloqueio de valores realizado, ora
        if 'bloqueio de valores realizado, ora' in texto:
            logger.info('[FLUXO_PZ][DEBUG] Regra especial "bloqueio de valores realizado, ora" detectada.')
            try:
                # 0. Extrair dados do processo
                from Fix import extrair_dados_processo
                dados_processo = extrair_dados_processo(driver)
                logger.info('[FLUXO_PZ][DEBUG] Dados do processo extraídos.')
                  # Verificação simplificada de advogados (dados detalhados salvos em JSON)
                parte_sem_advogado = False
                if dados_processo and 'partes' in dados_processo:
                    partes_passivas = dados_processo['partes'].get('passivas', [])
                    partes_sem_advogado = [p for p in partes_passivas if not p.get('representantes')]
                    parte_sem_advogado = len(partes_sem_advogado) > 0
                    
                    if parte_sem_advogado:
                        logger.info(f'[FLUXO_PZ][DEBUG] {len(partes_sem_advogado)} parte(s) sem advogado de {len(partes_passivas)} partes passivas')
                    else:
                        logger.info(f'[FLUXO_PZ][DEBUG] Todas as {len(partes_passivas)} partes passivas possuem advogados')
                
                # Verificar item mais recente da timeline
                itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
                primeiro_item = itens[0] if itens else None
                
                if primeiro_item:
                    primeiro_item_text = primeiro_item.text.lower()
                    logger.info(f'[FLUXO_PZ][DEBUG] Primeiro item da timeline: {primeiro_item_text[:100]}...')
                    
                    # Hipótese 1: GIGS Bruna - Liberação
                    if any(termo in primeiro_item_text for termo in ['edital', 'certidão de oficial de justiça', 'certidao de oficial de justica']):
                        logger.info('[FLUXO_PZ][DEBUG] Item mais recente é edital ou certidão. Criando GIGS Bruna - Liberação.')
                        criar_gigs(driver, 1, 'Bruna - Liberação')
                        logger.info('[FLUXO_PZ][DEBUG] GIGS "Bruna - Liberação" criado com sucesso.')
                    elif 'intimação' in primeiro_item_text or 'intimacao' in primeiro_item_text:
                        # Verificar se é intimação de correio via carta()
                        logger.info('[FLUXO_PZ][DEBUG] Item mais recente é intimação. Verificando se é de correio...')
                        from carta import carta
                        carta_result = carta(driver)
                        if carta_result:  # Se carta() encontrou intimação de correio
                            logger.info('[FLUXO_PZ][DEBUG] Intimação de correio encontrada. Criando GIGS Bruna - Liberação.')
                            criar_gigs(driver, 1, 'Bruna - Liberação')
                            logger.info('[FLUXO_PZ][DEBUG] GIGS "Bruna - Liberação" criado com sucesso.')
                        else:
                            logger.info('[FLUXO_PZ][DEBUG] Intimação não é de correio.')
                            # Verificar se há despacho anterior na timeline para condição "xs pec bloqueio"
                            despacho_encontrado = False
                            if len(itens) > 1:  # Verificar se há mais itens na timeline
                                for i, item_timeline in enumerate(itens[1:], 1):  # Começar do segundo item
                                    item_text = item_timeline.text.lower()
                                    if 'despacho' in item_text:
                                        despacho_encontrado = True
                                        logger.info(f'[FLUXO_PZ][DEBUG] Despacho encontrado no item {i+1} da timeline.')
                                        break
                            
                            # Hipótese 2: parte sem advogado + despacho → GIGS "xs pec bloqueio"
                            if parte_sem_advogado and despacho_encontrado:
                                logger.info('[FLUXO_PZ][DEBUG] Condições atendidas: parte sem advogado + despacho anterior. Criando GIGS xs pec bloqueio.')
                                criar_gigs(driver, 1, 'xs pec bloqueio')
                                logger.info('[FLUXO_PZ][DEBUG] GIGS "xs pec bloqueio" criado com sucesso.')
                            else:
                                logger.info(f'[FLUXO_PZ][DEBUG] Condições não atendidas (parte_sem_advogado={parte_sem_advogado}, despacho_encontrado={despacho_encontrado}). Criando GIGS Bruna - Liberação.')
                                criar_gigs(driver, 1, 'Bruna - Liberação')
                                logger.info('[FLUXO_PZ][DEBUG] GIGS "Bruna - Liberação" criado com sucesso.')
                    else:
                        # Hipótese 2: verificar despacho + parte sem advogado
                        if parte_sem_advogado and 'despacho' in primeiro_item_text:
                            logger.info('[FLUXO_PZ][DEBUG] Parte sem advogado + despacho. Criando GIGS xs pec bloqueio.')
                            criar_gigs(driver, 1, 'xs pec bloqueio')
                            logger.info('[FLUXO_PZ][DEBUG] GIGS "xs pec bloqueio" criado com sucesso.')
                        else:
                            logger.info('[FLUXO_PZ][DEBUG] Caso padrão. Criando GIGS Bruna - Liberação.')
                            criar_gigs(driver, 1, 'Bruna - Liberação')
                            logger.info('[FLUXO_PZ][DEBUG] GIGS "Bruna - Liberação" criado com sucesso.')
                
                logger.info('[FLUXO_PZ][DEBUG] Regra especial bloqueio processada completamente. Retornando do fluxo_pz.')
                return
                
            except Exception as bloqueio_error:
                logger.error(f'[FLUXO_PZ][DEBUG] Erro na regra especial de bloqueio: {bloqueio_error}')
                raise

        # 5. Iterate through rules and keywords to find the first match
        acao_definida = None
        parametros_acao = None
        termo_encontrado = None
        acao_secundaria = None # Reset before checking rules

        for keywords, tipo_acao, params, acao_sec in regras:
            for regex in keywords:
                if regex.search(texto_normalizado):
                    acao_definida = tipo_acao
                    parametros_acao = params
                    acao_secundaria = acao_sec
                    termo_encontrado = regex.pattern
                    logger.info(f'[FLUXO_PZ] Regra encontrada pelo termo (regex): "{termo_encontrado}". Ação Primária: {acao_definida}, Secundária: {acao_secundaria.__name__ if acao_secundaria else "Nenhuma"}')
                    break
            if acao_definida:
                break

        # 6. Perform action(s) based on the matched rule (or default)
        import datetime
        t_inicio_gigs = datetime.datetime.now()
        gigs_aplicado = False
        if acao_definida == 'gigs':
             dias, obs = parametros_acao
             logger.info(f'[FLUXO_PZ][PERF] Início criação GIGS: {t_inicio_gigs.strftime("%H:%M:%S.%f")[:-3]}')
             try:
                 criar_gigs(driver, dias, obs)
                 gigs_aplicado = True
                 t_fim_gigs = datetime.datetime.now()
                 logger.info(f'[FLUXO_PZ][PERF] Fim criação GIGS: {t_fim_gigs.strftime("%H:%M:%S.%f")[:-3]} (duração: {(t_fim_gigs-t_inicio_gigs).total_seconds():.2f}s)')
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
                     }                     # Preenche com valores se disponíveis na regra
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
                 resultado_movimento = func_movimento(driver)
                 if resultado_movimento:
                     logger.info(f'[FLUXO_PZ] Movimentação {func_movimento.__name__} executada com SUCESSO.')
                 else:
                     logger.error(f'[FLUXO_PZ][ERRO] Movimentação {func_movimento.__name__} FALHOU (retornou False).')
                     return  # Sai da função sem log de sucesso
                 time.sleep(1) # Pause after movement
             except Exception as mov_error:
                 logger.error(f'[FLUXO_PZ][ERRO] Falha ao executar movimentação {func_movimento.__name__}: {mov_error}')
                 return  # Sai da função sem log de sucesso

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
        logger.info(f'[FLUXO_PRAZO][CALLBACK] === INÍCIO DO CALLBACK ===')
        logger.info(f'[FLUXO_PRAZO][CALLBACK] URL atual: {driver_processo.current_url}')
        logger.info(f'[FLUXO_PRAZO][CALLBACK] Número de abas abertas: {len(driver_processo.window_handles)}')
        
        try:
            logger.info(f'[FLUXO_PRAZO][CALLBACK] Iniciando fluxo_pz para o processo atual.')
            fluxo_pz(driver_processo) # Call the main function for the process tab
            logger.info(f'[FLUXO_PRAZO][CALLBACK] fluxo_pz concluído com SUCESSO para o processo atual.')
        except Exception as callback_error:
            logger.error(f'[FLUXO_PRAZO][CALLBACK] ERRO no fluxo_pz: {callback_error}')
            # Adicionar screenshot em caso de erro
            try:
                driver_processo.save_screenshot(f'screenshot_erro_callback_{time.strftime("%Y%m%d_%H%M%S")}.png')
                logger.info('[FLUXO_PRAZO][CALLBACK] Screenshot de erro do callback salvo.')
            except Exception as screen_err:
                logger.error(f'[FLUXO_PRAZO][CALLBACK] Falha ao tirar screenshot: {screen_err}')
            raise  # Re-raise para que o indexar_e_processar_lista saiba que houve erro
        
        logger.info(f'[FLUXO_PRAZO][CALLBACK] === FIM DO CALLBACK ===')
        time.sleep(1)  # Pausa para evitar race condition/travamento entre processamentos

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
def executar_fluxo(driver):
    """
    Executa o fluxo completo de navegação, filtro e processamento, usando o driver já autenticado.
    """
    try:
        # Maximizar a janela do navegador
        logger.info('[NAVEGAR] Maximizar a janela do navegador.')
        driver.maximize_window()

        # Ajustar o zoom da página para 70% para garantir visibilidade do dropdown de quantidade por página
        driver.execute_script("document.body.style.zoom='70%'")

        # 2. Navegar diretamente para a página de atividades
        url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
        logger.info(f'[NAVEGAR] Navegando diretamente para {url_atividades}...')
        driver.get(url_atividades)

        # Verificar se a página foi carregada corretamente
        if not esperar_url(driver, url_atividades, timeout=30):
            logger.error(f'[NAVEGAR] Timeout aguardando URL {url_atividades}. URL atual: {driver.current_url}')
            raise Exception(f'Timeout aguardando URL {url_atividades}')
        logger.info('[NAVEGAR] Página de atividades carregada com sucesso.')        # 3. Aplicar filtro de 100 itens por página
        from Fix import aplicar_filtro_100
        if not aplicar_filtro_100(driver):
            raise Exception('Falha ao aplicar filtro de 100 itens por página')
        
        # Espera única de 2 segundos após aplicar o filtro 100
        time.sleep(2)
        
        try:            # Sequência específica de 3 passos após aplicar filtro lista 100:            # Passo 1: Remover chip "Vencidas" clicando no botão X com estratégia aprimorada
            logger.info('[FILTRO][PASSO_1] Removendo chip "Vencidas"...')
            chip_removal_success = False
            for tentativa in range(3):
                try:
                    # Aguarda a página carregar completamente e elementos estarem estáveis
                    time.sleep(0.5)
                    
                    # Re-search o elemento a cada tentativa para evitar StaleElementReferenceError
                    chip_remove_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[ngclass="chips-icone-fechar"][mattooltip="Remover filtro"]'))
                    )
                    
                    # Verifica se o elemento ainda está anexado ao DOM
                    try:
                        chip_remove_button.is_displayed()
                    except StaleElementReferenceException:
                        logger.warning(f'[FILTRO][PASSO_1] Elemento stale detectado na tentativa {tentativa + 1}, re-buscando...')
                        continue
                    
                    # Clique com verificação adicional
                    safe_click(driver, chip_remove_button)
                    logger.info('[FILTRO][PASSO_1] Chip "Vencidas" removido.')
                    chip_removal_success = True
                    break
                    
                except StaleElementReferenceException as e:
                    logger.warning(f'[FILTRO][PASSO_1] StaleElementReferenceException na tentativa {tentativa + 1}: {e}')
                    time.sleep(1)
                except Exception as e:
                    logger.warning(f'[FILTRO][PASSO_1] Tentativa {tentativa + 1} falhou: {e}')
                    if tentativa < 2:
                        time.sleep(1)
                    else:
                        logger.error('[FILTRO][PASSO_1] Falha ao remover chip após 3 tentativas.')
                        raise
            if not chip_removal_success:
                raise Exception("Falha na remoção do chip 'Vencidas'")
              # Passo 2: Clicar no ícone fa-pen
            logger.info('[FILTRO][PASSO_2] Clicando no ícone fa-pen...')
            btn_fa_pen = esperar_elemento(driver, 'i.fa-pen', timeout=15)
            safe_click(driver, btn_fa_pen)
            logger.info('[FILTRO][PASSO_2] Ícone fa-pen clicado.')
              # Passo 3: Aplicar filtro "xs"
            logger.info('[FILTRO][PASSO_3] Aplicando filtro "xs"...')
            campo_descricao = esperar_elemento(driver, 'input[aria-label*="Descrição"]', timeout=15)
            campo_descricao.clear()
            campo_descricao.send_keys('xs')
            campo_descricao.send_keys(Keys.ENTER)
            logger.info('[FILTRO][PASSO_3] Filtro "xs" aplicado.')
            
            # Aguardar 3 segundos para garantir que o filtro e indexação sejam aplicados completamente
            logger.info('[FILTRO][AGUARDO] Aguardando 3 segundos para aplicação completa do filtro e indexação...')
            time.sleep(3)
            logger.info('[FILTRO][AGUARDO] Filtro e indexação aplicados. Prosseguindo com o processamento da lista.')
            
        except Exception as e:
            logger.error(f'[FILTRO][ERRO] Erro na sequência de filtros: {e}')
            raise

        # 5. Executar fluxo de prazo
        fluxo_prazo(driver)

    except Exception as e:
        logger.error(f'[EXECUCAO][ERRO] {e}')
    finally:
        try:
            driver.quit()
        except Exception as e:
            logger.error(f'[EXECUCAO][ERRO] Falha ao fechar o driver: {e}')

def main():
    driver = driver_pc(headless=False)
    if not driver:
        print('[ERRO] Falha ao iniciar o driver.')
        return
    if not login_pc(driver):
        print('[ERRO] Falha no login. Encerrando script.')
        driver.quit()
        return
    print('[P2] Login realizado com sucesso.')
    # Passa o driver já autenticado para o fluxo principal
    executar_fluxo(driver)

if __name__ == "__main__":
    main()

class AutomacaoP2:
    def __init__(self):
        self.driver = None
        self.etapa_atual = None

    def iniciar(self):
        try:
            from Fix import driver_pc
            self.driver = driver_pc(headless=False)
            if not self.driver:
                logging.error('[AutomacaoP2] Falha ao iniciar o driver.')
                return False
            return True
        except Exception as e:
            logging.error(f'[AutomacaoP2] Erro ao iniciar driver: {e}')
            return False

    def login(self):
        self.etapa_atual = 'login'
        try:
            from Fix import login_pc
            if not login_pc(self.driver):
                logging.error('[AutomacaoP2] Falha no login.')
                return False
            logging.info('[AutomacaoP2] Login realizado com sucesso.')
            return True
        except Exception as e:
            logging.error(f'[AutomacaoP2] Erro no login: {e}')
            return False

    def executar_fluxo(self):
        self.etapa_atual = 'fluxo_principal'
        try:
            if not self.driver:
                if not self.iniciar():
                    return False
            if not self.login():
                return False
            executar_fluxo(self.driver)
            return True
        except Exception as e:
            logging.error(f'[AutomacaoP2] Erro ao executar fluxo: {e}')
            return False

    def reiniciar_etapa(self):
        logging.info(f'[AutomacaoP2] Reiniciando etapa: {self.etapa_atual}')
        # Implementar lógica de reinício se necessário

    def finalizar(self):
        if self.driver:
            try:
                self.driver.quit()
                logging.info('[AutomacaoP2] Driver finalizado.')
            except Exception as e:
                logging.error(f'[AutomacaoP2] Erro ao finalizar driver: {e}')
