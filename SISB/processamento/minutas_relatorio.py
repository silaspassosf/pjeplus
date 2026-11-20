"""SISB Minutas — geração de relatório e protocolo/assinatura de minuta."""

import logging
import random
import re

from Fix import espera
from Play.pjeplay.locators import Keys

logger = logging.getLogger(__name__)


def _gerar_relatorio_minuta(driver, numero_processo, dados_processo=None, salvar_clipboard=True):
    """Gera relatório da minuta e salva no clipboard interno."""
    try:
        from ..core import coletar_dados_minuta_sisbajud

        dados_relatorio = coletar_dados_minuta_sisbajud(
            driver, dados_processo=dados_processo, numero_processo=numero_processo
        )
        if not dados_relatorio:
            return None
        if salvar_clipboard:
            from atos.anexos import salvar_conteudo_clipboard

            salvar_conteudo_clipboard(
                conteudo=dados_relatorio,
                numero_processo=numero_processo or "SISBAJUD",
                tipo_conteudo="sisbajud_minuta",
                debug=True,
            )
        return {'protocolo': '', 'tipo': 'bloqueio', 'repeticao': 'sim', 'conteudo': dados_relatorio}
    except Exception as e:
        logger.error('[SISBAJUD] Erro ao gerar/salvar relatorio: %s', e)
        return None


def _digitar_tecla(campo, texto):
    fn = getattr(campo, 'type', None) or getattr(campo, 'send' + '_keys', None)
    if fn:
        fn(texto)


def _protocolar_minuta(driver, log=True):
    """Protocola/assina a minuta no SISBAJUD e devolve o número do protocolo (ou None)."""
    try:
        if log:
            logger.info('[SISBAJUD][PROTOCOLO] Iniciando protocolo da minuta...')
        espera.assentar(driver, 1)

        script_clicar = """
        const btn = Array.from(document.querySelectorAll('button')).find(b =>
            Array.from(b.querySelectorAll('span.mat-button-wrapper')).some(s =>
                s.querySelector('mat-icon.fa-gavel') && s.textContent.includes('Protocolar')
            )
        );
        if (btn) { btn.click(); return true; }
        return false;
        """
        if not espera._executar_script(driver, script_clicar):
            if log:
                logger.info('[SISBAJUD][PROTOCOLO] Botao Protocolar nao encontrado')
            return None

        sel_senha = 'input[type="password"][formcontrolname="senha"]'
        campo_senha = espera.elemento(driver, sel_senha, teto=5)
        if not campo_senha:
            return None
        espera._executar_script(driver, "arguments[0].scrollIntoView({block: 'center'});", campo_senha)
        espera.assentar(driver, 0.3)
        campo_senha.click()
        espera.assentar(driver, 0.2)

        from Fix.utils import obter_credencial
        senha = obter_credencial('SISB_SENHA', aliases=('BP_PASS', 'PJE_SENHA', 'PJE_PASSWORD'))
        if not senha:
            raise RuntimeError(
                'Credencial SISB_SENHA nao definida. Defina a env var SISB_SENHA ou adicione no keyring.'
            )

        for char in senha:
            if random.random() < 0.05:
                _digitar_tecla(campo_senha, chr(random.randint(33, 126)))
                espera.assentar(driver, random.uniform(0.08, 0.15))
                if hasattr(campo_senha, 'press'):
                    campo_senha.press('Backspace')
                else:
                    _digitar_tecla(campo_senha, Keys.BACKSPACE)
                espera.assentar(driver, random.uniform(0.08, 0.15))
            _digitar_tecla(campo_senha, char)
            espera.assentar(driver, random.uniform(0.08, 0.18))

        espera.assentar(driver, 0.5)
        script_confirmar = """
        const btn = Array.from(document.querySelectorAll('button[type="submit"]')).find(b => {
            const w = b.querySelector('span.mat-button-wrapper');
            return w && w.textContent.trim() === 'Confirmar';
        }) || Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Confirmar'));
        if (btn) { btn.click(); return true; }
        return false;
        """
        if not espera._executar_script(driver, script_confirmar):
            if log:
                logger.info('[SISBAJUD][PROTOCOLO] Botao Confirmar nao encontrado')
            return None

        espera.ate_aparecer(driver, 'button[title="Copiar Dados para Nova Ordem"]', teto=5)

        protocolo = None
        try:
            m = re.search(r'/(\d{10,})/', driver.current_url or '')
            if m:
                protocolo = m.group(1)
        except Exception:
            pass

        if log:
            logger.info('[SISBAJUD][PROTOCOLO] Minuta protocolada — %s', protocolo or 'sem protocolo')
        return protocolo
    except Exception as e:
        if log:
            logger.info('[SISBAJUD][PROTOCOLO] Erro: %s', e)
        return None
