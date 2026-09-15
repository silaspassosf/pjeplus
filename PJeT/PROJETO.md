# PJeT — Extensão Firefox  
## Projeto de Transformação: `pjetools.user.js` + `hcalc.user.js` → Firefox Extension

> **Status:** Esqueleto criado · Implementação pendente  
> **Localização:** `d:\PjePlus\PJeT\`  
> **Destino:** Extensão Firefox sem publicação na loja (distribuição via `.xpi`)

---

## 1. Por que migrar de Userscript para Extensão

| Aspecto | Userscript (Tampermonkey) | Extensão Firefox |
|---|---|---|
| Distribuição | Depende de Tampermonkey instalado | Arquivo `.xpi` — basta instalar |
| Permissões | Limitadas ao sandbox | `storage`, `scripting`, `tabs` nativos |
| Service Worker | ❌ | ✅ Background persistente |
| CSP / pdf.js | Workarounds com `@require` externo | Vendor local sem restrições CSP |
| Seleção de módulos | Comentar `@require` manualmente | UI popup com checkboxes |
| Atualização | GitHub raw URL | Bundle local versionado |
| Compartilhamento | Requer Tampermonkey | Envia `.xpi` e instala |

---

## 2. Como instalar PERMANENTEMENTE sem publicar na loja

### 2.1 Instalação Temporária (testes rápidos)

> Dura até fechar o Firefox. Não requer assinatura.

```
1. about:debugging  →  "Este Firefox"
2. "Carregar extensão temporária..."
3. Selecionar  d:\PjePlus\PJeT\src\manifest.json
```

### 2.2 Instalação Permanente — Firefox Developer Edition

> Permanece após reiniciar. Requer Firefox Developer Edition (gratuito).

```
1. Baixar: https://www.mozilla.org/pt-BR/firefox/developer/

2. about:config  →  xpinstall.signatures.required  →  false

3. Empacotar a extensão:
   d:\PjePlus\PJeT\tools\build.ps1
   → gera  d:\PjePlus\PJeT\dist\pjet-1.0.0.xpi

4. Arrastar pjet-1.0.0.xpi para dentro do Firefox
   OU: Menu → Complementos → ⚙ → "Instalar de arquivo"
   
5. Extensão fica PERMANENTE (sobrevive reinicializações)
```

### 2.3 Instalação Permanente — Qualquer Firefox (assinatura gratuita)

> Gera `.xpi` assinado pela Mozilla. Funciona em qualquer Firefox normal.
> Não aparece na loja pública (`--channel=unlisted`).

```
1. Conta gratuita em: addons.mozilla.org
2. npm install --global web-ext
3. API key em: addons.mozilla.org/developers/addon/api/key/

4. cd d:\PjePlus\PJeT\src
   web-ext sign --api-key=<KEY> --api-secret=<SECRET> --channel=unlisted

5. Resultado: dist/pjet-X.X.X.xpi  (assinado, distribuível)
6. Qualquer pessoa instala sem alterar configurações do Firefox
```

### 2.4 Distribuindo para outras pessoas

```
Opção A (simples):
  Firefox Dev Edition + xpinstall.signatures.required=false
  → Enviar o .xpi + instrução de instalar

Opção B (elegante, recomendada a médio prazo):
  Assinar via addons.mozilla.org --channel=unlisted
  → .xpi funciona em qualquer Firefox
  → Não aparece na loja pública
```

---

## 3. Arquitetura da Extensão

```
PJeT/src/
├── manifest.json               ← MV3: permissões, content scripts, popup
│
├── background/
│   └── background.js           ← Service Worker: mensagens, storage, fetch cross-origin
│
├── content/
│   └── loader.js               ← Orquestrador (≈ pjetools.user.js):
│                                  roteamento SPA, carregamento condicional,
│                                  monitor pushState
│
├── popup/
│   ├── popup.html              ← Interface de ativação de módulos (checkboxes)
│   ├── popup.js                ← Lê/escreve browser.storage.sync
│   └── popup.css
│
├── options/
│   ├── options.html            ← Configurações avançadas por módulo
│   ├── options.js
│   └── options.css
│
├── core/                       ← Infraestrutura compartilhada
│   ├── utils.js                ← Script/core/utils.js
│   ├── state.js                ← Script/core/state.js (CleanupRegistry, AsyncRunner, PJeState)
│   └── extrair.js              ← Script/core/extrair.js + EXT.MD (pjeExtrair, pjeExtrairApi)
│
├── ui/
│   └── painel.js               ← Script/ui/painel.js (criarPainel, botões flutuantes)
│
├── modules/
│   ├── lista/
│   │   ├── lista.check.js      ← Relatório de medidas (penhora, SISBAJUD)
│   │   ├── lista.edital.js     ← Relatório de editais
│   │   └── lista.pgto.js       ← Controle de pagamento
│   │
│   ├── atalhos/
│   │   ├── atalhos.js          ← Atalhos de teclado contextuais
│   │   └── atalhos.worker.js   ← BroadcastChannel worker
│   │
│   ├── infojud/
│   │   └── infojud.js          ← Worker InfoJud (/minutas) + e-CAC Receita
│   │
│   ├── sisbajud/
│   │   ├── core.js             ← API e lógica base
│   │   ├── relatorios.js       ← Geração de relatórios
│   │   ├── sisbajud.js         ← UI e fluxo principal
│   │   └── sisbpje.js          ← Integração PJe ↔ SISBAJUD
│   │
│   ├── simba/
│   │   └── simba.js            ← Preenchimento SIMBA + BCB
│   │
│   ├── debito/
│   │   └── registrar_debito.js ← Registro de obrigação de pagar
│   │
│   ├── argos/
│   │   └── argos.js            ← Assistente ARGOS (mandados)
│   │
│   ├── aud/
│   │   └── Aud.js              ← Módulo audiências (65KB)
│   │
│   ├── alvara/
│   │   ├── extracao_siscondj.js
│   │   └── siscon_consulta.js
│   │
│   └── hcalc/                  ← hcalc.user.js completo
│       ├── hcalc-core.js       ← Inicialização e boot (6KB)
│       ├── hcalc-pdf.js        ← Extração de PDF (38KB)
│       ├── hcalc-prep.js       ← Pré-processamento (57KB)
│       └── BASE/
│           ├── hcalc-overlay.js            ← UI principal (132KB)
│           ├── hcalc-overlay-draft.js      ← Seção minuta (26KB)
│           ├── hcalc-overlay-depositos.js  ← Depósitos (16KB)
│           ├── hcalc-overlay-responsabilidades.js (28KB)
│           ├── hcalc-overlay-partes.js     ← Partes (23KB)
│           └── hcalc-overlay-decisao.js    ← Análise decisão (68KB)
│
├── vendor/
│   ├── pdfjs/
│   │   ├── pdf.min.js          ← Copiar de calc/BASE/pdf.min.js
│   │   └── pdf.worker.min.js   ← Copiar de calc/BASE/pdf.worker.min.js
│   └── tesseract/
│       └── tesseract.min.js    ← CDN → local
│
└── icons/
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

---

## 4. Mapeamento Completo dos Módulos

### 4.1 pjetools.user.js — todos os módulos

| Módulo | Origem | URLs ativas |
|---|---|---|
| Core / Utils | `core/utils.js` | Todas |
| State / Cleanup | `core/state.js` | PJe |
| Extrair (DOM+API) | `core/extrair.js` + `EXT.MD` | PJe |
| Lista Check | `modules/lista/lista.check.js` | `/detalhe` |
| Lista Edital | `modules/lista/lista.edital.js` | `/detalhe` |
| Lista Pgto | `modules/lista/lista.pgto.js` | `/detalhe` |
| Atalhos | `modules/atalhos/atalhos.js` | `/detalhe` |
| Atalhos Worker | `modules/atalhos/atalhos.worker.js` | `/detalhe` |
| Painel UI | `ui/painel.js` | `/detalhe` |
| InfoJud | `modules/infojud/infojud.js` | `/minutas` + Receita |
| SISBAJUD Core | `modules/sisbajud/core.js` | PJe |
| SISBAJUD Relatórios | `modules/sisbajud/relatorios.js` | PJe |
| SISBAJUD Main | `modules/sisbajud/sisbajud.js` | PJe |
| SISBpje | `modules/sisbajud/sisbpje.js` | PJe |
| SIMBA | `modules/simba/simba.js` | PJe + BCB + SIMBA |
| Débito | `modules/debito/registrar_debito.js` | `/obrigacao-pagar` |
| ARGOS | `modules/argos/argos.js` | `/detalhe` |
| AUD | `modules/aud/Aud.js` | `/aud/` |
| Álvara Siscondj | `modules/alvara/extracao_siscondj.js` | PJe |
| Álvara Siscon | `modules/alvara/siscon_consulta.js` | PJe |

### 4.2 hcalc.user.js — todos os módulos

| Módulo | Origem | Papel |
|---|---|---|
| HCalc Core | `calc/BASE/hcalc-core.js` | Boot e inicialização |
| HCalc PDF | `calc/BASE/hcalc-pdf.js` | Leitura e extração de PDF |
| HCalc Prep | `calc/BASE/hcalc-prep.js` | Pré-processamento cálculos |
| Overlay Main | `calc/BASE/hcalc-overlay.js` | UI principal (botão + orquestra) |
| Overlay Draft | `calc/BASE/hcalc-overlay-draft.js` | Seção minuta/despacho |
| Overlay Depósitos | `calc/BASE/hcalc-overlay-depositos.js` | Seção depósitos |
| Overlay Resp. | `calc/BASE/hcalc-overlay-responsabilidades.js` | Responsabilidades |
| Overlay Partes | `calc/BASE/hcalc-overlay-partes.js` | Partes do processo |
| Overlay Decisão | `calc/BASE/hcalc-overlay-decisao.js` | Análise da decisão |

---

## 5. Sistema de Seleção de Módulos (Popup)

```
┌─────────────────────────────────────┐
│  🔧 PJeT — Gerenciar Módulos        │
├─────────────────────────────────────┤
│  PJe /detalhe                       │
│  ☑ Lista Check      ☑ Atalhos       │
│  ☑ Lista Edital     ☑ Painel UI     │
│  ☑ ARGOS            ☑ Débito        │
│  ☑ SISBAJUD         ☑ SIMBA         │
│  ☑ Álvara                           │
├─────────────────────────────────────┤
│  PJe /minutas                       │
│  ☑ InfoJud                          │
├─────────────────────────────────────┤
│  Homologação de Cálculos            │
│  ☑ HCalc (completo)                 │
├─────────────────────────────────────┤
│  Externos                           │
│  ☑ SIMBA/BCB    ☑ Receita/InfoJud   │
├─────────────────────────────────────┤
│          [💾 Salvar]                │
└─────────────────────────────────────┘
```

Preferências salvas em `browser.storage.sync` (sincroniza entre dispositivos do mesmo usuário Firefox). O `loader.js` lê as preferências a cada carregamento e só injeta os módulos habilitados.

---

## 6. Adaptações Técnicas Obrigatórias

### 6.1 GM_* → browser.* equivalentes

| Userscript | Extensão |
|---|---|
| `GM_setValue(k, v)` | `browser.storage.sync.set({[k]: v})` |
| `GM_getValue(k, def)` | `(await browser.storage.sync.get(k))[k] ?? def` |
| `GM_deleteValue(k)` | `browser.storage.sync.remove(k)` |
| `GM_openInTab(url)` | `browser.tabs.create({url})` |
| `GM_xmlhttpRequest(...)` | `fetch()` direto ou via background |
| `unsafeWindow` | `window.wrappedJSObject` (Firefox content scripts) |

### 6.2 pdf.js Worker — referência local

```js
// ANTES (userscript):
pdfjsLib.GlobalWorkerOptions.workerSrc =
  'https://cdnjs.cloudflare.com/.../pdf.worker.min.js';

// DEPOIS (extensão):
pdfjsLib.GlobalWorkerOptions.workerSrc =
  browser.runtime.getURL('vendor/pdfjs/pdf.worker.min.js');
```

O worker já está declarado como `web_accessible_resource` no manifest.

### 6.3 Expor window.xyz para a página (contexto isolado)

Content scripts MV3 rodam em sandbox isolado. Para expor funções ao `window` da página:

```js
// Método 1 — wrappedJSObject (Firefox only, mais simples):
window.wrappedJSObject.hcalcInitBotao = exportFunction(fn, window);

// Método 2 — Injeção via <script> (mais portável):
const s = document.createElement('script');
s.textContent = `window.hcalcInitBotao = ${fn.toString()};`;
document.documentElement.appendChild(s);
s.remove();
```

### 6.4 SPA Monitor (pushState)

O `monitorarSPA` atual (patching de `history.pushState`) funciona igual em content scripts. Nenhuma mudança necessária.

---

## 7. Fluxo de Carregamento (loader.js)

```
Página carrega
    │
    ▼
content/loader.js (injetado pelo manifest)
    │
    ├── Lê: browser.storage.sync.get('pjet_modulos')
    │
    ├── Detecta URL:
    │   ├── /detalhe        → módulos detalhe (se habilitados)
    │   ├── /minutas        → InfoJud (se habilitado)
    │   ├── /obrigacao-pagar→ Débito (se habilitado)
    │   ├── /aud/           → AUD (se habilitado)
    │   ├── receita.fazenda → InfoJud Parte 2
    │   ├── simba-novo.redejt → SIMBA
    │   └── bcb.gov.br      → SIMBA BCB
    │
    ├── Inicializa módulos em ordem:
    │   core → ui/painel → módulos funcionais
    │
    └── Registra monitor SPA
            └── A cada pushState: PJeState.dispose() + re-rotear
```

---

## 8. Roadmap de Implementação

### Fase 1 — Infraestrutura
- [ ] `icons/` — ícone 16, 48, 128px
- [ ] `background/background.js` — service worker base
- [ ] `popup/` — HTML + JS + CSS (seleção de módulos)
- [ ] `content/loader.js` — orquestrador completo
- [ ] Copiar vendors: `calc/BASE/pdf.min.js` → `vendor/pdfjs/`
- [ ] `tools/build.ps1` — empacota `.xpi`

### Fase 2 — Core
- [ ] `core/utils.js` (remover GM_*)
- [ ] `core/state.js` (sem alterações — já é puro JS)
- [ ] `core/extrair.js` (ajustar workerSrc)
- [ ] `ui/painel.js` (sem alterações significativas)

### Fase 3 — Módulos PJeTools (prioridade)
- [ ] `modules/lista/` (3 arquivos)
- [ ] `modules/atalhos/` (2 arquivos)
- [ ] `modules/sisbajud/` (4 arquivos)
- [ ] `modules/infojud/infojud.js`
- [ ] `modules/argos/argos.js`
- [ ] `modules/simba/simba.js`
- [ ] `modules/debito/registrar_debito.js`
- [ ] `modules/alvara/` (2 arquivos)
- [ ] `modules/aud/Aud.js`

### Fase 4 — HCalc
- [ ] `hcalc-core.js` — ajustar workerSrc
- [ ] `hcalc-pdf.js`, `hcalc-prep.js`
- [ ] `BASE/` — 5 overlays

### Fase 5 — Polimento e Distribuição
- [ ] `options/` — configurações avançadas por módulo
- [ ] Testes no Firefox Dev Edition
- [ ] `web-ext sign --channel=unlisted`
- [ ] Gerar `.xpi` distribuível final

---

## 9. Script de Build

```powershell
# tools/build.ps1
param([string]$version = "1.0.0")

$src  = "$PSScriptRoot\..\src"
$dist = "$PSScriptRoot\..\dist"
$out  = "$dist\pjet-$version.xpi"

if (!(Test-Path $dist)) { New-Item -ItemType Directory $dist | Out-Null }

$tmp = "$dist\pjet-$version.zip"
Compress-Archive -Path "$src\*" -DestinationPath $tmp -Force
if (Test-Path $out) { Remove-Item $out }
Rename-Item $tmp $out

Write-Host "Gerado: $out"
Write-Host "Instale arrastando para o Firefox Dev Edition (about:addons)"
```

---

## 10. Notas Críticas

> [!IMPORTANT]
> O maior desafio técnico é o **contexto isolado** dos content scripts MV3.
> Funções em `window.xyz` precisam de `window.wrappedJSObject` ou injeção via `<script>`.

> [!NOTE]
> O `pdf.worker.min.js` deve ficar em `vendor/pdfjs/` e ser referenciado via
> `browser.runtime.getURL(...)`. Já está configurado no manifest como `web_accessible_resource`.

> [!TIP]
> Comece pela Fase 1 + um único módulo simples (ex: `lista.check.js`) para validar
> o pipeline completo antes de portar todos os módulos.
