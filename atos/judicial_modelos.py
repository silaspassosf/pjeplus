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
#
# O seletor canônico é o do gigs-plugin (+pje/comum/seletores.js,
# SELETORES.editor.areaConteudo): `[role="textbox"]` é o que distingue o editor
# de minuta real das outras div[contenteditable] da tela (tópicos da sentença,
# preview do diálogo). Sem `role`, a busca cai em áreas que não recebem modelo.
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

# Confirmação de conteúdo no editor — porte fiel de
# gigs-plugin.js verificarSeExisteTextoNoEditor() (linha ~10771):
#
#   if (areaConteudo?.innerText.length > 1) { resposta = true }
#   if (areaConteudo.querySelector('figure')) { resposta = true }
#
# Três pontos do original que a versão anterior havia perdido:
#   1. ESCOPADO: decide SÓ o editor-alvo. A varredura por outras áreas comparava
#      cada uma com o baseline do alvo e dava True com o editor vazio.
#   2. ABSOLUTO: "editor tem texto", não "cresceu em relação a antes". O editor
#      de minuta nasce vazio; baseline só abria margem para falso-positivo.
#   3. O mesmo critério do gigs vale para retomada de minuta já preenchida.
_JS_EDITOR_COM_CONTEUDO = """(sel) => {
    var area = document.querySelector(sel);
    if (!area) return false;
    var texto = (area.innerText || '').trim();
    if (texto.length > 1) return true;          // texto real no editor
    return area.querySelector('figure') !== null;  // imagem anexada sem texto
}"""

# Medida de diagnóstico (não decide sucesso): -1 = editor ausente.
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


def _medir_conteudo_editor(driver: Any, seletor: str) -> int:
    """Comprimento do texto real do editor-alvo (-1 se o editor não existe).

    Diagnóstico apenas: a confirmação de sucesso é feita por
    _JS_EDITOR_COM_CONTEUDO (escopada e absoluta, padrão gigs-plugin).
    """
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
    """Insere um modelo no editor de minuta — fluxo ÚNICO (padrão gigs-plugin aaDespacho).

    Encapsula: foco prévio no editor-alvo → filtro → nodo-filtrado (com expansão da árvore) →
    diálogo → espera do teor no preview → clique em Inserir → confirmação de conteúdo no editor-ALVO.

    Retorna True só com conteúdo REAL confirmado no editor-alvo; False caso contrário.
    """
    if log is None:
        def log(_msg):
            return None

    try:
        # 0. Foco no editor-alvo ANTES de iniciar a busca (padrão aaDespacho gigs-plugin:
        #    permite que CKEditor saiba qual tópico ativo deve receber a inserção).
        _focar_editor_alvo(driver)

        # Editor-alvo (mesmo critério do gigs: prioriza [role="textbox"]).
        seletor_editor_alvo = _resolver_editor_alvo(driver)

        # 1. Filtro do modelo
        if not _preencher_filtro_modelo(driver, modelo_nome):
            log(f'[MODELO] Campo de filtro não encontrado para "{modelo_nome}"')
            return False

        # 2. Nodo filtrado: caminho primário = clique nativo (comportamento pré-refactor,
        #    validado no PEC); fallback = busca com espera de spinner e expansão de galhos.
        if not aguardar_e_clicar(driver, _SEL_NODO, timeout=10):
            log(f'[MODELO] Nodo filtrado não clicável via caminho nativo para "{modelo_nome}", tentando fallback com expansão')
            if not _localizar_e_clicar_nodo_filtrado(driver, timeout=8):
                log(f'[MODELO] Nodo filtrado não encontrado para "{modelo_nome}"')
                return False

        # 3. Diálogo de visualização
        if not aguardar_renderizacao_nativa(driver, _SEL_DIALOGO, modo='aparecer', timeout=15):
            log('[MODELO] Diálogo de visualização não abriu')
            return False

        # 4. GUARDA ANTI-CORRIDA: espera POSITIVA do teor no preview (não sleep fixo).
        if not espera.ate_js(driver, _JS_TEOR_CARREGADO, teto=timeout_teor):
            log('[MODELO] Teor do preview não confirmado no timeout, verificando se botão Inserir está disponível')
            espera.assentar(driver, 1.0, motivo='PJe carregando o teor do modelo')

        # 5. Botão Inserir (aria-label estável; fallback CSS estrutural)
        btn_inserir = wait_for_clickable(driver, _SEL_BTN_INSERIR, timeout=10)
        if not btn_inserir:
            btn_inserir = wait_for_clickable(driver, _SEL_BTN_INSERIR_CSS, timeout=5)
        if not btn_inserir:
            log('[MODELO] Botão Inserir não encontrado')
            return False

        safe_click_no_scroll(driver, btn_inserir)

        # 6. Aguardar diálogo de modelo sumir
        aguardar_renderizacao_nativa(driver, _SEL_DIALOGO, modo='sumir', timeout=15)

        # Tratar snackbar se aparecer
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

        # 7. Confirmação: conteúdo REAL no editor-alvo, escopado e absoluto.
        #    Mesmo critério do gigs (verificarSeExisteTextoNoEditor): decide SÓ o
        #    editor-alvo e exige texto presente — não "alguma área mudou desde o
        #    baseline", que dava True com o editor vazio (ato salvo em branco).
        #    A snackbar não entra na prova: a memória do repo registra que
        #    "Modelo inserido com sucesso" aparece também com o editor vazio.
        conteudo_confirmado = bool(espera.ate_js(
            driver,
            "(%s)(%s)" % (_JS_EDITOR_COM_CONTEUDO, json.dumps(seletor_editor_alvo)),
            teto=timeout_conteudo,
        ))

        if not conteudo_confirmado:
            log(f'[MODELO] Conteúdo do modelo "{modelo_nome}" NÃO confirmado no editor-alvo '
                f'({seletor_editor_alvo}) após {timeout_conteudo}s — editor vazio')
            return False

        # 8. Devolver foco ao editor (padrão gigs-plugin aaDespacho L12148: foco.focus()
        #    para forçar sync dos eventos do CKEditor com o modelo de formulário do Angular)
        _focar_editor_alvo(driver)
        espera.assentar(driver, 0.8, motivo='estabilização pós-inserção do modelo')

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