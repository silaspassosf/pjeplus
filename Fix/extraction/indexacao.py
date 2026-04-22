import re
import time
from typing import Optional, List, Tuple, Union, Any, Callable
from urllib.parse import urlparse

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

from Fix.utils_observer import aguardar_renderizacao_nativa
from Fix.log import logger
from Fix.abas import validar_conexao_driver, forcar_fechamento_abas_extras

try:
    from atos.core import verificar_carregamento_detalhe
    _ATOS_CORE_AVAILABLE = True
except ImportError:
    _ATOS_CORE_AVAILABLE = False

try:
    from PEC.core import reiniciar_driver_e_logar_pje
except Exception:
    reiniciar_driver_e_logar_pje = None


def filtrofases(driver: WebDriver, fases_alvo: List[str] = ['liquidação', 'execução'], tarefas_alvo: Optional[List[str]] = None, seletor_tarefa: str = 'Tarefa do processo') -> bool:
    try:
        fase_element = None
        try:
            fase_element = driver.find_element(By.XPATH, "//span[contains(text(), 'Fase processual')]")
        except Exception:
            try:
                seletor_fase = 'span.ng-tns-c82-22.ng-star-inserted'
                for elem in driver.find_elements(By.CSS_SELECTOR, seletor_fase):
                    if 'Fase processual' in elem.text:
                        fase_element = elem
                        break
            except Exception:
                logger.error('[ERRO] Não encontrou o seletor de fase processual.')
                return False
        if not fase_element:
            logger.error('[ERRO] Não encontrou o seletor de fase processual.')
            return False
        driver.execute_script("arguments[0].click();", fase_element)
        time.sleep(1)
        painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
        painel = None
        for _ in range(10):
            try:
                painel = driver.find_element(By.CSS_SELECTOR, painel_selector)
                if painel.is_displayed():
                    break
            except Exception:
                time.sleep(0.3)
        if not painel or not painel.is_displayed():
            logger.error('[ERRO] Painel de opções não apareceu.')
            return False
        fases_clicadas = set()
        opcoes = painel.find_elements(By.XPATH, ".//mat-option")
        for fase in fases_alvo:
            for opcao in opcoes:
                try:
                    texto = opcao.text.strip().lower()
                    if fase in texto and opcao.is_displayed():
                        driver.execute_script("arguments[0].click();", opcao)
                        fases_clicadas.add(fase)
                        time.sleep(0.5)
                        break
                except Exception:
                    continue
        if len(fases_clicadas) == 0:
            logger.error(f'[ERRO] Não encontrou opções {fases_alvo} no painel.')
            return False
        try:
            botao_filtrar = driver.find_element(By.CSS_SELECTOR, 'i.fas.fa-filter')
            driver.execute_script('arguments[0].click();', botao_filtrar)
            time.sleep(1)
        except Exception as e:
            logger.error(f'[ERRO] Não conseguiu clicar no botão de filtrar: {e}')
        # Generalização da seleção de tarefa
        if tarefas_alvo:
            tarefa_element = None
            try:
                tarefa_element = driver.find_element(By.XPATH, f"//span[contains(text(), '{seletor_tarefa}')]")
            except Exception:
                try:
                    seletor = 'span.ng-tns-c82-22.ng-star-inserted'
                    for elem in driver.find_elements(By.CSS_SELECTOR, seletor):
                        if seletor_tarefa in elem.text:
                            tarefa_element = elem
                            break
                except Exception:
                    logger.error(f'[ERRO] Não encontrou o seletor de tarefa: {seletor_tarefa}.')
                    return False
            if not tarefa_element:
                logger.error(f'[ERRO] Não encontrou o seletor de tarefa: {seletor_tarefa}.')
                return False
            driver.execute_script("arguments[0].click();", tarefa_element)
            time.sleep(1)
            painel = None
            painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
            for _ in range(10):
                try:
                    painel = driver.find_element(By.CSS_SELECTOR, painel_selector)
                    if painel.is_displayed():
                        break
                except Exception:
                    time.sleep(0.3)
            if not painel or not painel.is_displayed():
                logger.error('[ERRO] Painel de opções de tarefa não apareceu.')
                return False
            tarefas_clicadas = set()
            opcoes = painel.find_elements(By.XPATH, ".//mat-option")
            for tarefa in tarefas_alvo:
                for opcao in opcoes:
                    try:
                        texto = opcao.text.strip().lower()
                        if tarefa.lower() in texto and opcao.is_displayed():
                            driver.execute_script("arguments[0].click();", opcao)
                            tarefas_clicadas.add(tarefa)
                            time.sleep(0.5)
                            break
                    except Exception:
                        continue
            if len(tarefas_clicadas) == 0:
                logger.error(f'[ERRO] Não encontrou opções {tarefas_alvo} no painel de tarefas.')
                return False
            try:
                botao_filtrar = driver.find_element(By.CSS_SELECTOR, 'i.fas.fa-filter')
                driver.execute_script('arguments[0].click();', botao_filtrar)
                time.sleep(1)
            except Exception as e:
                logger.error(f'[ERRO] Não conseguiu clicar no botão de filtrar para tarefas: {e}')
    except Exception as e:
        logger.error(f'[ERRO] Erro no filtro de fase: {e}')
        return False
    return True


def indexar_processos(driver: WebDriver) -> List[Tuple[str, Optional[WebElement]]]:
    """
    Indexa processos de forma mais robusta, evitando problemas de stale elements
    """
    padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
    processos = []
    
    # Buscar elementos frescos a cada iteração para evitar stale elements
    def obter_linhas_frescas() -> List[WebElement]:
        return driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
    
    linhas = obter_linhas_frescas()
    logger.info(f'[INDEXAR] Encontradas {len(linhas)} linhas para processar')
    
    for idx in range(len(linhas)):
        try:
            # Sempre obter elementos frescos para evitar stale references
            linhas_atuais = obter_linhas_frescas()
            
            # Verificar se o índice ainda é válido
            if idx >= len(linhas_atuais):
                # print(f'[INDEXAR][SKIP] Linha {idx+1}: DOM mudou, menos linhas disponíveis')
                continue
                
            linha = linhas_atuais[idx]
            
            # Extrair texto do processo
            links = linha.find_elements(By.CSS_SELECTOR, 'a')
            texto = ''
            
            if links:
                texto = links[0].text.strip()
            else:
                tds = linha.find_elements(By.TAG_NAME, 'td')
                if tds:
                    texto = tds[0].text.strip()
            
            # Buscar número do processo
            match = padrao_proc.search(texto)
            num_proc = match.group(0) if match else '[sem número]'
            
            # Não armazenar o WebElement (pode ficar stale). Apenas guardar o número
            # O processamento futuro fará reindex por `proc_id` para obter o elemento fresco.
            processos.append((num_proc, None))
            
        except Exception as e:
            logger.info(f'[INDEXAR][ERRO] Linha {idx+1}: {e} (elemento pode ter ficado stale)')
            # Não tentar reindexar - apenas continuar
            continue
    
    logger.info(f'[INDEXAR] Processamento concluído: {len(processos)} processos indexados')
    return processos


def reindexar_linha(driver: WebDriver, proc_id: str) -> Optional[WebElement]:
    """
    Reindexar linha quando elemento fica stale.
    Agora com verificação de acesso negado e melhor tratamento de erros.
    NÃO navega automaticamente - respeita a página atual do módulo.
    """
    try:
        # Verificar se ainda estamos em uma página válida do PJE
        url_atual = driver.current_url
        if 'acesso-negado' in url_atual.lower() or 'access-denied' in url_atual.lower():
                logger.error(f'ACESSO NEGADO detectado na URL: {url_atual}')
                raise Exception(f'RESTART_PEC: Acesso negado detectado - driver quebrado')  # Forçar restart
        
        # Verificar se é uma URL válida do PJE
        if 'pje.trt2.jus.br' not in url_atual:
            logger.error(f'URL não é do PJE: {url_atual}')
            return None
        
        # REMOVIDO: Navegação automática para atividades
        # Cada módulo deve gerenciar sua própria navegação
        logger.info(f'[REINDEXAR] Tentando reindexar na página atual: {url_atual}')
        
        # Buscar linhas na página atual (diferentes seletores dependendo do módulo)
        possible_selectors = [
            'tr.cdk-drag',           # Atividades (PEC)
            'tr',                    # Documentos internos (M1) 
            'tbody tr',              # Outras tabelas
            '.linha-processo',       # Seletor alternativo
        ]
        
        linhas_atuais = []
        for selector in possible_selectors:
            try:
                linhas_temp = driver.find_elements(By.CSS_SELECTOR, selector)
                if linhas_temp:
                    linhas_atuais = linhas_temp
                    logger.info(f'[REINDEXAR] Usando seletor {selector}: {len(linhas_atuais)} linhas encontradas')
                    break
            except:
                continue
        
        if not linhas_atuais:
            logger.error(f'Nenhuma linha encontrada na página com os seletores testados')
            return None
        
        logger.info(f'[REINDEXAR] Buscando {proc_id} entre {len(linhas_atuais)} linhas...')
        for idx, linha_temp in enumerate(linhas_atuais):
            try:
                # Verificar se a linha ainda é válida
                if not linha_temp.is_displayed():
                    continue
                    
                # Buscar número do processo na linha (diferentes estratégias)
                texto_linha = ""
                
                # Estratégia 1: Links
                links = linha_temp.find_elements(By.CSS_SELECTOR, 'a')
                if links:
                    texto_linha = links[0].text.strip()
                else:
                    # Estratégia 2: Células td
                    tds = linha_temp.find_elements(By.TAG_NAME, 'td')
                    if tds:
                        # Procurar em várias células (processo pode estar em diferentes colunas)
                        for td in tds[:3]:  # Verificar as 3 primeiras colunas
                            td_text = td.text.strip()
                            if proc_id in td_text:
                                texto_linha = td_text
                                break
                        if not texto_linha:
                            texto_linha = tds[0].text.strip()
                    else:
                        # Estratégia 3: Texto geral da linha
                        texto_linha = linha_temp.text.strip()
                
                if proc_id in texto_linha:
                    return linha_temp
                    
            except Exception as e:
                # Não logar erros individuais para não poluir - linha pode estar stale mesmo
                continue
        
        logger.error(f'Processo {proc_id} não encontrado nas {len(linhas_atuais)} linhas da página atual')
        return None
        
    except Exception as e:
        logger.error(f'Erro geral na reindexação: {e}')
        return None


def abrir_detalhes_processo(driver: WebDriver, linha: WebElement) -> bool:
    try:
        btn = linha.find_element(By.CSS_SELECTOR, '[mattooltip*="Detalhes do Processo"]')
    except Exception:
        try:
            btn = linha.find_element(By.CSS_SELECTOR, 'button, a')
        except Exception:
            return False
    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
    driver.execute_script("arguments[0].click();", btn)
    return True


def trocar_para_nova_aba(driver: WebDriver, aba_lista_original: str) -> Optional[str]:
    """
    Troca para uma nova aba diferente da aba original da lista.
    Inclui tratamento robusto de erros, verificações adicionais e verificação de carregamento.
    
    Args:
        driver: O driver Selenium
        aba_lista_original: O handle da aba original da lista
        
    Returns:
        str: O handle da nova aba se foi bem-sucedido, None caso contrário
    """
    try:
        # Verificar se o driver está conectado
        if not validar_conexao_driver(driver, "ABAS"):
            logger.error('[ABAS][ERRO] Driver não está conectado ao tentar trocar de aba')
            return None
            
        # Obter lista atual de abas
        try:
            abas = driver.window_handles
            if not abas:
                logger.error('[ABAS][ERRO] Nenhuma aba disponível')
                return None
                
            if len(abas) == 1 and abas[0] == aba_lista_original:
                logger.error('[ABAS][ERRO] Apenas a aba original está disponível, nenhuma nova aba foi aberta')
                return None
                
            # Log melhorado - mostrar apenas a quantidade, não os IDs longos
        except Exception as e:
            logger.error(f'[ABAS][ERRO] Falha ao obter lista de abas: {e}')
            return None
            
        # Tentar trocar para uma aba diferente da original
        for h in abas:
            if h != aba_lista_original:
                try:
                    driver.switch_to.window(h)
                    # Verificar se realmente trocamos de aba
                    atual_handle = driver.current_window_handle
                    if atual_handle == h:
                        # Log com URL útil em vez de ID longo
                        try:
                            url_atual = driver.current_url
                            parsed = urlparse(url_atual)
                            path_parts = parsed.path.strip('/').split('/')
                            if len(path_parts) >= 2:
                                url_legivel = f"{path_parts[-2]}/{path_parts[-1]}"
                            else:
                                url_legivel = parsed.path or url_atual[-30:]
                        except Exception:
                            url_legivel = None
                        # VERIFICAÇÃO DE CARREGAMENTO: Se for página /detalhe, verificar se carregou
                        try:
                            current_url = driver.current_url or ''
                            if '/detalhe' in current_url.lower() and _ATOS_CORE_AVAILABLE:
                                if not verificar_carregamento_detalhe(driver, timeout_inicial=2.0, max_tentativas=3, log=True):
                                    logger.warning('[ABAS][ALERTA] Falha no carregamento da página /detalhe, mas continuando...')
                            # Se não temos o helper ATOS_CORE ou ainda assim a página não carregou, aplicar refresh rápido
                            if '/detalhe' in (current_url or '').lower():
                                try:
                                    # checagem rápida: conteúdo mínimo presente em 3s
                                    if not aguardar_renderizacao_nativa(driver, 'button', 'aparecer', 3):
                                        raise TimeoutException('Conteúdo mínimo não apareceu rapidamente')
                                except TimeoutException:
                                    logger.info('[ABAS][ALERTA] /detalhe não apresentou conteúdo rápido; recarregando aba e aguardando')
                                    try:
                                        driver.refresh()
                                    except Exception as e_ref:
                                        logger.info(f'[ABAS][ALERTA] Falha ao refresh da aba: {e_ref}')
                                    if not aguardar_renderizacao_nativa(driver, 'button', 'aparecer', 15):
                                        raise TimeoutException('Conteúdo mínimo não apareceu após refresh')
                        except Exception as e:
                            logger.error(f'[ABAS][ALERTA] Erro na verificação de carregamento: {e}')
                        
                        return h
                    else:
                        logger.warning(f'[ABAS][ALERTA] Troca para aba {h} falhou, handle atual é: {atual_handle}')
                except Exception as e:
                    logger.error(f'[ABAS][ERRO] Erro ao trocar para aba {h}: {e}')
                    continue
                    
        # Se chegou aqui, não conseguiu trocar para nenhuma nova aba
        logger.error('[ABAS][ERRO] Não foi possível trocar para nenhuma nova aba')
        return None
    except Exception as e:
        logger.error(f'[ABAS][ERRO] Erro geral ao tentar trocar de aba: {e}')
        return None


def _indexar_preparar_contexto(driver: WebDriver, max_processos: Optional[int] = None) -> Tuple[Optional[str], Optional[List[Tuple[str, Optional[WebElement]]]]]:
    """Valida conexão e indexa processos, retornando (aba_original, lista_processos) ou (None, None)."""
    import time
    
    conexao_inicial = validar_conexao_driver(driver, "FLUXO")
    if conexao_inicial == "FATAL":
        logger.info('[FLUXO][FATAL] Driver inutilizável no início do processamento!')
        return None, None
    elif not conexao_inicial:
        logger.info('[FLUXO][ERRO] Driver não está conectado no início do processamento!')
        return None, None
    
    try:
        aba_lista_original = driver.current_window_handle
        logger.info(f'[FLUXO] Aba da lista capturada: {aba_lista_original}')
    except Exception as e:
        logger.info(f'[FLUXO][ERRO] Falha ao capturar aba da lista: {e}')
        return None, None
    
    try:
        processos = indexar_processos(driver)
        if not processos:
            logger.info('[FLUXO][ALERTA] Nenhum processo encontrado para indexação')
            return None, None
    except Exception as e:
        logger.info(f'[FLUXO][ERRO] Falha ao indexar processos: {e}')
        return None, None
    
    if max_processos and max_processos > 0 and max_processos < len(processos):
        processos = processos[:max_processos]
        logger.info(f'[FLUXO] Limitando processamento a {max_processos} processos')
    
    return aba_lista_original, processos


def _indexar_tentar_reindexar(driver: WebDriver, proc_id: str, max_tentativas: int = 3) -> Optional[WebElement]:
    """
    Tenta reindexar linha com múltiplas tentativas.
    
    Args:
        driver: Instância do WebDriver Selenium
        proc_id: ID do processo a reindexar
        max_tentativas: Número máximo de tentativas (padrão 3)
    
    Returns:
        WebElement da linha reindexada ou None se falhar
    """
    import time
    for tent in range(max_tentativas):
        try:
            linha = reindexar_linha(driver, proc_id)
            if linha:
                return linha
            logger.info(f'[PROCESSAR] Tentativa {tent+1}/{max_tentativas} - Reindexando')
            time.sleep(1)
        except Exception as e:
            logger.info(f'[PROCESSAR][ERRO] Falha na tentativa {tent+1}: {e}')
            time.sleep(1)
    return None


def _indexar_tentar_trocar_aba(driver: WebDriver, aba_original: str, max_tentativas: int = 3) -> Optional[str]:
    """
    Tenta trocar para nova aba com múltiplas tentativas.
    
    Args:
        driver: Instância do WebDriver Selenium
        aba_original: Handle da aba original
        max_tentativas: Número máximo de tentativas (padrão 3)
    
    Returns:
        Handle da nova aba ou None se falhar
    """
    import time
    for tent in range(max_tentativas):
        try:
            nova_aba = trocar_para_nova_aba(driver, aba_original)
            if nova_aba:
                # Log melhorado - mostrar URL em vez de ID
                try:
                    url_atual = driver.current_url
                    parsed = urlparse(url_atual)
                    path_parts = parsed.path.strip('/').split('/')
                    if len(path_parts) >= 2:
                        url_legivel = f"{path_parts[-2]}/{path_parts[-1]}"
                    else:
                        url_legivel = parsed.path or url_atual[-30:]
                    logger.info(f'[PROCESSAR] Trocado para nova aba: {url_legivel}')
                except:
                    logger.info(f'[PROCESSAR] Trocado para nova aba')
                time.sleep(0.5)
                return nova_aba
        except Exception as e:
            logger.info(f'[PROCESSAR][ERRO] Falha ao trocar aba (tent {tent+1}): {e}')
            time.sleep(1)
    return None


# ---------------------------------------------------------------------------
# Fluxo de indexação e processamento em lista
# (anterior Fix/extracao_indexacao_fluxo.py)
# ---------------------------------------------------------------------------

from Fix.monitoramento_progresso_unificado import carregar_progresso_unificado


def _indexar_processar_item(driver, proc_id, linha, aba_lista_original, callback):
    """Processa um item individual da lista: abre, executa callback, limpa abas."""
    logger.info(f'[PROCESSAR] Processando {proc_id}...')

    conexao_status = validar_conexao_driver(driver, "PROCESSAR")
    if conexao_status == "FATAL":
        logger.error(f'[PROCESSAR][FATAL] Contexto descartado - interrompendo')
        return "FATAL"
    elif not conexao_status:
        logger.error(f'[PROCESSAR][ERRO] Conexão perdida para {proc_id}')
        return "ERRO"

    try:
        atual_url = driver.current_url
        if 'acesso-negado' in atual_url.lower() or 'login.jsp' in atual_url.lower():
            logger.warning(f'[PROCESSAR][ALERTA] Acesso negado detectado. Reiniciando driver...')
            novo_driver = reiniciar_driver_e_logar_pje(driver, log=True) if reiniciar_driver_e_logar_pje else None
            if not novo_driver:
                logger.error('[PROCESSAR][ERRO] Falha ao reiniciar driver')
                return "ERRO"
            driver = novo_driver
            aba_lista_original = driver.window_handles[0] if driver.window_handles else None

        if "escaninho" not in atual_url and "documentos" not in atual_url:
            if not aba_lista_original or aba_lista_original not in driver.window_handles:
                return "ERRO"
            driver.switch_to.window(aba_lista_original)
            logger.info('[PROCESSAR] Voltado para aba da lista')
    except Exception as e:
        logger.error(f'[PROCESSAR][ERRO] Falha ao verificar URL: {e}')
        return "ERRO"

    linha_atual = _indexar_tentar_reindexar(driver, proc_id)
    if not linha_atual:
        logger.error(f'[PROCESSAR][ERRO] Não reindexado após 3 tentativas')
        return "ERRO"

    try:
        if not abrir_detalhes_processo(driver, linha_atual):
            logger.error(f'[PROCESSAR][ERRO] Botão de detalhes não encontrado')
            return "ERRO"
    except Exception as e:
        logger.error(f'[PROCESSAR][ERRO] Falha ao abrir detalhes: {e}')
        return "ERRO"

    time.sleep(1)

    nova_aba = _indexar_tentar_trocar_aba(driver, aba_lista_original)
    if not nova_aba:
        logger.error(f'[PROCESSAR][ERRO] Nova aba não aberta após 3 tentativas')
        return "ERRO"

    try:
        time.sleep(1)

        def callback_wrapper(driver_inner):
            driver_inner._numero_processo_lista = proc_id
            return callback(driver_inner)

        logger.debug(f'[PROCESSAR] Chamando callback para {proc_id}')
        try:
            callback_result = callback_wrapper(driver)
            logger.debug(f'[PROCESSAR] callback_result for {proc_id}: {callback_result}')
            if callback_result:
                logger.info(f'[PROCESSAR] Callback OK para {proc_id}')
                conexao_pos = validar_conexao_driver(driver, "POS-CALLBACK")
                if conexao_pos == "FATAL":
                    logger.error(f'[PROCESSAR][FATAL] Contexto perdido durante callback')
                    return "FATAL"
            else:
                logger.error(f'[PROCESSAR][ERRO] Callback retornou False')
                return "ERRO"
        except Exception as e:
            logger.error(f'[PROCESSAR][ERRO] Falha inesperada em callback: {e}')
            return "ERRO"
    except Exception as e:
        logger.error(f'[PROCESSAR][ERRO] Falha inesperada em callback: {e}')
        return "ERRO"
    finally:
        if hasattr(driver, '_numero_processo_lista'):
            delattr(driver, '_numero_processo_lista')

    logger.info('[PROCESSAR] Callback completado. Sincronizando driver...')
    time.sleep(0.3)

    limpeza = forcar_fechamento_abas_extras(driver, aba_lista_original)
    if limpeza == "FATAL":
        logger.error(f'[PROCESSAR][FATAL] Contexto perdido durante limpeza')
        return "FATAL"
    elif not limpeza:
        logger.error(f'[PROCESSAR][ALERTA] Limpeza de abas falhou (não é fatal)')

    return "SUCESSO"


def indexar_e_processar_lista(driver, callback, seletor_btn=None, modo='tabela', max_processos=None, log=True, tipo_execucao: str = None):
    """
    Processa lista de processos com tratamento robusto de conexão e abas.
    Estratégia: reindexa a lista completa antes de cada processamento.
    """
    logger.info('[FLUXO] Iniciando indexação da lista de processos...')

    aba_original, processos_iniciais = _indexar_preparar_contexto(driver, max_processos)
    if not aba_original or not processos_iniciais:
        return False

    try:
        processos_iniciais = indexar_processos(driver)
        if not processos_iniciais:
            logger.info('[FLUXO] Nenhum processo encontrado para processar')
            return False

        if tipo_execucao:
            try:
                progresso = carregar_progresso_unificado(tipo_execucao, suppress_load_log=True)
                executados = progresso.get('processos_executados', []) or []
                executados_set = set(executados)
                executados_digits = set([re.sub(r'\D', '', e) for e in executados_set if e])

                def _is_executado(pid: str) -> bool:
                    if not pid:
                        return False
                    if pid in executados_set:
                        return True
                    return re.sub(r'\D', '', pid) in executados_digits

                processos_filtrados = [(pid, linha) for (pid, linha) in processos_iniciais if not _is_executado(pid)]
                skipped = len(processos_iniciais) - len(processos_filtrados)
                if skipped:
                    logger.info(f'[FLUXO] {skipped} processos pulados (já executados)')
                processos_iniciais = processos_filtrados
            except Exception as e:
                logger.info(f'[FLUXO][AVISO] Falha ao filtrar processos via progresso: {e}')

        logger.info(f'[FLUXO] {len(processos_iniciais)} processos para processamento')
    except Exception as e:
        logger.info(f'[FLUXO][ERRO] Falha ao indexar lista inicial: {e}')
        return False

    processados = 0
    erros = 0
    fatal = False

    for idx, (proc_id, linha_original) in enumerate(processos_iniciais):
        if max_processos and processados >= max_processos:
            logger.info(f'[FLUXO] Limite de {max_processos} processos atingido')
            break

        logger.info(f'[FLUXO] Processando item {idx+1}/{len(processos_iniciais)}: {proc_id}')
        resultado = _indexar_processar_item(driver, proc_id, linha_original, aba_original, callback)

        if resultado == "SUCESSO":
            processados += 1
        elif resultado == "FATAL":
            fatal = True
            logger.info(f'[FLUXO][FATAL] Interrompendo processamento')
            break
        else:
            erros += 1

    logger.info(f'[FLUXO] Concluído: {processados} sucesso, {erros} erros')

    if fatal:
        logger.error('[FLUXO][FATAL] Driver context fatal - aborting')
        raise SystemExit('Driver context fatal - aborting')

    return processados > 0

