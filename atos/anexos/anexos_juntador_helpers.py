"""atos.anexos.juntador.helpers - Helpers de decomposição para juntada."""

import logging
logger = logging.getLogger(__name__)

import os
import re
import types
from typing import Optional, Dict, Any, Callable, Union, List


from Fix.core import (
    aguardar_e_clicar,
    aguardar_renderizacao_nativa,
    selecionar_opcao,
    preencher_campo,
    safe_click,
    wait_for_clickable,
    wait_for_visible,
    esperar_url_conter,
)
from Fix.browser_suporte import aguardar_nova_aba, abrir_url_nova_aba
from Fix.utils import (
    inserir_html_no_editor_apos_marcador,
    obter_ultimo_conteudo_clipboard,
    executar_coleta_parametrizavel,
    inserir_link_ato_validacao,
)
from Fix import espera
from Fix.core import _executar_js


def _abrir_interface_anexacao(self: types.SimpleNamespace) -> bool:
    """Abre a interface de anexação de documentos."""
    driver = self.driver
    logger.debug('[JUNTADA] Abrindo interface de anexação...')

    try:
        if '/anexar' in (driver.current_url or ''):
            logger.debug('[JUNTADA] Já na interface de anexação, prosseguindo...')
            espera.ate_habilitar(driver, 'input[aria-label="Tipo de Documento"]', teto=4)
            return True
    except Exception:
        pass

    aba_atual = getattr(driver, 'current_window_handle', None)
    handles = list(getattr(driver, 'window_handles', []))
    for h in handles:
        if h == aba_atual:
            continue
        try:
            driver.switch_to.window(h)
            if '/anexar' in (driver.current_url or ''):
                logger.debug('[JUNTADA] Aba /anexar já existente detectada: %s', h)
                espera.ate_habilitar(driver, 'input[aria-label="Tipo de Documento"]', teto=4)
                return True
        except Exception:
            continue

    try:
        if aba_atual:
            driver.switch_to.window(aba_atual)
    except Exception:
        pass

    handles_antes = set(getattr(driver, 'window_handles', []))
    handle_original = aba_atual

    try:
        url_atual = driver.current_url or ''
        match = re.search(r'/processo/(\d+)', url_atual)
        if match:
            id_processo = match.group(1)
            url_anexar = f"https://pje.trt2.jus.br/pjekz/processo/{id_processo}/documento/anexar"
            logger.debug('[JUNTADA] ID do processo detectado (%s). Abrindo /documento/anexar via URL...', id_processo)
            abrir_url_nova_aba(driver, url_anexar)
        else:
            logger.debug('[JUNTADA] ID não encontrado na URL. Clicando no menu hambúrguer...')
            if not aguardar_e_clicar(driver, 'i[class*="fa-bars"].icone-botao-menu', 'Menu hambúrguer'):
                _executar_js(driver, "document.querySelector('i.fa-bars.icone-botao-menu')?.click();")
            espera.assentar(driver, 0.3)
            if not aguardar_e_clicar(driver, 'button[aria-label="Anexar Documentos"]', 'Anexar documentos'):
                _executar_js(driver, "document.querySelector('button[aria-label=\"Anexar Documentos\"]')?.click();")
    except Exception as e:
        logger.debug('[JUNTADA] Falha na abertura da interface: %s', e)

    if '/anexar' not in (driver.current_url or ''):
        logger.debug('[JUNTADA] Mudando para aba de anexação...')
        nova_aba = None
        for _ in range(30):
            novas = set(getattr(driver, 'window_handles', [])) - handles_antes
            if novas:
                nova_aba = list(novas)[0]
                break
            espera.pausa(driver, 0.2)

        if nova_aba:
            driver.switch_to.window(nova_aba)
        else:
            for h in getattr(driver, 'window_handles', []):
                try:
                    driver.switch_to.window(h)
                    if '/anexar' in (driver.current_url or ''):
                        nova_aba = h
                        break
                except Exception:
                    continue
            if not nova_aba and handle_original:
                driver.switch_to.window(handle_original)
                logger.debug('[JUNTADA] Nova aba /anexar não detectada, prosseguindo na aba atual...')

    espera.ate_url(driver, '/anexar', teto=6)
    espera.ate_sumir(driver, 'mat-progress-bar, mat-progress-spinner, pje-dialogo-status-progresso', teto=10)
    espera.ate_habilitar(driver, 'input[aria-label="Tipo de Documento"]', teto=8)
    return True


def _preencher_campos_basicos(self: types.SimpleNamespace, configuracao: Dict[str, Any]) -> bool:
    """Preenche os campos básicos: tipo, descrição e sigilo."""
    driver = self.driver
    tipo = configuracao.get('tipo', 'Certidão')
    if not selecionar_opcao(driver, 'input[aria-label="Tipo de Documento"]', tipo, 'Tipo de Documento'):
        return False

    descricao = configuracao.get('descricao', '')
    if descricao:
        if not preencher_campo(driver, 'input[aria-label="Descrição"]', descricao, 'Descrição'):
            return False

    # Sigilo
    sigilo = configuracao.get('sigilo', 'nao').lower()
    if 'sim' in sigilo:
        if not aguardar_e_clicar(driver, 'input[name="sigiloso"]', 'Sigilo'):
            return False

    return True


def _inserir_modelo(self: types.SimpleNamespace, configuracao: Dict[str, Any]) -> bool:
    """Insere o modelo no editor e verifica se foi carregado."""
    driver = self.driver
    modelo_original = configuracao.get('modelo', '')
    if modelo_original:
        logger.debug('[JUNTADA] Selecionando e inserindo modelo: %s', modelo_original)
        if not self._selecionar_modelo_gigs(modelo_original):
            return False
        logger.debug('[JUNTADA] Aguardando modelo ser inserido no editor...')
        aguardar_renderizacao_nativa(driver, '[contenteditable="true"]', 'aparecer', 5)

    logger.debug('[JUNTADA] Verificando se editor está disponível após inserção do modelo...')
    editor_encontrado = _obter_editor_principal(driver)
    if not editor_encontrado:
        logger.error('[JUNTADA] Nenhum editor principal encontrado na página!')
        return False

    logger.debug('[JUNTADA] Editor principal disponível para manipulação')
    return True


_JS_ENCONTRAR_EDITOR_PRINCIPAL = r"""
const marcador = arguments[0] || '';
const norm = (s) => (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const textoLimpo = (el) => {
    if (!el) return '';
    const clone = el.cloneNode(true);
    clone.querySelectorAll('.placeholder-conteudo, .ck-placeholder, [data-placeholder]').forEach(p => p.remove());
    return (clone.innerText || clone.textContent || '').replace(/\u00a0/g, ' ').trim();
};
const sels = [
    'div[class*="area-conteudo"][contenteditable="true"][aria-label*="Conteúdo principal"]',
    'div[class*="area-conteudo"][contenteditable="true"][aria-label*="Conteudo principal"]',
    'div[class*="area-conteudo"][contenteditable="true"][role="textbox"]',
    'div[class*="area-conteudo"][contenteditable="true"]',
    '.ck-editor__editable[contenteditable="true"]',
    'div.ck-content[contenteditable="true"]',
    'div[role="textbox"][contenteditable="true"]',
    'div.fr-element[contenteditable="true"]',
    // Fallback genérico: o motor pre-refatoração usava div[contenteditable="true"]
    // como último recurso. Sem ele um layout fora dos padrões PJe deixava de achar
    // o editor e a juntada abortava em branco.
    'div[contenteditable="true"]'
];
const vistos = new Set();
const candidatos = [];
for (const sel of sels) {
    for (const el of document.querySelectorAll(sel)) {
        if (vistos.has(el)) continue;
        vistos.add(el);
        if (el.closest('pje-dialogo-visualizar-modelo, mat-dialog-container, .mat-dialog-container')) continue;
        const lbl = norm(el.getAttribute('aria-label') || '');
        const ehPrincipal = lbl.includes('conteudo principal') || lbl.includes('dispositivo') || lbl.includes('fundamentacao');
        const ehAuxiliar = lbl.includes('cabecalho') || lbl.includes('rodape') || lbl.includes('ementa');
        const txt = textoLimpo(el);
        candidatos.push({ el, ehPrincipal, ehAuxiliar, temMarcador: !!(marcador && txt.includes(marcador)), len: txt.length });
    }
}
if (!candidatos.length) return null;
if (marcador) {
    const comMarcadorPrincipal = candidatos.find(c => c.temMarcador && c.ehPrincipal);
    if (comMarcadorPrincipal) return comMarcadorPrincipal.el;
    const comMarcador = candidatos.find(c => c.temMarcador && !c.ehAuxiliar);
    if (comMarcador) return comMarcador.el;
}
const principal = candidatos.find(c => c.ehPrincipal);
if (principal) return principal.el;
const naoAux = candidatos.find(c => !c.ehAuxiliar);
return (naoAux || candidatos[0]).el;
"""


def _obter_editor_principal(driver: Any, marcador: str = '', timeout: float = 4.0) -> Optional[Any]:
    """Retorna o elemento WebElement/PWElement do editor principal de /documento/anexar."""
    import time
    deadline = time.monotonic() + max(0.3, float(timeout))
    while True:
        try:
            el = _executar_js(driver, _JS_ENCONTRAR_EDITOR_PRINCIPAL, marcador or '')
            if el:
                return el
        except Exception:
            pass
        if time.monotonic() >= deadline:
            break
        espera.assentar(driver, 0.25)
    return None


def _extrair_assinatura_conteudo(conteudo: str) -> str:
    """Extrai trecho textual limpo (sem tags HTML) para verificar inserção no editor."""
    if not conteudo:
        return ''
    sem_tags = re.sub(r'<[^>]+>', ' ', conteudo)
    sem_ent = sem_tags.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    palavras = [p for p in re.split(r'\s+', sem_ent.strip()) if len(p) >= 3]
    if not palavras:
        return sem_ent.strip()[:40]
    return ' '.join(palavras[:6])


_JS_LER_ESTADO_EDITOR = r"""
const ed = arguments[0];
if (!ed) return { existe: false, ck: false, texto: '', htmlLimpo: '', len: 0 };
let ck = ed.ckeditorInstance || null;
if (!ck) {
    const wrap = ed.closest('.ck-editor');
    if (wrap && wrap.ckeditorInstance) ck = wrap.ckeditorInstance;
}
if (!ck && window.CKEDITOR && window.CKEDITOR.instances) {
    for (const k in window.CKEDITOR.instances) {
        const inst = window.CKEDITOR.instances[k];
        if (inst && inst.element && inst.element.$ === ed) { ck = inst; break; }
    }
}
const clone = ed.cloneNode(true);
clone.querySelectorAll('.placeholder-conteudo, .ck-placeholder, [data-placeholder]').forEach(p => p.remove());
const texto = (clone.innerText || clone.textContent || '').replace(/\u00a0/g, ' ').trim();
let htmlBruto = '';
try {
    htmlBruto = ck ? (ck.getData() || '') : (ed.innerHTML || '');
} catch (e) {
    htmlBruto = ed.innerHTML || '';
}
const htmlLimpo = htmlBruto.replace(/<!--[\s\S]*?-->/g, '').trim();
const temMidia = !!(ed.querySelector('figure, table'));
return { existe: true, ck: !!ck, texto: texto, htmlLimpo: htmlLimpo, len: texto.length, temMidia: temMidia };
"""


_JS_SUBSTITUIR_NO_EDITOR = r"""
const editor = arguments[0];
const htmlContent = arguments[1];
const marcador = arguments[2];
const textoPlano = arguments[3];

if (!editor) return { sucesso: false, erro: 'Editor nulo' };

const temTagBloco = /<(?:table|div|p|ul|ol|h[1-6]|blockquote)\b/i.test(htmlContent);
const escapeRegex = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const substituirForaDeTagsEComentarios = (html, marc, replacement) => {
    // Remove comentários HTML antes para nunca casar '--' dentro de <!-- ... -->
    const semComentarios = html.replace(/<!--[\s\S]*?-->/g, '');
    const esc = escapeRegex(marc);

    // 1. Se o marcador está isolado num parágrafo (<p>--</p> ou <p><span>--</span></p>)
    //    e o conteúdo a inserir tem tags de bloco, substitui o parágrafo inteiro
    //    (evita <p><table>...</table></p> inválido no CKEditor 5).
    if (temTagBloco) {
        const reParagrafo = new RegExp(
            '<p\\b[^>]*>(?:\\s|<br\\s*/?>|&nbsp;|<span[^>]*>|</span>|<strong[^>]*>|</strong>|<em[^>]*>|</em>)*'
            + esc
            + '(?:\\s|<br\\s*/?>|&nbsp;|<span[^>]*>|</span>|<strong[^>]*>|</strong>|<em[^>]*>|</em>)*</p>',
            'i'
        );
        if (reParagrafo.test(semComentarios)) {
            return { ok: true, html: semComentarios.replace(reParagrafo, replacement), modo: 'paragrafo' };
        }
    }

    // 2. Substituição no texto fora de tags HTML (<...>)
    const partes = semComentarios.split(/(<[^>]+>)/g);
    let trocou = false;
    for (let i = 0; i < partes.length; i++) {
        if (partes[i].startsWith('<')) continue;
        if (partes[i].includes(marc)) {
            partes[i] = partes[i].replace(marc, replacement);
            trocou = true;
            break;
        }
    }
    if (trocou) {
        return { ok: true, html: partes.join(''), modo: 'inline' };
    }

    // 3. Tolerância para autoformatação do CKEditor (-- convertido em en-dash – ou em-dash —)
    if (marc === '--') {
        for (const alt of ['\u2013', '\u2014', '&ndash;', '&mdash;']) {
            const altPartes = semComentarios.split(/(<[^>]+>)/g);
            for (let i = 0; i < altPartes.length; i++) {
                if (altPartes[i].startsWith('<')) continue;
                if (altPartes[i].includes(alt)) {
                    altPartes[i] = altPartes[i].replace(alt, replacement);
                    return { ok: true, html: altPartes.join(''), modo: 'dash_unicode' };
                }
            }
        }
    }

    return { ok: false, html: semComentarios, modo: 'nao_encontrado' };
};

const encontrarCkInstance = (ed) => {
    if (ed.ckeditorInstance) return ed.ckeditorInstance;
    const wrap = ed.closest('.ck-editor');
    if (wrap && wrap.ckeditorInstance) return wrap.ckeditorInstance;
    if (window.CKEDITOR && window.CKEDITOR.instances) {
        for (const k in window.CKEDITOR.instances) {
            const inst = window.CKEDITOR.instances[k];
            if (inst && inst.element && inst.element.$ === ed) return inst;
        }
    }
    return null;
};

const notificarAngular = (ed, ck) => {
    try { if (ck && typeof ck.updateSourceElement === 'function') ck.updateSourceElement(); } catch (e) {}
    try { if (ck && typeof ck.fire === 'function') ck.fire('change'); } catch (e) {}
    try { ed.dispatchEvent(new Event('input', { bubbles: true })); } catch (e) {}
    try { ed.dispatchEvent(new Event('change', { bubbles: true })); } catch (e) {}
};

try {
    // ── MÉTODO 1: CKEditor API (setData) ──
    const ckInstance = encontrarCkInstance(editor);
    if (ckInstance && typeof ckInstance.getData === 'function' && typeof ckInstance.setData === 'function') {
        const htmlOriginal = ckInstance.getData() || '';
        const textoSemTags = htmlOriginal.replace(/<!--[\s\S]*?-->/g, '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
        const sub = substituirForaDeTagsEComentarios(htmlOriginal, marcador, htmlContent);
        if (sub.ok) {
            ckInstance.setData(sub.html);
            notificarAngular(editor, ckInstance);
            return { sucesso: true, metodo: 'ckeditor_api_' + sub.modo, lenAntes: textoSemTags.length };
        }
        if (textoSemTags.length > 20) {
            const novoHtml = sub.html + (temTagBloco ? htmlContent : ('<p>' + htmlContent + '</p>'));
            ckInstance.setData(novoHtml);
            notificarAngular(editor, ckInstance);
            return { sucesso: true, metodo: 'ckeditor_api_append', lenAntes: textoSemTags.length };
        }
        return { sucesso: false, erro: 'Editor vazio via CKEditor API (modelo nao inserido)', lenAntes: textoSemTags.length };
    }

    // ── MÉTODO 2: Seleção DOM no marcador + ClipboardEvent('paste') / execCommand (atualiza modelo interno CKEditor 5) ──
    const clone = editor.cloneNode(true);
    clone.querySelectorAll('.placeholder-conteudo, .ck-placeholder, [data-placeholder]').forEach(p => p.remove());
    const textoAtual = (clone.innerText || clone.textContent || '').replace(/\u00a0/g, ' ').trim();
    if (textoAtual.length <= 1) {
        return { sucesso: false, erro: 'Editor principal vazio no DOM (modelo nao inserido)', lenAntes: textoAtual.length };
    }

    editor.focus();
    const sel = window.getSelection();
    const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT, null);
    let nodeAlvo = null;
    let posAlvo = -1;
    let lenMarc = marcador.length;
    const candidatosMarc = marcador === '--' ? ['--', '\u2013', '\u2014'] : [marcador];
    let n;
    while ((n = walker.nextNode())) {
        const val = n.nodeValue || '';
        for (const m of candidatosMarc) {
            const idx = val.indexOf(m);
            if (idx !== -1) {
                nodeAlvo = n;
                posAlvo = idx;
                lenMarc = m.length;
                break;
            }
        }
        if (nodeAlvo) break;
    }

    const range = document.createRange();
    if (nodeAlvo) {
        range.setStart(nodeAlvo, posAlvo);
        range.setEnd(nodeAlvo, posAlvo + lenMarc);
    } else {
        // Sem marcador exato, posiciona no final do editor
        range.selectNodeContents(editor);
        range.collapse(false);
    }
    sel.removeAllRanges();
    sel.addRange(range);

    // 2a. Dispara evento nativo 'paste' (CKEditor 5 ClipboardPipeline processa text/html)
    try {
        const htmlAntesPaste = editor.innerHTML || '';
        const dt = new DataTransfer();
        dt.setData('text/html', htmlContent);
        dt.setData('text/plain', textoPlano);
        const pasteEv = new ClipboardEvent('paste', { bubbles: true, cancelable: true, clipboardData: dt });
        const naoCancelado = editor.dispatchEvent(pasteEv);
        // Só assume sucesso se o DOM realmente mudou após o paste (evita falso-positivo de preventDefault no-op)
        if (!naoCancelado && (editor.innerHTML || '') !== htmlAntesPaste) {
            notificarAngular(editor, null);
            return { sucesso: true, metodo: nodeAlvo ? 'ckeditor_paste_marcador' : 'ckeditor_paste_append', lenAntes: textoAtual.length };
        }
    } catch (e) {}

    // 2b. Fallback execCommand('insertHTML') sobre a seleção
    try {
        const htmlAntesExec = editor.innerHTML || '';
        const okExec = document.execCommand('insertHTML', false, htmlContent);
        if (okExec && (editor.innerHTML || '') !== htmlAntesExec) {
            notificarAngular(editor, null);
            return { sucesso: true, metodo: nodeAlvo ? 'execCommand_insertHTML' : 'execCommand_append', lenAntes: textoAtual.length };
        }
    } catch (e) {}

    // ── MÉTODO 3: Fallback DOM direto (substituindo apenas fora de tags e comentários) ──
    const subDom = substituirForaDeTagsEComentarios(editor.innerHTML || '', marcador, htmlContent);
    if (subDom.ok) {
        editor.innerHTML = subDom.html;
        notificarAngular(editor, null);
        return { sucesso: true, metodo: 'dom_direto_' + subDom.modo, lenAntes: textoAtual.length };
    }
    if (textoAtual.length > 20) {
        editor.innerHTML = subDom.html + (temTagBloco ? htmlContent : ('<p>' + htmlContent + '</p>'));
        notificarAngular(editor, null);
        return { sucesso: true, metodo: 'dom_direto_append', lenAntes: textoAtual.length };
    }

    return { sucesso: false, erro: 'Nenhum metodo conseguiu inserir no editor', lenAntes: textoAtual.length };
} catch (e) {
    return { sucesso: false, erro: (e && e.message) ? e.message : String(e) };
}
"""


def substituir_marcador_por_conteudo(driver, conteudo_customizado: Optional[str] = None, debug: bool = True, marcador: str = "--") -> bool:
    """Localiza o marcador (ex: "--") no editor principal CKEditor 5 e substitui pelo conteúdo."""
    if debug:
        logger.debug("[SUBST_MARCADOR] Iniciando colagem no marcador '%s'...", marcador)

    try:
        conteudo_para_usar = None
        if conteudo_customizado:
            conteudo_para_usar = conteudo_customizado
        else:
            try:
                clipboard_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clipboard.txt")
                if os.path.exists(clipboard_file):
                    with open(clipboard_file, 'r', encoding='utf-8') as f:
                        conteudo_para_usar = f.read().strip()
            except Exception as e:
                logger.debug("[SUBST_MARCADOR] Erro ao carregar clipboard.txt: %s", e)

        if not conteudo_para_usar:
            logger.error("[SUBST_MARCADOR] Nenhum conteúdo disponível para colar")
            return False

        html_content_clean = conteudo_para_usar.replace('\x00', '').replace('\r', '').strip()
        texto_plano = re.sub(r'<[^>]+>', ' ', html_content_clean)
        texto_plano = re.sub(r'\s+', ' ', texto_plano).strip()
        assinatura = _extrair_assinatura_conteudo(html_content_clean).lower()

        editable = _obter_editor_principal(driver, marcador=marcador, timeout=6.0)
        if not editable:
            logger.error("[SUBST_MARCADOR] Editor principal CKEditor não encontrado na página")
            return False

        estado_antes = {'existe': False, 'ck': False, 'texto': '', 'htmlLimpo': '', 'len': 0}
        for i in range(16):
            try:
                st = _executar_js(driver, _JS_LER_ESTADO_EDITOR, editable)
                if isinstance(st, dict):
                    estado_antes = st
                    txt = st.get('texto') or ''
                    if marcador in txt or (marcador == '--' and ('\u2013' in txt or '\u2014' in txt)):
                        break
                    if st.get('len', 0) > 20 and (st.get('ck') or i >= 4):
                        break
            except Exception:
                pass
            espera.assentar(driver, 0.5)

        if estado_antes.get('len', 0) <= 1:
            logger.error(
                "[SUBST_MARCADOR] Editor principal continua vazio após espera (len=%d, ck=%s) — modelo não foi inserido no editor",
                estado_antes.get('len', 0), estado_antes.get('ck', False),
            )
            return False

        logger.info(
            "[SUBST_MARCADOR] Editor pronto (ck=%s, len_antes=%d, tem_marcador=%s)",
            estado_antes.get('ck', False),
            estado_antes.get('len', 0),
            marcador in (estado_antes.get('texto') or ''),
        )

        for tentativa in (1, 2):
            if tentativa == 2:
                logger.warning("[SUBST_MARCADOR] Reassentando e repetindo a inserção (2ª tentativa)...")
                espera.assentar(driver, 1.0)
                editable = _obter_editor_principal(driver, marcador=marcador, timeout=4.0) or editable

            try:
                _executar_js(driver, 'arguments[0].scrollIntoView({block:"center"}); arguments[0].focus();', editable)
            except Exception:
                pass
            espera.assentar(driver, 0.15)

            resultado = _executar_js(
                driver,
                _JS_SUBSTITUIR_NO_EDITOR,
                editable,
                html_content_clean,
                marcador,
                texto_plano,
            )

            if not (isinstance(resultado, dict) and resultado.get('sucesso')):
                erro = resultado.get('erro', 'Retorno inválido') if isinstance(resultado, dict) else str(resultado)
                logger.warning("[SUBST_MARCADOR] Tentativa %d falhou: %s", tentativa, erro)
                continue

            metodo_usado = resultado.get('metodo', 'desconhecido')

            confirmado = False
            estado_depois = estado_antes
            for _ in range(12):
                try:
                    st_pos = _executar_js(driver, _JS_LER_ESTADO_EDITOR, editable)
                    if isinstance(st_pos, dict):
                        estado_depois = st_pos
                        txt_pos_lower = ' '.join((st_pos.get('texto') or '').lower().split())
                        if assinatura and assinatura in txt_pos_lower:
                            confirmado = True
                            break
                        if st_pos.get('len', 0) > estado_antes.get('len', 0) + 10 and marcador not in (st_pos.get('texto') or ''):
                            confirmado = True
                            break
                except Exception:
                    pass
                espera.assentar(driver, 0.2)

            if confirmado:
                logger.info(
                    "[SUBST_MARCADOR] Conteúdo inserido e confirmado via %s (len %d -> %d)",
                    metodo_usado, estado_antes.get('len', 0), estado_depois.get('len', 0),
                )
                return True

            logger.warning(
                "[SUBST_MARCADOR] Método %s retornou ok mas conteúdo não foi confirmado no editor (tentativa %d, len %d -> %d)",
                metodo_usado, tentativa, estado_antes.get('len', 0), estado_depois.get('len', 0),
            )

        logger.error("[SUBST_MARCADOR] Falha na inserção no marcador '%s' após 2 tentativas", marcador)
        return False

    except Exception as e:
        logger.error("[SUBST_MARCADOR] Erro geral: %s", e)
        return False
