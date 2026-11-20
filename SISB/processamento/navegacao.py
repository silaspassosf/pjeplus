"""SISB Navegação — retorno entre listas de ordens e séries do SISBAJUD."""

import logging

from Fix import espera
from Fix.core import safe_click_no_scroll
from Fix.entrada_campos import _fechar_dropdown_ou_esc

logger = logging.getLogger(__name__)

_SEL_BACKDROP = 'div.cdk-overlay-backdrop.cdk-overlay-dark-backdrop.cdk-overlay-backdrop-showing'


def _voltar_para_lista_ordens_serie(driver, log=True):
    """Volta da ordem processada (/desdobrar) para a lista de ordens da série."""
    try:
        url_atual = (driver.current_url or '').lower()
        if "/desdobrar" not in url_atual:
            return "/detalhes" in url_atual

        espera.ate_js(driver, "document.readyState === 'complete'", teto=3)
        seletores_voltar = (
            "button[aria-label='Voltar'] i.fa-chevron-left",
            "button i.fa-chevron-left",
            ".fa-chevron-left",
            "i.fa-chevron-left",
            "button.btn-voltar",
            "[aria-label='Voltar']",
            "button[title='Voltar']",
        )

        botao_encontrado = False
        for seletor in seletores_voltar:
            for el in espera.elementos(driver, seletor, teto=0.2):
                try:
                    if el.is_displayed() and el.is_enabled():
                        safe_click_no_scroll(driver, el)
                        botao_encontrado = True
                        break
                except Exception:
                    continue
            if botao_encontrado:
                break

        if not botao_encontrado:
            try:
                js = """
                for (var b of document.querySelectorAll('button, a, .btn')) {
                    if (b.querySelector('i.fa-chevron-left, .fa-chevron-left') && b.offsetParent !== null) {
                        b.click(); return true;
                    }
                }
                return false;
                """
                botao_encontrado = bool(espera._executar_script(driver, js))
            except Exception:
                pass

        if not botao_encontrado:
            return False

        espera.ate_js(driver, "!location.href.includes('/desdobrar')", teto=5)
        if not espera.ate_aparecer(driver, 'table.mat-table', teto=10) and log:
            logger.error("[SISBAJUD] Erro ao aguardar tabela: nao apareceu")
        return True
    except Exception as e:
        if log:
            logger.error("[SISBAJUD] Erro ao voltar para lista de ordens da serie: %s", e)
        return False


def _voltar_para_lista_principal(driver, log=True):
    """Volta para a lista principal de séries preservando estado da SPA Angular."""
    try:
        overlays = espera.elementos(driver, _SEL_BACKDROP, teto=0.2)
        if overlays:
            for overlay in overlays:
                try:
                    overlay.click()
                    espera.ate_sumir(driver, _SEL_BACKDROP, teto=0.5)
                except Exception:
                    try:
                        espera._executar_script(driver, "arguments[0].style.display = 'none';", overlay)
                    except Exception:
                        pass
            espera.assentar(driver, 1)

        seletores_voltar = (
            'button.mat-icon-button .fa-chevron-left',
            'button[mat-icon-button] .fas.fa-chevron-left',
            'button .mat-icon.fa-chevron-left',
            'button i.fa-chevron-left',
            '.fa-chevron-left',
        )
        botao_voltar_clicado = False
        for _ in range(2):
            botao_voltar_clicado = False
            for seletor in seletores_voltar:
                try:
                    _fechar_dropdown_ou_esc(driver)
                    espera.ate_sumir(driver, _SEL_BACKDROP, teto=0.5)
                    botao_icon = espera.elemento(driver, seletor, teto=0.4)
                    if not botao_icon:
                        continue
                    botao = espera.elemento(botao_icon, './ancestor::button[1]', teto=0.2) or botao_icon
                    safe_click_no_scroll(driver, botao)
                    botao_voltar_clicado = True
                    espera.ate_aparecer(driver, 'table.mat-table', teto=5)
                    break
                except Exception:
                    continue
            if not botao_voltar_clicado:
                break

        return botao_voltar_clicado
    except Exception as e:
        if log:
            logger.error("[SISBAJUD] Erro ao voltar para lista principal: %s", e)
        return False
