import logging
from typing import Any, Optional, Callable
from Fix import espera
from Fix.core import (
    aguardar_e_clicar,
    wait_for_clickable,
    safe_click_no_scroll,
    aguardar_renderizacao_nativa,
    preencher_campo,
)

from .judicial_navegacao import (
    verificar_estado_atual,
    escolher_tipo_conclusao,
    aguardar_transicao_minutar,
    focar_campo_minutar_se_necessario,
)

logger = logging.getLogger(__name__)

# Seletores canônicos do fluxo de modelo (padrão gigs-plugin aaDespacho).
_SEL_FILTRO = 'input#inputFiltro'
_SEL_NODO = '.nodo-filtrado'
_SEL_DIALOGO = 'pje-dialogo-visualizar-modelo'
_SEL_BTN_INSERIR = 'button[aria-label="Inserir modelo de documento"]'
_SEL_BTN_INSERIR_CSS = (
    'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes'
    ' > div.div-botao-inserir > button'
)

# Editor-alvo: o MESMO que recebe o modelo (Dispositivo → Fundamentação → genérico).
# Inclui o CKEditor da juntada de anexos (.ck-editor__editable) para reuso do fluxo.
_JS_EDITOR_ALVO = """() => {
    var sels = [
        'div[class*="area-conteudo"][contenteditable="true"][aria-label*="Dispositivo"]',
        'div[class*="area-conteudo"][contenteditable="true"][aria-label*="Fundamentação"]',
        'div[class*="area-conteudo"][contenteditable="true"]',
        'div.ck-content[contenteditable="true"]',
        '.ck-editor__editable[contenteditable="true"]'
    ];
    for (var s of sels) { if (document.querySelector(s)) return s; }
    return null;
}"""

# Teor carregado no preview do diálogo (guarda anti-corrida: clicar antes = editor vazio).
_JS_TEOR_CARREGADO = """() => {
    var dlg = document.querySelector('pje-dialogo-visualizar-modelo');
    if (!dlg) return false;
    var preview = dlg.querySelector('.div-preview-conteudo, .preview-conteudo, .conteudo-modelo, .ck-content, [class*="preview"]');
    if (!preview) return false;
    var clone = preview.cloneNode(true);
    clone.querySelectorAll('.placeholder-conteudo, .ck-placeholder, [data-placeholder]').forEach(p => p.remove());
    var txt = (clone.innerText || clone.textContent || '').trim();
    return txt.length > 10 || clone.querySelector('figure') !== null || clone.querySelector('table') !== null;
}"""

# Conteúdo REAL no editor-alvo, exigindo mudança vs baseline (evita falso-positivo).
_JS_EDITOR_COM_CONTEUDO = """(sel, baseline) => {
    if (document.querySelector('pdf-viewer')) return true;
    var area = document.querySelector(sel);
    if (!area) return false;
    var clone = area.cloneNode(true);
    clone.querySelectorAll('.placeholder-conteudo, .ck-placeholder, [data-placeholder]').forEach(p => p.remove());
    var txt = (clone.innerText || clone.textContent || '').replace(/\\s/g, '');
    var temFigura = clone.querySelector('figure') !== null;
    var temConteudo = txt.length > 1 || temFigura;
    var mudou = txt.length > (baseline + 5) || (temFigura && baseline === 0);
    return temConteudo && mudou;
}"""


def _resolver_editor_alvo(driver: Any) -> str:
    """Seletor do editor-alvo (o que recebe o modelo)."""
    if hasattr(driver, 'page'):
        try:
            sel = driver.page.evaluate(_JS_EDITOR_ALVO)
            if sel:
                return sel
        except Exception:
            pass
    return 'div[class*="area-conteudo"][contenteditable="true"]'


def _medir_conteudo_editor(driver: Any, seletor: str) -> int:
    """Comprimento do texto real do editor-alvo (sem placeholders)."""
    expr = """(() => {
        var area = document.querySelector(%r);
        if (!area) return 0;
        var clone = area.cloneNode(true);
        clone.querySelectorAll('.placeholder-conteudo, .ck-placeholder, [data-placeholder]').forEach(p => p.remove());
        return (clone.innerText || clone.textContent || '').trim().length;
    })()""" % seletor
    try:
        if hasattr(driver, 'page'):
            return int(driver.page.evaluate(expr) or 0)
    except Exception:
        pass
    return 0


def _preencher_filtro_modelo(driver: Any, modelo_nome: str) -> bool:
    """Preenche o filtro de modelo (setter nativo + eventos + Enter)."""
    if hasattr(driver, 'page'):
        try:
            ok = driver.page.evaluate("""nome => {
                var input = document.querySelector('input#inputFiltro');
                if (!input) return false;
                input.removeAttribute('disabled');
                input.removeAttribute('readonly');
                input.focus();
                Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(input, nome);
                ['input', 'change', 'keyup'].forEach(ev => input.dispatchEvent(new Event(ev, {bubbles: true})));
                return true;
            }""", modelo_nome)
            if ok:
                driver.page.keyboard.press('Enter')
                return True
        except Exception:
            pass
    return bool(preencher_campo(driver, _SEL_FILTRO, modelo_nome, trigger_events=True, limpar=True))


def inserir_modelo_no_editor(
    driver: Any,
    modelo_nome: str,
    log: Optional[Callable] = None,
    timeout_teor: int = 15,
    timeout_conteudo: int = 8,
) -> bool:
    """Insere um modelo no editor de minuta — fluxo ÚNICO (padrão gigs-plugin aaDespacho).

    Encapsula: filtro → nodo-filtrado → diálogo → espera do teor no preview →
    clique em Inserir → confirmação de conteúdo no editor-ALVO (escopada + baseline).

    Retorna True só com conteúdo REAL confirmado no editor-alvo; False caso contrário.
    """
    if log is None:
        def log(_msg):
            return None

    try:
        # Editor-alvo + baseline ANTES de inserir (detecta mudança real depois).
        seletor_editor_alvo = _resolver_editor_alvo(driver)
        baseline_len = _medir_conteudo_editor(driver, seletor_editor_alvo)

        # 1. Filtro do modelo
        if not _preencher_filtro_modelo(driver, modelo_nome):
            log(f'[MODELO] Campo de filtro não encontrado para "{modelo_nome}"')
            return False

        # 2. Nodo filtrado (aguardar_e_clicar já espera aparecer)
        if not aguardar_e_clicar(driver, _SEL_NODO, timeout=15):
            log(f'[MODELO] Nodo filtrado não encontrado para "{modelo_nome}"')
            return False

        # 3. Diálogo de visualização
        if not aguardar_renderizacao_nativa(driver, _SEL_DIALOGO, modo='aparecer', timeout=15):
            log('[MODELO] Diálogo de visualização não abriu')
            return False

        # 4. GUARDA ANTI-CORRIDA: espera POSITIVA do teor no preview (não sleep fixo).
        if not espera.ate_js(driver, _JS_TEOR_CARREGADO, teto=timeout_teor):
            log('[MODELO] Teor do preview não confirmado — prosseguindo com guarda mínima')
            espera.assentar(driver, 1.2, motivo='PJe carregando o teor do modelo')

        # 5. Botão Inserir (aria-label estável; fallback CSS estrutural)
        btn_inserir = wait_for_clickable(driver, _SEL_BTN_INSERIR, timeout=10)
        if not btn_inserir:
            btn_inserir = wait_for_clickable(driver, _SEL_BTN_INSERIR_CSS, timeout=5)
        if not btn_inserir:
            log('[MODELO] Botão Inserir não encontrado')
            return False
        safe_click_no_scroll(driver, btn_inserir)

        # 6. Fecha o diálogo antes de confirmar (evita overlay no fluxo seguinte)
        espera.ate_sumir(driver, _SEL_DIALOGO, teto=15)

        # 7. Confirmação: conteúdo REAL no editor-alvo (escopado + baseline).
        #    Snackbar NÃO é prova (aparece com editor vazio) — só fallback.
        if not espera.ate_js(
            driver,
            "(%s)(%r, %d)" % (_JS_EDITOR_COM_CONTEUDO, seletor_editor_alvo, baseline_len),
            teto=timeout_conteudo,
        ):
            if not espera.ate_js(
                driver,
                "(%s)(%r, %d)" % (_JS_EDITOR_COM_CONTEUDO, seletor_editor_alvo, baseline_len),
                teto=timeout_conteudo,
            ):
                snack_ok = espera.ate_texto(
                    driver, 'simple-snack-bar', 'Modelo de documento inserido com sucesso', teto=5
                )
                if not snack_ok:
                    log(f'[MODELO] Conteúdo do modelo "{modelo_nome}" não confirmado no editor-alvo')
                    return False

        log(f'[MODELO] Modelo "{modelo_nome}" inserido e confirmado no editor-alvo')
        return True
    except Exception as e:
        log(f'[MODELO] Erro ao inserir modelo "{modelo_nome}": {e}')
        return False


def esperar_insercao_modelo(driver: Any, timeout: int = 8000) -> bool:
    try:
        timeout_segundos = timeout / 1000.0
        espera.assentar(driver, timeout_segundos, motivo='inserção de modelo')
        return True
    except Exception as e:
        logger.warning("[MODELO] Erro na espera de insercao de modelo: %s", e)
        return True