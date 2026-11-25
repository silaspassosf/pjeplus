import json
import logging
import time
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

_SEL_FILTRO = 'input#inputFiltro'
_SEL_NODO = '.nodo-filtrado'
_SEL_DIALOGO = 'pje-dialogo-visualizar-modelo'
_SEL_BTN_INSERIR = 'button[aria-label="Inserir modelo de documento"]'
_SEL_BTN_INSERIR_CSS = (
    'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes'
    ' > div.div-botao-inserir > button'
)

# Inclui o CKEditor da juntada de anexos (.ck-editor__editable) para reuso do fluxo.
_SEL_EDITOR_TEXTOBOX = 'div[class*="area-conteudo"][contenteditable="true"][role="textbox"]'

_JS_EDITOR_ALVO = """() => {
    var sels = [
        'div[class*="area-conteudo"][contenteditable="true"][role="textbox"][aria-label*="Dispositivo"]',
        'div[class*="area-conteudo"][contenteditable="true"][role="textbox"][aria-label*="Fundamentação"]',
        'div[class*="area-conteudo"][contenteditable="true"][role="textbox"]',
        'div[class*="area-conteudo"] div[contenteditable="true"][aria-label*="Dispositivo"]',
        'div[class*="area-conteudo"] div[contenteditable="true"][aria-label*="Fundamentação"]',
        'div[class*="area-conteudo"][contenteditable="true"][aria-label*="Dispositivo"]',
        'div[class*="area-conteudo"][contenteditable="true"][aria-label*="Fundamentação"]',
        'div[class*="area-conteudo"] div[contenteditable="true"]',
        'div[class*="area-conteudo"][contenteditable="true"]',
        'div.ck-content[contenteditable="true"]',
        '.ck-editor__editable[contenteditable="true"]'
    ];
    for (var s of sels) {
        var els = Array.from(document.querySelectorAll(s)).filter(function(el) {
            return !el.closest('pje-dialogo-visualizar-modelo');
        });
        if (els.length) return s;
    }
    return null;
}"""

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

_JS_EDITOR_COM_CONTEUDO = """(sel) => {
    var areas = Array.from(document.querySelectorAll(sel)).filter(function(el) {
        return !el.closest('pje-dialogo-visualizar-modelo');
    });
    var area = areas[0];
    if (!area) return false;
    // Placeholder ("Dispositivo", "Digite aqui...") tambem e innerText > 1 char e
    // fazia a confirmacao passar com o editor VAZIO — remover antes de medir.
    var clone = area.cloneNode(true);
    clone.querySelectorAll('.placeholder-conteudo, .ck-placeholder, [data-placeholder]').forEach(p => p.remove());
    var texto = (clone.innerText || '').trim();
    if (texto.length > 1) return true;          // texto real no editor
    return area.querySelector('figure') !== null;  // imagem anexada sem texto
}"""

_JS_TRECHO_PREVIEW = """() => {
    var dlg = document.querySelector('pje-dialogo-visualizar-modelo');
    if (!dlg) return '';
    var preview = dlg.querySelector('.div-preview-conteudo, .preview-conteudo, .conteudo-modelo, .ck-content, [class*="preview"]');
    if (!preview) return '';
    var clone = preview.cloneNode(true);
    clone.querySelectorAll('.placeholder-conteudo, .ck-placeholder, [data-placeholder], button').forEach(p => p.remove());
    var txt = (clone.innerText || clone.textContent || '').replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim().toLowerCase();
    var palavras = txt.split(' ').filter(w => w.length > 2);
    if (palavras.length < 4) return '';
    var meio = Math.max(0, Math.floor(palavras.length / 2) - 3);
    return palavras.slice(meio, meio + 6).join(' ');
}"""

_JS_EDITOR_CONTEM_TRECHO = """(trecho) => {
    if (!trecho) return false;
    var areas = Array.from(document.querySelectorAll(
        'div[class*="area-conteudo"][contenteditable="true"], div[class*="area-conteudo"] div[contenteditable="true"], .ck-editor__editable[contenteditable="true"]'));
    for (var a of areas) {
        if (a.closest('pje-dialogo-visualizar-modelo')) continue;
        var txt = (a.innerText || a.textContent || '').replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').toLowerCase();
        var palavras = txt.split(' ').filter(w => w.length > 2).join(' ');
        if (palavras.indexOf(trecho) !== -1) return true;
    }
    return false;
}"""

_JS_MEDIR = """(sel) => {
    var area = document.querySelector(sel);
    if (!area) return -1;
    return ((area.innerText || '').trim()).length;
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


def _focar_editor_alvo(driver: Any) -> bool:
    """Foca e ativa o editor-alvo (dispositivo -> fundamentação -> genérico), conforme padrão gigs-plugin aaDespacho."""
    js_foco = """() => {
        var areas = Array.from(document.querySelectorAll('div[class*="area-conteudo"] div[contenteditable="true"], div[class*="area-conteudo"][contenteditable="true"], div.ck-content[contenteditable="true"]'));
        if (!areas.length) return false;
        var ehSentenca = Array.from(document.querySelectorAll('div[class*="area-conteudo"] div[class*="placeholder-conteudo"]'))
            .some(function(el) { return (el.innerText || '').toLowerCase().indexOf('dispositivo') !== -1; });
        var nomeAlvo = ehSentenca ? 'dispositivo' : 'fundamentacao';
        var foco = areas.find(function(el) {
            var lbl = (el.getAttribute('aria-label') || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
            return lbl.indexOf(nomeAlvo) !== -1;
        }) || areas[0];
        if (foco) {
            foco.focus();
            try { foco.click(); } catch (e) {}
            return true;
        }
        return false;
    }"""
    try:
        if hasattr(driver, 'page'):
            return bool(driver.page.evaluate(js_foco))
        elif hasattr(driver, '_js'):
            return bool(driver._js(js_foco))
    except Exception:
        pass
    return False


def _sincronizar_editor_alvo(driver: Any, seletor: str) -> bool:
    """Dispara eventos de sincronização CKEditor -> Angular no editor-alvo."""
    js_sync = """(sel) => {
        var areas = Array.from(document.querySelectorAll(sel)).filter(function(el) {
            return !el.closest('pje-dialogo-visualizar-modelo');
        });
        var area = areas[0];
        if (!area) return false;
        try { area.focus(); } catch (e) {}
        try {
            var ck = area.ckeditorInstance;
            if (ck) {
                if (typeof ck.updateSourceElement === 'function') ck.updateSourceElement();
                if (ck.model && ck.model.document && typeof ck.model.document.fire === 'function') {
                    ck.model.document.fire('change:data');
                }
            }
        } catch (e) {}
        ['input', 'change', 'keyup'].forEach(function(ev) {
            try { area.dispatchEvent(new Event(ev, {bubbles: true})); } catch (e) {}
        });
        try { area.dispatchEvent(new FocusEvent('blur', {bubbles: true})); } catch (e) {}
        return true;
    }"""
    try:
        if hasattr(driver, 'page'):
            return bool(driver.page.evaluate(js_sync, seletor))
        elif hasattr(driver, '_js'):
            return bool(driver._js(f"({js_sync})({json.dumps(seletor)})"))
    except Exception:
        pass
    return False


def editor_tem_conteudo(driver: Any, seletor: Optional[str] = None) -> bool:
    """Verifica se o editor-alvo contém texto real (sem placeholders) ou figura."""
    sel = seletor or _resolver_editor_alvo(driver)
    expr = "(%s)(%s)" % (_JS_EDITOR_COM_CONTEUDO, json.dumps(sel))
    try:
        if hasattr(driver, 'page'):
            return bool(driver.page.evaluate(expr))
        return bool(espera.ate_js(driver, expr, teto=0.5))
    except Exception:
        return False


def _medir_conteudo_editor(driver: Any, seletor: str) -> int:
    """Comprimento do texto real do editor-alvo (-1 se o editor não existe)."""
    expr = "(%s)(%s)" % (_JS_MEDIR, json.dumps(seletor))
    try:
        if hasattr(driver, 'page'):
            return int(driver.page.evaluate(expr))
    except Exception:
        pass
    return -1


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


def _localizar_e_clicar_nodo_filtrado(driver: Any, timeout: int = 15) -> bool:
    """Aguarda o filtro da árvore concluir (sem spinner) e clica no nodo filtrado, expandindo galhos se necessário."""
    js_expandir_e_buscar = """() => {
        // 1. Se ainda está pesquisando, aguarda
        var ancora = document.querySelector('pje-arvore-modelo-documento #inputFiltro');
        if (ancora && ancora.parentElement) {
            var spin = ancora.parentElement.querySelector('i[class*="fa-spinner"], mat-progress-spinner, .fa-spin');
            if (spin && spin.offsetWidth > 0) return { status: 'pesquisando' };
        }
        // 2. Se achou nodo filtrado, clica nele
        var nodo = document.querySelector('pje-arvore-modelo-documento span.nodo-filtrado, .nodo-filtrado');
        if (nodo) {
            var alvo = nodo.closest('mat-tree-node') || nodo.parentElement || nodo;
            try { alvo.scrollIntoView({block: 'center', behavior: 'instant'}); } catch(e) {}
            nodo.click();
            return { status: 'encontrado' };
        }
        // 3. Se galhos estão fechados, tenta expandir
        var fechados = Array.from(document.querySelectorAll('pje-arvore-modelo-documento div[aria-expanded="false"], pje-arvore-modelo-documento mat-tree-node[aria-expanded="false"] button'));
        if (fechados.length > 0) {
            fechados[0].click();
            return { status: 'expandindo' };
        }
        return { status: 'aguardando' };
    }"""
    limite = time.time() + timeout
    while time.time() < limite:
        try:
            res = None
            if hasattr(driver, 'page'):
                res = driver.page.evaluate(js_expandir_e_buscar)
            elif hasattr(driver, '_js'):
                res = driver._js(js_expandir_e_buscar)
            if isinstance(res, dict) and res.get('status') == 'encontrado':
                return True
        except Exception:
            pass
        espera.assentar(driver, 0.4)
    return False


def inserir_modelo_no_editor(
    driver: Any,
    modelo_nome: str,
    log: Optional[Callable] = None,
    timeout_teor: int = 15,
    timeout_conteudo: int = 8,
) -> bool:
    """Insere um modelo no editor de minuta — fluxo ÚNICO (padrão gigs-plugin aaDespacho)."""
    if log is None:
        def log(_msg):
            return None

    try:
        #    permite que CKEditor saiba qual tópico ativo deve receber a inserção).
        _focar_editor_alvo(driver)

        seletor_editor_alvo = _resolver_editor_alvo(driver)

        if not espera.ate_aparecer(
            driver,
            'input#inputFiltro, pje-arvore-modelo-documento',
            teto=20,
        ):
            log('[MODELO] Árvore de modelos não apareceu em 20s — página de minutar sem árvore')
            return False
        seletor_editor_alvo = _resolver_editor_alvo(driver) or seletor_editor_alvo

        if not _preencher_filtro_modelo(driver, modelo_nome):
            log(f'[MODELO] Campo de filtro não encontrado para "{modelo_nome}"')
            return False

        conteudo_confirmado = False
        for tentativa in (1, 2, 3):
            rotulo = '1a' if tentativa == 1 else '%da' % tentativa

            _focar_editor_alvo(driver)
            seletor_editor_alvo = _resolver_editor_alvo(driver) or seletor_editor_alvo
            if tentativa > 1:
                _preencher_filtro_modelo(driver, modelo_nome)

            if not aguardar_e_clicar(driver, _SEL_NODO, timeout=10):
                log(f'[MODELO] Nodo filtrado não clicável via caminho nativo para "{modelo_nome}", tentando fallback com expansão')
                if not _localizar_e_clicar_nodo_filtrado(driver, timeout=8):
                    log(f'[MODELO] Nodo filtrado não encontrado para "{modelo_nome}" ({rotulo} tentativa) — refazendo')
                    continue

            if not aguardar_renderizacao_nativa(driver, _SEL_DIALOGO, modo='aparecer', timeout=15):
                log(f'[MODELO] Diálogo de visualização não abriu ({rotulo} tentativa) — refazendo')
                continue

            espera.assentar(driver, 1.0, motivo='PJe montando o teor do modelo no diálogo')

            if not espera.ate_js(driver, f"({_JS_TEOR_CARREGADO})()", teto=timeout_teor):
                log(f'[MODELO] Teor do preview não confirmado em {timeout_teor}s ({rotulo} tentativa) — fechando e refazendo')
                aguardar_renderizacao_nativa(driver, _SEL_DIALOGO, modo='sumir', timeout=5)
                continue

            btn_inserir = wait_for_clickable(driver, _SEL_BTN_INSERIR, timeout=10)
            if not btn_inserir:
                btn_inserir = wait_for_clickable(driver, _SEL_BTN_INSERIR_CSS, timeout=5)
            if not btn_inserir:
                log(f'[MODELO] Botão Inserir não encontrado ({rotulo} tentativa) — refazendo')
                aguardar_renderizacao_nativa(driver, _SEL_DIALOGO, modo='sumir', timeout=5)
                continue

            trecho_modelo = ''
            try:
                if hasattr(driver, 'page'):
                    trecho_modelo = driver.page.evaluate(_JS_TRECHO_PREVIEW) or ''
            except Exception:
                trecho_modelo = ''

            safe_click_no_scroll(driver, btn_inserir)

            if not aguardar_renderizacao_nativa(driver, _SEL_DIALOGO, modo='sumir', timeout=15):
                log(f'[MODELO] Diálogo não fechou após Inserir ({rotulo} tentativa) — tentando clique nativo')
                try:
                    btn_inserir.click()
                except Exception:
                    pass
                if not aguardar_renderizacao_nativa(driver, _SEL_DIALOGO, modo='sumir', timeout=10):
                    log(f'[MODELO] Inserir não efetivou ({rotulo} tentativa) — fechando o diálogo e refazendo')
                    try:
                        if hasattr(driver, 'page'):
                            driver.page.keyboard.press('Escape')
                    except Exception:
                        pass
                    aguardar_renderizacao_nativa(driver, _SEL_DIALOGO, modo='sumir', timeout=5)
                    continue

            js_fechar_snack = """() => {
                var s = document.querySelector('simple-snack-bar, snack-bar-container');
                if (s) {
                    var btn = s.querySelector('button');
                    if (btn) btn.click();
                    return true;
                }
                return false;
            }"""
            try:
                if hasattr(driver, 'page'):
                    driver.page.evaluate(js_fechar_snack)
            except Exception:
                pass

            conteudo_confirmado = bool(espera.ate_js(
                driver,
                "(%s)(%s)" % (_JS_EDITOR_COM_CONTEUDO, json.dumps(seletor_editor_alvo)),
                teto=timeout_conteudo,
            ))
            if conteudo_confirmado and trecho_modelo:
                conteudo_confirmado = bool(espera.ate_js(
                    driver,
                    "(%s)(%s)" % (_JS_EDITOR_CONTEM_TRECHO, json.dumps(trecho_modelo)),
                    teto=timeout_conteudo,
                ))
                if not conteudo_confirmado:
                    log(f'[MODELO] Teor do modelo "{modelo_nome}" NÃO encontrado no editor '
                        f'({rotulo} tentativa) — refazendo')
            if conteudo_confirmado:
                break
            log(f'[MODELO] Conteúdo do modelo "{modelo_nome}" NÃO confirmado no editor-alvo '
                f'({seletor_editor_alvo}) após {timeout_conteudo}s ({rotulo} tentativa) — refazendo')

        if not conteudo_confirmado:
            log(f'[MODELO] Conteúdo do modelo "{modelo_nome}" não entrou no editor após 3 tentativas')
            return False

        #    para forçar sync dos eventos do CKEditor com o modelo de formulário do Angular)
        _focar_editor_alvo(driver)
        _sincronizar_editor_alvo(driver, seletor_editor_alvo)
        espera.assentar(driver, 0.8, motivo='estabilização pós-inserção do modelo')

        if not editor_tem_conteudo(driver, seletor_editor_alvo):
            log(f'[MODELO] Editor-alvo ({seletor_editor_alvo}) esvaziou após sincronização para "{modelo_nome}"')
            return False

        log(
            f'[MODELO] Modelo "{modelo_nome}" inserido e confirmado no editor-alvo '
            f'(trecho_verificado={bool(trecho_modelo)})'
        )
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