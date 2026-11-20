from typing import Any, Optional
import logging
import time
from Fix.core import safe_click_no_scroll
from Fix import espera

logger = logging.getLogger(__name__)


_JS_ESTADO_VISIBILIDADE = """
const selDialogs = [
  'pje-doc-visibilidade-sigilo',
  'pje-data-table[nametabela="Tabela de Controle de Sigilo"]',
  'pje-dialogo-status-progresso',
  'mat-dialog-container',
  '.mat-dialog-container',
  '.mat-mdc-dialog-container'
];
const dialogs = [];
for (const sel of selDialogs) {
  if (document.querySelector(sel)) dialogs.push(sel);
}
const visivel = (el) => {
  if (!el) return false;
  const st = window.getComputedStyle(el);
  if (!st || st.display === 'none' || st.visibility === 'hidden' || parseFloat(st.opacity || '1') === 0) return false;
  const r = el.getBoundingClientRect();
  return (r.width > 0 || r.height > 0 || el.getClientRects().length > 0);
};
let backdrop = false;
for (const b of document.querySelectorAll('.cdk-overlay-backdrop.cdk-overlay-backdrop-showing, .modal-backdrop')) {
  if (visivel(b)) { backdrop = true; break; }
}
let loading = false;
for (const l of document.querySelectorAll('mat-progress-spinner, mat-spinner, mat-progress-bar, .loading-spinner, .loading-overlay')) {
  if (visivel(l)) { loading = true; break; }
}
return {
  dialogs: dialogs,
  backdrop: backdrop,
  loading: loading,
  livre: dialogs.length === 0 && !backdrop && !loading
};
"""


def _exec_js(driver: Any, script_body: str) -> Any:
    fn = getattr(driver, 'execute_script', None)
    if fn is not None:
        return fn(script_body)
    page = getattr(driver, 'page', getattr(driver, '_page', None))
    if page is not None and hasattr(page, 'evaluate'):
        return page.evaluate("() => { " + script_body + " }")
    if hasattr(driver, 'evaluate'):
        return driver.evaluate("() => { " + script_body + " }")
    return None


def _estado_visibilidade(driver: Any) -> dict:
    try:
        res = _exec_js(driver, _JS_ESTADO_VISIBILIDADE)
        if isinstance(res, dict) and 'livre' in res:
            return res
    except Exception as e:
        logger.debug('[VISIBILIDADE_AGUARDA] Falha ao consultar estado DOM: %s', e)
    return {'dialogs': [], 'backdrop': False, 'loading': False, 'livre': True}


def aguardar_visibilidade_concluida(
    driver: Any,
    timeout: float = 30.0,
    estabilidade: float = 0.5,
    log: bool = False,
) -> bool:
    """Aguarda ausência contínua de dialogs/overlay/spinner de visibilidade por `estabilidade`s."""
    inicio = time.monotonic()
    livre_desde: list[Optional[float]] = [None]
    ultimo_estado: dict = {'dialogs': [], 'backdrop': False, 'loading': False, 'livre': True}
    esperou = [False]

    def _estavel(_drv: Any) -> bool:
        agora = time.monotonic()
        estado = _estado_visibilidade(driver)
        ultimo_estado.clear()
        ultimo_estado.update(estado)
        if estado.get('livre', False):
            if livre_desde[0] is None:
                livre_desde[0] = agora
            if (agora - livre_desde[0]) >= estabilidade:
                if log and esperou[0]:
                    logger.info('[VISIBILIDADE_AGUARDA] Concluída e estável após %.2fs', agora - inicio)
                return True
            return False
        if not esperou[0] and log:
            logger.info(
                '[VISIBILIDADE_AGUARDA] Aguardando fechamento de visibilidade/overlay (dialogs=%s, backdrop=%s, loading=%s)...',
                estado.get('dialogs'), estado.get('backdrop'), estado.get('loading'),
            )
        esperou[0] = True
        livre_desde[0] = None
        return False

    if espera.ate(driver, _estavel, teto=max(0.2, float(timeout)), intervalo=0.15):
        return True
    if ultimo_estado.get('livre', False):
        return True

    logger.warning(
        '[VISIBILIDADE_AGUARDA] Timeout (%.1fs) — dialog/overlay ainda aberto: dialogs=%s backdrop=%s loading=%s',
        timeout, ultimo_estado.get('dialogs'), ultimo_estado.get('backdrop'), ultimo_estado.get('loading'),
    )
    return False


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

        # Verifica antes de dormir: quando o PJe já aplicou o sigilo no próprio
        # clique, o laço sai na primeira iteração em vez de pagar 250ms fixos.
        for _ in range(8):
            if _tem_sigilo():
                return True
            espera.assentar(driver, 0.25)

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
        return int(_exec_js(driver, _JS_MARCAR_SIGILOSOS) or 0)
    except Exception as e:
        logger.warning('[SIGILO_MARCAR] Erro ao executar js: %s', e)
        return 0


def visibilidade_sigilosos_lote_apenas(driver: Any, polo: str = 'ativo', log: bool = False) -> bool:
    try:
        # Garantir que nenhum dialog/overlay anterior esteja aberto antes de iniciar
        aguardar_visibilidade_concluida(driver, timeout=15.0, estabilidade=0.3, log=log)

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

        modal_container = '.cdk-overlay-container .mat-dialog-container, .cdk-overlay-container mat-dialog-container, pje-doc-visibilidade-sigilo'
        modal = espera.elemento(driver, modal_container, teto=5, visivel=False)
        if modal:
            espera.elemento(driver, '.cdk-overlay-container tr.cdk-drag, pje-doc-visibilidade-sigilo tr.cdk-drag', teto=5, visivel=False)
            # Aguardar barra de progresso inicial do modal carregar a tabela de partes
            espera.ate_sumir(driver, 'pje-doc-visibilidade-sigilo mat-progress-bar', teto=10)

        seletor_marcar = 'button[aria-label="Marcar todas"], i.fa.fa-check.botao-icone-titulo-coluna, .botao-icone-titulo-coluna'
        marcou_todos = False
        try:
            icone_header = espera.elemento(driver, seletor_marcar, teto=2)
            if icone_header:
                safe_click_no_scroll(driver, icone_header)
                # Marcar todas dispara mat-progress-bar interno do pje-doc-visibilidade-sigilo
                # (cf. api/gigs-plugin.js): aguardar concluir antes de clicar em Salvar.
                if espera.ate_aparecer(driver, 'pje-doc-visibilidade-sigilo mat-progress-bar', teto=0.8):
                    espera.ate_sumir(driver, 'pje-doc-visibilidade-sigilo mat-progress-bar', teto=10)
                espera.assentar(driver, 0.2)
                marcou_todos = True
        except Exception:
            pass

        # Fallback pré-limpeza do dia 29: se não marcou pelo header, marca cada checkbox do modal
        if not marcou_todos:
            try:
                checkboxes = espera.elementos(driver, '.cdk-overlay-container mat-checkbox', teto=2)
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

        xpath_salvar = '//mat-dialog-container//button[contains(., "Salvar") or .//span[contains(text(),"Salvar")]]'
        if not espera.ate_habilitar(driver, xpath_salvar, teto=10):
            logger.warning('[VISIBILIDADE_LOTE] Botao Salvar nao habilitou')
            return False

        btn_salvar = espera.elemento(driver, xpath_salvar, teto=2)
        if not btn_salvar:
            logger.warning('[VISIBILIDADE_LOTE] Botao Salvar nao encontrado')
            return False
        safe_click_no_scroll(driver, btn_salvar)

        # Se em 2.5s o modal não fechou nem entrou em progresso, retenta clique (re-render Angular).
        def _salvar_reagiu(_drv: Any) -> bool:
            st = _estado_visibilidade(driver)
            dialogs = st.get('dialogs', [])
            return bool(
                st.get('livre')
                or st.get('loading')
                or 'pje-dialogo-status-progresso' in dialogs
                or 'pje-doc-visibilidade-sigilo' not in dialogs
            )

        if not espera.ate(driver, _salvar_reagiu, teto=2.5, intervalo=0.15):
            try:
                btn_retry = espera.elemento(driver, xpath_salvar, teto=0.8)
                if btn_retry:
                    if log:
                        logger.info('[VISIBILIDADE_LOTE] Modal ainda aberto sem progresso após Salvar — retentando clique')
                    safe_click_no_scroll(driver, btn_retry)
            except Exception:
                pass

        # Barreira rigorosa: só prosseguir quando NENHUMA dialog de visibilidade,
        # diálogo de progresso ("Aguarde"), backdrop ou spinner existir e permanecer
        # estável sem reabrir.
        fechou = aguardar_visibilidade_concluida(driver, timeout=30.0, estabilidade=0.5, log=log)
        if not fechou:
            logger.warning('[VISIBILIDADE_LOTE] Dialog de visibilidade nao fechou completamente dentro do timeout')
            return False

        # Ocultar múltipla seleção somente APÓS confirmar fechamento completo do modal
        try:
            sel_ocultar = 'button[aria-label="Ocultar múltipla seleção."]'
            btn_ocultar = espera.elemento(driver, sel_ocultar, teto=1.5)
            if btn_ocultar:
                safe_click_no_scroll(driver, btn_ocultar)
                espera.ate_sumir(driver, sel_ocultar, teto=5)
        except Exception:
            pass

        # Confirmação final de estabilidade antes de devolver controle ao fluxo
        aguardar_visibilidade_concluida(driver, timeout=10.0, estabilidade=0.3, log=log)
        return True
    except Exception as e:
        logger.warning('[VISIBILIDADE_LOTE][ERRO] Falha ao aplicar visibilidade em lote: %s', e)
        return False
