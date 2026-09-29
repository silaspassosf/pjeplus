from typing import Any, Optional
import logging
from Fix.core import safe_click_no_scroll
from Fix import espera

logger = logging.getLogger(__name__)


def inserir_sigilo_individual(elemento: Any, driver: Any = None, debug: bool = False) -> bool:
    if not elemento:
        return False

    if not driver:
        try:
            if hasattr(elemento, '_parent'):
                driver = elemento._parent
            else:
                return False
        except Exception:
            return False

    def _tem_sigilo() -> bool:
        try:
            if hasattr(elemento, 'query_selector'):
                return elemento.query_selector('i.tl-sigiloso, a.is-sigiloso') is not None
            cls = (getattr(elemento, 'get_attribute', lambda a: '')('class') or '')
            return 'is-sigiloso' in cls or 'tl-sigiloso' in cls
        except Exception:
            return False

    try:
        if _tem_sigilo():
            return True

        btn_sigilo = None
        for seletor in [
            # LEGADO.md ~45110: o ícone de sigilo é `i.fa-wpexplorer` (dentro de
            # `pje-doc-sigiloso span button`). Sem estes seletores o sigilo não é
            # aplicado, o checkbox do anexo não é marcado e — como a seleção deve
            # preceder o "Visibilidade para Sigilo" — o botão nunca habilita.
            'button[name="Inserir sigilo"]',
            'pje-doc-sigiloso button',
            'pje-doc-sigiloso span button',
            'button i.fa-wpexplorer',
            'i.fa-wpexplorer',
        ]:
            try:
                if hasattr(elemento, 'query_selector'):
                    candidato = elemento.query_selector(seletor)
                    if candidato:
                        btn_sigilo = candidato
                        break
            except Exception:
                continue

        if not btn_sigilo:
            logger.warning('[SIGILO_INSERIR] Botao de sigilo nao encontrado')
            return False

        safe_click_no_scroll(driver, btn_sigilo)

        for _ in range(8):
            espera.assentar(driver, 0.25)
            if _tem_sigilo():
                return True

        logger.warning('[SIGILO_INSERIR] Clique executado, mas sigilo nao foi detectado')
        return False
    except Exception as e:
        logger.warning('[SIGILO_INSERIR] Erro geral: %s', e)
        return False


_JS_MARCAR_SIGILOSOS = """
var n = 0;
function marcar(item) {
  if (!item.querySelector('a.tl-documento.is-sigiloso')) { return; }
  var cb = item.querySelector('mat-checkbox input[type="checkbox"]');
  if (cb && !cb.checked) {
    var alvo = item.querySelector('mat-checkbox label') || cb;
    alvo.click();
    n++;
  }
}
Array.prototype.forEach.call(document.querySelectorAll('.tl-item-anexo'), marcar);
if (n === 0) {
  Array.prototype.forEach.call(document.querySelectorAll('ul.pje-timeline mat-card'), marcar);
}
return n;
"""


def marcar_sigilosos_timeline(driver: Any) -> int:
    """Marca os checkboxes dos documentos sigilosos da timeline.

    Ordem do LEGADO.md (~6793): a seleção do sigiloso vem ANTES do botão
    "Visibilidade para Sigilo". Devolve quantos checkboxes foram marcados.
    """
    try:
        executar = getattr(driver, 'execute_script', None)
        if not executar:
            return 0
        return int(executar(_JS_MARCAR_SIGILOSOS) or 0)
    except Exception:
        return 0


def visibilidade_sigilosos_lote_apenas(driver: Any, polo: str = 'ativo', log: bool = False) -> bool:
    try:
        # Ordem do LEGADO.md (~6793 / Fix.core.visibilidade_sigilosos): PRIMEIRO o
        # documento sigiloso tem de estar selecionado (múltipla seleção ativa), só
        # DEPOIS se clica em "Visibilidade para Sigilo". Sem seleção o botão nunca
        # habilita — era daí que vinha a falha silenciosa do lote.
        marcados = espera.ate_js(
            driver,
            """__pjeEls('ul.pje-timeline mat-checkbox input[type="checkbox"]').some(el => el.checked)""",
            teto=2,
        )
        if not marcados:
            qtd = marcar_sigilosos_timeline(driver)
            if qtd and log:
                logger.info('[VISIBILIDADE_LOTE] %s documento(s) sigiloso(s) selecionado(s) antes da visibilidade', qtd)
            marcados = bool(qtd) and espera.ate_js(
                driver,
                """__pjeEls('ul.pje-timeline mat-checkbox input[type="checkbox"]').some(el => el.checked)""",
                teto=3,
            )
        if not marcados:
            logger.warning('[VISIBILIDADE_LOTE] Nenhum documento sigiloso selecionado na timeline '
                           '— seleção deve preceder o clique em Visibilidade')
            return False

        sel_vis = 'button[mattooltip="Visibilidade para Sigilo"]'
        if not espera.ate_habilitar(driver, sel_vis, teto=5):
            logger.warning('[VISIBILIDADE_LOTE] Botao de visibilidade nao habilitou')
            return False

        btn_vis = espera.elemento(driver, sel_vis, teto=2)
        if not btn_vis:
            logger.warning('[VISIBILIDADE_LOTE] Botao de visibilidade nao encontrado')
            return False
        safe_click_no_scroll(driver, btn_vis)

        modal_container = '.cdk-overlay-container .mat-dialog-container'
        modal = espera.elemento(driver, modal_container, teto=4, visivel=False)
        if modal:
            espera.elemento(driver, f'{modal_container} tr.cdk-drag', teto=5, visivel=False)

        seletor_marcar = 'button[aria-label="Marcar todas"], i.fa.fa-check.botao-icone-titulo-coluna'
        if not espera.ate_habilitar(driver, seletor_marcar, teto=5):
            logger.warning('[VISIBILIDADE_LOTE] Botao Marcar todas nao habilitou')
            return False

        icone_header = espera.elemento(driver, seletor_marcar, teto=2)
        if not icone_header:
            logger.warning('[VISIBILIDADE_LOTE] Icone "Marcar todas" nao encontrado no modal')
            return False
        safe_click_no_scroll(driver, icone_header)

        xpath_salvar = '//button[.//span[contains(text(),"Salvar")]]'
        if not espera.ate_habilitar(driver, xpath_salvar, teto=10):
            logger.warning('[VISIBILIDADE_LOTE] Botao Salvar nao habilitou')
            return False

        btn_salvar = espera.elemento(driver, xpath_salvar, teto=2)
        if not btn_salvar:
            logger.warning('[VISIBILIDADE_LOTE] Botao Salvar nao encontrado')
            return False
        safe_click_no_scroll(driver, btn_salvar)

        return True
    except Exception as e:
        logger.warning('[VISIBILIDADE_LOTE][ERRO] Falha ao aplicar visibilidade em lote: %s', e)
        return False
