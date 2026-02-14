import logging
import time

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from .p2b_core import parse_gigs_param
from .p2b_fluxo_lazy import _lazy_import

logger = logging.getLogger(__name__)


def _processar_cabecalho_impugnacoes(driver: WebDriver) -> None:
    """
    Helper: Processa checagem de cabeçalho para impugnações.
    """
    # Lazy load modules
    m = _lazy_import()
    ato_pesquisas = m['ato_pesquisas']
    ato_pesqliq = m['ato_pesqliq']
    criar_gigs = m['criar_gigs']
    
    # Implementação baseada no p2b.py original
    try:
        cabecalho = driver.find_element(By.CSS_SELECTOR, 'mat-card.resumo-processo')
        cor_fundo = cabecalho.value_of_css_property('background-color')
        pass

        # Verifica se é verde: rgb(76, 175, 80) - fase de liquidação
        if 'rgb(76, 175, 80)' in cor_fundo:
            pass
            try:
                # Procurar "Iniciar Execução"
                iniciar_exec = driver.find_element(By.XPATH, "//button[contains(text(),'Iniciar Execução')]")
                iniciar_exec.click()
                time.sleep(1)
                pass
                sucesso, sigilo_ativado = ato_pesquisas(driver)
                if sucesso:
                    # Aplicar visibilidade se necessário
                    if sigilo_ativado:
                        _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
            except Exception as e:
                pass
                # Buscar conclusão homologação de cálculos
                try:
                    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
                    for item in itens:
                        link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento')
                        if 'homologação de cálculos' in link.text.lower() or 'homologacao de calculos' in link.text.lower():
                            link.click()
                            time.sleep(2)
                            pass
                            sucesso, sigilo_ativado = ato_pesquisas(driver)
                            if sucesso:
                                # Aplicar visibilidade se necessário
                                if sigilo_ativado:
                                    _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
                            break
                except Exception as e2:
                    logger.error(f'[FLUXO_PZ] Erro ao buscar conclusão homologação: {e2}')

        # Verifica se é cinza: rgb(144, 164, 174)
        elif 'rgb(144, 164, 174)' in cor_fundo:
            pass

            # 1. Criar gigs antes das pesquisas
            pass
            criar_gigs(driver, "1", "Silvia", "Argos")
            time.sleep(3)  # Aguardar modal fechar completamente e snackbar desaparecer
            # Criar GIGS adicional "1//xs sigilo"
            pass
            criar_gigs(driver, "1", "", "xs sigilo")

            # 2. Executar pesquisas
            pass
            sucesso, sigilo_ativado = ato_pesquisas(driver)
            if sucesso:
                # Aplicar visibilidade se necessário
                if sigilo_ativado:
                    _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
            else:
                pass
        else:
            pass

                # 1. Criar gigs antes de tudo
            pass
            criar_gigs(driver, "1", "Silvia", "Argos")
            time.sleep(3)  # Aguardar modal fechar completamente e snackbar desaparecer
            # Criar GIGS adicional "1/xs sigilo" (observacao='xs sigilo', responsavel='')
            pass
            criar_gigs(driver, "1", "", "xs sigilo")

            # 2. Executar movimento
            pass
            try:
                from atos.wrappers_mov import mov_exec
                mov_ok = mov_exec(driver)
            except Exception as _mov_e:
                logger.error(f'[FLUXO_PZ]  Erro em mov_exec: {_mov_e}')
                mov_ok = False

            # Se não conseguiu executar mov_exec, executar fallback PESQLIQ
            if not mov_ok:
                pass
                try:
                    resultado_pesq = ato_pesqliq(driver)
                    if isinstance(resultado_pesq, tuple):
                        sucesso, sigilo_ativado = resultado_pesq
                    else:
                        sucesso = resultado_pesq
                        sigilo_ativado = True  # ato_pesqliq ativa sigilo internamente
                    if sucesso:
                        if sigilo_ativado:
                            _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
                    else:
                        pass
                except Exception as _e_pesq:
                    logger.error(f'[FLUXO_PZ]  Erro no fallback ato_pesqliq: {_e_pesq}')
            else:
                # 3. Fechar aba atual para voltar ao processo
                pass
                try:
                    driver.close()
                    if len(driver.window_handles) > 0:
                        driver.switch_to.window(driver.window_handles[-1])
                        pass
                    else:
                        pass
                except Exception as close_error:
                    logger.error(f'[FLUXO_PZ]  Erro ao fechar aba: {close_error}')

                # 4. Executar pesquisas na aba do processo
                pass
                sucesso, sigilo_ativado = ato_pesquisas(driver)
                if sucesso:
                    # Aplicar visibilidade se necessário
                    if sigilo_ativado:
                        _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
                else:
                    pass

        time.sleep(1)
    except Exception as cabecalho_error:
        logger.error(f'[FLUXO_PZ] Erro ao verificar cor do cabeçalho para impugnações: {cabecalho_error}')


def _processar_checar_cabecalho(driver: WebDriver) -> None:
    """
    Helper: Processa checagem de cabeçalho para "Ante a notícia de descumprimento".
    """
    # Lazy load modules
    m = _lazy_import()
    ato_pesquisas = m['ato_pesquisas']
    ato_pesqliq = m['ato_pesqliq']
    criar_gigs = m['criar_gigs']
    
    try:
        cabecalho = driver.find_element(By.CSS_SELECTOR, 'mat-card.resumo-processo')
        cor_fundo = cabecalho.value_of_css_property('background-color')
        pass

        # Verifica se é cinza: rgb(144, 164, 174)
        if 'rgb(144, 164, 174)' in cor_fundo:
            pass
            sucesso, sigilo_ativado = ato_pesquisas(driver)
            if sucesso:
                # Aplicar visibilidade se necessário
                if sigilo_ativado:
                    _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
        else:
            pass
            dias, responsavel, observacao = parse_gigs_param('1/SILVIA/Argos')
            criar_gigs(driver, dias, responsavel, observacao)
            time.sleep(3)  # Aguardar modal fechar completamente e snackbar desaparecer
            # Criar GIGS adicional "1/xs sigilo" (observacao='xs sigilo', responsavel='')
            pass
            criar_gigs(driver, "1", "", "xs sigilo")
            # Executar ato_pesqliq como ação secundária
            sucesso, sigilo_ativado = ato_pesqliq(driver)
            if sucesso:
                # Aplicar visibilidade se necessário
                if sigilo_ativado:
                    _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
    except Exception as cabecalho_error:
        logger.error(f'[FLUXO_PZ] Erro ao verificar cor do cabeçalho: {cabecalho_error}')


def _executar_visibilidade_sigilosos(driver: WebDriver, sigilo_ativado: bool, debug: bool = False) -> None:
    """
    Helper: Executa visibilidade para sigilosos se necessário.
    """
    # Implementação será movida para helper específico
    pass