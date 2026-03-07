import logging
import time

logger = logging.getLogger(__name__)

"""
SISB Minutas - Salvar minuta
"""


def _salvar_minuta(driver):
    """Helper para salvar a minuta."""
    try:
        script_salvar = """
        var btnSalvar = document.querySelector('button.mat-fab.mat-primary mat-icon.fa-save');
        if (btnSalvar) {
            btnSalvar.closest('button').click();
            return true;
        }

        var btnFallback = document.querySelector('button mat-icon.fa-save');
        if (btnFallback) {
            btnFallback.closest('button').click();
            return true;
        }

        var buttons = document.querySelectorAll('button');
        for (var i = 0; i < buttons.length; i++) {
            if (buttons[i].textContent.includes('Salvar')) {
                buttons[i].click();
                return true;
            }
        }

        return false;
        """

        salvou = driver.execute_script(script_salvar)
        if salvou:
            time.sleep(3)

            script_verificar_salvamento = """
            var btnAlterar = document.querySelector('button mat-icon.fa-edit');
            if (btnAlterar) {
                var btnTexto = btnAlterar.closest('button');
                if (btnTexto && btnTexto.textContent.includes('Alterar')) {
                    return 'SALVO_COM_SUCESSO';
                }
            }

            var btnSalvar = document.querySelector('button mat-icon.fa-save');
            if (btnSalvar) {
                return 'AINDA_EDITANDO';
            }

            return 'STATUS_DESCONHECIDO';
            """

            status_salvamento = driver.execute_script(script_verificar_salvamento)

            if status_salvamento == 'SALVO_COM_SUCESSO':
                return True
            return False

        return False

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao salvar minuta: {e}')
        return False