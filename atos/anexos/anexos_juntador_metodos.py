"""atos.anexos.juntador.metodos - Métodos da classe Juntador."""

import json
import logging
logger = logging.getLogger(__name__)

import os
import re
import time
import types
import unicodedata
from typing import Optional, Dict, Any, Callable, Union, List


from Fix import espera
from Fix.core import (
    safe_click_no_scroll,
    aguardar_e_clicar,
    aguardar_renderizacao_nativa,
    selecionar_opcao,
    preencher_campo,
    safe_click,
    wait_for_clickable,
    wait_for_visible,
)
from Fix.browser_suporte import click_headless_safe
from Fix.utils import (
    inserir_html_no_editor_apos_marcador,
    obter_ultimo_conteudo_clipboard,
    executar_coleta_parametrizavel,
    inserir_link_ato_validacao,
)

from .anexos_extracao import extrair_numero_processo_da_url
from .anexos_formatacao import formatar_conteudo_ecarta
from .anexos_juntador_helpers import (
    substituir_marcador_por_conteudo,
    _obter_editor_principal,
    _JS_LER_ESTADO_EDITOR,
)
from Fix.core import _executar_js


def _normalizar_texto(texto: str) -> str:
    """Normaliza texto removendo acentos, espaços múltiplos e convertendo para minúsculas."""
    if not texto:
        return ''
    nfkd = unicodedata.normalize('NFKD', str(texto))
    sem_acentos = ''.join(ch for ch in nfkd if not unicodedata.combining(ch))
    return re.sub(r'\s+', ' ', sem_acentos).strip().lower()


def _escolher_melhor_opcao(opcoes: List[Any], alvo_norm: str) -> Optional[Any]:
    """Seleciona a melhor mat-option: match exato > prefixo > substring."""
    if not opcoes or not alvo_norm:
        return None
    candidatos = []
    for opcao in opcoes:
        texto = (getattr(opcao, 'text_content', None) and opcao.text_content()) or getattr(opcao, 'text', '') or ''
        texto_norm = _normalizar_texto(texto)
        if not texto_norm:
            continue
        if texto_norm == alvo_norm:
            return opcao
        candidatos.append((texto_norm, opcao))
    for texto_norm, opcao in candidatos:
        if texto_norm.startswith(alvo_norm + ' ') or texto_norm.startswith(alvo_norm):
            return opcao
    for texto_norm, opcao in candidatos:
        if alvo_norm in texto_norm:
            return opcao
    return None


def _escolher_opcao_gigs(self, seletor: str, valor: str, nome_campo: str) -> bool:
    """Implementa escolherOpcaoTeste/escolherOpcaoTeste2 do gigs-plugin.js com suporte a autocomplete."""
    try:
        driver = self.driver
        alvo_norm = _normalizar_texto(valor)

        elementos_campo = espera.elementos(driver, seletor, teto=6)
        if not elementos_campo:
            logger.error('[JUNTADA] Campo %s não apareceu a tempo', nome_campo)
            return False
        campo = elementos_campo[0]

        _executar_js(driver, """
            const el = arguments[0];
            el.focus();
            const p = el.closest('mat-form-field') || (el.parentElement ? el.parentElement.parentElement : el);
            if (p) p.click();
            el.click();
            el.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true}));
            el.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowDown', keyCode: 40, bubbles: true}));
        """, campo)

        if not espera.ate_aparecer(driver, "mat-option[role='option'], mat-option", teto=3):
            # Se não abriu imediatamente, preenche valor no input para ativar autocomplete do Angular
            _executar_js(driver, """
                const el = arguments[0];
                const val = arguments[1];
                el.focus();
                Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(el, val);
                ['input', 'change', 'keyup'].forEach(ev => el.dispatchEvent(new Event(ev, {bubbles: true})));
                el.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowDown', keyCode: 40, bubbles: true}));
            """, campo, valor)
            espera.ate_aparecer(driver, "mat-option[role='option'], mat-option", teto=4)

        opcoes = espera.elementos(driver, "mat-option[role='option'], mat-option", teto=4)
        escolhida = _escolher_melhor_opcao(opcoes, alvo_norm)
        if escolhida is not None:
            safe_click_no_scroll(driver, escolhida)
            try:
                _executar_js(driver, "if (arguments[0] && arguments[0].blur) arguments[0].blur();", campo)
            except Exception:
                pass
            espera.ate_sumir(driver, 'mat-progress-bar', teto=5)
            logger.debug('[JUNTADA] %s selecionado: %s', nome_campo, valor)
            return True

        _executar_js(driver, """
            const el = arguments[0];
            const val = arguments[1];
            el.focus();
            Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(el, val);
            ['input', 'change', 'keyup'].forEach(ev => el.dispatchEvent(new Event(ev, {bubbles: true})));
        """, campo, valor)
        espera.assentar(driver, 0.4)
        opcoes = espera.elementos(driver, "mat-option[role='option'], mat-option", teto=4)
        escolhida = _escolher_melhor_opcao(opcoes, alvo_norm)
        if escolhida is not None:
            safe_click_no_scroll(driver, escolhida)
            try:
                _executar_js(driver, "if (arguments[0] && arguments[0].blur) arguments[0].blur();", campo)
            except Exception:
                pass
            espera.ate_sumir(driver, 'mat-progress-bar', teto=5)
            logger.debug('[JUNTADA] %s selecionado após filtro: %s', nome_campo, valor)
            return True

        logger.error('[JUNTADA] Opção "%s" não encontrada em %s', valor, nome_campo)
        return False

    except Exception as e:
        logger.error('[JUNTADA] Falha ao selecionar %s: %s', nome_campo, e)
        return False


def _preencher_input_gigs(self, seletor: str, valor: str, nome_campo: str) -> bool:
    """Implementa preencherInput do gigs-plugin.js"""
    try:
        driver = self.driver

        elementos_campo = espera.elementos(driver, seletor, teto=8)
        if not elementos_campo:
            logger.error(f'[JUNTADA][ERRO] Campo {nome_campo} não apareceu a tempo')
            return False
        campo = elementos_campo[0]

        resultado = _executar_js(driver, """
            const elemento = arguments[0];
            const valor = arguments[1];

            // Focus no elemento (JavaScript, não WebElement)
            elemento.focus();

            // Define valor usando Object.getOwnPropertyDescriptor (padrão GIGS)
            Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(elemento, valor);

            // Dispara eventos exatos do GIGS
            function triggerEvent(el, eventType) {
                const event = new Event(eventType, {bubbles: true, cancelable: true});
                el.dispatchEvent(event);
            }

            triggerEvent(elemento, 'input');
            triggerEvent(elemento, 'change');
            triggerEvent(elemento, 'dateChange');
            triggerEvent(elemento, 'keyup');

            // Simula Enter (padrão GIGS)
            const enterEvent = new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true});
            elemento.dispatchEvent(enterEvent);

            // Blur no elemento
            elemento.blur();

            return true;
        """, campo, valor)

        return True

    except Exception as e:
        logger.error(f'[JUNTADA][ERRO] Falha ao preencher {nome_campo}: {e}')
        return False


def _clicar_elemento_gigs(self, seletor: str, nome_elemento: str) -> bool:
    """Implementa clicarBotao do gigs-plugin.js com múltiplas tentativas"""
    try:
        driver = self.driver

        if 'Salvar' in nome_elemento:
            seletores = [
                'button[aria-label="Salvar"]',
                'button[mat-raised-button][color="primary"][aria-label="Salvar"]',
                'button.mat-raised-button.mat-primary[aria-label="Salvar"]',
                'button.mat-focus-indicator.mat-raised-button.mat-button-base.mat-primary[aria-label="Salvar"]',
                'button:contains("Salvar")',
                '[aria-label="Salvar"]'
            ]
        elif 'Assinar' in nome_elemento:
            seletores = [
                'button[aria-label="Assinar documento e juntar ao processo"]',
                'button.mat-fab[aria-label="Assinar documento e juntar ao processo"]',
                'button.mat-focus-indicator.mat-fab.mat-button-base.mat-accent[aria-label="Assinar documento e juntar ao processo"]',
                'button[mat-fab].mat-accent[aria-label="Assinar documento e juntar ao processo"]',
                'button.mat-fab .fa-pen-nib',
                'button:contains("Assinar")',
                '[aria-label*="Assinar"]'
            ]
        else:
            seletores = [seletor]

        for i, sel in enumerate(seletores):
            try:
                logger.debug('[JUNTADA] Tentando seletor %d: %s', i + 1, sel)

                if ':contains(' in sel:
                    elemento = _executar_js(driver, """
                        const buttons = document.querySelectorAll('button');
                        return Array.from(buttons).find(btn =>
                            btn.textContent.trim().toLowerCase().includes('salvar') ||
                            btn.getAttribute('aria-label') === 'Salvar'
                        );
                    """)
                else:
                    elementos = espera.elementos(driver, sel, teto=1)
                    elemento = elementos[0] if elementos else None

                if elemento:
                    logger.debug('[JUNTADA] Elemento encontrado com seletor %d: %s', i + 1, sel)

                    for tentativa in range(2):
                        try:
                            _executar_js(driver, "arguments[0].scrollIntoView({block:'center'});", elemento)

                            is_enabled = getattr(elemento, 'is_enabled', None)
                            is_displayed = getattr(elemento, 'is_displayed', None)
                            ok_enabled = is_enabled() if callable(is_enabled) else True
                            ok_displayed = is_displayed() if callable(is_displayed) else True
                            if ok_enabled and ok_displayed:
                                safe_click_no_scroll(driver, elemento)
                                logger.debug('[JUNTADA] Clique realizado: %s (seletor %d, tentativa %d)', nome_elemento, i + 1, tentativa + 1)
                                return True
                            else:
                                logger.debug('[JUNTADA] Elemento não clicável (enabled: %s, visible: %s)', ok_enabled, ok_displayed)
                                espera.assentar(driver, 0.2)

                        except Exception as e:
                            if tentativa < 1:
                                logger.debug('[JUNTADA] Tentativa %d falhou para %s: %s', tentativa + 1, nome_elemento, e)
                                espera.assentar(driver, 0.3)
                            else:
                                logger.debug('[JUNTADA] Tentativas falharam para %s com seletor %s: %s', nome_elemento, sel, e)
                else:
                    logger.debug('[JUNTADA] Elemento não encontrado com seletor %d: %s', i + 1, sel)

            except Exception as e:
                if i < len(seletores) - 1:
                    logger.debug('[JUNTADA] Seletor %d "%s" falhou: %s', i + 1, sel, e)
                    continue
                else:
                    logger.debug('[JUNTADA] Último seletor "%s" falhou: %s', sel, e)

        logger.error('[JUNTADA] Todos os seletores falharam para %s', nome_elemento)
        return False

    except Exception as e:
        logger.error('[JUNTADA] Falha geral ao clicar %s: %s', nome_elemento, e)
        return False


def _focar_editor_alvo(driver: Any) -> bool:
    """Foca e ativa o editor principal da juntada / anexar (aaAnexar L10106)."""
    try:
        el = _obter_editor_principal(driver, timeout=3.0)
        if not el:
            return False
        _executar_js(
            driver,
            """
            const el = arguments[0];
            if (!el) return false;
            try { el.scrollIntoView({block: 'center', behavior: 'instant'}); } catch (e) {}
            el.focus();
            try { el.click(); } catch (e) {}
            return true;
            """,
            el,
        )
        return True
    except Exception:
        return False


def _ler_estado_editor_principal(driver: Any, timeout: float = 1.5) -> Dict[str, Any]:
    """Lê o estado real (texto sem placeholders/comentários, tamanho, ck, mídia) do editor principal."""
    vazio = {'existe': False, 'ck': False, 'texto': '', 'htmlLimpo': '', 'len': 0, 'temMidia': False}
    try:
        ed = _obter_editor_principal(driver, timeout=timeout)
        if not ed:
            return vazio
        st = _executar_js(driver, _JS_LER_ESTADO_EDITOR, ed)
        if isinstance(st, dict):
            return st
    except Exception:
        pass
    return vazio


_JS_TRECHO_PREVIEW = r"""
const dlg = document.querySelector('pje-dialogo-visualizar-modelo');
if (!dlg) return '';
const preview = dlg.querySelector('.div-preview-conteudo, .preview-conteudo, .conteudo-modelo, .ck-content, [class*="preview-conteudo"]')
             || dlg.querySelector('[class*="preview"]:not(.div-preview-botoes)')
             || dlg;
const clone = preview.cloneNode(true);
clone.querySelectorAll('.placeholder-conteudo, .ck-placeholder, [data-placeholder], button, .div-preview-botoes, .div-botao-inserir, .mat-dialog-title, header, h1, h2').forEach(p => p.remove());
const txt = (clone.innerText || clone.textContent || '').replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
const norm = txt.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const palavras = norm.split(' ').filter(w => w.length > 2 && !/[{}$#\[\]%@]/.test(w));
if (palavras.length < 2) return '';
if (palavras.length <= 5) return palavras.join(' ');
const meio = Math.max(0, Math.floor(palavras.length / 2) - 2);
return palavras.slice(meio, meio + 5).join(' ');
"""

_JS_TEOR_PREVIEW = r"""
const dlg = document.querySelector('pje-dialogo-visualizar-modelo');
if (!dlg) return false;
const preview = dlg.querySelector('.div-preview-conteudo, .preview-conteudo, .conteudo-modelo, .ck-content, [class*="preview-conteudo"]')
             || dlg.querySelector('[class*="preview"]:not(.div-preview-botoes)')
             || dlg;
const clone = preview.cloneNode(true);
clone.querySelectorAll('.placeholder-conteudo, .ck-placeholder, [data-placeholder], button, .div-preview-botoes, .div-botao-inserir, .mat-dialog-title').forEach(p => p.remove());
const txt = (clone.innerText || clone.textContent || '').replace(/\u00a0/g, ' ').trim();
return txt.length > 1 || clone.querySelector('figure') !== null || clone.querySelector('table') !== null;
"""

# NUNCA seleciona botões genéricos do diálogo (evita clicar no botão Fechar/X no topo do modal).
_JS_ENCONTRAR_BOTAO_INSERIR = r"""
const dlg = document.querySelector('pje-dialogo-visualizar-modelo');
if (!dlg) return null;
const visivel = (b) => {
    if (!b || b.disabled || b.getAttribute('aria-disabled') === 'true') return false;
    const r = b.getBoundingClientRect ? b.getBoundingClientRect() : { width: 1, height: 1 };
    return r.width > 0 && r.height > 0;
};
const sels = [
    'button[aria-label="Inserir modelo de documento"]',
    'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button',
    'pje-dialogo-visualizar-modelo .div-botao-inserir button'
];
for (const s of sels) {
    const b = document.querySelector(s);
    if (visivel(b)) return b;
}
const norm = (t) => (t || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
for (const b of dlg.querySelectorAll('button')) {
    if (!visivel(b)) continue;
    const info = norm((b.getAttribute('aria-label') || '') + ' ' + (b.innerText || b.textContent || ''));
    if (!info) continue;
    if (info.includes('fechar') || info.includes('cancelar') || info.includes('close') || info.includes('sair')) continue;
    if (info.includes('inserir')) return b;
}
return null;
"""

_JS_SELECIONAR_NODO_FILTRADO = r"""
const alvoNorm = arguments[0] || '';
const clicarPai = !!arguments[1];
const norm = (t) => (t || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ').trim().toLowerCase();
const escopo = document.querySelector('pje-arvore-modelo-documento') || document;
const nodos = Array.from(escopo.querySelectorAll('span.nodo-filtrado, .nodo-filtrado'));
if (nodos.length > 0) {
    let escolhido = null;
    if (alvoNorm) {
        escolhido = nodos.find(n => norm(n.textContent) === alvoNorm)
                 || nodos.find(n => norm(n.textContent).startsWith(alvoNorm + ' ') || norm(n.textContent).startsWith(alvoNorm))
                 || nodos.find(n => norm(n.textContent).includes(alvoNorm));
    }
    escolhido = escolhido || nodos[0];
    const container = (escolhido.parentElement && escolhido.parentElement.parentElement)
                   || escolhido.closest('mat-tree-node')
                   || escolhido.parentElement
                   || escolhido;
    try { container.scrollIntoView({block: 'center', behavior: 'instant'}); } catch (e) {}
    if (clicarPai) {
        container.click();
    } else {
        escolhido.click();
    }
    return { status: 'encontrado', texto: (escolhido.textContent || '').trim(), total: nodos.length };
}
const fechados = Array.from(escopo.querySelectorAll('div[aria-expanded="false"], mat-tree-node[aria-expanded="false"] button'));
if (fechados.length > 0) {
    fechados[0].click();
    return { status: 'expandindo', pendentes: fechados.length };
}
return { status: 'aguardando' };
"""

_JS_VERIFICAR_SNACKBAR_MODELO = r"""
const snacks = Array.from(document.querySelectorAll('simple-snack-bar, snack-bar-container'));
let ok = false;
let msg = '';
for (const s of snacks) {
    const txt = (s.innerText || s.textContent || '').replace(/\s+/g, ' ').trim();
    const low = txt.toLowerCase();
    if (low.includes('inserido') || (low.includes('modelo') && low.includes('sucesso'))) {
        ok = true;
        msg = txt;
        const btn = s.querySelector('button');
        if (btn) { try { btn.click(); } catch (e) {} }
    }
}
return { ok: ok, msg: msg };
"""


def _localizar_botao_inserir_modelo(driver: Any, timeout: float = 10.0) -> Optional[Any]:
    """Aguarda e retorna estritamente o botão Inserir dentro de pje-dialogo-visualizar-modelo."""
    deadline = time.monotonic() + max(0.5, float(timeout))
    while True:
        try:
            btn = _executar_js(driver, _JS_ENCONTRAR_BOTAO_INSERIR)
            if btn:
                return btn
        except Exception:
            pass
        if time.monotonic() >= deadline:
            break
        espera.assentar(driver, 0.25)
    return None


def _fechar_dialogo_preview(driver: Any) -> None:
    """Fecha pje-dialogo-visualizar-modelo se ainda estiver aberto."""
    try:
        if hasattr(driver, 'page') and driver.page:
            driver.page.keyboard.press('Escape')
        else:
            _executar_js(driver, """
                const dlg = document.querySelector('pje-dialogo-visualizar-modelo');
                if (dlg) {
                    const btnFechar = Array.from(dlg.querySelectorAll('button')).find(b => {
                        const info = ((b.getAttribute('aria-label') || '') + ' ' + (b.innerText || '')).toLowerCase();
                        return info.includes('fechar') || info.includes('cancelar') || info.includes('close');
                    });
                    if (btnFechar) btnFechar.click();
                }
            """)
    except Exception:
        pass
    aguardar_renderizacao_nativa(driver, 'pje-dialogo-visualizar-modelo', modo='sumir', timeout=5)


def _selecionar_modelo_gigs(
    self,
    modelo: str,
    timeout_teor: int = 15,
    timeout_conteudo: int = 8,
) -> bool:
    """Seleciona e insere o modelo no editor principal da juntada (aaAnexar)."""
    driver = self.driver
    modelo_norm = _normalizar_texto(modelo)
    try:
        espera.ate_sumir(driver, 'mat-progress-bar, pje-dialogo-status-progresso', teto=8)
        espera.ate_aparecer(driver, 'pje-arvore-modelo-documento, input#inputFiltro', teto=8)

        _focar_editor_alvo(driver)
        estado_antes = _ler_estado_editor_principal(driver, timeout=2.0)
        len_antes = int(estado_antes.get('len', 0) or 0)
        texto_antes = estado_antes.get('texto', '') or ''

        _executar_js(driver, """
            var f = document.getElementById('inputFiltro');
            if (f) {
                f.dispatchEvent(new Event('input', {bubbles: true}));
                f.dispatchEvent(new Event('keyup', {bubbles: true}));
            }
        """)

        campo_filtro = wait_for_clickable(driver, 'input#inputFiltro', timeout=10)
        if not campo_filtro:
            logger.error('[JUNTADA][MODELO][ERRO] Campo input#inputFiltro não encontrado')
            return False

        def _aplicar_filtro(modelo_nome: str) -> None:
            _executar_js(driver, """
                var el = arguments[0];
                var val = arguments[1];
                el.focus();
                Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')
                    .set.call(el, val);
                ['input', 'change', 'keyup'].forEach(ev =>
                    el.dispatchEvent(new Event(ev, {bubbles: true, cancelable: true}))
                );
                el.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true}));
                el.blur();
            """, campo_filtro, modelo_nome)
            espera.assentar(driver, 0.25, 'aguardando filtro de modelo iniciar na árvore')
            espera.ate_sumir(
                driver,
                'pje-arvore-modelo-documento i[class*="fa-spinner"], pje-arvore-modelo-documento mat-progress-spinner, mat-progress-bar',
                teto=6,
            )

        _aplicar_filtro(modelo)

        modelo_carregado = False
        estado_depois = estado_antes
        for tentativa in (1, 2, 3):
            rotulo = '1a' if tentativa == 1 else '%da' % tentativa
            trecho_modelo = ''
            snackbar_ok = False

            if tentativa > 1:
                _fechar_dialogo_preview(driver)
                _focar_editor_alvo(driver)
                estado_antes = _ler_estado_editor_principal(driver, timeout=1.5)
                len_antes = int(estado_antes.get('len', 0) or 0)
                texto_antes = estado_antes.get('texto', '') or ''
                _aplicar_filtro(modelo)

            clicou_nodo = False
            limite_nodo = time.monotonic() + 6.0
            while time.monotonic() < limite_nodo:
                try:
                    res = _executar_js(driver, _JS_SELECIONAR_NODO_FILTRADO, modelo_norm, False)
                    if isinstance(res, dict) and res.get('status') == 'encontrado':
                        clicou_nodo = True
                        logger.debug(
                            '[JUNTADA][MODELO] Nodo selecionado: "%s" (total=%s, %s tentativa)',
                            res.get('texto', ''), res.get('total', 1), rotulo,
                        )
                        break
                except Exception:
                    pass
                espera.assentar(driver, 0.25)

            if not clicou_nodo:
                logger.error('[JUNTADA][MODELO][ERRO] .nodo-filtrado não encontrado para "%s" (%s tentativa)', modelo, rotulo)
                continue

            dialogo_abriu = espera.ate_aparecer(driver, 'pje-dialogo-visualizar-modelo', teto=3)
            if not dialogo_abriu:
                logger.debug('[JUNTADA][MODELO] Diálogo não abriu após clique no span; tentando container do nodo (%s tentativa)', rotulo)
                try:
                    _executar_js(driver, _JS_SELECIONAR_NODO_FILTRADO, modelo_norm, True)
                except Exception:
                    pass
                dialogo_abriu = espera.ate_aparecer(driver, 'pje-dialogo-visualizar-modelo', teto=6)

            if not dialogo_abriu:
                logger.warning('[JUNTADA][MODELO] Diálogo pje-dialogo-visualizar-modelo não abriu (%s tentativa)', rotulo)
                continue

            espera.ate_sumir(
                driver,
                'pje-dialogo-visualizar-modelo mat-progress-bar, pje-dialogo-visualizar-modelo mat-progress-spinner',
                teto=8,
            )
            espera.assentar(driver, 0.4, motivo='PJe estabilizando teor do modelo no diálogo')

            if not espera.ate_js(driver, f"(function(){{{_JS_TEOR_PREVIEW}}})()", teto=timeout_teor):
                logger.warning('[JUNTADA][MODELO] Teor do preview não confirmado em %ss (%s tentativa) — fechando e refazendo', timeout_teor, rotulo)
                _fechar_dialogo_preview(driver)
                continue

            try:
                trecho_modelo = (_executar_js(driver, _JS_TRECHO_PREVIEW) or '').strip()
            except Exception:
                trecho_modelo = ''

            btn_inserir = _localizar_botao_inserir_modelo(driver, timeout=10.0)
            if not btn_inserir:
                logger.error('[JUNTADA][MODELO][ERRO] Botão "Inserir modelo de documento" não encontrado (%s tentativa)', rotulo)
                _fechar_dialogo_preview(driver)
                continue

            clicou_inserir = False
            try:
                clicou_inserir = bool(safe_click_no_scroll(driver, btn_inserir))
            except Exception:
                clicou_inserir = False
            if not clicou_inserir:
                try:
                    _executar_js(driver, """
                        const b = arguments[0];
                        b.scrollIntoView({block: 'center', behavior: 'instant'});
                        b.focus();
                        b.click();
                    """, btn_inserir)
                    clicou_inserir = True
                except Exception as e_clk:
                    logger.warning('[JUNTADA][MODELO] Falha ao clicar em Inserir (%s tentativa): %s', rotulo, e_clk)

            logger.debug('[JUNTADA][MODELO] Clique em Inserir modelo realizado (%s tentativa)', rotulo)

            if not aguardar_renderizacao_nativa(driver, 'pje-dialogo-visualizar-modelo', modo='sumir', timeout=12):
                logger.warning('[JUNTADA][MODELO] Diálogo não fechou após Inserir (%s tentativa) — repetindo clique JS', rotulo)
                try:
                    btn_retry = _localizar_botao_inserir_modelo(driver, timeout=2.0) or btn_inserir
                    _executar_js(driver, "arguments[0].focus(); arguments[0].click();", btn_retry)
                except Exception:
                    pass
                if not aguardar_renderizacao_nativa(driver, 'pje-dialogo-visualizar-modelo', modo='sumir', timeout=8):
                    logger.warning('[JUNTADA][MODELO] Inserir não fechou o diálogo (%s tentativa) — fechando e refazendo', rotulo)
                    _fechar_dialogo_preview(driver)
                    continue

            limite_conf = time.monotonic() + max(2.0, float(timeout_conteudo))
            while time.monotonic() < limite_conf:
                try:
                    snack_res = _executar_js(driver, _JS_VERIFICAR_SNACKBAR_MODELO)
                    if isinstance(snack_res, dict) and snack_res.get('ok'):
                        snackbar_ok = True
                except Exception:
                    pass

                st = _ler_estado_editor_principal(driver, timeout=0.6)
                estado_depois = st
                len_depois = int(st.get('len', 0) or 0)
                texto_depois = st.get('texto', '') or ''
                tem_midia = bool(st.get('temMidia'))

                if len_depois > 1 or tem_midia:
                    texto_depois_norm = _normalizar_texto(texto_depois)
                    if trecho_modelo and trecho_modelo in texto_depois_norm:
                        modelo_carregado = True
                        break
                    mudou_editor = (len_depois > len_antes + 5) or (texto_depois != texto_antes) or tem_midia
                    if mudou_editor and (snackbar_ok or len_depois > 15 or '--' in texto_depois):
                        modelo_carregado = True
                        break

                espera.assentar(driver, 0.3)

            if modelo_carregado:
                break

            logger.warning(
                '[JUNTADA][MODELO] Conteúdo do modelo "%s" NÃO confirmado no editor principal '
                '(%s tentativa | len %d -> %d | snackbar_ok=%s | trecho="%s") — refazendo',
                modelo, rotulo, len_antes, int(estado_depois.get('len', 0) or 0), snackbar_ok, trecho_modelo,
            )

        if not modelo_carregado:
            logger.error('[JUNTADA][MODELO][ERRO] Modelo "%s" não entrou no editor principal após 3 tentativas', modelo)
            return False

        _focar_editor_alvo(driver)
        espera.assentar(driver, 0.5, motivo='estabilização pós-inserção do modelo')

        logger.info(
            '[JUNTADA][MODELO] Modelo "%s" inserido e confirmado no editor principal (len %d -> %d)',
            modelo, len_antes, int(estado_depois.get('len', 0) or 0),
        )
        return True

    except Exception as e:
        logger.error('[JUNTADA][MODELO][ERRO] Falha ao selecionar/inserir modelo: %s', e)
        return False

def _executar_coleta_opcional(self, configuracao: Dict[str, Any]) -> bool:
    """Executa coleta de conteúdo se configurada."""
    coleta_conteudo = configuracao.get('coleta_conteudo')
    if not coleta_conteudo:
        return True

    numero_processo_atual = extrair_numero_processo_da_url(self.driver)
    if not numero_processo_atual:
        logger.debug('[JUNTADA][COLETA] Número do processo não identificado')
        return True

    try:
        logger.debug('[JUNTADA][COLETA] Iniciando coleta: %s | processo: %s', coleta_conteudo, numero_processo_atual)
        executar_coleta_parametrizavel(self.driver, numero_processo_atual, coleta_conteudo, debug=True)
        return True
    except Exception as e:
        logger.warning('[JUNTADA][COLETA] Falha ao executar coleta opcional: %s', e)
        return True


def _preencher_tipo(self, configuracao: Dict[str, Any]) -> bool:
    """Preenche Tipo de Documento."""
    tipo = configuracao.get('tipo', 'Certidão')
    return self._escolher_opcao_gigs('input[aria-label="Tipo de Documento"]', tipo, 'Tipo de Documento')


def _preencher_descricao(self, configuracao: Dict[str, Any]) -> bool:
    """Preenche Descrição."""
    descricao = configuracao.get('descricao', '')
    if not descricao:
        return True
    return self._preencher_input_gigs('input[aria-label="Descrição"]', descricao, 'Descrição')


def _configurar_sigilo(self, configuracao: Dict[str, Any]) -> bool:
    """Configura sigilo se necessário."""
    sigilo = configuracao.get('sigilo', 'nao').lower()
    if 'sim' in sigilo:
        return self._clicar_elemento_gigs('input[name="sigiloso"]', 'Sigilo')
    return True  # Não é erro não configurar sigilo


def _selecionar_e_inserir_modelo(self, configuracao: Dict[str, Any]) -> bool:
    """Seleciona e insere modelo no editor."""
    modelo = configuracao.get('modelo', '')
    if not modelo:
        return True
    return self._selecionar_modelo_gigs(modelo)


def _inserir_conteudo_customizado(self, configuracao: Dict[str, Any], substituir_link: bool = False) -> bool:
    """Insere conteúdo customizado ou substitui link."""
    try:
        inserir_conteudo = configuracao.get('inserir_conteudo')
        if inserir_conteudo:
            inserir_fn = inserir_conteudo
            if isinstance(inserir_conteudo, str):
                try:
                    if inserir_conteudo.lower() in ('link_ato', 'link_ato_validacao'):
                        inserir_fn = inserir_link_ato_validacao
                except Exception as _e:
                    logger.warning(f"[JUNTADA][INSERIR][WARN] Não foi possível resolver função por string: {inserir_conteudo} -> {_e}")

            numero_processo_atual = None
            try:
                import json
                from pathlib import Path
                dados_path = Path('dadosatuais.json')
                if dados_path.exists():
                    dados = json.loads(dados_path.read_text(encoding='utf-8'))
                    numero = dados.get('numero')
                    if isinstance(numero, list) and numero:
                        numero_processo_atual = numero[0]
                    elif isinstance(numero, str) and numero.strip():
                        numero_processo_atual = numero.strip()
            except Exception as e:
                logger.error(f'[JUNTADA][INSERIR][WARN] Erro ao ler dadosatuais.json: {e}')

            if not numero_processo_atual:
                numero_processo_atual = extrair_numero_processo_da_url(self.driver)
                logger.warning(f'[JUNTADA][INSERIR][WARN] Usando ID da URL como fallback: {numero_processo_atual}')

            modelo_esperado = bool((configuracao.get('modelo') or '').strip())
            editor_principal = _obter_editor_principal(self.driver, marcador='--', timeout=6.0)
            if modelo_esperado and not editor_principal:
                logger.error(
                    '[JUNTADA][INSERIR][ERRO] Editor principal não encontrado para o modelo '
                    '"%s" — colagem abortada para não salvar documento em branco.',
                    configuracao.get('modelo') or '',
                )
                return False
            if editor_principal and modelo_esperado:
                modelo_pronto = False
                estado_gate = {'len': 0, 'texto': ''}
                limite_gate = time.monotonic() + 10.0
                inicio_gate = time.monotonic()
                while time.monotonic() < limite_gate:
                    st = _ler_estado_editor_principal(self.driver, timeout=0.6)
                    estado_gate = st
                    txt_gate = st.get('texto', '') or ''
                    if '--' in txt_gate or '\u2013' in txt_gate or '\u2014' in txt_gate:
                        modelo_pronto = True
                        break
                    if int(st.get('len', 0) or 0) > 25 and (time.monotonic() - inicio_gate) >= 2.5:
                        modelo_pronto = True
                        break
                    espera.assentar(self.driver, 0.35)

                if not modelo_pronto and int(estado_gate.get('len', 0) or 0) > 25:
                    modelo_pronto = True

                if not modelo_pronto:
                    logger.error(
                        "[JUNTADA][INSERIR][ERRO] Conteúdo do modelo não chegou ao editor principal em 10s "
                        "(len=%d) — colagem abortada para não salvar documento incompleto.",
                        int(estado_gate.get('len', 0) or 0),
                    )
                    return False

            ok = False
            try:
                ok = inserir_fn(driver=self.driver, numero_processo=numero_processo_atual, debug=True)
            except TypeError as te:
                try:
                    ok = inserir_fn(self.driver, numero_processo_atual)
                except Exception as e2:
                    try:
                        ok = inserir_fn(self.driver)
                    except Exception as e3:
                        logger.error(f"[JUNTADA][INSERIR][ERRO] Todas as tentativas de chamada falharam: {e3}")
                        return False

            if ok:
                ed_sync = _obter_editor_principal(self.driver, timeout=2.0)
                if ed_sync:
                    _executar_js(self.driver, """
                        const ed = arguments[0];
                        if (ed) {
                            const ck = ed.ckeditorInstance || (ed.closest('.ck-editor') && ed.closest('.ck-editor').ckeditorInstance);
                            try { if (ck && typeof ck.updateSourceElement === 'function') ck.updateSourceElement(); } catch (e) {}
                            ed.dispatchEvent(new Event('input', { bubbles: true }));
                            ed.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    """, ed_sync)
                espera.assentar(self.driver, 0.8, 'assentamento pos-insercao e sincronizacao do editor')
            return ok

        elif substituir_link:
            espera.ate_js(
                self.driver,
                "typeof CKEDITOR !== 'undefined'"
                " && Object.keys(CKEDITOR.instances || {}).length > 0",
                teto=3,
            )
            if not substituir_marcador_por_conteudo(self.driver, debug=True):
                logger.error('[JUNTADA][ERRO] Falha na substituição do link!')
                return False
            espera.pausa(self.driver, 2, 'assentamento pos-substituicao no editor')
            return True

        return True

    except Exception as e:
        logger.error(f"[JUNTADA][INSERIR][WARN] Erro durante inserção opcional: {e}")
        return False


def _salvar_documento(self) -> bool:
    """Salva documento com confirmação efetiva no PJe."""
    driver = self.driver
    logger.info('[JUNTADA][SALVAR] Iniciando salvamento do documento...')

    # 1. Sincronização do editor principal com o Angular
    ed_salvar = _obter_editor_principal(driver, timeout=2.0)
    if ed_salvar:
        _executar_js(driver, """
            const ed = arguments[0];
            if (ed) {
                const ck = ed.ckeditorInstance || (ed.closest('.ck-editor') && ed.closest('.ck-editor').ckeditorInstance);
                try { if (ck && typeof ck.updateSourceElement === 'function') ck.updateSourceElement(); } catch (e) {}
                ed.dispatchEvent(new Event('input', { bubbles: true }));
                ed.dispatchEvent(new Event('change', { bubbles: true }));
                if (document.activeElement === ed) ed.blur();
            }
            // Descarta snackbars anteriores para evitar falso positivo de "salvo"
            // (comportamento do motor pre-refatoracao: um aviso velho do modelo
            // inserido confirmava o save antes de ele acontecer).
            const oldSnacks = document.querySelectorAll('simple-snack-bar, snack-bar-container');
            oldSnacks.forEach(snack => {
                const btn = snack.querySelector('button');
                if (btn) btn.click();
                else snack.remove();
            });
        """, ed_salvar)
    espera.assentar(driver, 0.5, 'sincronizacao do editor antes de salvar')

    _SEL_SALVAR = 'button[aria-label="Salvar"]'
    espera.ate_habilitar(driver, _SEL_SALVAR, teto=8)

    clicou = self._clicar_elemento_gigs(_SEL_SALVAR, 'Salvar documento')
    if not clicou:
        clicou = click_headless_safe(driver, _SEL_SALVAR, timeout=5)

    if not clicou:
        logger.error('[JUNTADA][SALVAR][ERRO] Falha ao clicar no botão Salvar!')
        return False

    logger.info('[JUNTADA][SALVAR] Clique no botão Salvar realizado, aguardando processamento...')

    espera.ate_sumir(driver, 'mat-progress-bar, mat-progress-spinner, .mat-progress-spinner, .mat-progress-bar', teto=15)

    js_verificar_salvamento = """() => {
        var snacks = Array.from(document.querySelectorAll('simple-snack-bar, snack-bar-container'));
        for (var s of snacks) {
            var txt = (s.innerText || s.textContent || '').toLowerCase();
            if (txt.includes('erro') || txt.includes('falha') || txt.includes('obrigat') || txt.includes('inválid') || txt.includes('preencha')) {
                return { status: 'erro', msg: txt };
            }
            if (!txt.includes('modelo') && (txt.includes('salv') || txt.includes('gravad') || txt.includes('sucesso') || txt.includes('documento'))) {
                return { status: 'sucesso', msg: txt };
            }
        }
        return { status: 'pendente' };
    }"""

    limite_confirmacao = time.monotonic() + 10.0
    salvo = False
    while time.monotonic() < limite_confirmacao:
        res = _executar_js(driver, f"return ({js_verificar_salvamento})();")
        if isinstance(res, dict):
            if res.get('status') == 'erro':
                logger.error('[JUNTADA][SALVAR][ERRO] Salvamento rejeitado pelo PJe: %s', res.get('msg'))
                return False
            if res.get('status') == 'sucesso':
                logger.info('[JUNTADA][SALVAR] Sucesso confirmado via snackbar: "%s"', res.get('msg', '').strip().replace('\\n', ' '))
                salvo = True
                break
        espera.assentar(driver, 0.4)

    if not salvo:
        btn_ainda_ativo = _executar_js(driver, """
            const btn = document.querySelector('button[aria-label="Salvar"]');
            return !!(btn && !btn.disabled && btn.getAttribute('aria-disabled') !== 'true');
        """)
        if btn_ainda_ativo:
            logger.warning('[JUNTADA][SALVAR] Documento ainda não salvo após 10s, executando retry do clique...')
            click_headless_safe(driver, _SEL_SALVAR, timeout=4)
            espera.ate_sumir(driver, 'mat-progress-bar, mat-progress-spinner', teto=10)
            limite_retry = time.monotonic() + 6.0
            while time.monotonic() < limite_retry:
                res = _executar_js(driver, f"return ({js_verificar_salvamento})();")
                if isinstance(res, dict) and res.get('status') == 'sucesso':
                    logger.info('[JUNTADA][SALVAR] Sucesso confirmado após retry: "%s"', res.get('msg'))
                    salvo = True
                    break
                espera.assentar(driver, 0.4)

    if not salvo:
        js_estado_pos_salvar = """() => {
            var btnSalvar = document.querySelector('button[aria-label="Salvar"]');
            var btnAssinar = document.querySelector('button[aria-label="Assinar documento e juntar ao processo"], button[aria-label*="Assinar"]');
            var salvarDesab = !btnSalvar || btnSalvar.disabled || btnSalvar.getAttribute('aria-disabled') === 'true';
            var assinarHabil = btnAssinar && !btnAssinar.disabled && btnAssinar.getAttribute('aria-disabled') !== 'true';
            return salvarDesab && assinarHabil;
        }"""
        if bool(_executar_js(driver, f"return ({js_estado_pos_salvar})();")):
            logger.info('[JUNTADA][SALVAR] Salvo confirmado via estado de transição (Salvar inativo + Assinar habilitado)')
            salvo = True

    if not salvo:
        logger.error('[JUNTADA][SALVAR][ERRO] Não houve confirmação de salvamento do documento — abortando juntada')
        return False

    espera.assentar(driver, 1.5, 'estabilizacao pos-salvamento da juntada')
    logger.info('[JUNTADA][SALVAR] Documento salvo com sucesso e persistido')
    return True


def _assinar_se_necessario(self, configuracao: Dict[str, Any]) -> bool:
    """Assina documento se configurado."""
    if configuracao.get('assinar', 'nao').lower() == 'sim':
        seletor_assinar = 'button[aria-label="Assinar documento e juntar ao processo"]'
        espera.ate_habilitar(self.driver, seletor_assinar, teto=3)
        return self._clicar_elemento_gigs(seletor_assinar, 'Assinar')
    return True
