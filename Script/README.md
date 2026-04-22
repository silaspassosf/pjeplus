# Script/ — Guia de Engenharia

Guia de referência para desenvolvimento e manutenção de scripts JavaScript no ecossistema PJeTools Pro.
Aplica-se a: **Tampermonkey UserScript**, **scripts de console** e **bookmarklets**.

---

## 1. Propósito

O `Script/` contém automações JavaScript que complementam o fluxo do PJe e do Infojud.
As regras aqui são específicas para scripts executados no navegador, não para a automação Python.

---

## 2. Estrutura da pasta

```
Script/
├── pjetools.user.js        Orquestrador principal (Tampermonkey)
├── hcalc.user.js           Orquestrador da calculadora (Tampermonkey)
├── core/
│   ├── utils.js            Primitivas de DOM, espera, formatação e toast
│   ├── state.js            CleanupRegistry, AsyncRunner, estado compartilhado
│   ├── extrair.js          window.PjeExtrair — extrator universal de documentos
│   └── loader.js           Loader de módulos e inicialização
├── modules/
│   ├── lista/              timeline, relatórios e verificação de documentos
│   ├── atalhos/            atalhos de teclado e hotkeys
│   ├── debito/             registrar débito em obrigação-pagar
│   ├── infojud/            worker Infojud e correções de editor
│   └── sisbajud/           integrações e relatórios SISBAJUD
├── ui/
│   └── painel.js           Painel flutuante principal
├── Java/                   scripts isolados (console/bookmarklet)
└── calc/BASE/              módulos da calculadora hcalc
```

---

## 3. Tipo de artefato

| Tipo | Formato | Uso |
|---|---|---|
| Tampermonkey UserScript | `@require` via URL raw | Ferramenta persistente, com acesso a `GM_*` |
| Script de console | IIFE colado no DevTools | Execução pontual; pode usar `async/await` |
| Bookmarklet | URI `javascript:` | Ação imediata; sem `async/await` no nível raiz |

---

## 4. APIs reutilizáveis

### `core/utils.js`

| Função | Uso |
|---|---|
| `sleep(ms)` | Pausa sem polling quando necessário |
| `waitElement(sel, timeout?)` | Aguarda elemento visível no DOM |
| `waitElementVisible(sel, timeout?)` | Aguarda elemento presente no DOM |
| `formatMoney(value)` | Formata número em moeda pt-BR |
| `parseMoney(str)` | Converte texto monetário em número |
| `normalizeText(str)` | Remove acentos e normaliza texto |
| `showToast(text, color?, duration?)` | Feedback visual leve |
| `playBeep(freq?, ms?)` | Sinal sonoro via WebAudio |

### `core/state.js`

| API | Uso |
|---|---|
| `new CleanupRegistry()` | Rastreia/remova listeners, intervals, observers |
| `new AsyncRunner()` | Garante uma única operação assíncrona por vez |
| `PJeState` | Estado compartilhado entre módulos |

### `core/extrair.js`

```javascript
const texto = await window.PjeExtrair();
```

### `modules/lista/`

```javascript
const docs = await lerTimelineCompleta();
renderTabela('meuPainel','📋 Título','#007bff',docs, async (doc) => { ... });
```

---

## 5. Regras de negócio

### 5.1 Angular SPA — Timing

| ✅ Correto | ❌ Proibido |
|---|---|
| `await waitElement('.seletor')` | `setTimeout(fn, N)` para renderização |
| `await waitElementVisible('.seletor')` | `setInterval` de polling de DOM |
| `sleep(0)` | loops de delay fixo |

> O PJe é um SPA Angular pesado. Renderização é assíncrona e event-driven. Polling explícito traz race conditions.

### 5.2 Clique em timeline

`scrollIntoView` pode quebrar o DOM do Angular e invalidar referências de elementos. Use um clique via `dispatchEvent` no link e invalide o cache quando necessário.

```javascript
const textLink = elem.querySelector('a.tl-documento:not([target="_blank"])');
if (textLink) {
  textLink.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
}
if (PJeState?.lista) PJeState.lista.readAt = 0;
```

### 5.3 Cleanup

Em módulos `@require`, registre todos os listeners/observers/intervals/timeouts em `CleanupRegistry`.

### 5.4 Exposição de API

```javascript
window.MeuModulo = { metodoPublico };
window.PjeMeuModulo = window.pjeMeuModulo;
```

### 5.5 Bookmarklets

- Sem `async/await` no nível raiz.
- Evite `sleep`/`setTimeout` para aguardar renderização Angular; use espera baseada em DOM (MutationObserver) sempre que possível.
- URL deve ser codificada com `encodeURIComponent`.
- Se ultrapassar ~2 KB não minificado, faça script de console.

---

## 6. Versionamento de `@require`

- Ao alterar arquivo em `calc/BASE/`, bumpe `?v=NNN` em `hcalc.user.js`.
- Ao alterar módulo em `modules/`, bumpe `@version` no orquestrador afetado (`pjetools.user.js` ou `hcalc.user.js`).
- Não use `git add -A` para mudanças de módulo; commite apenas o módulo alterado e o orquestrador.

---

## 7. Domínios e `@match`

```
pje.trt2.jus.br
pje1g.trt2.jus.br
sisbajud.cnj.jus.br
sisbajud.pdpj.jus.br
cav.receita.fazenda.gov.br/ServicosAT/SRDecjuiz
```

---

## 8. Checklist

- [ ] Tipo de script definido (Tampermonkey/console/bookmarklet)
- [ ] Reutilizei APIs de `core/`
- [ ] Evitei `scrollIntoView` em timeline
- [ ] Usei `CleanupRegistry` em módulo
- [ ] Exposei `window.NomeModulo` + alias PascalCase
- [ ] Bump de versão do orquestrador se necessário
- [ ] Bookmarklet < 2 KB ou script de console
- [ ] Não usei `setTimeout` para esperar Angular
- [ ] Código completo, sem `TODO`
