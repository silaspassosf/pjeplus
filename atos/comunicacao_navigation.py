import time
import re
from typing import Any
from Fix.log import getmodulelogger
logger = getmodulelogger(__name__)

from Fix.core import aguardar_renderizacao_nativa, esperar_url_conter
from Fix.abas import aguardar_nova_aba
from Fix.variaveis import url_processo_detalhe
from .core import aguardar_e_clicar


def abrir_minutas(driver: Any, debug: bool = False) -> bool:
    try:
        current_url = getattr(driver, 'current_url', '') or ''

        if '/comunicacoesprocessuais/minutas' in current_url:
            return True

        match = re.search(r'/processo/(\d+)/detalhe', current_url)
        if not match:
            raise Exception('ID do processo não encontrado na URL /detalhe')

        processo_id = match.group(1)
        url_minutas = url_processo_detalhe(processo_id, "comunicacoesprocessuais/minutas")

        driver.switch_to.new_window('tab')
        driver.get(url_minutas)

        if not aguardar_renderizacao_nativa(driver, timeout=15):
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
