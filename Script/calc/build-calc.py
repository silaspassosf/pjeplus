#!/usr/bin/env python3
"""Build hcalc.user.js - Concatenate hcalc modules locally"""

import os

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
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content += f"\n// ── {mod} ──────────────────────────────────\n"
            content += f.read()
            content += "\n"

# Write output na raiz de Script
with open(out, 'w', encoding='utf-8') as f:
    f.write(content)

size = os.path.getsize(out) / 1024
print(f"OK build: hcalc.user.js ({size:.1f} KB)")
