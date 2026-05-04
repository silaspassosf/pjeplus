# PJe Grab — Recorder de Sessao Autenticada

Captura cliques, digitacoes, selecoes e chamadas de API durante uma sessao real
do PJe, sem instrumentacao previa dos seletores.

---

## Problema que Resolve

O PJe usa Angular + Angular Material. Seletores mudam a cada deploy.
A cada quebra de seletor e necessario:

1. Abrir o browser no PJe autenticado
2. Inspecionar manualmente o elemento no DevTools
3. Testar o seletor via `driver.find_element`
4. Atualizar `aprendizado_seletores.json` ou `Fix/variaveis.py`

O Grab elimina os passos manuais: basta navegar normalmente e o sistema descobre
tudo automaticamente.

---

## Arquitetura

```
tools/grab.py           Orquestrador Python
tools/grab_recorder.js  Listener de eventos DOM (clicks/inputs/changes)
Script/Java/pjeapi.js   Interceptor de fetch + XHR (ja existia)
```

Os dois scripts JS rodam em paralelo no mesmo browser.
O Python faz poll a cada 2 segundos via `window.__grab.flush()`.

```
Browser (Firefox autenticado)
  ├─ grab_recorder.js  → window.__grab.events[]   ← click/input/change
  └─ pjeapi.js         → window.__pje.log[]        ← fetch/XHR API calls
           ↑ poll 2s
tools/grab.py  →  organiza  →  grab_out/session_<ts>/
```

---

## Como Usar

### Modo Padrao (PC)

```powershell
py tools/grab.py
```

1. Driver Firefox abre com login automatico (credentials do Windows Keyring)
2. Navegue normalmente no PJe — abra processos, clique botoes, preencha campos
3. Feche o browser (ou Ctrl+C no terminal)
4. Dados sao exportados e organizados automaticamente
5. O script pergunta se deseja aplicar o patch em `aprendizado_seletores.json`

### Modo Notebook

```powershell
py tools/grab.py --notebook
```

### Log Verbose (ver cada evento no terminal)

```powershell
py tools/grab.py --verbose
```

---

## Saida — `grab_out/session_<timestamp>/`

| Arquivo | Conteudo | Uso |
|---------|----------|-----|
| `raw_events.json` | Todos os eventos capturados | Debug/auditoria |
| `raw_api.json` | Log completo do pjeapi.js | Descoberta de endpoints |
| `selectors.json` | Seletores agrupados por pagina | Referencia humana |
| `api_map.json` | Endpoints por urlTemplate | Referencia de API |
| `merged.json` | Eventos com API correlacionadas | Analise de fluxo |
| `patch_seletores.json` | Delta para `aprendizado_seletores.json` | Aplicar automaticamente |

---

## Estrutura de um Evento de Clique

```json
{
  "ts": 1746359221456,
  "type": "click",
  "page_url": "https://pje.trt2.jus.br/pje/Painel.seam",
  "page_path": "/pje/Painel.seam",
  "el_info": {
    "tag": "button",
    "id": null,
    "classes": ["mat-button", "pje-btn-primary"],
    "ariaLabel": "Assinar documento",
    "role": "button",
    "name": null,
    "type": "button",
    "placeholder": null,
    "text": "Assinar",
    "ngReflect": {},
    "dataAttrs": {},
    "selector_candidates": [
      { "selector": "button[aria-label=\"Assinar documento\"]", "stability": "medium", "type": "aria" },
      { "selector": "button[role=\"button\"].mat-button.pje-btn-primary", "stability": "medium", "type": "role-mat" },
      { "selector": "button.mat-button.pje-btn-primary", "stability": "low", "type": "tag-class" },
      { "selector": "//button[normalize-space(.)=\"Assinar\"]", "stability": "low", "type": "xpath-text" }
    ],
    "best_selector": "button[aria-label=\"Assinar documento\"]",
    "stability": "medium"
  },
  "xpath": "/html/body/app-root/pje-painel/div[1]/button[3]",
  "triggered_apis": [
    {
      "method": "POST",
      "urlTemplate": "/pje-comum-api/api/documentos/{id}/assinar",
      "url": "/pje-comum-api/api/documentos/9987623/assinar",
      "status": 200,
      "duration_ms": 342
    }
  ]
}
```

---

## Niveis de Estabilidade de Seletor

| Nivel | Tipo | Exemplo | Quando usar |
|-------|------|---------|-------------|
| `high` | `id` | `#btn-assinar` | ID nao gerado pelo Angular |
| `high` | `data-attr` | `[data-cy="btn-assinar"]` | Atributo data-* intencional |
| `medium` | `aria` | `button[aria-label="Assinar"]` | Recomendado para botoes/inputs |
| `medium` | `ng-reflect-name` | `[ng-reflect-name="processo"]` | Formularios Angular reativos |
| `medium` | `name-attr` | `input[name="numeroCNJ"]` | Inputs com name |
| `medium` | `role-mat` | `mat-select[role="combobox"].mat-select` | Dropdowns Material |
| `low` | `tag-class` | `button.mat-button.pje-btn` | Fallback |
| `low` | `xpath-text` | `//button[normalize-space(.)="Assinar"]` | Ultimo recurso |

O grab escolhe automaticamente o candidato de maior estabilidade como `best_selector`.

---

## Estrutura do API Map

```json
{
  "/pje-comum-api/api/processos/{id}/partes": {
    "method": "GET",
    "urlTemplate": "/pje-comum-api/api/processos/{id}/partes",
    "count": 12,
    "example_url": "/pje-comum-api/api/processos/9987623/partes",
    "example_status": 200,
    "response_fields": ["id", "nome", "cpf", "tipo", "polo", "advogados"]
  }
}
```

---

## Correlacao Clique → API

O `merged.json` liga cada clique as chamadas de API disparadas nos 3 segundos
seguintes. Isso responde: "qual botao chama qual endpoint?".

Exemplo de correlacao:

```
Clique em "Movimentar" (button.mat-button)
  └─ POST /pje-comum-api/api/processos/{id}/movimentos  (200, 245ms)
  └─ GET  /pje-comum-api/api/processos/{id}/timeline    (200, 180ms)
```

---

## Opcoes de Captura

### Opcao A — Modo Passivo Global (padrao)
Captura qualquer tela navegada durante a sessao.
`py tools/grab.py`

### Opcao B — Verbose (ver tudo em tempo real)
`py tools/grab.py --verbose`
Cada evento aparece no terminal:
```
  [click   ] /pje/Painel.seam | button[aria-label="Movimentar"]
  [input   ] /pje/editor.seam | input[name="texto"]
```

### Opcao C — Console do Browser (discovery manual)
Com o browser aberto pelo grab, use no console do DevTools:
```js
__pje.watchNext()         // proximo clique + APIs disparadas
__pje.fromEl($0)          // elemento selecionado no Inspector → endpoint
__pje.search("1000632")   // busca numero em todas as respostas
__pje.summary()           // todos os endpoints vistos
__grab.stats()            // estatisticas do recorder
```
Atalhos: `Shift+Alt+W` = watchNext | `Shift+Alt+S` = summary

### Opcao D — Probe Manual de Endpoint
```js
__pje.probe('/pje-comum-api/api/processos/id/9987623/partes')
```
Retorna estrutura completa da resposta com XSRF automatico.

### Opcao E — Exportar Sessao do Console
```js
__pje.export()   // copia JSON do log API para clipboard
__grab.export()  // retorna array com todos os eventos
```

---

## Patch em aprendizado_seletores.json

Ao terminar a sessao, o grab compara os seletores descobertos com o arquivo
existente e exibe apenas entradas novas ou com estabilidade maior.

```
[GRAB] Novos seletores descobertos:
  btn_movimentar: stability=medium  selector=button[aria-label="Movimentar processo"]
  campo_numero:   stability=high    selector=input[name="numeroCNJ"][type="text"]
  dropdown_fase:  stability=medium  selector=mat-select[ng-reflect-name="fase"]

[GRAB] Aplicar patch em aprendizado_seletores.json? [s/N]
```

Respondendo `s`, o arquivo e atualizado imediatamente.

---

## Workflow Recomendado para Seletor Quebrado

```
1. py tools/grab.py
2. Navegue ate a tela com o seletor quebrado
3. Execute o fluxo completo (preencher campos, clicar botoes)
4. Feche o browser
5. Responder "s" para aplicar o patch
6. Verificar selectors.json para conferir o seletor escolhido
7. Atualizar Fix/variaveis.py se necessario (copia de selectors.json)
```

---

## Workflow para Descoberta de Endpoint Desconhecido

```
1. py tools/grab.py
2. No DevTools do browser: cole o pjeapi.js (ou use Shift+Alt+S apos navegar)
3. Inspecione o elemento no Inspector (clique direito → Inspecionar)
4. No console: __pje.fromEl($0)
5. Anote o endpoint retornado
6. Feche o browser
7. Consulte api_map.json para ver campos da resposta
```

---

## Dependencias

- `Fix.core.criar_driver_PC` / `criar_driver_notebook` (ja existem)
- `Script/Java/pjeapi.js` (ja existe)
- `tools/grab_recorder.js` (criado agora)
- Sem dependencias externas novas

---

## Arquivos

```
tools/
  grab.py             Orquestrador Python
  grab_recorder.js    Listener DOM (cliques/inputs)
docs/
  grab.md             Esta documentacao
Script/Java/
  pjeapi.js           Interceptor fetch/XHR (pre-existente)
grab_out/             Saida das sessoes (gitignored recomendado)
  session_<ts>/
    raw_events.json
    raw_api.json
    selectors.json
    api_map.json
    merged.json
    patch_seletores.json
aprendizado_seletores.json  Base de seletores (atualizado pelo patch)
```

---

## Limitacoes Conhecidas

| Limitacao | Impacto | Workaround |
|-----------|---------|------------|
| Nao captura requests feitos antes da injecao | Seed via Performance API (pjeapi.js ja faz) | Recarregar a pagina apos injecao |
| Correlation window de 3s pode ser curta | APIs lentas podem nao ser correlacionadas | Aumentar `3000` em `_merge()` |
| XPath absoluto quebra com reordenacao DOM | Nao usar XPath em producao | Usar `best_selector` (CSS) |
| Seletores Angular gerados (ng-tns-*) filtrados | Alguns elementos podem nao ter candidato | Usar watchNext() + inspecao manual |
| Nao captura shadow DOM (alguns componentes) | Elementos dentro de shadow root | Nao ha solucao generica |
