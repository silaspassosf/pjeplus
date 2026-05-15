# CalcAPI — Mapeamento hcalc → API pura

**Versão:** 0.1 · **Data:** 2026-04-12  
**Objetivo:** Eliminar dependência de DOM no `hcalc-prep.js`, substituindo cada operação DOM por chamada REST ao `pje-comum-api`.  
**Arquivo de teste:** `Script/calcapi.js` (standalone Tampermonkey)

---

## 1. Endpoints Conhecidos

| # | Endpoint | Método | Autenticação | Retorno |
|---|---|---|---|---|
| E1 | `/pje-comum-api/api/processos/id/{id}/partes` | GET | XSRF cookie | `{ ATIVO[], PASSIVO[], TERCEIROS[] }` — partes com representantes/advogados |
| E2 | `/pje-comum-api/api/processos/id/{id}/timeline?buscarDocumentos=true&buscarMovimentos=false&somenteDocumentosAssinados=false` | GET | XSRF cookie | `Item[]` — ver campos abaixo |
| E3 | `/pje-comum-api/api/processos/id/{id}/documentos/id/{idDoc}` | GET | XSRF cookie | Metadados do documento (tipo, título, assinatura…) |
| E4 | `/pje-comum-api/api/processos/id/{id}/documentos/id/{idDoc}/conteudo` | GET | XSRF cookie | PDF (binary) ou HTML raw |
| E5 | `/pje-comum-api/api/processos/id/{id}/documentos/id/{idDoc}/html` | GET | XSRF cookie | HTML do documento (texto da decisão/edital/etc.) |
| E6 | `/pje-comum-api/api/processos/id/{id}/audiencias?status=M` | GET | XSRF cookie | Audiências marcadas (visto em aud_triagem) |

**Auth padrão:**
```js
headers: {
  'Accept': 'application/json',
  'Content-Type': 'application/json',
  'X-Grau-Instancia': '1',
  'X-XSRF-TOKEN': /* cookie XSRF-TOKEN decodificado */
}
credentials: 'include'
```

---

## 2. Campos do Item de Timeline (E2)

Campos confirmados via uso em `lista.check.js`, `erec.js` e `execapi.js`:

| Campo | Tipo | Descrição |
|---|---|---|
| `idUnicoDocumento` | string (7 hex) | UID do documento (aparece como `- abc1234` no link DOM) |
| `id` | integer | **ID numérico** usado nos endpoints E3/E4/E5 |
| `titulo` | string | Título legível: "Sentença", "Acórdão - RO", "Edital de Citação"… |
| `nomeDocumento` | string | Nome interno do tipo de documento |
| `descricao` | string | Descrição adicional (pode estar vazia) |
| `tipo` | string | Categoria interna PJe (ex: "SENTENÇA", "ACÓRDÃO", "RECURSO_ORDINARIO") — **a confirmar** |
| `data` | string ISO | Data do item (ex: `"2024-11-17T00:00:00"`) |
| `atualizadoEm` | string ISO | Data de atualização |
| `anexos` | `Anexo[]` | Sub-documentos: Serasa, CNIB, depósito em RO/RR |

Campos do `Anexo`:

| Campo | Tipo | Descrição |
|---|---|---|
| `idUnicoDocumento` | string | UID do anexo |
| `id` | integer | ID numérico do anexo (usa em E4/E5) |
| `titulo` | string | Ex: "Depósito Recursal", "CNIB", "Comprovante Serasa" |
| `nomeDocumento` | string | Nome interno |
| `data` / `atualizadoEm` | string ISO | Datas |

> **⚠ A CONFIRMAR via `calcApi.timeline()`:** campos `polo` (ATIVO/PASSIVO), `nomeParte`, quaisquer campos de classificação que evitem a leitura de `aria-label` DOM.

---

## 3. Mapeamento DOM → API por Função (hcalc-prep.js)

### 3.1 `varrerTimeline()` — Varredura de itens DOM

**Status:** 🟡 PARCIAL — classificação por `titulo` funciona; polo passivo incerto

| DOM (atual) | API (calcapi) | Observação |
|---|---|---|
| `document.querySelectorAll('li.tl-item-container')` | E2 `/timeline` | Substitui 100% a iteração de elementos |
| `tipoDocumentoDoItem()` → `aria-label` parse | `item.tipo` ou `item.titulo` | Confirmar se `tipo` retorna "SENTENÇA", "ACÓRDÃO", etc. |
| `tituloDocumentoDoItem()` → `aria-label` parse | `item.titulo` | Confirmar se cobre todos os casos |
| `textoDoItem()` → `a.tl-documento textContent` | `item.titulo + item.descricao` | OK |
| `extractDataFromItem()` → DOM sibling `.tl-data` | `item.data` ou `item.atualizadoEm` | OK — normalizar ISO→`dd/mm/yy` |
| `hrefDoItem()` → `a.tl-documento[target=_blank].href` | Não disponível diretamente | **GAP** — href é montado client-side; usar `item.id` para E4/E5 em vez de href |
| `idDocumentoDoItem()` → `span.ng-star-inserted` regex | `item.idUnicoDocumento` | OK |
| `hasAnexoNoItem()` → DOM paperclip icon | `item.anexos.length > 0` | OK |
| `isPoloPassivoNoItem()` → `.icone-polo-passivo` | campo `polo` ou `nomeParte`? | **A CONFIRMAR** |
| `nomePassivoDoItem()` → `aria-label div[name=tipoItemTimeline]` | campo `nomeParte`? | **A CONFIRMAR** — fallback: cruzar `titulo` com nomes do passivo (E1) |
| `extrairAnexosDoItem()` → expand DOM toggle + read | `item.anexos[]` diretamente | OK — elimina click + sleep |

**Classificação de categoria por `titulo` (implementado em calcapi.js):**
```
sentenca  → /sentença|sentenca/i no titulo
acordao   → /acórdão|acordao/i no titulo, excluindo "intima"  
RO        → /recurso ordinário|recurso ordinario/i no titulo/tipo
RA        → /recurso adesivo/i no titulo/tipo
RR        → /recurso de revista/i no titulo/tipo
edital    → /edital/i no titulo
hon_ajjt  → /periciai.*aj.*jt|pericia.*aj.*jt/i no titulo
outro     → não classificado
```

---

### 3.2 `lerHtmlOriginal()` — Abrir viewer e ler `#previewModeloDocumento`

**Status:** 🟢 SUBSTITUÍVEL — endpoint E5 retorna o HTML diretamente

| DOM (atual) | API (calcapi) |
|---|---|
| Click em `button[aria-label="Visualizar HTML original"]` | — eliminado |
| Polling `document.getElementById('previewModeloDocumento')` | — eliminado |
| `previewEl.innerText` | Resposta de E5 (`/html`), strip via `div.innerHTML` |
| `fecharViewer()` click | — eliminado |
| Depend: `idDoc` por `idDocumentoDoItem()` | `item.id` (integer) de E2 |

> ⚠ E5 retorna HTML bruto. Pode retornar JSON `{conteudo: "...", html: "..."}` em alguns tipos.  
> Confirmar via `calcApi.docHtml(idDoc)`.

---

### 3.3 `extrairDadosSentenca(texto)` — Regex no texto da sentença

**Status:** 🟢 SEM MUDANÇA — lógica pura de regex, não depende de DOM.  
Só muda a **origem do `texto`**: antes via `lerHtmlOriginal()`, depois via E5.

Campos extraídos:
- `custas` — valor das custas processuais
- `hsusp` — condição suspensiva
- `trteng` / `trtmed` — honorários periciais pagos pelo Tribunal
- `responsabilidade` — `'subsidiaria'` | `'solidaria'` | `null`
- `honorariosPericiais[]` — `{ valor, trt }`

---

### 3.4 `buscarAjJtPeritos()` — Abrir docs AJ-JT e buscar nome do perito

**Status:** 🟡 PARCIAL — pode usar E5 para ler o HTML do AJ-JT sem abrir viewer

| DOM (atual) | API (calcapi) |
|---|---|
| `abrirDocumentoInlineViaHref(ajjt.href)` | E5 com `ajjt.idDoc` (de E2) |
| `lerHtmlOriginal()` | E5 |
| `fecharViewer()` | — eliminado |
| Parse do texto para nome do perito | Mesmo regex — sem mudança |

> `idDoc` dos itens AJ-JT vem de `item.id` no E2 (campo `id` integer).

---

### 3.5 `buscarPartesEdital()` — Abrir editais e cruzar com passivo

**Status:** 🟡 PARCIAL — E5 elimina DOM; polo passivo vem de E1

| DOM (atual) | API (calcapi) |
|---|---|
| `abrirDocumentoInlineViaHref(edital.href)` | E5 com `edital.idDoc` |
| `lerHtmlOriginal()` | E5 |
| `fecharViewer()` | — eliminado |
| Cruzar nomes com `passivo` (já de E1) | Mesmo algoritmo |

---

### 3.6 `fetchPartesViaApi()` — Partes via API

**Status:** 🟢 JÁ API — sem mudança. Endpoint E1.  
Campos: `nome`, `documento` (CPF/CNPJ), `pessoaFisica` (telefones), `representantes[]`.

---

### 3.7 `extrairAnexosDoItem()` (depósito recursal)

**Status:** 🟢 SUBSTITUÍVEL — `item.anexos[]` de E2

| DOM (atual) | API (calcapi) |
|---|---|
| Click em toggle "mostrar anexos" | — eliminado |
| `querySelectorAll('.pje-timeline-anexos li')` | `item.anexos[]` |
| Ler texto de cada anexo | `anexo.titulo` / `anexo.nomeDocumento` |
| Sleep 500ms para DOM carregar | — eliminado |

---

## 4. Gaps Ainda Abertos

| # | Gap | Impacto | Sugestão |
|---|---|---|---|
| G1 | Campo `polo` (ATIVO/PASSIVO) no item de timeline | Detecção de recursos do passivo para depósitos | Cruzar `titulo` com nomes do passivo (E1). Testar se API retorna campo polo. |
| G2 | `href` do item (link de navegação) | `destacarElementoNaTimeline()` e click de abertura | Montar URL a partir de `idUnicoDocumento`:`/pjekz/processo/{id}/detalhe?documentoId={uid}` — testar |
| G3 | E5 para sentenças em PDF | Alguns documentos não têm HTML — retornam PDF binário | Usar pdf.js (já incluso no hcalc) para extrair texto de arraybuffer |
| G4 | Peritos no AJ-JT | Cruzar nome do perito no texto do AJ-JT via E5 | Provavelmente funciona; confirmar no teste |

---

## 5. Operações que NUNCA precisam de DOM

Estas funções já são puras/API e **não mudam**:
- `extrairDadosSentenca(texto)` — regex pura
- `normalizarDataTimeline()` / `_pjeTlNormData()` — string pura
- `normalizeText()` — string pura
- `shapePartesPayload()` — transform de objeto
- `_dateToTs()` — conversão de data
- Ordenação de depósitos por data

---

## 6. Plano de Testes — `calcApi.*`

### Fase 1 — Endpoints isolados (sem orquestração)

| Teste | Comando console | Verificar |
|---|---|---|
| T01 | `await calcApi.partes()` | Retorna `{ ativo, passivo, outros }` com nomes e advogados |
| T02 | `await calcApi.timeline()` | Array com 20+ itens; cada item tem `id`, `idUnicoDocumento`, `titulo`, `data` |
| T03 | `await calcApi.timelineClass()` | Itens classificados: sentença, acórdão, RO, edital detectados |
| T04 | `calcApi.timelineRaw()` | Console.table dos campos disponíveis para descoberta de `tipo`, `polo`, `nomeParte` |
| T05 | `await calcApi.docHtml(idDoc)` | Retorna texto legível ≥ 200 chars para sentença conhecida |
| T06 | `await calcApi.docMeta(idDoc)` | Retorna objeto com tipo, título, assinatura |
| T07 | `await calcApi.docConteudo(idDoc)` | Retorna `{ tipo: 'html' | 'pdf-buffer', conteudo }` |

### Fase 2 — Extração de dados

| Teste | Comando console | Verificar |
|---|---|---|
| T10 | `await calcApi.lerSentenca()` | Retorna `{ custas, hsusp, responsabilidade, honorariosPericiais }` |
| T11 | `await calcApi.lerEdital()` | Retorna array de nomes do passivo encontrados no texto |
| T12 | `await calcApi.lerAjJt()` | Retorna array de peritos encontrados |
| T13 | `await calcApi.depositos()` | Lista recursos com `tipo: 'RO'|'RR'`, `depositante`, `anexos[]` |

### Fase 3 — Orquestração completa

| Teste | Comando console | Verificar |
|---|---|---|
| T20 | `await calcApi.prep()` | Mesmo shape que `hcalcPrepResult` atual; sem click/sleep no log de rede |
| T21 | Comparar `calcApi.prep()` vs `hcalcPrepResult` | Valores de custas, datas, responsabilidade devem bater |
| T22 | Performance | `prep()` deve concluir em < 5s (vs ~10-15s com DOM click/sleep) |

### Fase 4 — Casos especiais

| Teste | Cenário | Verificar |
|---|---|---|
| T30 | Processo com múltiplas reclamadas | Polo correto em cada recurso? (G1) |
| T31 | Sentença em PDF (não HTML) | Fallback pdf.js funciona? (G3) |
| T32 | AJ-JT com perito de conhecimento | Nome extraído sem abrir viewer? (G4) |
| T33 | Processo sem acórdão | Classificação correta? Sem crash? |
| T34 | Processo com edital | Partes intimadas detectadas? (G5) |

---

## 7. Shape do Resultado `calcApi.prep()` (espelho de `hcalcPrepResult`)

```js
{
  idProcesso: '12345',
  partes: {
    ativo: [{ nome, cpfcnpj, telefone, representantes[] }],
    passivo: [{ nome, cpfcnpj, telefone, representantes[] }],
    outros: []
  },
  sentenca: {
    data: 'dd/mm/aa',
    idDoc: 12345,           // id integer da API (novo — antes: href DOM)
    uid: 'abc1234',         // idUnicoDocumento
    titulo: 'Sentença',
    custas: '300,00',
    hsusp: false,
    responsabilidade: 'subsidiaria' | 'solidaria' | null,
    honorariosPericiais: [{ valor, trt }],
    trteng: false,
    trtmed: false
  },
  acordaos: [{ data, idDoc, uid, titulo }],
  depositos: [{             // recursos do passivo com anexos
    tipo: 'RO' | 'RR',
    data: 'dd/mm/aa',
    idDoc: 12345,
    uid: 'abc1234',
    titulo: '...',
    depositante: 'Nome Reclamada',
    polo: 'PASSIVO',        // se disponível na API
    anexos: [{ titulo, idDoc, uid, data }]
  }],
  honAjJt: [{ data, idDoc, uid, titulo }],
  editais: [{ data, idDoc, uid, titulo }],
  partesIntimadasEdital: ['Nome Reclamada 1'],
  peritos: [{ nome, trt, idAjJt }],
  _meta: {
    durMs: 1234,            // tempo total da operação
    endpointsUsados: ['E1','E2','E5'],
    versao: '0.1'
  }
}
```

---

## 8. Migração Planejada para hcalc-prep.js

Depois de validar todos os testes acima:

1. **Substituir `varrerTimeline()`** por chamada a E2 + classificação por `titulo`
2. **Substituir `lerHtmlOriginal()`** por `_fetchDocHtml(idDoc)` — sem click/sleep
3. **Substituir `abrirDocumentoInlineViaHref()`** — eliminado
4. **Substituir `fecharViewer()`** — eliminado
5. **Substituir `extrairAnexosDoItem()`** por `item.anexos[]`
6. **Manter `extrairDadosSentenca()`** — só muda origem do texto
7. **Manter `fetchPartesViaApi()`** — já correto

Resultado esperado: `hcalc-prep.js` sem nenhuma dependência de DOM (zero `querySelector`, zero `click`, zero `sleep`).

---

*Atualize este documento ao concluir cada grupo de testes. Marque `✅` nos testes OK e `❌` com observação nos que apresentarem gaps.*
