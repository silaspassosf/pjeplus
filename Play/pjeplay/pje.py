"""Vocabulário PJe nativo — as primitivas em que os fluxos portados são escritos."""
import logging
import re
import time as _time

logger = logging.getLogger("pjeplay")


def _aguardar_eval(page, fn, timeout=10, passo_ms=50):
    """Polling síncrono via `page.evaluate` (imune a `ZoneAwarePromise` no Firefox)."""
    limite = _time.monotonic() + max(0.0, float(timeout))
    while True:
        try:
            if page.evaluate(fn):
                return True
        except Exception:
            pass
        if _time.monotonic() >= limite:
            return False
        page.wait_for_timeout(passo_ms)

PAINEL_CDK = "div.cdk-overlay-pane"
BACKDROP_CDK = ".cdk-overlay-backdrop"
OPCOES = "mat-option, [role='option']"
SPINNER = "mat-spinner, mat-progress-spinner, .mat-spinner"
MODAL = "mat-dialog-container, [role='dialog']"

_JS_ANGULAR_ESTAVEL = """
() => {
  const t = window.getAllAngularTestabilities?.();
  if (!t || t.length === 0) return true;
  return t.every(x => x.isStable());
}
"""

# R3: o PJe pode servir CKEditor 4 (CKEDITOR global) ou 5 (instância no DOM).
_JS_CKEDITOR_VERSAO = """
() => {
  if (typeof CKEDITOR !== 'undefined' && Object.keys(CKEDITOR.instances || {}).length) return 'ck4';
  const el = document.querySelector('.ck-editor__editable');
  if (el && el.ckeditorInstance) return 'ck5';
  return null;
}
"""

_JS_CKEDITOR_SET = """
([html, versao]) => {
  if (versao === 'ck4') {
    const id = Object.keys(CKEDITOR.instances)[0];
    CKEDITOR.instances[id].setData(html);
    return true;
  }
  const el = document.querySelector('.ck-editor__editable');
  if (el && el.ckeditorInstance) { el.ckeditorInstance.setData(html); return true; }
  return false;
}
"""

_JS_CKEDITOR_GET = """
(versao) => {
  if (versao === 'ck4') {
    const id = Object.keys(CKEDITOR.instances)[0];
    return CKEDITOR.instances[id].getData();
  }
  const el = document.querySelector('.ck-editor__editable');
  return el && el.ckeditorInstance ? el.ckeditorInstance.getData() : null;
}
"""


def pagina(alvo):
    """Extrai a Page do Playwright de um PWDriver, Page ou Frame."""
    return getattr(alvo, "page", alvo)


def _ms(timeout):
    return int(float(timeout) * 1000)


def aguardar_angular(alvo, timeout=10):
    """Aguarda o ngZone estabilizar. Cai para ausência de spinner (R4)."""
    page = pagina(alvo)
    if _aguardar_eval(page, _JS_ANGULAR_ESTAVEL, timeout=timeout):
        return True
    return esperar_spinner(page, timeout=timeout)


def esperar_spinner(alvo, timeout=30):
    """Aguarda o spinner sumir. Retorna True também se ele nunca apareceu."""
    page = pagina(alvo)
    try:
        page.locator(SPINNER).first.wait_for(state="hidden", timeout=_ms(timeout))
        return True
    except Exception:
        return False


def esperar_rota(alvo, padrao, timeout=15):
    """Aguarda o router Angular chegar numa rota (`**/processo/**`)."""
    page = pagina(alvo)
    try:
        page.wait_for_url(padrao, timeout=_ms(timeout))
        return True
    except Exception:
        return False


# -- Angular Material -------------------------------------------------------

def mat_select(alvo, seletor, opcao, exato=False, timeout=10):
    """Seleciona opção num mat-select (ou <select> nativo)."""
    page = pagina(alvo)
    ms = _ms(timeout)
    try:
        campo = page.locator(seletor).first
        campo.wait_for(state="visible", timeout=ms)

        if campo.evaluate("el => el.tagName.toLowerCase()") == "select":
            campo.select_option(label=opcao)
            return True

        campo.click(timeout=ms)
        page.locator(PAINEL_CDK).first.wait_for(state="visible", timeout=ms)
        opcoes = page.locator(OPCOES)
        opcoes.first.wait_for(state="visible", timeout=ms)

        filtro = re.compile(rf"^\s*{re.escape(opcao)}\s*$") if exato else opcao
        opcoes.filter(has_text=filtro).first.click(timeout=ms)

        try:
            page.locator(PAINEL_CDK).first.wait_for(state="hidden", timeout=ms)
        except Exception:
            logger.debug("mat_select: overlay seguiu aberto em '%s'", seletor)
        return True
    except Exception as e:
        logger.error("mat_select '%s' -> '%s': %s", seletor, opcao, e)
        return False


def mat_input(alvo, seletor, valor, limpar=True, timeout=10):
    """Preenche campo Angular Material. `fill` já dispara input/change."""
    page = pagina(alvo)
    try:
        campo = page.locator(seletor).first
        campo.wait_for(state="visible", timeout=_ms(timeout))
        if limpar:
            campo.fill(str(valor))
        else:
            campo.press_sequentially(str(valor))
        return True
    except Exception as e:
        logger.error("mat_input '%s': %s", seletor, e)
        return False


def mat_checkbox(alvo, seletor, marcar=True, timeout=10):
    """Garante o estado do checkbox — sem toggle indesejado."""
    page = pagina(alvo)
    try:
        caixa = page.locator(seletor).first
        caixa.wait_for(state="visible", timeout=_ms(timeout))
        interno = caixa.locator("input[type='checkbox']")
        atual = interno.is_checked() if interno.count() else caixa.is_checked()
        if atual != marcar:
            caixa.click(timeout=_ms(timeout))
        return True
    except Exception as e:
        logger.error("mat_checkbox '%s': %s", seletor, e)
        return False


def mat_data(alvo, seletor, data, timeout=10):
    """Preenche datepicker e fecha o calendário."""
    page = pagina(alvo)
    if not mat_input(page, seletor, data, timeout=timeout):
        return False
    page.keyboard.press("Escape")
    return True


def filtro_100(alvo, timeout=15):
    """Aplica 100 itens por página no painel global."""
    page = pagina(alvo)
    seletor = ("mat-select[aria-label*='Items per page'], "
               "mat-select[aria-label*='itens'], mat-paginator mat-select")
    if not mat_select(page, seletor, "100", exato=True, timeout=timeout):
        return False
    return esperar_spinner(page, timeout=timeout)


def abrir_modal(alvo, timeout=10):
    page = pagina(alvo)
    try:
        page.locator(MODAL).first.wait_for(state="visible", timeout=_ms(timeout))
        return True
    except Exception:
        return False


def fechar_modal(alvo, timeout=5):
    page = pagina(alvo)
    try:
        page.keyboard.press("Escape")
        page.locator(MODAL).first.wait_for(state="hidden", timeout=_ms(timeout))
        return True
    except Exception:
        return False


def esperar_overlay_fechar(alvo, timeout=5):
    page = pagina(alvo)
    try:
        page.locator(BACKDROP_CDK).first.wait_for(state="hidden", timeout=_ms(timeout))
        return True
    except Exception:
        return False


def abrir_em_nova_aba(alvo, acao, timeout=15):
    """Executa `acao` e devolve a Page que ela abriu."""
    page = pagina(alvo)
    with page.context.expect_page(timeout=_ms(timeout)) as info:
        acao()
    nova = info.value
    nova.wait_for_load_state("domcontentloaded")
    return nova


def fechar_abas_extras(alvo, manter=None):
    """Fecha todas as abas menos `manter` (padrão: a primeira do contexto)."""
    page = pagina(alvo)
    principal = manter or page.context.pages[0]
    fechadas = 0
    for aba in list(page.context.pages):
        if aba is not principal and not aba.is_closed():
            try:
                aba.close()
                fechadas += 1
            except Exception:
                pass
    return fechadas


# -- CKEditor ---------------------------------------------------------------

def ckeditor_versao(alvo, timeout=10):
    """Detecta CKEditor 4 / 5 / ausente, aguardando a inicialização (R3)."""
    page = pagina(alvo)
    if not _aguardar_eval(page, f"() => ({_JS_CKEDITOR_VERSAO})() !== null", timeout=timeout):
        return None
    return page.evaluate(_JS_CKEDITOR_VERSAO)


def ckeditor_definir(alvo, html, timeout=10):
    page = pagina(alvo)
    versao = ckeditor_versao(page, timeout=timeout)
    if versao is None:
        logger.error("ckeditor_definir: nenhuma instância encontrada")
        return False
    return bool(page.evaluate(_JS_CKEDITOR_SET, [html, versao]))


def ckeditor_obter(alvo, timeout=10):
    page = pagina(alvo)
    versao = ckeditor_versao(page, timeout=timeout)
    if versao is None:
        return None
    return page.evaluate(_JS_CKEDITOR_GET, versao)


def linha_tabela(alvo, texto, seletor_linha="mat-row, tr"):
    """Locator da linha que contém `texto` — lazy, re-resolve a cada uso."""
    return pagina(alvo).locator(seletor_linha).filter(has_text=texto)


def esperar_tabela(alvo, seletor="mat-table, table", timeout=15):
    """Aguarda a tabela existir e ter ao menos uma linha."""
    page = pagina(alvo)
    try:
        page.locator(seletor).first.wait_for(state="visible", timeout=_ms(timeout))
        page.locator("mat-row, tbody tr").first.wait_for(
            state="visible", timeout=_ms(timeout))
        return True
    except Exception:
        return False


def acesso_negado(alvo):
    page = pagina(alvo)
    try:
        if "acesso negado" in (page.title() or "").lower():
            return True
        return page.locator("text=/Acesso negado/i").first.is_visible(timeout=500)
    except Exception:
        return False


def sessao_expirada(alvo):
    page = pagina(alvo)
    try:
        if "/login" in (page.url or ""):
            return True
        return page.locator("input[type='password']").first.is_visible(timeout=500)
    except Exception:
        return False
