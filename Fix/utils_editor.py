import logging
logger = logging.getLogger(__name__)

"""
Fix.utils_editor - Funcoes de insercao no editor e clipboard interno.

Extraido do monolito Fix/utils.py para manter o shim fino.
"""

import os
import re
import time
from typing import Optional, Dict, Any, List, Union, Callable
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By


def _get_editable(driver: WebDriver, debug: bool = False) -> WebDriver:
    """Localiza o editor CKEditor na pagina."""
    sels = [
        '.ck-editor__editable[contenteditable="true"]',
        '.ck-content[contenteditable="true"]',
        'div[role="textbox"][contenteditable="true"]',
    ]
    for sel in sels:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el and el.is_displayed() and el.is_enabled():
                if debug:
                    logger.info(f"[EDITOR]  Editor encontrado por seletor: {sel}")
                return el
        except Exception:
            continue
    raise RuntimeError("Editor CKEditor nao encontrado na pagina")


def _place_selection_at_marker(driver: WebDriver, editable: Any, marcador: str = "--", modo: str = "after", debug: bool = False) -> bool:
    """Posiciona a selecao no marcador dentro do editor."""
    js = """
    const root = arguments[0];
    const marker = arguments[1];
    const mode = arguments[2];
    function findNodeWith(root, text) {
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let node;
      while ((node = walker.nextNode())) {
        const idx = node.data.indexOf(text);
        if (idx !== -1) return { node, idx };
      }
      return null;
    }
    const found = findNodeWith(root, marker);
    if (!found) return { ok: false, reason: 'marker_not_found' };
    const sel = window.getSelection();
    const range = document.createRange();
    if (mode === 'replace') {
      range.setStart(found.node, found.idx);
      range.setEnd(found.node, found.idx + marker.length);
    } else {
      range.setStart(found.node, found.idx + marker.length);
      range.setEnd(found.node, found.idx + marker.length);
    }
    sel.removeAllRanges();
    sel.addRange(range);
    return { ok: true };
    """
    result = driver.execute_script(js, editable, marcador, modo)
    return result and result.get('ok', False)


def inserir_html_editor(driver: WebDriver, html_content: str, marcador: str = "--", modo: str = "replace", debug: bool = False) -> bool:
    """
    Insere conteudo HTML no editor CKEditor apos o marcador.
    """
    try:
        if debug:
            logger.info(f"[EDITOR] Marcador: \"{marcador}\"")
            logger.info(f"[EDITOR] HTML: {html_content[:100]}...")

        editable = _get_editable(driver, debug)

        if debug:
            try:
                conteudo_atual = driver.execute_script("return arguments[0].innerHTML;", editable)
                logger.info(f"[EDITOR] Conteudo atual do editor: {conteudo_atual[:200]}...")
            except Exception as e:
                logger.info(f"[EDITOR] Erro ao verificar conteudo: {e}")

        driver.execute_script('arguments[0].scrollIntoView({block:"center"});', editable)
        time.sleep(0.2)
        try:
            editable.click()
        except Exception:
            driver.execute_script('arguments[0].focus();', editable)
        time.sleep(0.1)

        if not _place_selection_at_marker(driver, editable, marcador, modo, debug):
            if debug:
                logger.info(f"[EDITOR] Marcador \"{marcador}\" nao encontrado")
            return False

        html_content_clean = (html_content.replace('\x00', '').replace('\r', '').strip())
        html_escaped = (html_content_clean
                       .replace('\\', '\\\\')
                       .replace('`', '\\`')
                       .replace('$', '\\$')
                       .replace('"', '\\"')
                       .replace('\n', '\\n')
                       .replace('\t', '\\t'))

        js_insert = f"""
        const sel = window.getSelection();
        const html = `{html_escaped}`;

        try {{
            if (document.execCommand && typeof document.execCommand === 'function') {{
                document.execCommand('insertHTML', false, html);
                return true;
            }}
        }} catch (e) {{
            console.log('execCommand falhou:', e);
        }}

        try {{
            if (window.CKEDITOR && window.CKEDITOR.instances) {{
                const instances = Object.values(window.CKEDITOR.instances);
                if (instances.length > 0) {{
                    const editor = instances[0];
                    editor.insertHtml(html);
                    return true;
                }}
            }}
        }} catch (e) {{
            console.log('CKEditor API falhou:', e);
        }}

        try {{
            if (sel.rangeCount > 0) {{
                const range = sel.getRangeAt(0);
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = html;
                const fragment = document.createDocumentFragment();
                while (tempDiv.firstChild) {{
                    fragment.appendChild(tempDiv.firstChild);
                }}
                range.deleteContents();
                range.insertNode(fragment);
                return true;
            }}
        }} catch (e) {{
            console.log('Insercao manual falhou:', e);
        }}

        return false;
        """

        sucesso = driver.execute_script(js_insert)
        if sucesso and debug:
            try:
                conteudo_apos = driver.execute_script("return arguments[0].innerHTML;", editable)
                logger.info(f"[EDITOR] Conteudo apos insercao: {conteudo_apos[:200]}...")
            except Exception as e:
                logger.info(f"[EDITOR] Erro ao verificar conteudo apos: {e}")

        return bool(sucesso)

    except Exception as e:
        if debug:
            _ = e
        return False


def inserir_texto_editor(driver: WebDriver, texto: str, marcador: str = "--", modo: str = "replace", debug: bool = False) -> bool:
    """Insere texto simples no editor CKEditor."""
    try:
        editable = _get_editable(driver, debug)

        driver.execute_script('arguments[0].scrollIntoView({block:"center"});', editable)
        time.sleep(0.2)
        editable.click()
        time.sleep(0.1)

        if not _place_selection_at_marker(driver, editable, marcador, modo, debug):
            return False

        if modo == "replace":
            js_replace = f"""
            const sel = window.getSelection();
            if (sel.rangeCount > 0) {{
                const range = sel.getRangeAt(0);
                const text = `{texto.replace('`', '\\`')}`;
                range.deleteContents();
                range.insertNode(document.createTextNode(text));
                return true;
            }}
            return false;
            """
        else:
            js_after = f"""
            const sel = window.getSelection();
            if (sel.rangeCount > 0) {{
                const range = sel.getRangeAt(0);
                const text = `{texto.replace('`', '\\`')}`;
                range.insertNode(document.createTextNode(text));
                return true;
            }}
            return false;
            """

        script = js_replace if modo == "replace" else js_after
        sucesso = driver.execute_script(script)

        return bool(sucesso)

    except Exception as e:
        if debug:
            logger.error(f'Erro na insercao de texto: {e}')
        return False


def obter_ultimo_conteudo_clipboard(numero_processo: Optional[str] = None, tipo_regex: Optional[str] = None, debug: bool = False) -> Optional[str]:
    """Obtem o ultimo conteudo salvo no clipboard."""
    try:
        if debug:
            logger.info(f"[CLIPBOARD] Buscando ultimo conteudo para processo: {numero_processo}")

        projeto_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        clipboard_file = os.path.join(projeto_root, 'PEC', 'clipboard.txt')

        if not os.path.exists(clipboard_file):
            if debug:
                logger.info(f"[CLIPBOARD] Arquivo nao encontrado: {clipboard_file}")
            return None

        with open(clipboard_file, 'r', encoding='utf-8') as f:
            texto = f.read()

        pattern = re.compile(r"={3,}\nPROCESSO:\s*(?P<proc>.+?)\n={3,}\n(?P<conteudo>.*?)(?=(\n={3,}|\Z))", re.DOTALL)
        matches = list(pattern.finditer(texto))

        if not matches:
            if debug:
                logger.info('[CLIPBOARD] Nenhum registro encontrado no arquivo de clipboard')
            return None

        def _norm(s: str) -> str:
            return re.sub(r"\W+", "", s or "").lower()

        if numero_processo:
            n_req = _norm(numero_processo)
            for m in reversed(matches):
                proc = m.group('proc').strip()
                if _norm(proc) == n_req:
                    conteudo = m.group('conteudo').strip()
                    if tipo_regex:
                        if re.search(tipo_regex, conteudo):
                            return conteudo
                        else:
                            continue
                    return conteudo
            if debug:
                logger.info(f"[CLIPBOARD] Nenhum registro correspondente ao processo {numero_processo} encontrado")
            return None

        for m in reversed(matches):
            conteudo = m.group('conteudo').strip()
            if tipo_regex:
                if re.search(tipo_regex, conteudo):
                    return conteudo
                else:
                    continue
            return conteudo

        if debug:
            logger.info('[CLIPBOARD] Nenhum registro passou no filtro tipo_regex')
        return None
    except Exception as e:
        if debug:
            logger.info(f"[CLIPBOARD] Erro ao obter conteudo: {e}")
        return None


def substituir_marcador_por_conteudo(driver: WebDriver, conteudo_customizado: Optional[str] = None, debug: bool = True, marcador: str = "--") -> bool:
    """
    Função melhorada para localizar marcador (ex: "--") e colar conteúdo após ele.
    Usa a mesma lógica robusta para maior compatibilidade com CKEditor.
    Args:
        driver: Selenium WebDriver
        conteudo_customizado: Conteúdo específico para usar (se None, usa clipboard/arquivo)
        debug: Se deve exibir logs
        marcador: Texto a ser localizado (padrão: "--")
    """
    if debug:
        logger.info(f"[SUBST_MARCADOR] Iniciando colagem após marcador '{marcador}'...")

    try:
        # 1. Determina qual conteúdo usar
        conteudo_para_usar = conteudo_customizado

        if not conteudo_para_usar:
            conteudo_para_usar = obter_ultimo_conteudo_clipboard(None, debug=debug)

        if not conteudo_para_usar:
            if debug:
                logger.info("[SUBST_MARCADOR] ✗ Nenhum conteúdo disponível para colar")
            return False

        # 2. Encontrar o editor
        editable = _get_editable(driver, debug)

        # Foco e rolagem
        driver.execute_script('arguments[0].scrollIntoView({block:"center"});', editable)
        time.sleep(0.2)
        try:
            editable.click()
        except Exception:
            driver.execute_script('arguments[0].focus();', editable)
        time.sleep(0.1)

        # Limpar caracteres problemáticos e escapar para JavaScript
        html_content_clean = (conteudo_para_usar
                             .replace('\x00', '')  # Remove null bytes
                             .replace('\r', '')    # Remove carriage returns
                             .strip())             # Remove espaços extras

        # IMPLEMENTAÇÃO ROBUSTA COM API DO CKEDITOR
        script_ckeditor = """
        console.log('[SUBST_MARCADOR] === USANDO LÓGICA ROBUSTA ===');
        let editor = arguments[0];
        let htmlContent = arguments[1];
        let marcador = arguments[2];
        try {
            let ckInstance = null;
            if (editor.ckeditorInstance) ckInstance = editor.ckeditorInstance;
            if (!ckInstance && window.CKEDITOR) {
                for (let name in window.CKEDITOR.instances) {
                    let instance = window.CKEDITOR.instances[name];
                    if (instance.element && instance.element.$ === editor) { ckInstance = instance; break; }
                }
            }
            if (!ckInstance) {
                let closest = editor.closest('.ck-editor');
                if (closest && closest.ckeditorInstance) ckInstance = closest.ckeditorInstance;
            }
            if (ckInstance) {
                let htmlOriginal = ckInstance.getData();
                if (htmlOriginal.includes(marcador)) {
                    if (ckInstance.insertHtml) {
                        ckInstance.insertHtml(htmlContent, 'unfiltered_html');
                        return { sucesso: true, metodo: 'ckeditor_insertHtml' };
                    }
                    let novoHtml = htmlOriginal.replace(marcador, htmlContent);
                    ckInstance.setData(novoHtml);
                    return { sucesso: true, metodo: 'ckeditor_setData' };
                }
            } else {
                let htmlOriginal = editor.innerHTML;
                if (htmlOriginal.includes(marcador)) {
                    editor.innerHTML = htmlOriginal.replace(marcador, htmlContent);
                    ['input', 'change', 'keyup'].forEach(ev => editor.dispatchEvent(new Event(ev, { bubbles: true })));
                    return { sucesso: true, metodo: 'dom_direto' };
                }
            }
            return { sucesso: false, erro: 'Marcador não encontrado ou API falhou' };
        } catch (e) { return { sucesso: false, erro: e.message }; }
        """

        resultado = driver.execute_script(script_ckeditor, editable, html_content_clean, marcador)
        
        if debug:
            logger.info(f"[SUBST_MARCADOR] Resultado: {resultado}")

        return bool(resultado and isinstance(resultado, dict) and resultado.get('sucesso'))

    except Exception as e:
        if debug:
            logger.error(f"[SUBST_MARCADOR] ✗ Erro geral: {e}")
        return False


def inserir_link_ato(driver: WebDriver, numero_processo: Optional[str] = None, modo: str = 'after', debug: bool = False) -> bool:
    """Insere link de validacao de ato no editor (coleta + insercao)."""
    try:
        link_validacao = obter_ultimo_conteudo_clipboard(numero_processo, r"/validacao/", debug)

        if not link_validacao:
            link_validacao = obter_ultimo_conteudo_clipboard(None, r"/validacao/", debug)

        if link_validacao:
            # Usar a função local para evitar dependência circular com PEC
            resultado = substituir_marcador_por_conteudo(driver, link_validacao, debug, "--")
            return resultado
        else:
            return False

    except Exception as e:
        if debug:
            logger.error(f'[LINK_ATO] Erro: {e}')
        return False


def inserir_html_no_editor_apos_marcador(driver: WebDriver, html_content: str, marcador: str = "--", modo: str = "replace", debug: bool = False) -> bool:
    """Compatibilidade com editor_insert.py."""
    return inserir_html_editor(driver, html_content, marcador, modo, debug)


def inserir_link_ato_validacao(driver: WebDriver, numero_processo: Optional[str] = None, modo: str = 'after', debug: bool = False) -> bool:
    """Compatibilidade com editor_insert.py."""
    return inserir_link_ato(driver, numero_processo, modo, debug)


def inserir_conteudo_formatado(driver: WebDriver, numero_processo: Optional[str] = None, modo: str = 'after', debug: bool = False) -> bool:
    """
    Insere conteudo formatado (transcricao de documento) no editor.
    """
    try:
        conteudo = obter_ultimo_conteudo_clipboard(numero_processo, r"Transcrição do\(a\)", debug)

        if not conteudo:
            conteudo = obter_ultimo_conteudo_clipboard(None, r"Transcrição do\(a\)", debug)

        if conteudo:
            # Usar a função local para evitar dependência circular com PEC
            resultado = substituir_marcador_por_conteudo(driver, conteudo, debug, "--")
            return resultado
        else:
            return False

    except Exception as e:
        if debug:
            logger.error(f'[CONTEUDO_FORMATADO] Erro: {e}')
        return False