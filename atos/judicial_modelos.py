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
    var preview = dlg.querySelector('.div-preview, .div-preview-conteudo, .preview-conteudo, .conteudo-modelo, .ck-content');
    if (!preview) return false;
    var clone = preview.cloneNode(true);
    clone.querySelectorAll('.div-preview-botoes, button, .placeholder-conteudo, .ck-placeholder, [data-placeholder]').forEach(p => p.remove());
    var txt = (clone.innerText || clone.textContent || '').trim();
    return txt.length > 5 || clone.querySelector('figure') !== null || clone.querySelector('table') !== null;
}"""

_JS_EDITOR_COM_CONTEUDO = """(sel) => {
    var areas = Array.from(document.querySelectorAll(sel)).filter(function(el) {
        return !el.closest('pje-dialogo-visualizar-modelo');
    });
    if (!areas.length) return false;
    // Placeholder visual (.placeholder-conteudo / .ck-placeholder) pode ter innerText > 1 char;
    // NAO remover [data-placeholder] porque CKEditor mantem esse atributo em <p> com texto real.
    for (var i = 0; i < areas.length; i++) {
        var area = areas[i];
        try {
            var ck = area.ckeditorInstance;
            if (ck && typeof ck.getData === 'function') {
                var dados = (ck.getData() || '').replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').trim();
                if (dados.length > 1) return true;
            }
        } catch (e) {}
        var clone = area.cloneNode(true);
        clone.querySelectorAll('.placeholder-conteudo, .ck-placeholder').forEach(p => p.remove());
        var texto = (clone.innerText || clone.textContent || '').trim();
        if (texto.length > 1) return true;          // texto real no editor
        if (area.querySelector('figure') !== null || area.querySelector('table') !== null) return true;
    }
    return false;
}"""

_JS_MEDIR_TOTAL_EDITORES = """(sel) => {
    var areas = Array.from(document.querySelectorAll(sel)).filter(function(el) {
        return !el.closest('pje-dialogo-visualizar-modelo');
    });
    if (!areas.length) return -1;
    var total = 0;
    for (var i = 0; i < areas.length; i++) {
        var area = areas[i];
        var len = 0;
        try {
            var ck = area.ckeditorInstance;
            if (ck && typeof ck.getData === 'function') {
                len = (ck.getData() || '').replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').trim().length;
            }
        } catch (e) {}
        if (len === 0) {
            var clone = area.cloneNode(true);
            clone.querySelectorAll('.placeholder-conteudo, .ck-placeholder').forEach(p => p.remove());
            len = (clone.innerText || clone.textContent || '').trim().length;
        }
        if (len === 0 && (area.querySelector('figure') !== null || area.querySelector('table') !== null)) {
            len = 10;
        }
        total += len;
    }
    return total;
}"""

_JS_ARMAR_OBSERVER_MODELO = """() => {
    try {
        if (window.__pjeModeloObserver) {
            try { window.__pjeModeloObserver.disconnect(); } catch (e) {}
        }
        window.__pjeModeloInseridoSnack = false;
        var obs = new MutationObserver(function(muts) {
            for (var m of muts) {
                for (var n of m.addedNodes) {
                    if (!n || !n.tagName) continue;
                    var tag = (n.tagName || '').toUpperCase();
                    if (tag.indexOf('SNACK-BAR') !== -1 || (n.querySelector && n.querySelector('simple-snack-bar'))) {
                        var txt = (n.innerText || n.textContent || '').toLowerCase();
                        if (txt.indexOf('modelo de documento inserido') !== -1 || txt.indexOf('inserido com sucesso') !== -1) {
                            window.__pjeModeloInseridoSnack = true;
                        }
                    }
                }
            }
        });
        obs.observe(document.body, { childList: true, subtree: true });
        window.__pjeModeloObserver = obs;
        return true;
    } catch (e) {
        return false;
    }
}"""

_JS_DESARMAR_OBSERVER_MODELO = """() => {
    var ok = !!window.__pjeModeloInseridoSnack;
    try {
        if (window.__pjeModeloObserver) {
            window.__pjeModeloObserver.disconnect();
            window.__pjeModeloObserver = null;
        }
    } catch (e) {}
    return ok;
}"""

_JS_CONFIRMAR_INSERCAO = """(sel, lenAntes) => {
    var snackOk = !!window.__pjeModeloInseridoSnack;
    if (!snackOk) {
        var snacks = Array.from(document.querySelectorAll('simple-snack-bar, snack-bar-container'));
        for (var s of snacks) {
            var stxt = (s.innerText || s.textContent || '').toLowerCase();
            if (stxt.indexOf('modelo de documento inserido') !== -1 || stxt.indexOf('inserido com sucesso') !== -1) {
                snackOk = true;
                window.__pjeModeloInseridoSnack = true;
                break;
            }
        }
    }
    var areas = Array.from(document.querySelectorAll(sel)).filter(function(el) {
        return !el.closest('pje-dialogo-visualizar-modelo');
    });
    var total = 0;
    var temMidia = false;
    for (var i = 0; i < areas.length; i++) {
        var area = areas[i];
        var len = 0;
        try {
            var ck = area.ckeditorInstance;
            if (ck && typeof ck.getData === 'function') {
                len = (ck.getData() || '').replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').trim().length;
            }
        } catch (e) {}
        if (len === 0) {
            var clone = area.cloneNode(true);
            clone.querySelectorAll('.placeholder-conteudo, .ck-placeholder').forEach(p => p.remove());
            len = (clone.innerText || clone.textContent || '').trim().length;
        }
        total += len;
        if (area.querySelector('figure') !== null || area.querySelector('table') !== null) {
            temMidia = true;
        }
    }
    if (lenAntes > 0) {
        return (total > lenAntes) || (snackOk && (total > 1 || temMidia));
    }
    return total > 1 || temMidia;
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
        var areas = Array.from(document.querySelectorAll(
            'div[class*="area-conteudo"][contenteditable="true"][role="textbox"], ' +
            'div[class*="area-conteudo"] div[contenteditable="true"], ' +
            'div[class*="area-conteudo"][contenteditable="true"], ' +
            'div.ck-content[contenteditable="true"]'
        )).filter(function(el) {
            return !el.closest('pje-dialogo-visualizar-modelo');
        });
        if (!areas.length) return false;
        var ehSentenca = Array.from(document.querySelectorAll('div[class*="area-conteudo"] div[class*="placeholder-conteudo"], div[class*="area-conteudo"]'))
            .some(function(el) {
                if (el.closest('pje-dialogo-visualizar-modelo')) return false;
                var txt = (el.innerText || '').trim().toLowerCase();
                return txt === '(dispositivo)' || txt.indexOf('dispositivo') !== -1 && txt.length < 30;
            });
        var nomeAlvo = ehSentenca ? 'dispositivo' : 'fundamentacao';
        var foco = areas.find(function(el) {
            var lbl = (el.getAttribute('aria-label') || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
            if (lbl.indexOf(nomeAlvo) !== -1) return true;
            var prev = el.previousElementSibling;
            if (prev) {
                var ptxt = (prev.innerText || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
                if (ptxt.indexOf(nomeAlvo) !== -1) return true;
            }
            return false;
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
    try:
        if hasattr(driver, 'page'):
            return bool(driver.page.evaluate(_JS_EDITOR_COM_CONTEUDO, sel))
        expr = "(%s)(%s)" % (_JS_EDITOR_COM_CONTEUDO, json.dumps(sel))
        return bool(espera.ate_js(driver, expr, teto=0.5))
    except Exception as e:
        logger.warning('[MODELO] editor_tem_conteudo exceção (sel=%s): %s', sel, e)
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


def _medir_total_editores(driver: Any, seletor: str) -> int:
    """Comprimento total do conteúdo real nos editores-alvo (-1 se ausente)."""
    try:
        if hasattr(driver, 'page'):
            return int(driver.page.evaluate(_JS_MEDIR_TOTAL_EDITORES, seletor))
        expr = "(%s)(%s)" % (_JS_MEDIR_TOTAL_EDITORES, json.dumps(seletor))
        if hasattr(driver, '_js'):
            return int(driver._js(expr))
    except Exception:
        pass
    return -1


def _ativar_aba_modelos(driver: Any) -> bool:
    """Se `input#inputFiltro` não está visível porque outra aba lateral está ativa, clica na aba Modelos."""
    js_aba = """() => {
        var filtro = document.querySelector('input#inputFiltro, pje-arvore-modelo-documento input');
        if (filtro && filtro.getClientRects().length > 0) return 'ja_visivel';
        var abas = Array.from(document.querySelectorAll('pje-editor-lateral div[role="tab"], pje-editor-lateral .mat-tab-label'));
        var abaModelos = abas.find(function(t) {
            return (t.textContent || '').toLowerCase().indexOf('modelo') !== -1;
        });
        if (abaModelos) {
            abaModelos.click();
            return 'clicada';
        }
        return 'ausente';
    }"""
    try:
        res = None
        if hasattr(driver, 'page'):
            res = driver.page.evaluate(js_aba)
        elif hasattr(driver, '_js'):
            res = driver._js(js_aba)
        return res in ('ja_visivel', 'clicada')
    except Exception:
        return False


def inserir_modelo_no_editor(
    driver: Any,
    modelo_nome: str,
    log: Optional[Callable] = None,
    timeout_teor: int = 15,
    timeout_conteudo: int = 8,
) -> bool:
    """Insere um modelo no editor de minuta — fluxo único (padrão gigs-plugin aaDespacho) com guarda anti-duplicação."""
    if log is None:
        def log(_msg):
            return None

    def _fechar_snack() -> None:
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

    try:
        _focar_editor_alvo(driver)
        _ativar_aba_modelos(driver)

        seletor_editor_alvo = _resolver_editor_alvo(driver)

        if not espera.ate_aparecer(
            driver,
            'input#inputFiltro, pje-arvore-modelo-documento',
            teto=20,
        ):
            _ativar_aba_modelos(driver)
            if not espera.ate_aparecer(
                driver,
                'input#inputFiltro, pje-arvore-modelo-documento',
                teto=5,
            ):
                log('[MODELO] Árvore de modelos não apareceu em 20s — página de minutar sem árvore')
                return False
        espera.ate_sumir(
            driver,
            'pje-arvore-modelo-documento mat-progress-spinner, pje-arvore-modelo-documento mat-progress-bar, '
            'pje-arvore-modelo-documento .fa-spin, pje-editor-lateral mat-progress-spinner',
            teto=12,
        )
        seletor_editor_alvo = _resolver_editor_alvo(driver) or seletor_editor_alvo
        len_antes = max(0, _medir_total_editores(driver, seletor_editor_alvo))

        if not _preencher_filtro_modelo(driver, modelo_nome):
            log(f'[MODELO] Campo de filtro não encontrado para "{modelo_nome}"')
            return False

        conteudo_confirmado = False
        snack_confirmado = False
        for tentativa in (1, 2):
            rotulo = '1a' if tentativa == 1 else '2a'

            # Guarda anti-duplicação: nunca reinserir se o editor já recebeu conteúdo real.
            if tentativa > 1:
                len_agora = _medir_total_editores(driver, seletor_editor_alvo)
                if (len_antes == 0 and len_agora > 1) or (len_antes > 0 and len_agora > len_antes):
                    log(
                        f'[MODELO] Conteúdo já presente no editor antes da {rotulo} tentativa '
                        f'(len {len_antes} -> {len_agora}) — abortando retry para evitar duplicação'
                    )
                    conteudo_confirmado = True
                    break
                _focar_editor_alvo(driver)
                seletor_editor_alvo = _resolver_editor_alvo(driver) or seletor_editor_alvo
                _preencher_filtro_modelo(driver, modelo_nome)
            else:
                _focar_editor_alvo(driver)
                seletor_editor_alvo = _resolver_editor_alvo(driver) or seletor_editor_alvo

            if not aguardar_e_clicar(driver, _SEL_NODO, timeout=10):
                log(f'[MODELO] Nodo filtrado não clicável via caminho nativo para "{modelo_nome}", tentando fallback com expansão')
                if not _localizar_e_clicar_nodo_filtrado(driver, timeout=8):
                    log(f'[MODELO] Nodo filtrado não encontrado para "{modelo_nome}" ({rotulo} tentativa) — refazendo')
                    continue

            if not aguardar_renderizacao_nativa(driver, _SEL_DIALOGO, modo='aparecer', timeout=15):
                log(f'[MODELO] Diálogo de visualização não abriu ({rotulo} tentativa) — refazendo')
                continue

            if not espera.ate_js(driver, f"({_JS_TEOR_CARREGADO})()", teto=timeout_teor):
                log(f'[MODELO] Teor do preview não confirmado em {timeout_teor}s ({rotulo} tentativa) — fechando e refazendo')
                try:
                    if hasattr(driver, 'page'):
                        driver.page.keyboard.press('Escape')
                except Exception:
                    pass
                aguardar_renderizacao_nativa(driver, _SEL_DIALOGO, modo='sumir', timeout=5)
                continue

            # Pequeno respiro pós-teor para o Angular finalizar o binding do botão Inserir
            espera.assentar(driver, 0.25, motivo='binding final do diálogo de modelo')

            btn_inserir = wait_for_clickable(driver, _SEL_BTN_INSERIR, timeout=10)
            if not btn_inserir:
                btn_inserir = wait_for_clickable(driver, _SEL_BTN_INSERIR_CSS, timeout=5)
            if not btn_inserir:
                log(f'[MODELO] Botão Inserir não encontrado ({rotulo} tentativa) — refazendo')
                try:
                    if hasattr(driver, 'page'):
                        driver.page.keyboard.press('Escape')
                except Exception:
                    pass
                aguardar_renderizacao_nativa(driver, _SEL_DIALOGO, modo='sumir', timeout=5)
                continue

            if hasattr(driver, 'page'):
                try:
                    driver.page.evaluate(_JS_ARMAR_OBSERVER_MODELO)
                except Exception:
                    pass

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

            conteudo_confirmado = bool(espera.ate_js(
                driver,
                "(%s)(%s, %d)" % (_JS_CONFIRMAR_INSERCAO, json.dumps(seletor_editor_alvo), len_antes),
                teto=timeout_conteudo,
            ))

            if hasattr(driver, 'page'):
                try:
                    snack_confirmado = bool(driver.page.evaluate(_JS_DESARMAR_OBSERVER_MODELO))
                except Exception:
                    snack_confirmado = False
            _fechar_snack()

            if conteudo_confirmado:
                # Devolve o foco ao editor-alvo (padrão gigs-plugin aaDespacho) e reconfirma
                # após breve assentamento antes de liberar para o Salvar.
                _focar_editor_alvo(driver)
                espera.assentar(driver, 0.3, motivo='reconfirmação pós-inserção do modelo')
                if editor_tem_conteudo(driver, seletor_editor_alvo):
                    break
                log(f'[MODELO] Editor-alvo esvaziou durante estabilização ({rotulo} tentativa) — reinserindo "{modelo_nome}"')
                conteudo_confirmado = False
                continue

            log(f'[MODELO] Conteúdo do modelo "{modelo_nome}" NÃO confirmado no editor-alvo '
                f'({seletor_editor_alvo}) após {timeout_conteudo}s ({rotulo} tentativa) — refazendo')

        if not conteudo_confirmado:
            log(f'[MODELO] Conteúdo do modelo "{modelo_nome}" não entrou no editor após 2 tentativas')
            return False

        len_depois = _medir_total_editores(driver, seletor_editor_alvo)
        log(
            f'[MODELO] Modelo "{modelo_nome}" inserido e confirmado no editor-alvo '
            f'(len {len_antes}->{len_depois}, snack={snack_confirmado})'
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