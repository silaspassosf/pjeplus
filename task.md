# Migração hcalc-prep.js: DOM → API (v2 — Aprovada)

## Objetivo

Substituir `hcalc-prep.js` por uma versão que usa as APIs REST do `pje-comum-api` (já mapeadas e validadas em `calcapi.js`) em vez de manipular o DOM da timeline.  
O contrato de saída — o objeto `prepResult` — deve ser 100% compatível com o overlay.  
Além disso, adicionar na seção Decisões do overlay os dados da **conferência de acórdão** (CTPS, FGTS, exclusão de reclamadas, rearbitramento de custas) lidos via `_conferirAcordao()`.

---

## Progresso

- Slice 1: Adicionados `API helpers` mínimos (`_idProcesso`, `_montarHref`, `_normData`) — concluído.
- Slice 2: `executarPrep` agora delega para `window.calcApi.prep()` quando disponível e adapta o resultado ao `prepResult` do overlay — concluído.
- Remoção de logs de agente locais (`fetch('http://127.0.0.1:7803/...')`) do `hcalc-prep.js` — concluído.

Próximo: adaptar e validar `depositos`/`anexos` (classificação via `classificarAnexo`) e integrar `conferenciaAcordao` no `prepResult` (slice 3).

-- Slice 3: `depositos` anexos classificados e `conferenciaAcordao` normalizada — concluído.

 - ESLint: rodei `npx eslint Script/calc/BASE/hcalc-prep.js` (com config mínima). Resultado inicial: **71 warnings, 0 errors** — a maioria referia-se a globals de browser (`window`, `document`, `console`). Adicionei declarações de globals no `eslint.config.cjs` e reexecutei o ESLint: agora não há avisos relevantes para `hcalc-prep.js`.
 - ESLint: rodei `npx eslint Script/calc/BASE/hcalc-prep.js` (com config mínima). Resultado inicial: **71 warnings, 0 errors** — a maioria referia-se a globals de browser (`window`, `document`, `console`). Adicionei declarações de globals no `eslint.config.cjs` e reexecutei o ESLint: agora não há avisos relevantes para `hcalc-prep.js`.

- Slice 4: Iteração em `depositos`/`editais`/`anexos` — concluído. Ajustes:
  - `depositos` da API: normalizei `data` com `_normData()` e garanti `anexos[].id` como `string|null`.
  - `depositos` da varredura DOM: removi referências DOM em `anexos` (agora `{texto,id,tipo,ordem}`) para evitar vazamento de elementos.
  - Ordenação de depósitos permanece por data (mais antigos primeiro).
 - Slice 5: Integração `conferenciaAcordao` — concluído. Ajustes:
   - Adicionei o card `Conferência Pós-Acórdão` no overlay (`conferencia-acordao-container`).
   - Preencho o card com `prep.conferenciaAcordao` logo após `executarPrep()` retornar; mostro indicadores visuais para status, despacho e análise (CTPS/FGTS/exclusões/rearbitramento).


## Análise: O que o `hcalc-prep.js` Atual Faz

### Fluxo de `executarPrep(partesData, peritosConhecimento)`

```
executarPrep(partesData, peritosConhecimento)
  │
  ├─ ETAPA 1: varrerTimeline()          ← DOM: querySelectorAll('li.tl-item-container')
  │     Classifica itens em: sentencas, acordaos, editais, recursosPassivo, honAjJt
  │
  ├─ ETAPA 1.5: filtrar recursos + extrairAnexosDoItem()
  │     ← DOM: expand toggle click + sleep + querySelectorAll('.pje-timeline-anexos li')
  │
  ├─ ETAPA 2: buscarAjJtPeritos()
  │     ← DOM: abrirDocumentoInline (click) + lerHtmlOriginal (polling #previewModeloDocumento)
  │
  ├─ ETAPA 3: Sentença
  │     ← DOM: abrirDocumentoInlineViaHref (click) + lerHtmlOriginal + fecharViewer
  │     → extrairDadosSentenca(texto)   ← puro regex, sem DOM
  │
  └─ ETAPA 4: buscarPartesEdital()
        ← DOM: abrirDocumentoInlineViaHref + lerHtmlOriginal + fecharViewer
```

### Shape do `prepResult` retornado (contrato com o overlay)

```js
{
  sentenca: {
    data: 'dd/mm/aaaa',
    href: 'https://...',           // ← usado por destacarElementoNaTimeline()
    custas: '300,00' | null,
    hsusp: false,
    responsabilidade: 'subsidiaria' | 'solidaria' | null,
    honorariosPericiais: [{ valor, trt }]
  },
  pericia: {
    trteng: false,
    trtmed: false,
    peritosComAjJt: [{ nome, trt, idAjJt }]
  },
  acordaos: [{ data, href, id }],   // ← href usado por destacarElementoNaTimeline()
  depositos: [{
    tipo: 'RO' | 'RR',
    texto: '...',
    href: '...',                    // ← usado para click e destacar na timeline
    data: 'dd/mm/aaaa',
    depositante: '...',
    anexos: [{ texto, id, tipo, ordem }]
  }],
  editais: [{ data, href }],        // ← href usado para links de edital
  partesIntimadasEdital: ['Nome...']
}
```

---

## ✅ Confirmações Definitivas (pós-análise)

### 1. Formato de Data — 4 dígitos obrigatório

O prep DOM atual gera `"17/11/2025"` (4 dígitos). O overlay usa `prep.sentenca.data` diretamente em campos de formulário (`custas-data-origem`, `val-perito-data`, etc.). O `calcapi._normData()` atual usa 2 dígitos (`dd/mm/aa`). **Ajuste obrigatório no novo prep:**

```js
// CORRETO — 4 dígitos de ano
function _normData(s) {
    const m = s.match(/(\d{4})-(\d{2})-(\d{2})/);
    return m ? `${m[3]}/${m[2]}/${m[1]}` : s;  // dd/mm/AAAA
}
```

### 2. Anexos via API — padrão confirmado (lista.check.js)

Confirmado em `lista.check.js` linhas 93-108 **e** `coleta.py` linhas 270-272 e 417-420: os anexos de cada item da timeline já vêm no JSON da API no campo `item.anexos[]`. **Nenhum click, nenhum toggle, nenhum sleep.** A lógica no novo prep é:

```js
// item = resultado de _fetchTimeline() já classificado
const anexosApi = Array.isArray(item.anexos) ? item.anexos : [];
for (const anexo of anexosApi) {
    const titulo = anexo.titulo || anexo.nomeDocumento || '';
    const uid = anexo.idUnicoDocumento || null;
    const idDoc = anexo.id ? Number(anexo.id) : null;
    const { tipo, ordem } = classificarAnexo(titulo);  // Depósito/Custas/Garantia/Anexo
    // ... montar objeto compatível com prepResult.depositos[].anexos[]
}
```

### 3. href — Manter Geração Sintética

O overlay usa `href` em **8 call sites** confirmados via `Select-String`:
- `destacarElementoNaTimeline(prep.sentenca.href)` — clique do usuário no link da sentença
- `destacarElementoNaTimeline(acordao.href)` — clique nos links de acórdão  
- `dep.href` para `destacarElementoNaTimeline` e `encontrarItemTimeline` — clique nos cards de depósito
- `edital.href` — `<a href="edital.href">` link direto

Como `destacarElementoNaTimeline` e `encontrarItemTimeline` fazem `document.querySelector(`a[href="${href}"]`)`, o href sintético **deve corresponder exatamente** ao href DOM:

```js
function _montarHref(uid) {
    if (!uid) return null;
    return `${location.origin}/pjekz/processo/${_idProcesso()}/detalhe?documentoId=${uid}`;
}
```

> ⚠️ **Isso precisa ser validado em campo no console:** clicar em um link da timeline, inspecionar `a.tl-documento[target="_blank"].href` e confirmar que o padrão é `/pjekz/processo/{id}/detalhe?documentoId={uid}`. Se o padrão for diferente, ajustar `_montarHref`.

### 4. Funções DOM de UI — Mantidas

`destacarElementoNaTimeline`, `encontrarItemTimeline` e `expandirAnexos` são acionadas **apenas por clique do usuário** após o overlay já estar montado e os dados carregados. Dependência de DOM legítima e mantida.

### 5. AbortController — Simplificado

Sem polling de DOM, o AbortController perde a função principal. O novo prep pode manter uma flag simples `window.hcalcPrepRunning` para evitar execução dupla, sem AbortController complexo.

### 6. Logs de Agente — Removidos

Os blocos `#region agent log` com `fetch('http://127.0.0.1:7803/...')` serão removidos.

### 7. Partes (`partesData`) — Sem Mudança

O overlay já passa `partesData` formado via API. O novo prep usa esse parâmetro diretamente (como hoje) sem rebuscar.

---

## Análise: O que o `calcapi.js` (`_prep()`) Produz

O `_prep()` de `calcapi.js` já tem toda a lógica equivalente, mas produz um shape ligeiramente diferente. Comparação:

| Campo `prepResult` | Shape atual (`hcalc-prep.js`) | Shape `calcapi._prep()` | Ajuste necessário |
|---|---|---|---|
| `sentenca.data` | `'dd/mm/aaaa'` | `'dd/mm/aa'` (2 dígitos ano) | normalizar para 4 dígitos |
| `sentenca.href` | URL DOM completa | **não existe** (usa `idDoc`) | gerar via `uid` ou manter null |
| `sentenca.custas` | string | igual | ✅ compatível |
| `sentenca.hsusp` | bool | igual | ✅ compatível |
| `sentenca.responsabilidade` | string\|null | igual | ✅ compatível |
| `sentenca.honorariosPericiais` | `[{valor,trt}]` | igual | ✅ compatível |
| `pericia.trteng/trtmed` | bool | **no sentença** flat | mover para `pericia` |
| `pericia.peritosComAjJt` | `[{nome,trt,idAjJt}]` | `peritos` flat | renomear |
| `acordaos[].href` | URL DOM | **não existe** | gerar ou manter null |
| `acordaos[].id` | uid 7hex | `idDoc` integer | adaptar |
| `depositos[].href` | URL DOM | **não existe** | gerar ou manter null |
| `depositos[].texto` | textContent | `titulo` | usar `titulo` |
| `depositos[].anexos[].texto` | textContent | `titulo` | usar `titulo` |
| `depositos[].anexos[].id` | uid 7hex | `idDoc` integer | adaptar |
| `depositos[].anexos[].tipo` | 'Depósito'\|'Custas'\|... | precisa classificar | aplicar `classificarAnexo()` |
| `editais[].href` | URL DOM | **não existe** | gerar ou manter null |
| `partesIntimadasEdital` | string[] | igual | ✅ compatível |

---

## Estratégia de Implementação

### Abordagem: Substituição Total + Adaptador de Compatibilidade + Seção Nova no Overlay

O novo `hcalc-prep.js` vai:

1. **Importar toda a lógica de `calcapi.js`** de forma interna (sem `window.calcApi`) — ou seja, copiar/referenciar os mesmos helpers (`_fetchPartes`, `_fetchTimeline`, `_classifyItem`, `_fetchDocHtml`, `_extrairDadosSentenca`, `_lerPeritosAjJt`, `_lerPartesEdital`, `_detectarPoloPassivo`)
2. **Produzir um `prepResult` com exatamente o mesmo shape** que o overlay consome
3. **Continuar expondo `window.executarPrep`** com a mesma assinatura `(partesData, peritosConhecimento) => Promise<prepResult>`
4. **Manter as funções utilitárias DOM** que o overlay ainda precisa: `destacarElementoNaTimeline`, `encontrarItemTimeline`, `expandirAnexos` — pois essas são usadas diretamente pelo overlay para UI (scroll + highlight + expandir anexos)

### O Que Some (DOM eliminado)

| Função DOM | Eliminada? | Razão |
|---|---|---|
| `varrerTimeline()` | ✅ SIM | substituída por `_fetchTimeline()` + `_classifyItem()` |
| `abrirDocumentoInline()` | ✅ SIM | substituída por `_fetchDocHtml(idDoc)` |
| `lerHtmlOriginal()` | ✅ SIM | substituída por E4/E5 REST |
| `fecharViewer()` | ✅ SIM | não existe mais viewer aberto |
| `extrairAnexosDoItem()` | ✅ SIM | `item.anexos[]` vem direto da API |
| `expandirAnexos()` | ❌ MANTIDA | usada pelo overlay para UI |
| `destacarElementoNaTimeline()` | ❌ MANTIDA | usada pelo overlay para UI |
| `encontrarItemTimeline()` | ❌ MANTIDA | usada pelo overlay para UI |
| `safeDispatch()` | ❌ MANTIDA | usada pelas funções UI acima |
| `sleep()` no prep | ✅ SIM | não há mais click/polling |
| AbortController no prep | ✅ SIM (simplificado) | sem operações DOM assíncronas |

### O Que Permanece (lógica pura)

- `normalizeText()` / `normalizarDataTimeline()`
- `extrairDadosSentenca(texto)` — regex pura (idêntica)
- `classificarAnexo(texto)` — para mapear `titulo` da API para `tipo` (Depósito/Custas/Garantia/Anexo)
- Ordenação de depósitos por data

---

## Mudanças Detalhadas em `hcalc-prep.js`

### [MODIFY] [hcalc-prep.js](file:///d:/PjePlus/Script/calc/BASE/hcalc-prep.js)

#### Seção 1 — Novo Helpers de API (copiar de calcapi.js)

Adicionar internamente no IIFE:
- `_xsrf()` — lê cookie XSRF
- `_headers()` — monta headers com XSRF
- `_idProcesso()` — extrai ID do processo da URL
- `_base()` — URL base do processo
- `_normData(s)` — ISO → `dd/mm/aaaa` (4 dígitos!)
- `_get(url)` — fetch JSON com XSRF
- `_getRaw(url)` — fetch raw (PDF/HTML)
- `_stripHtml(html)` — strip tags
- `_pdfToText(buffer)` — extrair texto de PDF (ja existe em calcapi.js)
- `_fetchDocConteudo(idDoc)` — E4/E5
- `_fetchDocHtml(idDoc)` — E5 + PDF fallback
- `_fetchPartes()` — E1
- `_fetchTimeline()` — E2
- `_classifyItem(item)` — classificação por título
- `_detectarPoloPassivo(item, passivo)` — cruzar titulo com passivo

#### Seção 2 — Novo `executarPrep` (orquestrador API)

```js
async function executarPrep(partesData, peritosConhecimento) {
  // 1. Partes via API (ou usar partesData se já disponível)
  // 2. Timeline via API
  // 3. Classificar itens
  // 4. Sentença: _fetchDocHtml + extrairDadosSentenca
  // 5. AJ-JT: _fetchDocHtml para cada + match perito
  // 6. Depósitos: filtrar RO/RR + classificarAnexo nos .anexos[]
  // 7. Editais: _fetchDocHtml + cruzar com passivo
  // 8. Montar prepResult com shape 100% compatível
}
```

#### Seção 3 — Compatibilidade de Saída (Adaptador)

O shape de saída terá:

```js
const prepResult = {
  sentenca: {
    data: ...,         // 'dd/mm/aaaa' 4 dígitos
    href: _montarHref(sentencaAlvo.uid),  // sintético via uid
    custas: ...,
    hsusp: ...,
    responsabilidade: ...,
    honorariosPericiais: [...]
  },
  pericia: {
    trteng: ...,       // extraído de _extrairDadosSentenca
    trtmed: ...,
    peritosComAjJt: [{ nome, trt, idAjJt }]
  },
  acordaos: [{
    data: ...,
    href: _montarHref(a.uid),
    id: a.uid          // manter campo 'id' como uid para compatibilidade com overlay
  }],
  depositos: [{
    tipo: rec.categoria,   // 'RO' | 'RR'
    texto: rec.titulo,
    href: _montarHref(rec.uid),
    data: rec.data,
    depositante: ...,
    anexos: rec.anexos.map(ax => ({
      texto: ax.titulo,
      id: ax.uid || String(ax.idDoc),
      tipo: classificarAnexo(ax.titulo).tipo,
      ordem: classificarAnexo(ax.titulo).ordem,
    }))
  }],
  editais: [{
    data: ...,
    href: _montarHref(e.uid)
  }],
  partesIntimadasEdital: [...]
};
```

#### Seção 4 — Manter Exports DOM-UI

Ao final do IIFE, manter expostos:
```js
window.executarPrep = executarPrep;
window.destacarElementoNaTimeline = destacarElementoNaTimeline;
window.encontrarItemTimeline = encontrarItemTimeline;
window.expandirAnexos = expandirAnexos;
```

---


## NOVO: Seção "Conferência de Acórdão" no Overlay

### 5.1 — O que `_conferirAcordao()` já retorna

O `calcapi._prep()` já chama `_conferirAcordao()` e retorna em `conferenciaAcordao`:

```js
{
  ok: true,
  lastAcordao: { data, idDoc, uid, titulo },
  despacho: { data, idDoc, uid, titulo },
  analise: {
    mantidaSentenca: bool,        // sentença mantida
    exclusaoReclamadas: ['Nome'], // reclamadas excluídas do acórdão
    rearbitramentoCustas: bool,   // custas rearbitradas
    ctpsAnotacao: bool,           // CTPS mencionada no despacho pós-acórdão
    fgtsDeposito: bool,           // FGTS mencionado no despacho
  }
}
```

### 5.2 — Onde exibir no Overlay

Na seção **"Dados Copiados"** (que aparece primeiro no overlay, antes de Decisões), adicionar um **card colapsável** chamado **"Conferência de Acórdão"** que exibe esses dados como informação de apoio, sem mudar o comportamento do overlay.

A exibição deve ser simples — apenas indicadores visuais:

```
[✅/❌] Sentença mantida no acórdão
[✅/❌] CTPS — anotação/retificação
[✅/❌] FGTS — depósito/recolhimento  
[✅/❌] Rearbitramento de custas
[lista] Reclamadas excluídas: Nome1, Nome2  (ou "nenhuma")
[info] Despacho pós-acórdão: dd/mm/aaaa
```

### 5.3 — Como carregar

No novo `executarPrep`, a `conferenciaAcordao` vem de `_conferirAcordao()` que já está implementado em `calcapi.js`. Será incorporado internamente ao novo `hcalc-prep.js`. O `prepResult` ganha um novo campo:

```js
prepResult.conferenciaAcordao = {
    ok: bool,
    despacho: { data, uid },
    analise: {
        mantidaSentenca, exclusaoReclamadas,
        rearbitramentoCustas, ctpsAnotacao, fgtsDeposito
    }
};
```

### 5.4 — Onde no overlay

Após o bloco `link-sentenca-acordao-container` (que já exibe links de sentença/acórdão/depósitos), adicionar:

```html
<div id="conferencia-acordao-container" class="hidden">
  <label style="font-weight:bold; color:#5b21b6;">Conferência Pós-Acórdão:</label>
  <div id="conferencia-acordao-body"></div>
</div>
```

Preenchido via JS no handler do `btn-abrir-homologacao` após o `prep` retornar.

---

## Novas Especificações de Funcionalidades

---

### A. Editais → Intimação Automática por Parte

**Situação atual:** `hcalc-prep.js` preenche `prepResult.partesIntimadasEdital` (string[] com nomes). Em `hcalc-overlay-partes.js` linha 115, já existe:
```js
else if (partesIntimadasEdital.includes(parte.nome)) modoDefault = 'edital';
```
**Isso já funciona!** A única mudança necessária é no `prep`: editais **não precisam mais ser abertos ou destacados** — a API já retorna os itens classificados como `edital`. O `buscarPartesEdital()` lê o HTML do edital via `_fetchDocHtml(edital.idDoc)` e cruza com o passivo para montar a lista. O resultado é exatamente `partesIntimadasEdital`.

**Mudança no overlay:** Remover ou não exibir mais links clicáveis de editais como "abrir edital" — apenas exibir como informação: _"Editais detectados: parte intimada por edital → [Nome1, Nome2]"_. O `#links-editais-container` pode ser mantido mas simplificado para exibição de texto, sem href.

**Arquivos:** `hcalc-prep.js` (sem mudança na saída), `hcalc-overlay.js` (simplificar bloco de editais linhas 1293–1312).

---

### B. Default de Honorários Adv. Réu — Condição Suspensiva + 5%

**Situação atual (confirmada via Select-String):**
- `chk-hon-reu` → `checked` (= "Não há Hon. Adv. Réu" marcado → campos ocultos)
- `chk-hon-reu-suspensiva` → `checked`
- `rad-hon-reu-tipo` → `value="percentual"` checked
- `val-hon-reu-perc` → `value="5%"`

**O padrão já está correto:** condição suspensiva + 5% é o default. O que está errado é que o checkbox `chk-hon-reu` vem **marcado** (= "Não há"), então os campos ficam ocultos e o usuário precisa desmarcar manualmente para ver que o padrão real é suspensiva + 5%.

**Mudança desejada:** Inverter o default → `chk-hon-reu` vem **desmarcado** por padrão, expondo os campos com `suspensiva + 5%` já preenchidos. O usuário marca "Não há" apenas quando quiser suprimir os honorários.

**Arquivo:** `hcalc-overlay.js` — linha ~607: remover `checked` do `chk-hon-reu`.

> ⚠️ O handler da REGRA 6 (linha 1427) que verifica `prep.sentenca.hsusp` para decidir se mostra/oculta os campos precisa ser revisado para o novo default — se `hsusp=false`, o estado padrão agora seria **mostrado** (não oculto), invertendo a lógica atual.

---

### C. Responsabilidades de Reclamadas Extras — Compatibilidade Confirmada

**Escopo correto (esclarecido):** Responsabilidades extras definem:
1. O bloco de responsabilidade da decisão (subsidiariária/solidária por extra)
2. Os blocos de período diverso quando a reclamada extra tem planilha diferente

As **intimações** são uma seção totalmente separada — usam os mesmos dados da API de partes inicial (`partesData`) + informação de advogado por parte (já via API, `hcalcStatusAdvogados`) + `partesIntimadasEdital` (do prep). O `construirSecaoIntimacoes()` em `hcalc-overlay-partes.js` já consome tudo isso corretamente — **sem mudança necessária**.

**Compatibilidade com Draft:** ✅ Cada box de extra chama `queueOverlayDraftSave()` em todos os eventos. Totalmente compatível.

**Compatibilidade com geração de decisão:** ✅ `gerarTextoResponsabilidades()` monta `subsidiariasComPeriodo[]` lendo os boxes extras. O decisao.js consome para gerar parágrafos de período diverso. **Cadeia está funcionando.**

**Único ponto crítico:** Com período "diverso", o box precisa do `dataset.idPlanilha`. Hoje vem de upload de PDF. Com item D (extru00e7ão por ID), esse campo é preenchido automaticamente pelo retorno de `pjeExtrairApi`.

---

### D. Extração de Planilha por ID de Documento — Pipeline + OCR

#### Status do OCR

**`extrair.js`:** Não tem OCR implementado. Quando o PDF é imagem, retorna apenas `{ aviso: 'PDF sem texto extraível (possivelmente escaneado/imagem)' }` — apenas avisa.

**`coleta.py` (Triagem):** Tem OCR via `PyMuPDF` + `pytesseract` (Tesseract local). O padrão é:
```
fetch /conteudo → pdfplumber extrai texto
  ├─ media >= 200 chars/pag → texto nativo ✅
  └─ media < 200 (imagem) → _ocr_via_pymupdf() → pytesseract → texto
```
`pytesseract` + `fitz` são dependências Python nativas. **Não há equivalente nativo em JS sem biblioteca externa.** Tesseract.js existe mas é pesado e requer worker.

**Decisão para OCR em JS:**
- PDF textível → `_apiExtrairTextoPdf()` via pdf.js nativo do PJe → **sem dependência extra**
- PDF imagem → **fallback para upload de arquivo** (caminho atual, já funciona)
- OCR nativo em JS (Tesseract.js) → fora do escopo, pode ser adicionado futuramente se necessário

O threshold do `coleta.py` de **200 chars/página** será replicado no JS para detectar automaticamente se o texto extraído via pdf.js é insuficiente e acionar fallback.

#### Nova Interface — Botão Dual-Mode

**Botão atual:** `📄 Carregar Planilha` → aciona `document.getElementById('input-planilha-pdf').click()` diretamente.

**Nova interface:** O botão principal se transforma em um **painel expandido** com duas opções ao clicar:

```
[ 📄 Carregar Planilha ▾ ]
    ↓ expande:
┌─────────────────────────────────────────────┐
│ 🔑 UID do documento: [_________] [OK ⇒]    │
│ 📁 ou: [Selecionar arquivo PDF]              │
└─────────────────────────────────────────────┘
```

- **[OK ⇒]**: chama `pjeExtrairApi(uid)` → tenta API → se falhar (PDF imagem) → expande botão de upload
- **[Selecionar arquivo PDF]**: comportamento atual (caminho de fallback sempre visível)
- O `input#input-planilha-pdf` **permanece** mas fica dentro desse painel em vez de acessado diretamente

A **mesma interface** se aplica nos boxes de extras em `hcalc-overlay-responsabilidades.js`: `btn-extra-carregar-${idx}` ganha o campo de UID ao lado.

#### Pipeline completo da extração por UID

```js
async function carregarPlanilhaPorUid(uid) {
    const r = await window.pjeExtrairApi(uid, { idProcesso: _idProcesso() });
    if (!r.sucesso) { mostrarErro(r.erro); return null; }
    
    const texto = r.conteudo_bruto || r.conteudo || '';
    const LIMIAR = 200; // chars/pag (mesmo threshold do coleta.py)
    const paginas = texto.split('--- PÁGINA ---').length;
    const media = texto.length / Math.max(paginas, 1);
    
    if (media < LIMIAR && r.tipo !== 'api-html') {
        // PDF possivelmente escaneado — acionar fallback upload
        mostrarAvisoOcr();
        return null;
    }
    
    return processarPlanilhaPDF(texto); // extração de campos existente
}
```

**Arquivos modificados:**
- `hcalc-overlay.js` linhas ~87-247: substituir lógica do botão principal para painel dual-mode
- `hcalc-overlay-responsabilidades.js` linha ~146-198: adicionar campo UID ao lado do `btn-extra-carregar`
- `extrair.js`: **sem mudança**


---

## Arquivos Modificados (final consolidado)

| Arquivo | Tipo | Descrição |
|---|---|---|
| [hcalc-prep.js](file:///d:/PjePlus/Script/calc/BASE/hcalc-prep.js) | MODIFY | Substituição total DOM→API + `_conferirAcordao` + expor `hcalcFetchDocTexto` |
| [hcalc-overlay.js](file:///d:/PjePlus/Script/calc/BASE/hcalc-overlay.js) | MODIFY | Card conferência acórdão + default hon-reu + campo ID planilha principal + simplificar bloco editais |
| [hcalc-overlay-responsabilidades.js](file:///d:/PjePlus/Script/calc/BASE/hcalc-overlay-responsabilidades.js) | MODIFY | Trocar input file por input texto + botão Carregar por ID (planilha extras) |
| [hcalc.user.js](file:///d:/PjePlus/Script/hcalc.user.js) | MODIFY | Bump de versão e timestamp |

> ⚠️ `calcapi.js` **não é modificado** — era script standalone de teste. A lógica interna é portada para o `hcalc-prep.js`.

---

## Verificação Final

- `window.executarPrep({passivo: [...]}, [])` retorna `prepResult` com todos os campos
- `prep.sentenca.data` tem 4 dígitos de ano (`dd/mm/AAAA`)
- `prep.sentenca.href` gera URL sintética via `uid` → link clicável no overlay
- `prep.depositos[].anexos[].tipo` classifica corretamente via `item.anexos[]` da API
- `prep.partesIntimadasEdital` popula corretamente o select de intimação das partes
- `prep.conferenciaAcordao.analise` exibido no card do overlay
- `chk-hon-reu` desmarcado por padrão → campos de suspensiva + 5% visíveis
- Planilha principal e extras carregáveis por ID numérico do documento PJe
- Performance: sem DOM polling → prep completa em **< 5s**



# Tarefas — Migração hcalc-prep.js DOM → API

## Fase 1 — hcalc-prep.js (reescrita total)  `Script/calc/BASE/hcalc-prep.js`

**Status: ✅ concluído**

### Tarefa 1.1 — Internalisar helpers de API (portar de calcapi.js)

Substituir o bloco `// API HELPERS (Slice 1...)` atual pelos helpers completos:
- `_xsrf()`, `_headers(accept)` — XSRF e headers padrão
- `_base()` — URL base do processo
- `_normalize(str)` — alias interno (além do `normalizeText` existente)
- `_compactNormalize(str)`, `_windowAround(text, idx, before, after)`, `_cooccursInWindow(...)` — helpers de janela para análise de texto
- `_stripHtml(html)` — strip de tags
- `_get(url)` — fetch JSON com XSRF
- `_getRaw(url)` — fetch bruto (PDF/HTML)

**Manter já existentes:** `_idProcesso()` (versão atual OK), `_normData()` (versão 4 dígitos OK), `_montarHref(uid)` (OK).

**Aceite:** `typeof _xsrf === 'function' && typeof _get === 'function'` (verificável no console após carga)

### Tarefa 1.2 — Portar funções de coleta de dados (de calcapi.js)

- `_shapePartes(dados)` + `_fetchPartes()` — E1 Partes
- `_TIMELINE_URL` + `_fetchTimeline()` — E2 Timeline
- `_classifyItem(item)` → retorna `{categoria, uid, idDoc, titulo, tipo, data, polo, nomeParte, anexos[], _raw}` (sem DOM)
- `_fetchDocMeta(idDoc)` — E3
- `_fetchDocConteudo(idDoc)` — E4 (tenta /conteudo depois /html, retorna PDF buffer ou texto)
- `_pdfToText(arrayBuffer)` — extrai texto via pdf.js nativo do PJe ou CDN fallback
- `_fetchDocHtml(idDoc)` — E5 (wraps _fetchDocConteudo, resolve PDF se necessário)

**Aceite:** `typeof _fetchTimeline === 'function' && typeof _classifyItem === 'function'`

### Tarefa 1.3 — Portar funções de extração de conteúdo (de calcapi.js)

- `_extrairDadosSentenca(texto)` — substituir a função `extrairDadosSentenca` existente; a versão do calcapi.js tem a mesma lógica base **mais** os campos `ctpsAnotacao`/`fgtsDeposito` (mas esses não são usados no `prepResult` final — incluir mesmo assim para consistência futura)
- `_lerPeritosAjJt(ajJtItems, peritosConhecimento)` — substitui `buscarAjJtPeritos`; usa `_fetchDocHtml(item.idDoc)` em vez de DOM click
- `_lerPartesEdital(editais, passivo)` — substitui `buscarPartesEdital`; usa `_fetchDocHtml(edital.idDoc)` em vez de DOM click
- `_detectarPoloPassivo(itemRaw, passivo)` — detecta polo sem DOM; recebe `rec._raw`

**Remover (DOM eliminado):** `varrerTimeline`, `abrirDocumentoInline`, `abrirDocumentoInlineViaHref`, `lerHtmlOriginal`, `fecharViewer`, `extrairAnexosDoItem`, `buscarAjJtPeritos`, `buscarPartesEdital`, `getTimelineItems`, `extractDataFromItem`, `tipoDocumentoDoItem`, `tituloDocumentoDoItem`, `hasAnexoNoItem`, `isPoloPassivoNoItem`, `nomePassivoDoItem`, `hrefDoItem`, `textoDoItem`, `idDocumentoDoItem`, `normalizarDataTimeline`, `sleep` (top-level).

**Manter (usadas pelo overlay pós-carga):** `safeDispatch`, `encontrarItemTimeline`, `destacarElementoNaTimeline`, `expandirAnexos` (internalizar `sleep` dentro de `expandirAnexos`/`destacarElementoNaTimeline`).

**Aceite:** `typeof _extrairDadosSentenca === 'function' && typeof _lerPartesEdital === 'function'`

### Tarefa 1.4 — Portar `_conferirAcordao()` (de calcapi.js)

Portagem completa da função (linhas 481-714 de calcapi.js). Partes internas a portar:
- Subfunções locais: `isDespachoLike`, `isFirstInstance`, `readTextoFor`, `detectarExclusoes`
- Busca estrita por despacho pós-acórdão com frase "ante o retorno" (normalizada)
- Análise de CTPS/FGTS via `_cooccursInWindow`

**Aceite:** `typeof _conferirAcordao === 'function'`

### Tarefa 1.5 — Reescrever `executarPrep()` como orquestrador API puro

Substituir a função `executarPrep` atual (que ainda delega `window.calcApi` e tem fallback DOM) pelo orquestrador puro:

```
1. Partes: usar partesData.passivo se válido; senão _fetchPartes()
2. Timeline: _fetchTimeline() → items.map(_classifyItem)
3. Sentença: _fetchDocHtml(sentencaAlvo.idDoc) → _extrairDadosSentenca()
   (preferir pjeExtrairApi se disponível)
4. Peritos: _lerPeritosAjJt(honAjJt, peritosConhecimento)
5. Depósitos: filtrar RO/RR por polo passivo via _detectarPoloPassivo
   - oldestAcordaoIdx = items.indexOf(acordao mais antigo)
   - rec após acórdão (itemIdx < oldestAcordaoIdx) → incluir direto
   - rec antes do acórdão → exige polo === 'PASSIVO'
   - Mapear anexos via rec.anexos[] da API + classificarAnexo()
6. Editais: _lerPartesEdital(editais, passivo) → partesIntimadasEdital[]
7. Conferência: _conferirAcordao() (silencia erros)
8. Montar prepResult shape 100% compatível com overlay
```

**Remover:** `window.calcApi` delegation, AbortController (manter apenas flag `window.hcalcPrepRunning`).

**Shape de saída idêntico ao contrato do overlay** (+ campo `conferenciaAcordao`).

**Aceite:**
- `window.executarPrep({passivo:[{nome:'Teste'}]}, [])` retorna objeto sem lançar erro
- `prep.sentenca.data` formato `dd/mm/AAAA` (4 dígitos)
- `typeof window.destacarElementoNaTimeline === 'function'`
- `typeof window.expandirAnexos === 'function'`

---

## Fase 2 — hcalc-overlay.js  `Script/calc/BASE/hcalc-overlay.js`

**Status: ✅ concluído** (2.1 + 2.2 + 2.3)

### Tarefa 2.1 — Default `chk-hon-reu` + corrigir REGRA 6

**Arquivo:** `hcalc-overlay.js`

**Mudança A** (linha ~607): remover `checked` do checkbox `chk-hon-reu`:
```html
<!-- antes -->
<input type="checkbox" id="chk-hon-reu" checked ...>
<!-- depois -->
<input type="checkbox" id="chk-hon-reu" ...>
```

**Mudança B** (linhas ~1473-1476): o `else` da REGRA 6 força `chk-hon-reu` marcado quando `hsusp=false`, que conflita com o novo default. Remover o bloco `else`:
```js
// ANTES:
} else {
    if (chkHonReu) chkHonReu.checked = true;
    if (honReuCampos) honReuCampos.classList.add('hidden');
}
// DEPOIS: remover o else inteiro (default vem do HTML)
```

**Aceite:** ao abrir overlay sem prep, `chk-hon-reu` desmarcado e campos `hon-reu-campos` visíveis por padrão.

### Tarefa 2.2 — Simplificar bloco de editais (links → texto informativo)

**Arquivo:** `hcalc-overlay.js` linhas ~1329-1348

Substituir os links `<a href>` clicáveis por texto descritivo:
```js
// antes: cria <a href="edital.href">Edital N</a>
// depois: exibir texto apenas com data/indicação
editaisLista.innerHTML = prep.editais.map((e, i) =>
    `<span style="...">Edital ${i+1}${e.data ? ' ('+e.data+')' : ''}</span>`
).join(' | ');
```

Manter o container e a lógica de show/hide.

**Aceite:** Editais exibidos como texto sem links clicáveis.

### Tarefa 2.3 — Botão dual-mode (campo UID + fallback PDF)

**Arquivo:** `hcalc-overlay.js`

**HTML** (substituir botão simples por painel expandível, ~linhas 87-99):
```html
<div id="hcalc-floating-wrap">
  <button id="btn-abrir-homologacao" type="button">📄 Carregar Planilha ▾</button>
  <div id="hcalc-planilha-panel" style="display:none; ...">
    <div style="display:flex; gap:6px; align-items:center; margin-bottom:6px;">
      <input id="input-planilha-uid" type="text" placeholder="UID ou ID do documento" style="...">
      <button id="btn-planilha-uid-ok" type="button">OK ⇒</button>
    </div>
    <label style="font-size:11px; color:#6b7280;">ou: </label>
    <button id="btn-planilha-file" type="button" style="font-size:11px;">📁 Selecionar arquivo PDF</button>
  </div>
</div>
<input id="input-planilha-pdf" type="file" accept="application/pdf" style="display:none">
```

**JS** — toggle do painel ao clicar `btn-abrir-homologacao`; handler de `btn-planilha-uid-ok` chama `carregarPlanilhaPorUid()`; handler de `btn-planilha-file` chama `input-planilha-pdf.click()`.

**Função** `carregarPlanilhaPorUid(uid)`:
```js
async function carregarPlanilhaPorUid(uid) {
    if (!uid || !uid.trim()) return;
    if (typeof window.pjeExtrairApi !== 'function') { alert('pjeExtrairApi não disponível'); return; }
    const r = await window.pjeExtrairApi(uid.trim(), { idProcesso: _idProcesso() });
    if (!r.sucesso) { alert('Erro ao extrair: ' + (r.erro || 'desconhecido')); return; }
    const texto = r.conteudo_bruto || r.conteudo || '';
    const paginas = texto.split('--- PÁGINA ---').length;
    const media = texto.length / Math.max(paginas, 1);
    if (media < 200 && r.tipo !== 'api-html') {
        alert('PDF possivelmente escaneado. Use "Selecionar arquivo PDF".');
        return;
    }
    processarPlanilhaPDF(texto); // função existente
}
```

**Atenção:** verificar nome exato da função que processa o texto da planilha (pode ser diferente de `processarPlanilhaPDF`). Ajustar conforme encontrado.

**Aceite:** clicar em "Carregar Planilha ▾" expande painel; campo UID + botão OK visíveis; "Selecionar arquivo PDF" chama `input-planilha-pdf.click()`.

---

## Fase 3 — hcalc-overlay-responsabilidades.js  `Script/calc/BASE/hcalc-overlay-responsabilidades.js`

**Status: ✅ concluído** (3.1)

### Tarefa 3.1 — Campo UID nos extras de responsabilidades

**Arquivo:** `hcalc-overlay-responsabilidades.js`

Ao lado de cada `btn-extra-carregar-${idx}` (botão de carregar planilha do extra), adicionar:
```html
<input type="text" id="input-extra-uid-${idx}" placeholder="UID/ID" style="width:90px; font-size:11px; padding:2px 4px; border:1px solid #d1d5db; border-radius:4px;">
<button id="btn-extra-uid-${idx}" type="button" style="font-size:11px; padding:2px 6px;">API ⇒</button>
```

Handler de `btn-extra-uid-${idx}`: lê `input-extra-uid-${idx}.value`, chama `window.pjeExtrairApi(uid, {idProcesso})`, processa resultado da mesma forma que o upload de PDF para o extra `idx`.

**Aceite:** campo UID e botão "API ⇒" visíveis ao lado do botão de carregar planilha de cada extra.

---

## Fase 4 — hcalc.user.js

**Status: ✅ concluído** (4.1 @version 3.1.41)

### Tarefa 4.1 — Bump de versão

**Arquivo:** `Script/hcalc.user.js`

Atualizar `@version` e `@updateURL` timestamp para refletir a versão pós-migração.

**Aceite:** `@version` incrementado.

---

## Verificação Final

- [ ] `window.executarPrep({passivo:[{nome:'Teste Ltda'}]}, [])` retorna `prepResult` sem erro
- [ ] `prep.sentenca.data` tem 4 dígitos de ano (`dd/mm/AAAA`)
- [ ] `prep.sentenca.href` gera URL sintética via uid → link clicável na timeline
- [ ] `prep.partesIntimadasEdital` popula corretamente select de intimação
- [ ] `prep.conferenciaAcordao.analise` exibido no card do overlay
- [ ] `chk-hon-reu` desmarcado por padrão → campos hon-reu-campos visíveis
- [ ] Botão dual-mode expande painel; campo UID funcional
- [ ] Upload de PDF (fallback) permanece funcional via `btn-planilha-file`
- [ ] ESLint sem erros em `hcalc-prep.js`: `npx eslint Script/calc/BASE/hcalc-prep.js`
