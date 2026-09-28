#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aud_server.py - PJeTools Aud Standalone
========================================
Serve a interface Aud como app local e injeta HTML no Chrome via Playwright CDP.

Requisitos: pip install playwright flask
            playwright install chromium  (só na 1ª vez)

Uso: py aud_server.py
     (ou via aud.bat)
"""

import sys, os, json, time, threading, webbrowser, subprocess
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory

# ── Playwright ────────────────────────────────────────────────
try:
    from playwright.sync_api import sync_playwright, Error as PWError
except ImportError:
    print("ERRO: instale playwright com:  pip install playwright && playwright install chromium")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────
PORT          = 7823
CDP_PORT      = 9222
CDP_URL       = f"http://localhost:{CDP_PORT}"
BASE_DIR      = Path(__file__).parent
UI_FILE       = BASE_DIR / "aud_ui.html"

# Caminhos comuns do Chrome no Windows
CHROME_PATHS  = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]

app = Flask(__name__, static_folder=str(BASE_DIR))

# ── Estado global do Playwright ───────────────────────────────
_pw_state = {"browser": None, "context": None, "lock": threading.Lock()}

def _get_browser():
    """Conecta (ou reconecta) ao Chrome via CDP."""
    with _pw_state["lock"]:
        if _pw_state["browser"] and _pw_state["browser"].is_connected():
            return _pw_state["browser"]
        pw = sync_playwright().start()
        try:
            browser = pw.chromium.connect_over_cdp(CDP_URL)
            _pw_state["browser"] = browser
            return browser
        except Exception as e:
            raise RuntimeError(
                f"Não foi possível conectar ao Chrome em {CDP_URL}.\n"
                f"Certifique-se de que o Chrome está aberto com --remote-debugging-port={CDP_PORT}\n"
                f"Detalhe: {e}"
            )

def _find_pje_page(browser):
    """Encontra a aba do PJe que contém '/aud' na URL."""
    for ctx in browser.contexts:
        for page in ctx.pages:
            try:
                url = page.url
                if "/aud" in url:
                    return page
            except Exception:
                pass
    # Se não achou /aud, retorna a aba ativa (última)
    for ctx in browser.contexts:
        pages = ctx.pages
        if pages:
            return pages[-1]
    return None

def _inject_html(html_content):
    """Injeta HTML no editor do PJe na aba ativa."""
    browser = _get_browser()
    page    = _find_pje_page(browser)
    if not page:
        raise RuntimeError("Nenhuma aba encontrada no Chrome.")

    # Script de injeção — igual ao Aud.js original
    script = r"""
    (function(htmlContent) {
        // Tenta encontrar o editor CKEditor ou textarea do PJe
        function injetarNoPJe(html) {
            // 1. CKEditor (mais comum no PJe)
            if (window.CKEDITOR) {
                for (var name in CKEDITOR.instances) {
                    try {
                        var inst = CKEDITOR.instances[name];
                        if (inst && inst.editable && inst.editable()) {
                            inst.insertHtml(html);
                            return 'ckeditor:' + name;
                        }
                    } catch(e) {}
                }
            }
            // 2. iframe contenteditable
            var iframes = document.querySelectorAll('iframe');
            for (var i = 0; i < iframes.length; i++) {
                try {
                    var doc = iframes[i].contentDocument || iframes[i].contentWindow.document;
                    var ed = doc.querySelector('[contenteditable="true"]');
                    if (ed) {
                        ed.focus();
                        document.execCommand('insertHTML', false, html);
                        return 'iframe-contenteditable';
                    }
                } catch(e) {}
            }
            // 3. contenteditable direto
            var ce = document.querySelector('[contenteditable="true"]');
            if (ce) {
                ce.focus();
                document.execCommand('insertHTML', false, html);
                return 'contenteditable';
            }
            // 4. textarea
            var ta = document.querySelector('textarea');
            if (ta) {
                var pos = ta.selectionStart || ta.value.length;
                ta.value = ta.value.substring(0, pos) + html + ta.value.substring(pos);
                ta.dispatchEvent(new Event('input', {bubbles: true}));
                return 'textarea';
            }
            throw new Error('Nenhum editor encontrado na página.');
        }
        return injetarNoPJe(htmlContent);
    })(arguments[0]);
    """

    result = page.evaluate(script, html_content)
    return result


# ── Rotas Flask ───────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR), "aud_ui.html")

@app.route("/inject", methods=["POST"])
def inject():
    """Recebe HTML da UI e injeta no Chrome."""
    data = request.get_json(force=True)
    html = data.get("html", "")
    if not html:
        return jsonify({"ok": False, "error": "HTML vazio"}), 400
    try:
        result = _inject_html(html)
        return jsonify({"ok": True, "editor": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/status")
def status():
    """Verifica conexão com o Chrome."""
    try:
        browser = _get_browser()
        pages = []
        for ctx in browser.contexts:
            for p in ctx.pages:
                try:
                    pages.append({"url": p.url, "title": p.title()})
                except Exception:
                    pass
        return jsonify({"ok": True, "pages": pages, "cdp": CDP_URL})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/cep/<cep>")
def buscar_cep(cep):
    """Proxy para busca de CEP (evita CORS)."""
    import urllib.request
    cep_num = "".join(c for c in cep if c.isdigit())
    if len(cep_num) != 8:
        return jsonify({"error": "CEP inválido"}), 400
    try:
        url = f"https://viacep.com.br/ws/{cep_num}/json/"
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read().decode())
        if data.get("erro"):
            return jsonify({"error": "CEP não encontrado"}), 404
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Inicialização ─────────────────────────────────────────────

def _open_ui():
    time.sleep(1.2)
    webbrowser.open(f"http://localhost:{PORT}")

def _find_chrome():
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p
    return None

def _check_chrome_cdp():
    """Verifica se Chrome já está com CDP ativo."""
    import urllib.request
    try:
        urllib.request.urlopen(f"{CDP_URL}/json", timeout=2)
        return True
    except Exception:
        return False

def _launch_chrome():
    chrome = _find_chrome()
    if not chrome:
        print("Chrome não encontrado nos caminhos padrão.")
        print("Abra o Chrome manualmente com:")
        print(f'  chrome.exe --remote-debugging-port={CDP_PORT}')
        return False
    args = [
        chrome,
        f"--remote-debugging-port={CDP_PORT}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    subprocess.Popen(args)
    print(f"Chrome iniciado com --remote-debugging-port={CDP_PORT}")
    time.sleep(2)
    return True

if __name__ == "__main__":
    print(f"\n{'='*55}")
    print("  PJeTools - Aud Standalone  (Playwright + Flask)")
    print(f"{'='*55}")

    # Verifica/inicia Chrome com CDP
    if _check_chrome_cdp():
        print(f"✓ Chrome já conectado em {CDP_URL}")
    else:
        print(f"Chrome não detectado em {CDP_URL}. Iniciando...")
        _launch_chrome()
        if not _check_chrome_cdp():
            print("\nAVISO: Chrome não respondeu. Abra-o manualmente com:")
            print(f"  chrome.exe --remote-debugging-port={CDP_PORT}")

    # Abre a UI no browser padrão
    threading.Thread(target=_open_ui, daemon=True).start()

    print(f"\n→ Interface: http://localhost:{PORT}")
    print(f"→ Status:    http://localhost:{PORT}/status")
    print("\nPressione Ctrl+C para encerrar.\n")

    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
