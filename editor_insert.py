import re
import time
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


def _get_editable(driver, debug: bool = False):
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
                    print(f"[EDITOR] ✓ Editor encontrado por seletor: {sel}")
                return el
        except Exception:
            continue
    raise RuntimeError("Editor CKEditor não encontrado na página")


def _place_selection_at_marker(driver, editable, marcador: str = "--", modo: str = "after", debug: bool = False) -> bool:
    """
    Posiciona a seleção exatamente no marcador dentro do editor.
    modo: 'after' (caret após marcador) ou 'replace' (seleciona o marcador para sobrescrever)
    """
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
      range.collapse(true);
    }
    sel.removeAllRanges();
    sel.addRange(range);
    return { ok: true, start: range.startOffset };
    """
    res = driver.execute_script(js, editable, marcador, 'replace' if modo == 'replace' else 'after')
    if debug:
        print(f"[EDITOR] Seleção no marcador: {res}")
    return bool(res and res.get('ok'))


def _dispatch_sync(driver, editable, debug: bool = False):
    js = """
    const el = arguments[0];
    ['input','change'].forEach(type => {
      const ev = new Event(type, { bubbles: true });
      el.dispatchEvent(ev);
    });
    return true;
    """
    try:
        driver.execute_script(js, editable)
    except Exception as e:
        if debug:
            print(f"[EDITOR] Aviso: falha ao despachar eventos: {e}")


def inserir_html_no_editor_apos_marcador(driver, html_content: str, marcador: str = "--", modo: str = "replace", debug: bool = False) -> bool:
    """
    Insere conteúdo HTML formatado no CKEditor usando método cópia/colagem
    que simula exatamente como funciona o JavaScript bookmarklet.
    - modo 'replace': substitui o marcador
    - modo 'after': insere imediatamente após o marcador
    Retorna True se sucesso.
    """
    try:
        if debug:
            print(f'[EDITOR] Iniciando inserção HTML via método cópia/colagem')
            print(f'[EDITOR] Marcador: "{marcador}"')
            print(f'[EDITOR] HTML (primeiros 100 chars): {html_content[:100]}...')
        
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
        # Remove caracteres null que causam erro "source code string cannot contain null bytes"
        html_content_clean = (html_content
                             .replace('\x00', '')  # Remove null bytes
                             .replace('\r', '')    # Remove carriage returns
                             .strip())             # Remove espaços extras
        
        # Escape mais robusto para JavaScript - evita problemas com innerHTML
        html_escaped = (html_content_clean
                       .replace('\\', '\\\\')      # Escape backslashes primeiro
                       .replace('`', '\\`')        # Escape backticks (template literals)
                       .replace('$', '\\$')        # Escape dollar signs (template literals)
                       .replace('"', '\\"')        # Escape aspas duplas
                       .replace('\n', '\\n')       # Escape quebras de linha
                       .replace('\t', '\\t'))      # Escape tabs
        
        # Escape do marcador de forma similar
        marcador_escaped = (marcador
                           .replace('\\', '\\\\')
                           .replace('`', '\\`')
                           .replace('$', '\\$')
                           .replace('"', '\\"')
                           .replace('\n', '\\n'))

        # DEPURAÇÃO REAL - verificar HTML antes da execução
        html_antes = driver.execute_script("return arguments[0].innerHTML;", editable)
        texto_antes = driver.execute_script("return arguments[0].innerText || arguments[0].textContent || '';", editable)
        print(f"[DEBUG] HTML ANTES: {html_antes}")
        print(f"[DEBUG] TEXTO ANTES: {texto_antes}")
        print(f"[DEBUG] Contém marcador '--' no HTML? {('--' in html_antes)}")
        print(f"[DEBUG] Contém marcador '--' no TEXTO? {('--' in texto_antes)}")
        
        # IMPLEMENTAÇÃO EXATA DO HISTÓRICO QUE FUNCIONAVA
        script_ckeditor = f"""
        console.log('[EDITOR] === USANDO API CKEDITOR ===');
        
        let editor = arguments[0];
        let htmlContent = arguments[1];
        let marcador = arguments[2];
        
        try {{
            // 1. Tentar encontrar a instância do CKEditor
            let ckInstance = null;
            
            // Método 1: Via elemento pai
            if (editor.ckeditorInstance) {{
                ckInstance = editor.ckeditorInstance;
                console.log('[EDITOR] ✓ CKEditor via ckeditorInstance');
            }}
            
            // Método 2: Via global CKEDITOR
            if (!ckInstance && window.CKEDITOR) {{
                for (let instanceName in window.CKEDITOR.instances) {{
                    let instance = window.CKEDITOR.instances[instanceName];
                    if (instance.element && instance.element.$ === editor) {{
                        ckInstance = instance;
                        console.log('[EDITOR] ✓ CKEditor via CKEDITOR.instances');
                        break;
                    }}
                }}
            }}
            
            // Método 3: Via CKEditor 5 (novo)
            if (!ckInstance) {{
                let ckEditor = editor.closest('.ck-editor');
                if (ckEditor && ckEditor.ckeditorInstance) {{
                    ckInstance = ckEditor.ckeditorInstance;
                    console.log('[EDITOR] ✓ CKEditor 5 via closest');
                }}
            }}
            
            if (ckInstance) {{
                console.log('[EDITOR] Usando API CKEditor');
                let htmlOriginal = ckInstance.getData();
                console.log('[EDITOR] HTML via getData:', htmlOriginal.substring(0, 100));
                
                if (htmlOriginal.includes(marcador)) {{
                    let novoHtml = htmlOriginal.replace(marcador, htmlContent);
                    ckInstance.setData(novoHtml);
                    console.log('[EDITOR] ✓ setData() executado');
                    return {{ sucesso: true, metodo: 'ckeditor_api' }};
                }} else {{
                    console.error('[EDITOR] Marcador não encontrado via API');
                }}
            }} else {{
                console.log('[EDITOR] CKEditor API não encontrada, usando DOM direto');
                
                // Fallback: DOM direto com foco
                editor.focus();
                
                let htmlOriginal = editor.innerHTML;
                if (htmlOriginal.includes(marcador)) {{
                    let novoHtml = htmlOriginal.replace(marcador, htmlContent);
                    editor.innerHTML = novoHtml;
                    
                    // Forçar eventos de mudança
                    editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    editor.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    editor.dispatchEvent(new Event('keyup', {{ bubbles: true }}));
                    
                    // Forçar blur/focus para CKEditor detectar
                    editor.blur();
                    setTimeout(() => editor.focus(), 10);
                    
                    console.log('[EDITOR] ✓ DOM direto + eventos');
                    return {{ sucesso: true, metodo: 'dom_direto_com_eventos' }};
                }}
            }}
            
            return {{ sucesso: false, erro: 'Nenhum método funcionou' }};
            
        }} catch (e) {{
            console.error('[EDITOR] Erro:', e);
            return {{ sucesso: false, erro: e.message }};
        }}
        """
        
        # Executar o script com API do CKEditor
        resultado = driver.execute_script(script_ckeditor, editable, html_content, marcador)
        
        # DEPURAÇÃO REAL - verificar HTML depois da execução
        time.sleep(1)  # Aguardar processamento
        html_depois = driver.execute_script("return arguments[0].innerHTML;", editable)
        print(f"[DEBUG] HTML DEPOIS: {html_depois}")
        print(f"[DEBUG] HTML mudou? {html_antes != html_depois}")
        print(f"[DEBUG] Contém marcador depois? {('--' in html_depois)}")
        
        if debug:
            print(f"[EDITOR] Resultado do script: {resultado}")
        
        if resultado and resultado.get('sucesso'):
            if debug:
                print(f'[EDITOR] ✅ HTML inserido com sucesso via método: {resultado.get("metodo")}')
            
            # Aguardar processamento
            time.sleep(0.3)
            
            # Verificar se marcador foi removido (apenas para log)
            html_final = driver.execute_script("return arguments[0].innerHTML;", editable)
            marcador_removido = marcador not in html_final
            
            if debug:
                print(f'[EDITOR] Verificação final: marcador removido = {marcador_removido}')
            
            # Se o JavaScript retornou sucesso, confiar no resultado
            return True
        else:
            erro = resultado.get('erro', 'Erro desconhecido') if resultado else 'Script retornou None'
            if debug:
                print(f'[EDITOR] ❌ Falha na inserção: {erro}')
            return False
            
    except Exception as e:
        if debug:
            print(f'[EDITOR] ❌ Erro na função de inserção: {e}')
        return False


def _inserir_html_via_javascript(driver, editable, html_content: str, debug: bool = False) -> bool:
    """
    Fallback: insere HTML via JavaScript quando clipboard falha
    """
    try:
        script = """
        const editor = arguments[0];
        const htmlContent = arguments[1];
        
        // Obter seleção atual
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            
            // Criar elemento temporário para converter HTML
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = htmlContent;
            
            // Inserir cada nó do HTML
            const fragment = document.createDocumentFragment();
            while (tempDiv.firstChild) {
                fragment.appendChild(tempDiv.firstChild);
            }
            
            // Deletar conteúdo selecionado e inserir novo
            range.deleteContents();
            range.insertNode(fragment);
            
            // Posicionar cursor após inserção
            range.collapse(false);
            selection.removeAllRanges();
            selection.addRange(range);
            
            return true;
        }
        return false;
        """
        
        resultado = driver.execute_script(script, editable, html_content)
        if debug:
            print(f"[EDITOR] Inserção via JavaScript: {resultado}")
        return bool(resultado)
        
    except Exception as e:
        if debug:
            print(f"[EDITOR] Erro na inserção via JavaScript: {e}")
        return False


def inserir_no_editor_apos_marcador(driver, texto: str, marcador: str = "--", modo: str = "replace", debug: bool = False) -> bool:
    """
    Insere 'texto' no CKEditor no ponto do marcador '--', com digitação humana.
    - modo 'replace': substitui o marcador
    - modo 'after': insere imediatamente após o marcador
    Retorna True se verificado no innerText.
    """
    try:
        editable = _get_editable(driver, debug)

        # Foco e rolagem
        driver.execute_script('arguments[0].scrollIntoView({block:"center"});', editable)
        time.sleep(0.2)
        try:
            editable.click()
        except Exception:
            driver.execute_script('arguments[0].focus();', editable)
        time.sleep(0.1)

        if not _place_selection_at_marker(driver, editable, marcador=marcador, modo=modo, debug=debug):
            if debug:
                print("[EDITOR] Marcador não encontrado; tentativa de fallback: inserir ao final")
            # posiciona no fim como fallback
            driver.execute_script("""
                const el = arguments[0];
                const sel = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(el);
                range.collapse(false);
                sel.removeAllRanges();
                sel.addRange(range);
            """, editable)

        # Digitar texto como humano
        active = driver.switch_to.active_element
        for part in str(texto).split('\n'):
            if part:
                active.send_keys(part)
            active.send_keys(Keys.ENTER) if '\n' in texto else None

        _dispatch_sync(driver, editable, debug)
        time.sleep(0.2)

        # Verificação
        inner_text = driver.execute_script('return arguments[0].innerText;', editable) or ''
        ok = str(texto).split('\n')[0][:10] in inner_text
        if debug:
            print(f"[EDITOR] Verificação pós-inserção contém prefixo? {ok}")
        return ok
    except Exception as e:
        if debug:
            print(f"[EDITOR] Erro na inserção: {e}")
        return False


def _iter_clipboard_records(raw: str):
    """
    Itera sobre registros do clipboard em dois formatos suportados:
    - Formato antigo (com TIPO/TIMESTAMP):
      ======
      PROCESSO: <proc>
      TIPO: <tipo>
      TIMESTAMP: ...
      ======
      <conteudo>
      ======
    - Formato novo (simplificado, sem TIPO/TIMESTAMP):
      ======
      PROCESSO: <proc>
      ======
      <conteudo>
      ======

    Retorna tuplas na ordem de aparição: (proc, tipo|None, conteudo)
    """
    records = []
    # Antigo
    pat_old = re.compile(
        r"=+\s*\n"  # linha de ==== 
        r"PROCESSO:\s*(?P<proc>[^\n]+)\n"
        r"TIPO:\s*(?P<tipo>[^\n]+)\n"
        r"TIMESTAMP:[^\n]*\n"
        r"=+\s*\n"
        r"(?P<conteudo>[\s\S]*?)\n"
        r"=+",
        re.MULTILINE,
    )
    for m in pat_old.finditer(raw):
        records.append((m.start(), m.group('proc').strip(), m.group('tipo').strip(), (m.group('conteudo') or '').strip()))
    # Novo
    pat_new = re.compile(
        r"=+\s*\n"  # linha de ==== 
        r"PROCESSO:\s*(?P<proc>[^\n]+)\n"
        r"=+\s*\n"
        r"(?P<conteudo>[\s\S]*?)\n"
        r"=+",
        re.MULTILINE,
    )
    for m in pat_new.finditer(raw):
        records.append((m.start(), m.group('proc').strip(), None, (m.group('conteudo') or '').strip()))
    # Ordena por posição de início no arquivo e produz na sequência
    records.sort(key=lambda t: t[0])
    for _, proc, tipo, conteudo in records:
        yield proc, tipo, conteudo


def obter_ultimo_conteudo_clipboard(numero_processo: Optional[str], tipo_regex: Optional[str] = None, debug: bool = False) -> Optional[str]:
    try:
        with open('clipboard.txt', 'r', encoding='utf-8') as f:
            data = f.read()
    except FileNotFoundError:
        if debug:
            print('[CLIPBOARD] Arquivo clipboard.txt não encontrado')
        return None
    # Coleta todos os registros e percorre de trás pra frente
    registros = list(_iter_clipboard_records(data))
    for proc, tipo, conteudo in reversed(registros):
        if numero_processo and proc != numero_processo:
            continue
        if tipo_regex:
            if tipo is not None:
                if not re.search(tipo_regex, tipo or ""):
                    continue
            else:
                # Sem tipo (formato novo). Para manter segurança, usa heurística:
                # quando solicitado link_ato_*_validacao, exige que o conteúdo pareça um link de validação.
                if 'link_ato' in tipo_regex:
                    if not re.search(r"https?://[^\s]*validacao[^\s]*", conteudo or "", re.IGNORECASE):
                        continue
        if conteudo:
            if debug:
                print(f"[CLIPBOARD] Conteúdo encontrado (tipo: {tipo}) com {len(conteudo)} chars")
            return conteudo
    if debug:
        print('[CLIPBOARD] Nenhum conteúdo correspondente encontrado')
    return None


def inserir_link_ato_validacao(driver, numero_processo: Optional[str] = None, modo: str = 'after', debug: bool = False) -> bool:
    """
    Recupera do clipboard.txt o último link de validação de ato para o processo
    (TIPO correspondente a regex: link_ato_.*_validacao) e insere no editor no marcador '--'.
    """
    # Extrair preferencialmente o CNJ da página; se não vier, tentar URL; por fim, sem filtro
    def _extrair_cnj_da_pagina():
        try:
            cnj_regex = r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}"
            body_text = driver.execute_script('return document.body ? document.body.innerText : "";') or ''
            m = re.search(cnj_regex, body_text)
            if m:
                return m.group(0)
        except Exception:
            pass
        return None

    cnj = _extrair_cnj_da_pagina()
    url_id = None
    if not numero_processo:
        try:
            from anexos import extrair_numero_processo_da_url
            url_id = extrair_numero_processo_da_url(driver)
        except Exception:
            url_id = None

    if debug:
        print(f"[EDITOR] Inserção de link de ato | CNJ: {cnj} | URL_ID: {url_id}")

    conteudo = None
    if cnj:
        conteudo = obter_ultimo_conteudo_clipboard(cnj, tipo_regex=r"^link_ato_.*_validacao$", debug=debug)
    if not conteudo and (numero_processo or url_id):
        conteudo = obter_ultimo_conteudo_clipboard(numero_processo or url_id, tipo_regex=r"^link_ato_.*_validacao$", debug=debug)
    if not conteudo:
        # Fallback: pega o último do tipo, independente do processo
        conteudo = obter_ultimo_conteudo_clipboard(None, tipo_regex=r"^link_ato_.*_validacao$", debug=debug)
    if not conteudo:
        if debug:
            print('[EDITOR] Nenhum link de validação encontrado no clipboard')
        return False
    return inserir_no_editor_apos_marcador(driver, conteudo, marcador='--', modo=modo, debug=debug)
