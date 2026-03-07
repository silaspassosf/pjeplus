#!/usr/bin/env python3
"""Build hcalc.user.js - Concatenate hcalc modules locally"""

import os

def detect_encoding(filepath):
    """Detecta encoding do arquivo pelo BOM (UTF-16 LE, UTF-8 BOM, ou UTF-8)."""
    with open(filepath, 'rb') as f:
        bom = f.read(4)
    if bom[:2] == b'\xff\xfe':
        return 'utf-16-le'
    if bom[:2] == b'\xfe\xff':
        return 'utf-16-be'
    if bom[:3] == b'\xef\xbb\xbf':
        return 'utf-8-sig'
    return 'utf-8'

# Headers and modules
metadata = """// ==UserScript==
// @name         Homologação de Cálculos
// @namespace    http://tampermonkey.net/
// @version      1.17.0
// @description  Assistente de homologação PJe-Calc
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @connect      cdnjs.cloudflare.com
// @run-at       document-idle
// @grant        unsafeWindow
// ==/UserScript==

"""

modules = [
    'lib.js',
    'hcalc-core.js',
    'hcalc-pdf.js',
    'hcalc-overlay.js',
    'hcalc.js',
]

# Output na raiz de Script (pasta pai)
out = os.path.join(os.path.dirname(__file__), '..', 'hcalc.user.js')
content = metadata

for mod in modules:
    path = os.path.join(os.path.dirname(__file__), mod)
    if os.path.exists(path):
        enc = detect_encoding(path)
        with open(path, 'r', encoding=enc) as f:
            content += f"\n// ── {mod} ──────────────────────────────────\n"
            txt = f.read()
            # Remove BOM residual se presente
            if txt and txt[0] == '\ufeff':
                txt = txt[1:]
            content += txt
            content += "\n"

# Write output na raiz de Script
with open(out, 'w', encoding='utf-8') as f:
    f.write(content)

size = os.path.getsize(out) / 1024
print(f"OK build: hcalc.user.js ({size:.1f} KB)")
