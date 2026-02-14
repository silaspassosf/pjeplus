import logging
logger = logging.getLogger(__name__)

"""
Fix.utils_editor - Funcoes de insercao no editor e clipboard interno.

Extraido do monolito Fix/utils.py para manter o shim fino.
"""

import os
import re
import time
from typing import Optional
from selenium.webdriver.common.by import By


def _get_editable(driver, debug: bool = False):
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
                    print(f"[EDITOR]  Editor encontrado por seletor: {sel}")
                return el
        except Exception:
            continue
    raise RuntimeError("Editor CKEditor nao encontrado na pagina")


def _place_selection_at_marker(driver, editable, marcador: str = "--", modo: str = "after", debug: bool = False) -> bool:
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


def inserir_html_editor(driver, html_content: str, marcador: str = "--", modo: str = "replace", debug: bool = False) -> bool:
    """
    Insere conteudo HTML no editor CKEditor apos o marcador.
    """
    try:
        if debug:
            print(f"[EDITOR] Marcador: \"{marcador}\"")
            print(f"[EDITOR] HTML: {html_content[:100]}...")

        editable = _get_editable(driver, debug)

        if debug:
            try:
                conteudo_atual = driver.execute_script("return arguments[0].innerHTML;", editable)
                print(f"[EDITOR] Conteudo atual do editor: {conteudo_atual[:200]}...")
            except Exception as e:
                print(f"[EDITOR] Erro ao verificar conteudo: {e}")

        driver.execute_script('arguments[0].scrollIntoView({block:"center"});', editable)
        time.sleep(0.2)
        try:
            editable.click()
        except Exception:
            driver.execute_script('arguments[0].focus();', editable)
        time.sleep(0.1)

        if not _place_selection_at_marker(driver, editable, marcador, modo, debug):
            if debug:
                print(f"[EDITOR] Marcador \"{marcador}\" nao encontrado")
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
                print(f"[EDITOR] Conteudo apos insercao: {conteudo_apos[:200]}...")
            except Exception as e:
                print(f"[EDITOR] Erro ao verificar conteudo apos: {e}")

        return bool(sucesso)

    except Exception as e:
        if debug:
            _ = e
        return False


def inserir_texto_editor(driver, texto: str, marcador: str = "--", modo: str = "replace", debug: bool = False) -> bool:
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
            print(f"[CLIPBOARD] Buscando ultimo conteudo para processo: {numero_processo}")

        projeto_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        clipboard_file = os.path.join(projeto_root, 'PEC', 'clipboard.txt')

        if not os.path.exists(clipboard_file):
            if debug:
                print(f"[CLIPBOARD] Arquivo nao encontrado: {clipboard_file}")
            return None

        with open(clipboard_file, 'r', encoding='utf-8') as f:
            texto = f.read()

        pattern = re.compile(r"={3,}\nPROCESSO:\s*(?P<proc>.+?)\n={3,}\n(?P<conteudo>.*?)(?=(\n={3,}|\Z))", re.DOTALL)
        matches = list(pattern.finditer(texto))

        if not matches:
            if debug:
                print('[CLIPBOARD] Nenhum registro encontrado no arquivo de clipboard')
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
                print(f"[CLIPBOARD] Nenhum registro correspondente ao processo {numero_processo} encontrado")
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
            print('[CLIPBOARD] Nenhum registro passou no filtro tipo_regex')
        return None
    except Exception as e:
        if debug:
            print(f"[CLIPBOARD] Erro ao obter conteudo: {e}")
        return None


def inserir_link_ato(driver, numero_processo: Optional[str] = None, modo: str = 'after', debug: bool = False) -> bool:
    """Insere link de validacao de ato no editor (coleta + insercao)."""
    try:
        link_validacao = obter_ultimo_conteudo_clipboard(numero_processo, r"/validacao/", debug)

        if not link_validacao:
            link_validacao = obter_ultimo_conteudo_clipboard(None, r"/validacao/", debug)

        if link_validacao:
            from PEC.anexos import substituir_marcador_por_conteudo

            resultado = substituir_marcador_por_conteudo(driver, link_validacao, debug, "--")
            return resultado
        else:
            return False

    except Exception as e:
        if debug:
            logger.error(f'[LINK_ATO] Erro: {e}')
        return False


def inserir_html_no_editor_apos_marcador(driver, html_content, marcador="--", modo="replace", debug=False):
    """Compatibilidade com editor_insert.py."""
    return inserir_html_editor(driver, html_content, marcador, modo, debug)


def inserir_link_ato_validacao(driver, numero_processo=None, modo='after', debug=False):
    """Compatibilidade com editor_insert.py."""
    return inserir_link_ato(driver, numero_processo, modo, debug)


def inserir_conteudo_formatado(driver, numero_processo: Optional[str] = None, modo: str = 'after', debug: bool = False) -> bool:
    """
    Insere conteudo formatado (transcricao de documento) no editor.
    """
    try:
        conteudo = obter_ultimo_conteudo_clipboard(numero_processo, r"Transcrição do\(a\)", debug)

        if not conteudo:
            conteudo = obter_ultimo_conteudo_clipboard(None, r"Transcrição do\(a\)", debug)

        if conteudo:
            from PEC.anexos import substituir_marcador_por_conteudo

            resultado = substituir_marcador_por_conteudo(driver, conteudo, debug, "--")
            return resultado
        else:
            return False

    except Exception as e:
        if debug:
            logger.error(f'[CONTEUDO_FORMATADO] Erro: {e}')
        return False