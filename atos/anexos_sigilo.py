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

    _SEL_SIGILOSO = (
        'i.tl-sigiloso, a.is-sigiloso, '
        'i.fa-wpexplorer.tl-sigiloso, i.fas.fa-plus.tl-sigiloso, '
        'button[name="Retirar sigilo"], button[aria-label*="Retirar sigilo" i], '
        'button[mattooltip*="Retirar sigilo" i]'
    )

    def _tem_sigilo() -> bool:
        try:
            if hasattr(elemento, '_handle') and hasattr(elemento._handle, 'query_selector'):
                if elemento._handle.query_selector(_SEL_SIGILOSO) is not None:
                    return True
            if hasattr(elemento, 'query_selector'):
                if elemento.query_selector(_SEL_SIGILOSO) is not None:
                    return True
            if espera.elementos(elemento, _SEL_SIGILOSO, teto=0.3):
                return True
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
            'button[aria-label*="Inserir sigilo" i]',
            'button[mattooltip*="Inserir sigilo" i]',
            'pje-doc-sigiloso button',
            'pje-doc-sigiloso span button',
            'button i.fa-wpexplorer',
            'i.fa-wpexplorer',
        ]:
            try:
                if hasattr(elemento, '_handle') and hasattr(elemento._handle, 'query_selector'):
                    h = elemento._handle.query_selector(seletor)
                    if h:
                        from Play.pjeplay.element import PWElement
                        btn_sigilo = PWElement(h)
                        break
                elif hasattr(elemento, 'query_selector'):
                    candidato = elemento.query_selector(seletor)
                    if candidato:
                        btn_sigilo = candidato
                        break
                else:
                    candidato = espera.elemento(elemento, seletor, teto=0.5, visivel=True)
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

        # Se clicou sem erro e o botão de inserir sumiu/mudou, considerar inserido
        try:
            ainda_inserir = espera.elementos(elemento, 'button[name="Inserir sigilo"]', teto=0.2)
            if not ainda_inserir:
                return True
        except Exception:
            pass

        logger.info('[SIGILO_INSERIR] Clique em sigilo executado com sucesso')
        return True
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
        fn = getattr(driver, 'execute_script', None)
        if fn is not None:
            return int(fn(_JS_MARCAR_SIGILOSOS) or 0)
        page = getattr(driver, 'page', getattr(driver, '_page', getattr(driver, 'evaluate', None)))
        if hasattr(page, 'evaluate'):
            script_pw = "() => { " + _JS_MARCAR_SIGILOSOS + " }"
            return int(page.evaluate(script_pw) or 0)
        return 0
    except Exception as e:
        logger.warning('[SIGILO_MARCAR] Erro ao executar js: %s', e)
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

        seletor_marcar = 'button[aria-label="Marcar todas"], i.fa.fa-check.botao-icone-titulo-coluna, .botao-icone-titulo-coluna'
        marcou_todos = False
        try:
            icone_header = espera.elemento(driver, seletor_marcar, teto=2)
            if icone_header:
                safe_click_no_scroll(driver, icone_header)
                espera.assentar(driver, 0.2)
                marcou_todos = True
        except Exception:
            pass

        # Fallback pré-limpeza do dia 29: se não marcou pelo header, marca cada checkbox do modal
        if not marcou_todos:
            try:
                checkboxes = espera.elementos(driver, f'{modal_container} mat-checkbox', teto=2)
                for cb in checkboxes:
                    try:
                        inp = espera.elemento(cb, 'input[type="checkbox"]', teto=0.3)
                        is_sel = getattr(inp, 'is_selected', lambda: False)() or getattr(inp, 'is_checked', lambda: False)()
                        if not is_sel:
                            safe_click_no_scroll(driver, cb)
                            espera.assentar(driver, 0.05)
                    except Exception:
                        continue
            except Exception:
                pass

        xpath_salvar = '//mat-dialog-container//button[contains(., "Salvar")] | //button[.//span[contains(text(),"Salvar")]]'
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
