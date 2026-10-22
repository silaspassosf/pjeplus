import logging
import time
from pathlib import Path
from Fix import espera

logger = logging.getLogger(__name__)

"""
SISB Minutas - Salvar minuta
"""


def _carregar_js(nome_arquivo, scripts_dir=None):
    """Carrega arquivo JS do diretório de scripts."""
    if scripts_dir is None:
        scripts_dir = Path(__file__).parent.parent / "scripts"
    caminho = scripts_dir / nome_arquivo
    if not caminho.exists():
        raise FileNotFoundError(f"Script não encontrado: {caminho}")
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()


def _salvar_minuta(driver):
    """Helper para salvar a minuta e aguardar confirmação efetiva."""
    try:
        SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
        script_salvar = _carregar_js("salvar_minuta.js", SCRIPTS_DIR)
        script_verificar = _carregar_js("verificar_salvamento_minuta.js", SCRIPTS_DIR)

        logger.info('[SISBAJUD] Clicando no botão Salvar da minuta...')
        salvou = espera._executar_script(driver, script_salvar)
        if not salvou:
            logger.error('[SISBAJUD] Botão Salvar não pôde ser acionado')
            return False

        logger.info('[SISBAJUD] Botão Salvar clicado. Aguardando confirmação do salvamento...')

        # Aguardar até 20s confirmação do salvamento (polling a cada 0.5s tolerante a navegação)
        def _verificar_salvo(drv):
            try:
                st = espera._executar_script(drv, script_verificar)
                if st == 'SALVO_COM_SUCESSO':
                    return True
                url = drv.current_url or ''
                if '/cadastrar' not in url and ('/detalhar' in url or '/detalhe' in url or '/minuta/' in url):
                    return True
                return False
            except Exception:
                return False

        salvo_confirmado = espera.ate(driver, _verificar_salvo, teto=20, intervalo=0.5)

        url_atual = driver.current_url or ''
        status_final = 'DESCONHECIDO'
        try:
            status_final = espera._executar_script(driver, script_verificar)
        except Exception:
            pass

        logger.info(f'[SISBAJUD] Status do salvamento: {status_final} (confirmado={salvo_confirmado}, URL: {url_atual})')

        if salvo_confirmado or status_final == 'SALVO_COM_SUCESSO' or ('/cadastrar' not in url_atual and ('/detalhar' in url_atual or '/detalhe' in url_atual or '/minuta/' in url_atual)):
            logger.info('[SISBAJUD] Minuta salva com sucesso!')
            espera.assentar(driver, 1.5, motivo="carregamento de detalhes da minuta salva")
            return True

        if status_final == 'AINDA_EDITANDO' and '/cadastrar' in url_atual:
            logger.warning('[SISBAJUD] Formulário de minuta ainda em edição após 20s de espera')
            return False

        return False

    except Exception as e:
        logger.error(f'[SISBAJUD] Erro ao salvar minuta: {e}')
        return False
