"""
judicial_navegacao.py - Funções de navegação para atos judiciais
====================================================================

Funções para abertura de tarefas, navegação entre estados do PJE,
limpeza de overlays e transição entre URLs.
"""

from Fix.selenium_base import aguardar_e_clicar, safe_click
from Fix.selenium_base.wait_operations import esperar_url_conter
from Fix.abas import aguardar_nova_aba
from Fix.core import wait_for_page_load, aguardar_renderizacao_nativa, encontrar_elemento_inteligente, safe_click_no_scroll
from Fix.log import logger
from Fix.selectors_pje import BTN_TAREFA_PROCESSO
from Fix.utils import remover_acentos
from Fix import espera
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException

from typing import Optional, Tuple
from selenium.webdriver.remote.webdriver import WebDriver


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

        if tarefa_do_botao:
            tarefa_lower = tarefa_do_botao.lower()
            if 'assinar' in tarefa_lower or 'minutar' in tarefa_lower:
                logger.info(f'[NAVEGAÇÃO] ⏭ Tarefa "{tarefa_do_botao}" em minutar/assinar — ato pronto, sem ação')
                return True, True

        # Clicar para abrir tarefa
        if not safe_click(driver, btn_abrir_tarefa):
            logger.error('[NAVEGAÇÃO] Falha ao clicar em "Abrir tarefa do processo"')
            return False, False

        # Aguardar nova aba
        nova_aba = None
        try:
            nova_aba = aguardar_nova_aba(driver, next(iter(abas_antes)), timeout=10)
        except TimeoutException:
            logger.info('[NAVEGAÇÃO] Nenhuma nova aba detectada (continuando na mesma aba)')

        if nova_aba:
            driver.switch_to.window(nova_aba)
            logger.info('[NAVEGAÇÃO] Foco trocado para nova aba')

            # Aguardar carregamento mínimo
            try:
                aguardar_renderizacao_nativa(driver, timeout=3)
            except Exception:
                pass

        # Verificar estado final após abertura
        current_url = (driver.current_url or '').lower()
        ja_em_estado_final = ('/assinar' in current_url or
                            '/minutar' in current_url)

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
        # Overlays principais — desabilitar implicit_wait para não bloquear 10s quando não há overlay
        driver.implicitly_wait(0)
        overlays = driver.find_elements(By.CSS_SELECTOR, '.cdk-overlay-backdrop, .mat-dialog-container')
        driver.implicitly_wait(10)
        if overlays:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            aguardar_renderizacao_nativa(driver, 'div.cdk-overlay-backdrop.cdk-overlay-dark-backdrop.cdk-overlay-backdrop-showing', 'sumir', timeout=2)
            logger.info('[NAVEGAÇÃO] Overlays removidos')
    except Exception as e:
        driver.implicitly_wait(10)
        logger.debug(f'[NAVEGAÇÃO] Erro ao limpar overlays: {e}')


def _estrategias_botao_navegacao(aria_label: str):
    """Fallbacks para localizar botões de navegação de tarefa (Análise, Conclusão ao
    magistrado) cujo seletor único vinha causando NoSuchElementError imediato quando
    o aria-label do PJe muda de formatação entre versões/varas."""
    return [
        (By.CSS_SELECTOR, f"button[aria-label='{aria_label}']"),
        (By.CSS_SELECTOR, f"button[aria-label*='{aria_label}']"),
        (By.XPATH, f"//button[.//span[normalize-space(text())='{aria_label}']]"),
    ]


def navegar_para_conclusao(driver: WebDriver) -> bool:
    """
    Navega da tarefa atual para "Conclusão ao Magistrado".

    Estratégia:
    1. Tenta clicar diretamente em "Conclusão ao Magistrado"
    2. Se não disponível, clica em "Análise" primeiro, remove overlays, depois clica em "Conclusão ao Magistrado"
    3. Aguarda o elemento da próxima tela (botões de tipo de conclusão) — não a URL,
       que não é um sinal confiável dessa transição (mesmo padrão do gigs-plugin.js)

    Returns:
        bool: True se conseguiu navegar para conclusão
    """
    try:
        # 0. Verificação prévia estritamente via URL (conforme especificação e legado)
        current_url = (driver.current_url or '').lower()
        if '/minutar' in current_url:
            logger.info('[NAVEGAÇÃO] Já em /minutar — destino alcançado')
            return True
        if '/conclusao' in current_url:
            logger.info('[NAVEGAÇÃO] Já em /conclusao — tela de conclusão alcançada')
            return True

        logger.info('[NAVEGAÇÃO] Navegando para Conclusão ao Magistrado...')

        # Garantir que os botões de navegação/transição terminaram de renderizar (estilo gigs-plugin)
        seletor_botoes = (
            "button[aria-label='Análise'], button[aria-label*='Análise'], "
            "button[aria-label='Conclusão ao magistrado'], button[aria-label*='Conclusão ao magistrado'], "
            "pje-botoes-transicao button"
        )
        if not espera.ate_aparecer(driver, seletor_botoes, teto=10):
            if '/conclusao' in (driver.current_url or '').lower():
                logger.info('[NAVEGAÇÃO] URL já está em /conclusao — assumindo transição concluída')
                return True
            logger.error('[NAVEGAÇÃO] Botões de navegação não apareceram no DOM')
            return False

        # Desabilitar implicit_wait temporariamente para checagem rápida
        driver.implicitly_wait(0)
        try:
            btn_conclusao_encontrado = False

            # Tentar clique direto em "Conclusão ao magistrado"
            btn_conclusao_direto = encontrar_elemento_inteligente(
                driver, 'Conclusão ao magistrado',
                estrategias_custom=_estrategias_botao_navegacao('Conclusão ao magistrado')
            )
            if btn_conclusao_direto and btn_conclusao_direto.is_displayed() and safe_click_no_scroll(driver, btn_conclusao_direto):
                btn_conclusao_encontrado = True
                logger.info('[NAVEGAÇÃO] Clique direto em "Conclusão ao magistrado" realizado')
            else:
                logger.info('[NAVEGAÇÃO] Conclusão não disponível diretamente, tentando via "Análise"...')

            # Se não encontrou, usar estratégia via "Análise"
            if not btn_conclusao_encontrado:
                logger.info('[NAVEGAÇÃO] Tentando via "Análise"...')
                btn_analise = encontrar_elemento_inteligente(
                    driver, 'Análise', estrategias_custom=_estrategias_botao_navegacao('Análise')
                )
                if btn_analise and safe_click_no_scroll(driver, btn_analise):
                    logger.info('[NAVEGAÇÃO] Clique em "Análise" realizado')
                    espera.assentar(driver, 1.0, motivo='pós-clique Análise')
                else:
                    logger.warning('[NAVEGAÇÃO] Botão "Análise" não encontrado diretamente')

        finally:
            driver.implicitly_wait(10)

        # Remover overlays após Análise se houver
        logger.info('[NAVEGAÇÃO] Verificando overlays...')
        driver.implicitly_wait(0)
        try:
            overlays = driver.find_elements(By.CSS_SELECTOR, '.cdk-overlay-backdrop-showing')
            if overlays:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                aguardar_renderizacao_nativa(driver, '.cdk-overlay-backdrop-showing', modo='sumir', timeout=2)
        except Exception:
            pass
        finally:
            driver.implicitly_wait(10)

        # Clicar na conclusão após Análise se necessário
        if not btn_conclusao_encontrado:
            seletor_conclusao = "button[aria-label='Conclusão ao magistrado'], button[aria-label*='Conclusão ao magistrado']"
            espera.ate_aparecer(driver, seletor_conclusao, teto=8)
            btn_conclusao = encontrar_elemento_inteligente(
                driver, 'Conclusão ao magistrado',
                estrategias_custom=_estrategias_botao_navegacao('Conclusão ao magistrado')
            )
            if btn_conclusao and safe_click_no_scroll(driver, btn_conclusao):
                logger.info('[NAVEGAÇÃO] Clique em "Conclusão ao magistrado" realizado após Análise')
            else:
                if espera.ate_url(driver, '/conclusao', teto=2):
                    logger.info('[NAVEGAÇÃO] Processo já transicionou para Conclusão')
                else:
                    logger.warning('[NAVEGAÇÃO] Botão "Conclusão ao magistrado" não encontrado após aguardar renderização')

        # Confirmar chegada: /minutar (pulou direto) ou /conclusao na URL (conforme legado)
        current_after = (driver.current_url or '').lower()
        if '/minutar' in current_after:
            logger.info('[NAVEGAÇÃO] Processo foi direto para /minutar')
            return True

        if espera.ate_url(driver, '/conclusao', teto=15):
            logger.info('[NAVEGAÇÃO] URL confirma transição para /conclusao')
            return True

        # Fallback: aguardar botões de conclusão renderizarem
        if aguardar_renderizacao_nativa(driver, 'pje-concluso-tarefa-botao button', 'aparecer', timeout=5):
            logger.info('[NAVEGAÇÃO] Navegação para conclusão concluída com sucesso (botões visíveis)')
            return True

        botoes = driver.find_elements(By.CSS_SELECTOR, 'pje-concluso-tarefa-botao button')
        if botoes and any(b.is_displayed() for b in botoes):
            logger.info('[NAVEGAÇÃO] Navegação para conclusão concluída com sucesso (botões encontrados via fallback)')
            return True

        logger.error(f'[NAVEGAÇÃO] URL não mudou para /conclusao. URL atual: {driver.current_url}')
        return False

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
        campo_filtro_modelo = espera.elemento(driver, 'input#inputFiltro', teto=10)
        if not campo_filtro_modelo:
            raise Exception('input#inputFiltro não apareceu')

        # Limpar e preparar campo
        driver.execute_script('arguments[0].removeAttribute("disabled"); arguments[0].removeAttribute("readonly");', campo_filtro_modelo)
        driver.execute_script('arguments[0].value = arguments[1];', campo_filtro_modelo, "")  # Limpa campo
        driver.execute_script('arguments[0].focus();', campo_filtro_modelo)

        # Disparar eventos para garantir que está ativo
        driver.execute_script('var el=arguments[0]; el.dispatchEvent(new Event("input", {bubbles:true})); el.dispatchEvent(new Event("keyup", {bubbles:true}));', campo_filtro_modelo)

        logger.info('[NAVEGAÇÃO] Campo de filtro preparado com sucesso')
        aguardar_renderizacao_nativa(driver, 'input#inputFiltro', 'aparecer', timeout=2)
        return True

    except Exception as e:
        logger.error(f'[NAVEGAÇÃO] Falha ao preparar campo de filtro: {e}')
        return False


def verificar_estado_atual(driver: WebDriver) -> str:
    """
    Verifica o estado atual do processo baseado na URL.

    Returns:
        str: Estado atual ('assinar', 'minutar', 'conclusao', 'detalhe', 'outro')
    """
    current_url = (driver.current_url or '').lower()

    if '/assinar' in current_url:
        return 'assinar'
    elif '/minutar' in current_url:
        return 'minutar'
    elif '/conclusao' in current_url:
        return 'conclusao'
    elif '/detalhe' in current_url:
        return 'detalhe'
    else:
        return 'outro'


def escolher_tipo_conclusao(driver: WebDriver, conclusao_tipo: str) -> bool:
    """
    Escolhe o tipo de conclusão na tela de conclusão do processo (/conclusao).
    Clica no botão correspondente (ex: Despacho, Decisão) em pje-concluso-tarefa-botao.
    """
    try:
        conclusao_tipo = (conclusao_tipo or 'Despacho').strip()
        tipo_norm = remover_acentos(conclusao_tipo).lower()
        logger.info(f'[NAVEGAÇÃO][CONCLUSÃO] Escolhendo tipo de conclusão: {conclusao_tipo} (norm: {tipo_norm})')

        # Aguardar presença real dos botões de conclusão (não apenas o container vazio)
        if not aguardar_renderizacao_nativa(driver, 'pje-concluso-tarefa-botao button', 'aparecer', timeout=10):
            logger.warning('[NAVEGAÇÃO][CONCLUSÃO] Botões de conclusão não carregaram via observer, tentando busca direta')

        btn_tipo_conclusao = None

        # Estratégia 1: Procurar em botões estruturados (pje-concluso-tarefa-botao button)
        try:
            candidatos = driver.find_elements(By.CSS_SELECTOR, 'pje-concluso-tarefa-botao button')
            for btn in candidatos:
                try:
                    txt = remover_acentos(btn.text or btn.get_attribute('innerText') or '').strip().lower()
                    if txt and tipo_norm in txt and btn.is_displayed() and btn.is_enabled():
                        btn_tipo_conclusao = btn
                        logger.info(f'[NAVEGAÇÃO][CONCLUSÃO] Botão encontrado via pje-concluso-tarefa-botao button (Estratégia 1)')
                        break
                except Exception:
                    continue
        except Exception:
            pass

        # Estratégia 2: Procurar por texto visível via XPath (idêntico ao legado)
        if not btn_tipo_conclusao:
            try:
                xpath = f"//button[contains(normalize-space(text()), '{conclusao_tipo}')]"
                btns = driver.find_elements(By.XPATH, xpath)
                for btn in btns:
                    try:
                        if btn.is_displayed() and btn.is_enabled():
                            aria = (btn.get_attribute('aria-label') or '').lower()
                            if 'remover' not in aria and 'fechar' not in aria and 'excluir' not in aria:
                                btn_tipo_conclusao = btn
                                logger.info(f'[NAVEGAÇÃO][CONCLUSÃO] Botão encontrado via XPath texto (Estratégia 2)')
                                break
                    except Exception:
                        continue
            except Exception:
                pass

        # Estratégia 3: Container pje-concluso-tarefa-botao pegando button filho
        if not btn_tipo_conclusao:
            try:
                ancoras = driver.find_elements(By.CSS_SELECTOR, 'pje-concluso-tarefa-botao')
                for ancora in ancoras:
                    try:
                        txt_ancora = remover_acentos(ancora.text or ancora.get_attribute('innerText') or '').strip().lower()
                        if tipo_norm in txt_ancora:
                            btn_filho = ancora.find_elements(By.CSS_SELECTOR, 'button')
                            if btn_filho and btn_filho[0].is_displayed() and btn_filho[0].is_enabled():
                                btn_tipo_conclusao = btn_filho[0]
                                logger.info(f'[NAVEGAÇÃO][CONCLUSÃO] Botão encontrado via container pje-concluso-tarefa-botao (Estratégia 3)')
                                break
                    except Exception:
                        continue
            except Exception:
                pass

        # Estratégia 4: Procurar por aria-label
        if not btn_tipo_conclusao:
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, "button[aria-label]")
                for btn in btns:
                    try:
                        aria = remover_acentos(btn.get_attribute('aria-label') or '').lower()
                        if tipo_norm in aria:
                            if 'remover' not in aria and 'fechar' not in aria and 'excluir' not in aria:
                                if btn.is_displayed() and btn.is_enabled():
                                    btn_tipo_conclusao = btn
                                    logger.info(f'[NAVEGAÇÃO][CONCLUSÃO] Botão encontrado via aria-label (Estratégia 4)')
                                    break
                    except Exception:
                        continue
            except Exception:
                pass

        if not btn_tipo_conclusao:
            logger.error(f'[NAVEGAÇÃO][CONCLUSÃO] Botão de conclusão "{conclusao_tipo}" não encontrado')
            return False

        # Clique no botão de conclusão: scrollIntoView + tentativa Selenium com fallback JS
        logger.info(f'[NAVEGAÇÃO][CONCLUSÃO] Clicando em tipo de conclusão "{conclusao_tipo}"...')
        driver.execute_script('arguments[0].scrollIntoView({block: "center", behavior: "instant"});', btn_tipo_conclusao)
        espera.assentar(driver, 0.3)
        clicado = False
        try:
            btn_tipo_conclusao.click()
            clicado = True
        except Exception:
            pass

        if not clicado:
            try:
                driver.execute_script('arguments[0].click();', btn_tipo_conclusao)
                clicado = True
            except Exception:
                safe_click_no_scroll(driver, btn_tipo_conclusao)

        logger.info(f'[NAVEGAÇÃO][CONCLUSÃO] ✅ Botão de conclusão "{conclusao_tipo}" clicado')
        espera.assentar(driver, 0.5)
        return True

    except Exception as e:
        logger.error(f'[NAVEGAÇÃO][CONCLUSÃO] Erro ao escolher tipo de conclusão: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return False


def aguardar_transicao_minutar(driver: WebDriver) -> bool:
    """
    Aguarda a transição da tela de conclusão para a tela de minutar.
    Verifica estritamente se a URL mudou para /minutar (conforme legado).

    Returns:
        bool: True se conseguiu fazer a transição
    """
    try:
        logger.info('[NAVEGAÇÃO] Aguardando transição para tela de minutar...')

        # Aguardar estritamente a URL /minutar (idêntico ao legado)
        if not esperar_url_conter(driver, '/minutar', timeout=20):
            logger.error(f'[NAVEGAÇÃO] URL não mudou para /minutar: {driver.current_url}')
            return False

        logger.info('[NAVEGAÇÃO] Transição para minutar concluída (URL /minutar)')
        return True

    except Exception as e:
        logger.error(f'[NAVEGAÇÃO] Erro na transição para minutar: {e}')
        return False


def focar_campo_minutar_se_necessario(driver: WebDriver) -> bool:
    """
    Foca no campo de filtro de modelos se estiver na tela de minutar.

    Returns:
        bool: True se conseguiu focar ou se não era necessário
    """
    try:
        if verificar_estado_atual(driver) == 'minutar':
            logger.info('[NAVEGAÇÃO] Já em minutar - focando no campo de filtro')
            campo_filtro_modelo = espera.elemento(driver, 'input#inputFiltro', teto=10)
            if not campo_filtro_modelo:
                raise Exception('input#inputFiltro não apareceu')
            driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
            logger.info('[NAVEGAÇÃO] Foco no campo #inputFiltro realizado')
        return True
    except Exception as e:
        logger.warning(f'[NAVEGAÇÃO] Erro ao focar campo minutar: {e}')
        return False


def navegar_para_minutar(driver: WebDriver, conclusao_tipo: str) -> bool:
    """
    Navega até a tela de minutar (/minutar) de forma coesa e unificada.
    1. Se já em /minutar: retorna True.
    2. Se em /conclusao: escolhe o tipo de conclusão e aguarda /minutar.
    3. Se não em /conclusao: navega para Conclusão ao magistrado, escolhe o tipo e aguarda /minutar.
    """
    current_url = (driver.current_url or '').lower()
    if '/minutar' in current_url:
        logger.info('[NAVEGAÇÃO] Já em /minutar — destino alcançado')
        return True

    if '/conclusao' not in current_url:
        logger.info('[NAVEGAÇÃO] Navegando para Conclusão ao Magistrado...')
        if not navegar_para_conclusao(driver):
            logger.error('[NAVEGAÇÃO] Falha ao navegar para conclusão')
            return False

    logger.info(f'[NAVEGAÇÃO] Escolhendo tipo de conclusão: {conclusao_tipo}')
    if not escolher_tipo_conclusao(driver, conclusao_tipo):
        logger.error(f'[NAVEGAÇÃO] Falha ao escolher tipo de conclusão: {conclusao_tipo}')
        return False

    logger.info('[NAVEGAÇÃO] Aguardando transição para /minutar...')
    if not aguardar_transicao_minutar(driver):
        logger.error('[NAVEGAÇÃO] Falha na transição para /minutar')
        return False

    return True