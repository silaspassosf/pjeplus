import time
import re
from selenium.webdriver.common.by import By
from Fix.log import getmodulelogger
logger = getmodulelogger(__name__)

from Fix.core import aguardar_renderizacao_nativa, esperar_url_conter
from Fix.abas import aguardar_nova_aba

from Fix.variaveis import url_processo_detalhe
from .core import aguardar_e_clicar


def abrir_minutas(driver, debug=False):
    """Tenta navegação direta para a página de minutas; faz fallback para navegação por cliques.
    Retorna True se a tela de minutas estiver pronta, levanta Exception em erro crítico.
    """
    try:
        current_url = driver.current_url
        if debug:
            logger.info(f'[URL] URL atual: {current_url}')

        if '/comunicacoesprocessuais/minutas' in current_url:
            if debug:
                logger.info('[URL] Já está na página de minutas; pulando redirecionamento.')
            return True

        match = re.search(r'/processo/(\d+)/detalhe', current_url)
        if not match:
            raise Exception('ID do processo não encontrado na URL /detalhe')

        processo_id = match.group(1)
        url_minutas = url_processo_detalhe(processo_id, "comunicacoesprocessuais/minutas")
        if debug:
            logger.info(f'[URL] Abrindo URL de minutas: {url_minutas}')

        aba_atual = driver.current_window_handle
        driver.execute_script(f"window.open('{url_minutas}', '_blank');")

        try:
            nova_aba = aguardar_nova_aba(driver, aba_atual, timeout=10)
        except Exception:
            nova_aba = None

        if not nova_aba:
            raise Exception('Nova aba de minutas não abriu')

        driver.switch_to.window(nova_aba)
        driver.execute_script("window.focus();")

        # Aguardar readyState == complete (padrao PEC, sem suposicoes de spinner)
        if not aguardar_renderizacao_nativa(driver, timeout=15):
            logger.info('[MINUTAS] Timeout readyState; refresh na aba')
            try:
                driver.refresh()
            except Exception:
                pass
            if not aguardar_renderizacao_nativa(driver, timeout=20):
                raise Exception('Página de minutas não completou carregamento')

        if not esperar_url_conter(driver, '/minutas', timeout=20):
            raise Exception('URL de minutas não carregou após aguardar readyState')

        # UI check com timeout generoso (10s) antes de refresh
        if not aguardar_renderizacao_nativa(driver, 'pje-tipo-expediente, [aria-label*="Tipo de Expediente"], button', 'aparecer', 10):
            logger.info('[MINUTAS] Elemento esperado não encontrado; refresh na aba')
            try:
                driver.refresh()
            except Exception as e_ref:
                logger.info(f'[MINUTAS] Falha ao refresh da aba: {e_ref}')
            if not aguardar_renderizacao_nativa(driver, 'pje-tipo-expediente, [aria-label*="Tipo de Expediente"], button', 'aparecer', 20):
                raise Exception('Página de minutas não exibiu conteúdo esperado após refresh')
        return True

    except Exception as url_error:
        if debug:
            logger.info(f'[URL][ERRO] Falha na navegação direta por URL: {url_error}')
            logger.info('[URL] Fazendo fallback para navegação tradicional por cliques...')

        # FALLBACK: Navegação tradicional por cliques
        from Fix.selectors_pje import BTN_TAREFA_PROCESSO

        aba_antes = driver.current_window_handle
        btn_abrir_tarefa = aguardar_e_clicar(driver, BTN_TAREFA_PROCESSO, timeout=15)
        if not btn_abrir_tarefa:
            raise Exception('Botão tarefa do processo não encontrado')

        try:
            nova_aba = aguardar_nova_aba(driver, aba_antes, timeout=10)
        except Exception:
            nova_aba = None

        if nova_aba:
            driver.switch_to.window(nova_aba)
            aguardar_renderizacao_nativa(driver, timeout=15)

        if not esperar_url_conter(driver, '/minutas', timeout=20):
            if not aguardar_renderizacao_nativa(driver, 'pje-tipo-expediente, [aria-label*="Tipo de Expediente"], button', 'aparecer', 20):
                raise Exception('URL e conteúdo de minutas não carregaram')
        # UI check com timeout generoso antes de refresh
        if not aguardar_renderizacao_nativa(driver, 'pje-tipo-expediente, [aria-label*="Tipo de Expediente"], button', 'aparecer', 10):
            logger.info('[MINUTAS][FALLBACK] Elemento esperado não encontrado; refresh na aba')
            try:
                driver.refresh()
            except Exception as e_ref2:
                logger.info(f'[MINUTAS][FALLBACK] Falha ao refresh da aba: {e_ref2}')
            if not aguardar_renderizacao_nativa(driver, 'pje-tipo-expediente, [aria-label*="Tipo de Expediente"], button', 'aparecer', 20):
                raise Exception('Página de minutas não exibiu conteúdo esperado após refresh')
        if debug:
            logger.info('[MINUTAS] Tela de minutas carregada com sucesso')
        return True
