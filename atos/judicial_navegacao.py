"""
judicial_navegacao.py - Funções de navegação para atos judiciais
====================================================================

Funções para abertura de tarefas, navegação entre estados do PJE,
limpeza de overlays e transição entre URLs.
"""

from Fix.core import aguardar_e_clicar, safe_click, logger, esperar_url_conter
from Fix.selectors_pje import BTN_TAREFA_PROCESSO
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from Fix.core import safe_click_no_scroll

from typing import Optional, Tuple
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
import time


def abrir_tarefa_processo(driver: WebDriver) -> Tuple[bool, bool]:
    """
    Abre a tarefa do processo atual e troca para nova aba se necessário.

    Returns:
        Tuple[bool, bool]: (sucesso_abertura, ja_em_estado_final)
        - sucesso_abertura: True se conseguiu abrir a tarefa
        - ja_em_estado_final: True se já estava em /assinar, /minutar ou /conclusao
    """
    try:
        logger.info('[NAVEGAÇÃO] Abrindo tarefa do processo...')
        abas_antes = set(driver.window_handles)

        # Obter botão da tarefa
        btn_abrir_tarefa = aguardar_e_clicar(driver, BTN_TAREFA_PROCESSO, timeout=10, retornar_elemento=True)
        if not btn_abrir_tarefa:
            logger.error('[NAVEGAÇÃO] Botão "Abrir tarefa do processo" não encontrado!')
            return False, False

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
            logger.info(f'[NAVEGAÇÃO] ⏭ Tarefa "{tarefa_do_botao}" contém "assinar" — ato pronto')
            return True, True

        # Clicar para abrir tarefa
        if not safe_click(driver, btn_abrir_tarefa):
            logger.error('[NAVEGAÇÃO] Falha ao clicar em "Abrir tarefa do processo"')
            return False, False

        # Aguardar nova aba
        nova_aba = None
        try:
            WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > len(abas_antes))
            abas_depois = set(driver.window_handles)
            novas_abas = abas_depois - abas_antes
            if novas_abas:
                nova_aba = novas_abas.pop()
        except TimeoutException:
            logger.info('[NAVEGAÇÃO] Nenhuma nova aba detectada (continuando na mesma aba)')

        if nova_aba:
            driver.switch_to.window(nova_aba)
            logger.info('[NAVEGAÇÃO] Foco trocado para nova aba')

            # Aguardar carregamento mínimo
            try:
                WebDriverWait(driver, 8).until(lambda d: d.find_element(By.TAG_NAME, 'body'))
            except Exception:
                pass

        # Verificar estado final após abertura
        current_url = (driver.current_url or '').lower()
        ja_em_estado_final = ('/assinar' in current_url or
                            '/minutar' in current_url or
                            '/conclusao' in current_url)

        if ja_em_estado_final:
            logger.info(f'[NAVEGAÇÃO] Após abertura: já em estado final ({current_url})')

        return True, ja_em_estado_final

    except Exception as e:
        logger.error(f'[NAVEGAÇÃO] Erro ao abrir tarefa: {e}')
        return False, False


def limpar_overlays(driver: WebDriver) -> None:
    """
    Remove overlays e elementos flutuantes que podem interferir nos cliques.
    """
    try:
        # Overlays principais
        overlays = driver.find_elements(By.CSS_SELECTOR, '.cdk-overlay-backdrop, .mat-dialog-container')
        if overlays:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.15)
            logger.info('[NAVEGAÇÃO] Overlays removidos')
    except Exception as e:
        logger.debug(f'[NAVEGAÇÃO] Erro ao limpar overlays: {e}')


def navegar_para_conclusao(driver: WebDriver) -> bool:
    """
    Navega da tarefa atual para "Conclusão ao Magistrado".

    Estratégia:
    1. Tenta clicar diretamente em "Conclusão ao Magistrado"
    2. Se não disponível, clica em "Análise" primeiro, remove overlays, depois clica em "Conclusão ao Magistrado"
    3. Aguarda URL /conclusao

    Returns:
        bool: True se conseguiu navegar para conclusão
    """
    try:
        logger.info('[NAVEGAÇÃO] Navegando para Conclusão ao Magistrado...')

        # Aguardar botões de transição
        botoes_presentes = True
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-botoes-transicao button'))
            )
        except Exception:
            botoes_presentes = False
            logger.warning('[NAVEGAÇÃO] Botões de transição não carregaram')
            # Fallback rápido: aguardar 2s e dar refresh para tentar recuperar os botões
            try:
                logger.info('[NAVEGAÇÃO] Tentando refresh rápido em 2s para recarregar botões...')
                time.sleep(2)
                try:
                    driver.refresh()
                except Exception as rerr:
                    logger.debug(f'[NAVEGAÇÃO] Refresh falhou: {rerr}')
                try:
                    WebDriverWait(driver, 6).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-botoes-transicao button'))
                    )
                    botoes_presentes = True
                    logger.info('[NAVEGAÇÃO] Botões detectados após refresh rápido')
                except Exception:
                    logger.warning('[NAVEGAÇÃO] Refresh rápido não recarregou os botões')
            except Exception:
                pass

        # Tentar clique direto em "Conclusão ao Magistrado"
        btn_conclusao_encontrado = False
        try:
            btn_conclusao = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Conclusão ao magistrado']"))
            )
            btn_conclusao.click()
            btn_conclusao_encontrado = True
            logger.info('[NAVEGAÇÃO] Clique direto em "Conclusão ao magistrado" realizado')
        except Exception as e:
            logger.info('[NAVEGAÇÃO] Botão "Conclusão ao magistrado" não disponível imediatamente')

        # Se não encontrou, usar estratégia via "Análise"
        if not btn_conclusao_encontrado:
            logger.info('[NAVEGAÇÃO] Tentando via "Análise"...')

            # Clicar em "Análise"
            try:
                btn_analise = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Análise']"))
                )
                btn_analise.click()
                logger.info('[NAVEGAÇÃO] Clique em "Análise" realizado')

                # Aguardar transição para /transicao
                if not esperar_url_conter(driver, '/transicao', timeout=8):
                    logger.warning(f'[NAVEGAÇÃO] URL não contém /transicao após Análise: {driver.current_url}')

                # Remover overlays após Análise
                logger.info('[NAVEGAÇÃO] Removendo overlays após Análise...')
                max_tentativas_overlay = 5
                for tentativa in range(max_tentativas_overlay):
                    try:
                        overlays_visiveis = driver.find_elements(
                            By.CSS_SELECTOR,
                            'div.cdk-overlay-backdrop.cdk-overlay-dark-backdrop.cdk-overlay-backdrop-showing'
                        )
                        if overlays_visiveis:
                            logger.info(f'[NAVEGAÇÃO] Overlay detectado (tentativa {tentativa + 1}/{max_tentativas_overlay})')
                            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            time.sleep(0.3)
                        else:
                            logger.info('[NAVEGAÇÃO] Nenhum overlay detectado')
                            break
                    except Exception as overlay_err:
                        logger.debug(f'[NAVEGAÇÃO] Erro ao verificar overlay: {overlay_err}')
                        break

                # Aguardar pausa para estabilização
                time.sleep(0.5)

                # Aguardar botões novamente
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-botoes-transicao button'))
                    )
                except Exception:
                    pass

                # Agora clicar em "Conclusão ao magistrado"
                logger.info('[NAVEGAÇÃO] Tentando "Conclusão ao magistrado" após Análise...')
                max_tentativas_clique = 3

                for tentativa_clique in range(max_tentativas_clique):
                    try:
                        btn_conclusao = WebDriverWait(driver, 8).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Conclusão ao magistrado']"))
                        )

                        # Estratégias de clique
                        if tentativa_clique == 0:
                            logger.info(f'[NAVEGAÇÃO] Tentativa {tentativa_clique + 1}: Clique normal')
                            btn_conclusao.click()
                        elif tentativa_clique == 1:
                            logger.info(f'[NAVEGAÇÃO] Tentativa {tentativa_clique + 1}: JavaScript click')
                            driver.execute_script('arguments[0].click();', btn_conclusao)
                        else:
                            logger.info(f'[NAVEGAÇÃO] Tentativa {tentativa_clique + 1}: safe_click_no_scroll')
                            safe_click_no_scroll(driver, btn_conclusao, log=False)

                        btn_conclusao_encontrado = True
                        logger.info('[NAVEGAÇÃO] Clique em "Conclusão ao magistrado" realizado após Análise')
                        break

                    except ElementClickInterceptedException as click_err:
                        logger.warning(f'[NAVEGAÇÃO] Clique interceptado (tentativa {tentativa_clique + 1}): {click_err}')
                        # Tentar remover overlays
                        try:
                            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            time.sleep(0.5)
                        except Exception:
                            pass
                    except Exception as other_err:
                        logger.warning(f'[NAVEGAÇÃO] Erro na tentativa {tentativa_clique + 1}: {other_err}')
                        time.sleep(0.5)

                if not btn_conclusao_encontrado:
                    logger.error('[NAVEGAÇÃO] Falha ao clicar em "Conclusão ao magistrado" após todas as tentativas')
                    return False

            except Exception as e2:
                logger.error(f'[NAVEGAÇÃO] Falha na navegação via Análise: {e2}')
                return False

        # Aguardar URL /conclusao
        if not esperar_url_conter(driver, '/conclusao', timeout=15):
            current_after = (driver.current_url or '').lower()
            logger.error(f'[NAVEGAÇÃO] URL não mudou para /conclusao: {driver.current_url}')

            # Verificar se foi direto para /minutar
            if '/minutar' in current_after:
                logger.info('[NAVEGAÇÃO] Processo foi direto para /minutar')
                return True

            # Verificar se há botões de conclusão disponíveis
            try:
                WebDriverWait(driver, 6).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-concluso-tarefa-botao button'))
                )
                logger.info('[NAVEGAÇÃO] Botões de conclusão disponíveis em /transicao')
                return True
            except Exception:
                return False

        logger.info('[NAVEGAÇÃO] Navegação para conclusão concluída com sucesso')
        return True

    except Exception as e:
        logger.error(f'[NAVEGAÇÃO] Erro na navegação para conclusão: {e}')
        return False


def preparar_campo_minutar(driver: WebDriver) -> bool:
    """
    Prepara o campo de filtro de modelos na tela de minutar.

    Returns:
        bool: True se conseguiu preparar o campo
    """
    try:
        logger.info('[NAVEGAÇÃO] Preparando campo de filtro para minutar...')

        # Aguardar campo de filtro
        campo_filtro_modelo = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'input#inputFiltro'))
        )

        # Limpar e preparar campo
        driver.execute_script('arguments[0].removeAttribute("disabled"); arguments[0].removeAttribute("readonly");', campo_filtro_modelo)
        driver.execute_script('arguments[0].value = arguments[1];', campo_filtro_modelo, "")  # Limpa campo
        driver.execute_script('arguments[0].focus();', campo_filtro_modelo)

        # Disparar eventos para garantir que está ativo
        driver.execute_script('var el=arguments[0]; el.dispatchEvent(new Event("input", {bubbles:true})); el.dispatchEvent(new Event("keyup", {bubbles:true}));', campo_filtro_modelo)

        logger.info('[NAVEGAÇÃO] Campo de filtro preparado com sucesso')
        time.sleep(0.3)
        return True

    except Exception as e:
        logger.error(f'[NAVEGAÇÃO] Falha ao preparar campo de filtro: {e}')
        return False