import logging
logger = logging.getLogger(__name__)

"""
Fix.extracao_bndt - Rotinas BNDT.

Separado de Fix.extracao para reduzir tamanho do arquivo principal.
"""

import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from Fix.selenium_base.click_operations import aguardar_e_clicar
from Fix.selenium_base.wait_operations import esperar_url_conter
from Fix.utils_observer import aguardar_renderizacao_nativa
from Fix.log import logger


def bndt(driver, inclusao=False, debug=False, **kwargs):
    """
    Executa rotinas BNDT - versão refatorada processando ambos os polos.
    Orquestrador principal que coordena as etapas.

    Nota: aceita `debug` e `**kwargs` para compatibilidade com chamadas
    que possam passar parâmetros extras (ex: via executor genérico).
    """
    # Log explícito do valor recebido para diagnosticar chamadas incorretas
    try:
        logger.info(f'BNDT: parâmetro inclusao recebido: {inclusao!r} (tipo: {type(inclusao)})')
    except Exception:
        pass
    operacao = "Inclusão" if inclusao else "Exclusão"
    logger.info(f'Iniciando operação BNDT: {operacao}')

    main_window = driver.current_window_handle
    nova_aba = None
    erro_classe = False

    try:
        # Etapa 1: Validar localização
        _bndt_validar_localizacao(driver)

        # Tentativa prévia: abrir BNDT via URL/API (igual ao comportamento da extensão maisPJe)
        # Extrai id do processo da URL atual e tenta abrir /pjekz/processo/{idProcesso}/bndt?maisPje=excluir
        try:
            import re
            current = driver.current_url or ''
            m = re.search(r"/processo/(\d+)/detalhe", current)
            if m:
                idproc = m.group(1)
                base = current.split('/processo/')[0]
                target = f"{base}/pjekz/processo/{idproc}/bndt?maisPje=excluir"
                try:
                    driver.execute_script("window.open(arguments[0], '_blank')", target)
                    logger.info(f'BNDT: aberta aba via API: {target}')
                except Exception as e:
                    logger.warning(f'BNDT: falha ao abrir via API ({e}), continuará com fluxo UI')
            else:
                logger.info('BNDT: id do processo não encontrado na URL; usando fluxo UI')
        except Exception as e:
            logger.warning(f'BNDT: erro na etapa de abertura via API: {e}')

        # Etapa 2: Abrir menu e ícone (fallback/compatibilidade)
        _bndt_abrir_menu(driver)
        _bndt_clicar_icone(driver)

        # Etapa 3: Abrir nova aba
        main_window, nova_aba = _bndt_abrir_nova_aba(driver)

        # PROCESSAR POLOS: exclusão trata Ativo + Passivo (como a.py), inclusão mantém Passivo
        polos = ['Passivo'] if inclusao else ['Ativo', 'Passivo']
        sucesso = False

        for polo in polos:
            logger.info(f'============ Processando Polo {polo} ============')

            # 1. Clicar no botão do polo
            logger.info(f'Procurando botão de polo {polo}...')
            try:
                if not aguardar_e_clicar(driver, f"//input[@value='{polo}']/ancestor::mat-radio-button | //mat-radio-button[@value='{polo}']", timeout=5, by=By.XPATH):
                    raise Exception('botão de polo não clicou')
                logger.info(f'Polo {polo} selecionado')
                time.sleep(0.5)
            except Exception as e:
                logger.error(f'Erro ao selecionar polo {polo}: {e}')
                continue

            # 2. Selecionar operação (Inclusão ou Exclusão)
            if not _bndt_selecionar_operacao_para_polo(driver, inclusao, polo):
                logger.warning(f'Falha ao selecionar operação para polo {polo}, continuando...')
                continue

            # 3. Verificar se existe mensagem "Não existem partes a serem selecionadas"
            try:
                no_reg_elems = driver.find_elements(By.CSS_SELECTOR, '#tabela-registros-bndt div[class*="mensagem"], pje-bndt-partes-sem-registro .mensagem, mat-card .mensagem, div.mensagem.ng-star-inserted')
                for elem in no_reg_elems:
                    texto_no_reg = (elem.text or '').strip().lower()
                    if ('não há registros' in texto_no_reg or
                        'não há registros disponíveis' in texto_no_reg or
                        'não existem partes a serem selecionadas' in texto_no_reg):
                        logger.info(f'Polo {polo}: "{elem.text}" — nada a fazer')
                        raise StopIteration
            except StopIteration:
                continue
            except Exception:
                pass

            # 4. Verificar se há mensagem de classe não permitida
            try:
                msg_classe_elems = driver.find_elements(By.XPATH, "//*[contains(text(),'A classe judicial do processo não pode acessar')]")
                if msg_classe_elems:
                    logger.warning(f'Polo {polo}: Classe judicial do processo não permite cadastro no BNDT')
                    erro_classe = True
                    continue
            except Exception:
                pass

            # 5. Processar seleções (marcar checkboxes)
            _bndt_processar_selecoes_polo(driver, polo)

            # 6. Gravar e confirmar
            _bndt_gravar_e_confirmar_polo(driver, polo)
            sucesso = True

        logger.info(f'============ Finalizando operação {operacao} ============')

        if erro_classe:
            logger.warning('ATENÇÃO: Classe do processo não suporta BNDT!')

        # Fechar aba BNDT
        driver.close()
        driver.switch_to.window(main_window)
        logger.info(f'Operação {operacao} concluída')
        return True if sucesso or not erro_classe else False

    except Exception as e:
        logger.error(f'ERRO na operação {operacao}: {e}')
        # Fechar apenas a aba BNDT (se aberta) para não encerrar o driver principal
        if nova_aba and nova_aba in driver.window_handles:
            try:
                driver.switch_to.window(nova_aba)
                driver.close()
            except Exception:
                pass

        # Garantir retorno para a aba principal original
        if main_window and main_window in driver.window_handles:
            try:
                driver.switch_to.window(main_window)
            except Exception:
                pass
        return False


def _bndt_validar_localizacao(driver):
    """Valida se está em /detalhe."""
    current_url = driver.current_url
    if '/detalhe' not in current_url:
        raise Exception(f'bndt deve ser executado a partir de /detalhe. URL atual: {current_url}')
    logger.info('Confirmado: Estamos na página /detalhe')
    return True


def _bndt_abrir_menu(driver: WebDriver) -> bool:
    """
    Abre o menu hambúrguer com validação robusta.
    """
    try:
        if not aguardar_e_clicar(driver, 'i.fa-bars.icone-botao-menu', timeout=10):
            raise TimeoutException('Não clicou menu hambúrguer')
        logger.info('Menu hambúrguer clicado')
        time.sleep(0.2)
        return True
    except TimeoutException:
        logger.error('Menu hambúrguer não encontrado')
        return False
    except Exception as e:
        logger.error(f'Erro ao abrir menu: {e}')
        return False


def _bndt_clicar_icone(driver: WebDriver) -> bool:
    """
    Clica no ícone BNDT com validação robusta.
    """
    try:
        if not aguardar_e_clicar(driver, 'i.fas.fa-money-check-alt.icone-padrao', timeout=10):
            raise TimeoutException('Não clicou ícone BNDT')
        logger.info('Ícone BNDT clicado')
        time.sleep(0.3)
        return True
    except TimeoutException:
        logger.error('Ícone BNDT não encontrado')
        return False
    except Exception as e:
        logger.error(f'Erro ao clicar ícone BNDT: {e}')
        return False


def _bndt_abrir_nova_aba(driver):
    """Abre nova aba BNDT e retorna seu handle."""
    main_window = driver.current_window_handle
    nova_aba_handle = aguardar_nova_aba(driver, main_window, timeout=15)

    all_windows = driver.window_handles
    nova_aba = [w for w in all_windows if w != main_window]
    if not nova_aba:
        raise Exception('Nova aba BNDT não foi criada')

    nova_aba = nova_aba[-1]
    driver.switch_to.window(nova_aba)
    if not esperar_url_conter(driver, '/bndt', timeout=15):
        raise Exception('Timeout esperando URL da aba BNDT')

    time.sleep(0.5)
    if not aguardar_renderizacao_nativa(driver, 'mat-card, mat-radio-group, button', 'aparecer', timeout=10):
        logger.warning('AVISO: Elementos podem não ter carregado: seletor mat-card, mat-radio-group, button')
    else:
        logger.info('Elementos da página BNDT detectados')

    logger.info(f'Nova aba BNDT aberta: {driver.current_url}')
    return main_window, nova_aba


def _bndt_selecionar_operacao(driver, inclusao):
    """Seleciona Inclusão ou Exclusão."""
    operacao = "Inclusão" if inclusao else "Exclusão"

    try:
        from Fix.core import wait_for_page_load
        wait_for_page_load(driver, timeout=10)
    except Exception as e:
        logger.warning(f'AVISO: Página pode não ter carregado: {e}')

    if inclusao:
        try:
            try:
                inp = driver.find_element(By.XPATH, "//input[@name='mat-radio-group-1' and @value='INCLUSAO']")
                checked = False
                try:
                    checked = inp.is_selected() or inp.get_attribute('checked') or inp.get_attribute('aria-checked') == 'true'
                except Exception:
                    checked = False
                if checked:
                    logger.info('BNDT: Inclusão já selecionada — sem ação necessária')
                    return True
                else:
                    try:
                        parent = inp.find_element(By.XPATH, 'ancestor::mat-radio-button')
                        parent.click()
                        logger.info('BNDT: Radio Inclusão clicado (detected unchecked -> clicked)')
                        time.sleep(0.5)
                        return True
                    except Exception:
                        logger.info('BNDT: Inclusão requisitada — assumindo opção padrão já selecionada')
                        return True
            except Exception:
                logger.info('BNDT: Inclusão requisitada — assumindo opção padrão já selecionada')
                return True
        except Exception as e:
            logger.warning(f'BNDT: Falha ao verificar radio Inclusão, mas prosseguindo sem clique: {e}')
            return True

    selectors = [
        (By.XPATH, "//mat-radio-button[@id='mat-radio-7']"),
        (By.XPATH, "//mat-radio-button[contains(@id,'mat-radio-')][.//input[@value='EXCLUSAO'] ]"),
        (By.XPATH, "//mat-radio-button[.//span[contains(text(),'Exclusão')]]"),
        (By.XPATH, "//input[@name='mat-radio-group-1'][@value='EXCLUSAO']/ancestor::mat-radio-button")
    ]

    radio_operacao = None
    for by, selector in selectors:
        try:
            if aguardar_e_clicar(driver, selector, timeout=5, by=by):
                logger.info(f'Radio {operacao} encontrado')
                radio_operacao = selector
                break
        except Exception:
            continue

    if not radio_operacao:
        raise Exception(f'Não foi possível encontrar o radio button de {operacao}')

    logger.info(f'Radio {operacao} clicado')
    time.sleep(0.5)

    try:
        mensagem_nao_existem_partes = driver.find_elements(By.XPATH, "//div[contains(@class, 'mensagem') and contains(text(), 'Não existem partes a serem selecionadas')]")
        if mensagem_nao_existem_partes:
            logger.info('BNDT: Não existem partes a serem selecionadas — operação cumprida sem seleções')
            return True
    except Exception as e:
        logger.warning(f'BNDT: Erro ao verificar mensagem de partes não existentes: {e}')


def _bndt_selecionar_operacao_para_polo(driver, inclusao, polo):
    """Seleciona Inclusão ou Exclusão para um polo específico."""
    operacao = "Inclusão" if inclusao else "Exclusão"
    tipo_operacao = "INCLUSAO" if inclusao else "EXCLUSAO"

    logger.info(f'Selecionando operação: {operacao} para polo {polo}')

    try:
        if aguardar_e_clicar(driver, f"//input[@value='{tipo_operacao}']/ancestor::mat-radio-button | //mat-radio-button[@value='{tipo_operacao}']", timeout=5, by=By.XPATH):
            logger.info(f'Operação {operacao} selecionada para polo {polo}')
            time.sleep(0.5)
            return True
        raise Exception('botão de operação não clicou')
    except Exception as e:
        logger.warning(f'Erro ao selecionar operação {operacao} no polo {polo}: {e}')
        return False


def _bndt_processar_selecoes(driver):
    """Seleciona o checkbox de "Selecionar todos" se disponível."""
    selectors = [
        (By.XPATH, "//mat-checkbox[.//span[contains(text(),'Selecionar todos')]]//label"),
        (By.XPATH, "//mat-checkbox[.//span[contains(text(),'Selecionar todos')]]//input[@type='checkbox']"),
        (By.XPATH, "//span[contains(@class,'mat-checkbox-label')][contains(text(),'Selecionar todos')]/ancestor::mat-checkbox//label"),
        (By.XPATH, "//input[@type='checkbox'][@aria-label='Selecionar todos']/ancestor::mat-checkbox//label")
    ]

    for by, selector in selectors:
        try:
            chk_todos = driver.find_element(by, selector)
            driver.execute_script('arguments[0].click();', chk_todos)
            logger.info('Checkbox "Selecionar todos" clicado (sem aguardar elementos extras)')
            time.sleep(0.25)
            return
        except Exception:
            continue

    logger.warning('Checkbox "Selecionar todos" não encontrado — ação concluída sem seleção adicional')


def _bndt_processar_selecoes_polo(driver, polo):
    """Procurar e clicar em todos os checkboxes de débito/crédito para um polo específico."""
    logger.info(f'Procurando checkboxes para marcar no polo {polo}...')
    try:
        labels = driver.find_elements(By.CSS_SELECTOR, 'pje-bndt-exclusao label[for*="debito"][for*="-input"], pje-bndt-inclusao label[for*="debito"][for*="-input"]')
        if not labels:
            logger.warning(f'Nenhum checkbox encontrado no polo {polo}')
            return

        for label in labels:
            try:
                label.click()
                time.sleep(0.1)
            except Exception as e:
                logger.warning(f'Erro ao clicar checkbox: {e}')

        logger.info(f'{len(labels)} checkbox(es) marcados no polo {polo}')
        time.sleep(0.5)
    except Exception as e:
        logger.warning(f'Erro ao marcar checkboxes no polo {polo}: {e}')


def _bndt_gravar_e_confirmar(driver, main_window, nova_aba):
    """Clica Gravar, confirma e fecha aba."""
    selectors_gravar = [
        (By.XPATH, "//button[.//span[contains(text(),'Gravar')]]"),
        (By.XPATH, "//button[contains(@class,'mat-raised-button')][contains(text(),'Gravar')]"),
        (By.CSS_SELECTOR, "button[mat-raised-button]:contains('Gravar')"),
        (By.XPATH, "//button[@type='submit'][contains(text(),'Gravar')]"),
    ]

    btn_gravar = None
    for by, selector in selectors_gravar:
        try:
            if aguardar_e_clicar(driver, selector, timeout=5, by=by):
                logger.info('Botão Gravar encontrado')
                btn_gravar = selector
                break
        except Exception:
            continue

    if not btn_gravar:
        raise Exception('Botão Gravar não encontrado')

    logger.info('Botão Gravar clicado')
    time.sleep(1)

    if aguardar_e_clicar(driver, "//button[.//span[contains(text(),'Sim')]]", timeout=3, by=By.XPATH):
        logger.info('Confirmação clicada')
        time.sleep(1)

    driver.close()
    driver.switch_to.window(main_window)
    logger.info('Aba BNDT fechada')


def _bndt_gravar_e_confirmar_polo(driver, polo):
    """Clica Gravar e confirma para um polo específico."""
    logger.info(f'Procurando botão Gravar para polo {polo}...')
    btn_gravar = None
    selectors_gravar = [
        (By.XPATH, "//button[.//span[contains(text(),'Gravar')]]"),
        (By.XPATH, "//button[contains(@class,'mat-raised-button')][contains(text(),'Gravar')]"),
        (By.XPATH, "//pje-bndt-exclusao//button[contains(text(),'Gravar')] | //pje-bndt-inclusao//button[contains(text(),'Gravar')]"),
    ]
    for by, selector in selectors_gravar:
        try:
            if aguardar_e_clicar(driver, selector, timeout=3, by=by):
                logger.info('Botão Gravar encontrado')
                btn_gravar = selector
                break
        except Exception:
            continue

    if not btn_gravar:
        logger.warning(f'Botão Gravar não encontrado no polo {polo}')
        return


    logger.info('Botão Gravar clicado')
    time.sleep(0.5)

    try:
        if aguardar_e_clicar(driver, "//div[contains(@class,'cdk-overlay-pane')]//button[contains(.,'Sim')]", timeout=3, by=By.XPATH):
            logger.info('Confirmação "Sim" clicada')
            time.sleep(0.5)
    except Exception:
        logger.warning('Botão "Sim" não encontrado (pode não ser necessário)')

    try:
        if aguardar_renderizacao_nativa(driver, 'simple-snack-bar', 'aparecer', 3):
            aviso = driver.find_element(By.CSS_SELECTOR, 'simple-snack-bar')
            texto_aviso = aviso.text
            logger.info(f'Aviso: {texto_aviso}')

            if 'Excluído registro de' in texto_aviso or 'Partes excluídas' in texto_aviso or 'Incluído registro de' in texto_aviso or 'Partes incluídas' in texto_aviso:
                logger.info(f'Operação no polo {polo} concluída com sucesso')
                try:
                    btn_close = aviso.find_element(By.CSS_SELECTOR, 'button')
                    btn_close.click()
                except Exception:
                    pass
            elif 'A classe judicial do processo não pode acessar' in texto_aviso:
                logger.warning('Classe judicial não permite BNDT')
            else:
                logger.warning(f'Mensagem inesperada: {texto_aviso}')
    except Exception:
        logger.warning('Nenhum aviso detectado')