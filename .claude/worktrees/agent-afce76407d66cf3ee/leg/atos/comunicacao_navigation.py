import time
import re
from selenium.webdriver.common.by import By
from Fix.log import getmodulelogger
logger = getmodulelogger(__name__)

from Fix.core import aguardar_renderizacao_nativa, esperar_url_conter
from Fix.exceptions import NavegacaoError
from .core import aguardar_e_verificar_aba, aguardar_e_clicar


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
        url_minutas = f'https://pje.trt2.jus.br/pjekz/processo/{processo_id}/comunicacoesprocessuais/minutas'
        if debug:
            logger.info(f'[URL] Abrindo URL de minutas: {url_minutas}')

        abas_antes = driver.window_handles
        driver.execute_script(f"window.open('{url_minutas}', '_blank');")

        nova_aba = None
        for tentativa in range(15):
            abas_apos_abertura = driver.window_handles
            if len(abas_apos_abertura) > len(abas_antes):
                nova_aba = abas_apos_abertura[-1]
                break
            else:
                # Usar aguardar_renderizacao_nativa ao invés de time.sleep hardcoded
                try:
                    aguardar_renderizacao_nativa(driver, timeout=0.5)
                except Exception:
                    pass

        if not nova_aba:
            raise Exception('Nova aba de minutas não abriu')

        driver.switch_to.window(nova_aba)
        driver.execute_script("window.focus();")

        try:
            aguardar_e_verificar_aba(driver, timeout_spinner=0.5, max_tentativas_reload=2, log=debug)
        except NavegacaoError as e:
            raise Exception('Página travou no carregamento (spinner)') from e

        if not esperar_url_conter(driver, '/minutas', timeout=20):
            raise Exception('URL de minutas não carregou')

        # Quick check: if 'Tipo de Expediente' (ou botões suficientes) não aparecer em 3s, refresh na aba e tentar novamente
        if not aguardar_renderizacao_nativa(driver, 'pje-tipo-expediente, [aria-label*="Tipo de Expediente"], button', 'aparecer', 3):
            logger.info('[MINUTAS] Elemento esperado não encontrado rápido; recarregando aba e tentando novamente')
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

        abas_antes = set(driver.window_handles)
        btn_abrir_tarefa = aguardar_e_clicar(driver, BTN_TAREFA_PROCESSO, timeout=15)
        if not btn_abrir_tarefa:
            raise Exception('Botão tarefa do processo não encontrado')

        nova_aba = None
        for _ in range(20):
            abas_depois = set(driver.window_handles)
            novas_abas = abas_depois - abas_antes
            if novas_abas:
                nova_aba = novas_abas.pop()
                break
            else:
                # Usar aguardar_renderizacao_nativa ao invés de time.sleep hardcoded
                try:
                    aguardar_renderizacao_nativa(driver, timeout=0.5)
                except Exception:
                    pass

        if nova_aba:
            driver.switch_to.window(nova_aba)
            try:
                aguardar_e_verificar_aba(driver, timeout_spinner=0.5, max_tentativas_reload=2, log=debug)
            except NavegacaoError as e:
                raise Exception('Página travou no carregamento (spinner)') from e

        if not esperar_url_conter(driver, '/minutas', timeout=20):
            if not aguardar_renderizacao_nativa(driver, 'pje-tipo-expediente, [aria-label*="Tipo de Expediente"], button', 'aparecer', 20):
                raise Exception('URL e conteúdo de minutas não carregaram')
        # Quick refresh attempt if UI parts not present shortly after load
        if not aguardar_renderizacao_nativa(driver, 'pje-tipo-expediente, [aria-label*="Tipo de Expediente"], button', 'aparecer', 3):
            logger.info('[MINUTAS][FALLBACK] Elemento esperado não encontrado rápido; recarregando aba e tentando novamente')
            try:
                driver.refresh()
            except Exception as e_ref2:
                logger.info(f'[MINUTAS][FALLBACK] Falha ao refresh da aba: {e_ref2}')
            if not aguardar_renderizacao_nativa(driver, 'pje-tipo-expediente, [aria-label*="Tipo de Expediente"], button', 'aparecer', 20):
                raise Exception('Página de minutas não exibiu conteúdo esperado após refresh')
        if debug:
            logger.info('[MINUTAS] Tela de minutas carregada com sucesso')
        return True
