#!/usr/bin/env python3
"""Build pjetools.user.js - Concatenate modules"""

import os

metadata = """// ==UserScript==
// @name         PJe Tools Pro
// @namespace    http://tampermonkey.net/
// @version      1.0.0
// @description  Suite de ferramentas para PJe (Lista + Atalhos + Infojud)
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/*
// @grant        unsafeWindow
// ==/UserScript==

"""

modules = [
    'core/utils.js',
    'core/state.js',
    'modules/lista/lista.timeline.js',
    'modules/lista/lista.check.js',
    'modules/lista/lista.edital.js',
    'modules/lista/lista.sibajud.js',
    'modules/lista/lista.sigilo.js',
    'modules/atalhos/atalhos.js',
    'modules/atalhos/atalhos.worker.js',
    'modules/infojud/infojud.js',
    'modules/infojud/infojud.ui.js',
    'ui/painel.js',
    'orchestrator.js',
]

out = 'pjetools.user.js'
content = metadata

for mod in modules:
    path = os.path.join(os.path.dirname(__file__), mod)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content += f"\n// ── {mod} ──────────────────────────────────────\n"
            content += f.read()
            content += "\n"

# Write output to root
with open(out, 'w', encoding='utf-8') as f:
    f.write(content)

size = os.path.getsize(out) / 1024
print(f"OK build: {out} ({size:.1f} KB)")
