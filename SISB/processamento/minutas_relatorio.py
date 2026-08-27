import logging
import os

logger = logging.getLogger(__name__)

"""
SISB Minutas - Relatorio
"""


def _gerar_relatorio_minuta(driver, numero_processo):
    """Helper para gerar relatorio da minuta."""
    try:
        from ..core import coletar_dados_minuta_sisbajud
        dados_relatorio = coletar_dados_minuta_sisbajud(driver)
        if dados_relatorio:
            try:
                from PEC.anexos import salvar_conteudo_clipboard

                sucesso = salvar_conteudo_clipboard(
                    conteudo=dados_relatorio,
                    numero_processo=numero_processo or "SISBAJUD",
                    tipo_conteudo="sisbajud_minuta",
                    debug=True
                )

                _ = sucesso

                protocolo = None
                try:
                    url = driver.current_url
                    import re
                    match = re.search(r'/(\d{10,})/', url)
                    if match:
                        protocolo = match.group(1)
                except Exception:
                    pass

                return {
                    'protocolo': protocolo,
                    'tipo': 'bloqueio',
                    'repeticao': 'sim',
                    'conteudo': dados_relatorio
                }
            except Exception as e:
                logger.error(f'[SISBAJUD]  Erro ao salvar relatorio: {e}')
                return None
        return None

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao gerar relatorio: {e}')
        return None


def _protocolar_minuta(driver, log=True):
    """Protocolar/assinar minuta no SISBAJUD.

    Clica em 'Protocolar', digita senha no modal, confirma e verifica
    sucesso pelo botao 'Copiar Dados para Nova Ordem'.

    Args:
        driver: WebDriver SISBAJUD (ja na pagina da minuta apos salvar)
        log: Se True, exibe logs detalhados

    Returns:
        str: protocolo extraido da URL se sucesso, None caso contrario
    """
    import random
    import time
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.by import By
    from Fix import espera

    try:
        if log:
            logger.info('[SISBAJUD][PROTOCOLO] Iniciando protocolo da minuta...')

        espera.assentar(driver, 1)

        # 1. Clicar no botao "Protocolar" (martelo + texto)
        script_clicar = """
        const buttons = Array.from(document.querySelectorAll('button'));
        const btn = buttons.find(b => {
            const spans = b.querySelectorAll('span.mat-button-wrapper');
            return Array.from(spans).some(s =>
                s.querySelector('mat-icon.fa-gavel') &&
                s.textContent.includes('Protocolar'));
        });
        if (btn) { btn.click(); return true; }
        return false;
        """
        if not driver.execute_script(script_clicar):
            if log:
                logger.info('[SISBAJUD][PROTOCOLO] Botao Protocolar nao encontrado')
            return None

        if log:
            logger.info('[SISBAJUD][PROTOCOLO] Botao Protocolar clicado')

        # 2. Aguardar modal de senha
        espera.ate_aparecer(driver, 'input[type="password"][formcontrolname="senha"]', teto=5)

        # 3. Digitar senha
        campo_senha = driver.find_element(By.CSS_SELECTOR, 'input[type="password"][formcontrolname="senha"]')
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", campo_senha)
        espera.assentar(driver, 0.3)
        campo_senha.click()
        espera.assentar(driver, 0.2)

        senha = os.environ.get('SISB_SENHA')
        if not senha:
            raise RuntimeError(
                'Credencial SISB_SENHA nao definida. '
                'Defina a variavel de ambiente SISB_SENHA com a senha de acesso ao SISBAJUD.'
            )
        for char in senha:
            if random.random() < 0.05:
                campo_senha.send_keys(chr(random.randint(33, 126)))
                espera.assentar(driver, random.uniform(0.08, 0.15))
                campo_senha.send_keys(Keys.BACKSPACE)
                espera.assentar(driver, random.uniform(0.08, 0.15))
            campo_senha.send_keys(char)
            espera.assentar(driver, random.uniform(0.08, 0.18))

        if log:
            logger.info('[SISBAJUD][PROTOCOLO] Senha digitada')

        # 4. Clicar Confirmar
        espera.assentar(driver, 0.5)
        script_confirmar = """
        const buttons = Array.from(document.querySelectorAll('button[type="submit"]'));
        const btn = buttons.find(b => {
            const w = b.querySelector('span.mat-button-wrapper');
            return w && w.textContent.trim() === 'Confirmar';
        }) || Array.from(document.querySelectorAll('button'))
                .find(b => b.textContent.includes('Confirmar'));
        if (btn) { btn.click(); return true; }
        return false;
        """
        if not driver.execute_script(script_confirmar):
            if log:
                logger.info('[SISBAJUD][PROTOCOLO] Botao Confirmar nao encontrado')
            return None

        if log:
            logger.info('[SISBAJUD][PROTOCOLO] Confirmar clicado — aguardando...')

        # 5. Verificar sucesso (botao "Copiar Dados para Nova Ordem")
        for _ in range(10):
            espera.assentar(driver, 0.5)
            try:
                ok = driver.execute_script(
                    "return !!document.querySelector('button[title=\"Copiar Dados para Nova Ordem\"]')"
                )
                if ok:
                    break
            except Exception:
                pass

        # 6. Extrair protocolo da URL
        import re as _re
        protocolo = None
        try:
            url = driver.current_url
            m = _re.search(r'/(\d{10,})/', url)
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