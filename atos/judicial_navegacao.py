"""
judicial_navegacao.py - Funções de navegação para atos judiciais
====================================================================

Funções para abertura de tarefas, navegação entre estados do PJE,
limpeza de overlays e transição entre URLs.
"""

from Fix.selenium_base import aguardar_e_clicar, safe_click_no_scroll, safe_click
from Fix.abas import aguardar_nova_aba
from Fix.core import wait_for_page_load, aguardar_renderizacao_nativa, encontrar_elemento_inteligente
from Fix.log import logger
from Fix.selectors_pje import BTN_TAREFA_PROCESSO
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
            driver.pje_tarefa_atual = tarefa_do_botao
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
        logger.info('[NAVEGAÇÃO] Navegando para Conclusão ao Magistrado...')

        # Obter nome da tarefa se disponível (do DOM ou do driver salvo anteriormente)
        nome_tarefa = getattr(driver, 'pje_tarefa_atual', '').lower()
        if not nome_tarefa:
            try:
                driver.implicitly_wait(0)
                h1 = driver.find_elements(By.CSS_SELECTOR, "pje-cabecalho-tarefa h1.titulo-tarefa, span.texto-tarefa-processo")
                if h1:
                    nome_tarefa = h1[0].text.strip().lower()
            except Exception:
                pass
            finally:
                driver.implicitly_wait(10)

        logger.info(f'[NAVEGAÇÃO] Nome da Tarefa Detectado: "{nome_tarefa}"')

        # Garantir que a página Angular terminou de renderizar os botões de navegação
        # antes de desligar o wait implícito. No Playwright, a navegação é mais rápida
        # que no Selenium, e o Angular pode ainda não ter renderizado os botões quando
        # esta função é chamada. Sem esta espera, find_element com implicitly_wait=0
        # faz query_selector() imediato que retorna None.
        # Usa espera.elemento (wait_for_selector nativo no PW) em vez de aguardar_
        # renderizacao_nativa: o _ALGUM_VISIVEL JS pode achar "Conclusão" visível e
        # retornar antes do "Análise" entrar no DOM, gerando falso positivo.
        if not (
            espera.elemento(driver, "button[aria-label='Análise'], button[aria-label*='Análise']", teto=5)
            or espera.elemento(driver, "button[aria-label='Conclusão ao magistrado'], button[aria-label*='Conclusão ao magistrado']", teto=5)
        ):
            logger.error('[NAVEGAÇÃO] Botões de navegação não apareceram no DOM')
            return False

        # Desabilitar implicit_wait temporariamente para evitar delays de 10s ao buscar elementos que não existem
        driver.implicitly_wait(0)
        try:
            btn_conclusao_encontrado = False

            # Tentar clique direto em "Conclusão ao magistrado" independente do tipo de tarefa.
            # Busca robusta (múltiplas estratégias) no lugar de um único seletor fixo: o aria-label
            # do PJe varia de formatação entre versões/varas e causava NoSuchElementError imediato.
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

                # Clicar em "Análise" (mesma busca robusta; clique via JS dispatchEvent evita
                # ElementClickInterceptedException por overlay ainda em transição)
                btn_analise = encontrar_elemento_inteligente(
                    driver, 'Análise', estrategias_custom=_estrategias_botao_navegacao('Análise')
                )
                if btn_analise and safe_click_no_scroll(driver, btn_analise):
                    logger.info('[NAVEGAÇÃO] Clique em "Análise" realizado')
                else:
                    logger.error('[NAVEGAÇÃO] Falha ao clicar em "Análise": botão não encontrado no DOM')
                    # Não re-levanta o erro imediatamente, deixa o fluxo tentar tratar ou retornar False.

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

        # Aguardar renderização e clicar na conclusão
        if not btn_conclusao_encontrado:
            seletor_conclusao = "button[aria-label='Conclusão ao magistrado'], button[aria-label*='Conclusão ao magistrado']"
            aguardar_renderizacao_nativa(driver, seletor_conclusao, 'aparecer', timeout=8)
            btn_conclusao = encontrar_elemento_inteligente(
                driver, 'Conclusão ao magistrado',
                estrategias_custom=_estrategias_botao_navegacao('Conclusão ao magistrado')
            )
            if not btn_conclusao or not safe_click_no_scroll(driver, btn_conclusao):
                logger.error('[NAVEGAÇÃO] Falha na navegação via Análise: botão "Conclusão ao magistrado" não encontrado após aguardar renderização')
                return False
            logger.info('[NAVEGAÇÃO] Clique em "Conclusão ao magistrado" realizado após Análise')

        # Confirmar chegada: /minutar (pulou direto) ou botões de tipo de conclusão renderizados.
        # Não checar a URL /conclusao aqui: ela não reflete a transição do Angular de forma
        # confiável (o próprio gigs-plugin.js espera o elemento seguinte aparecer, não a URL).
        current_after = (driver.current_url or '').lower()
        if '/minutar' in current_after:
            logger.info('[NAVEGAÇÃO] Processo foi direto para /minutar')
            return True

        if not aguardar_renderizacao_nativa(driver, 'pje-concluso-tarefa-botao button', 'aparecer', timeout=10):
            logger.error(f'[NAVEGAÇÃO] Botões de conclusão não apareceram. URL atual: {driver.current_url}')
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