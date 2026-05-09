import logging
import time
from pathlib import Path

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
    """Helper para salvar a minuta."""
    try:
        SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
        script_salvar = _carregar_js("salvar_minuta.js", SCRIPTS_DIR)
        salvou = driver.execute_script(script_salvar)
        if salvou:
            # Aguardar confirmação do salvamento
            time.sleep(3)

            # Verificar se foi salvo
            script_verificar_salvamento = _carregar_js("verificar_salvamento_minuta.js", SCRIPTS_DIR)
            status_salvamento = driver.execute_script(script_verificar_salvamento)

            if status_salvamento == 'SALVO_COM_SUCESSO':
                return True
            elif status_salvamento == 'AINDA_EDITANDO':
                return False
            else:
                return False
        else:
            return False

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao salvar minuta: {e}')
        return False
