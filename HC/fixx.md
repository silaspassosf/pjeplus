Segue um guia em Markdown, focado em corrigir: (1) botão que não aparece e (2) erro ao carregar/processar o PDF, mantendo sua estrutura atual.

***

## 1. Corrigir o `hcalc.user.js` (boot quebrado)

Seu `hcalc.user.js` está truncado: o `aguardarPJe` não fecha o `else` nem a função. Isso impede o botão de ser inicializado.

Use assim:

```js
// ==UserScript==
// @name         Homologação de Cálculos
// @namespace    http://tampermonkey.net/
// @version      1.17.0
// @description  Assistente de homologação PJe-Calc (loader @require — Estratégia 2)
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/calc/hcalc-core.js?v=117
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/calc/hcalc-pdf.js?v=117
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/calc/hcalc-overlay.js?v=117
// @connect      cdnjs.cloudflare.com
// @connect      raw.githubusercontent.com
// @run-at       document-idle
// @grant        unsafeWindow
// ==/UserScript==

(function () {
  'use strict';

  // Anti-iframe
  if (window.self !== window.top) return;

  // Evitar dupla execução
  if (document.documentElement.getAttribute('data-hcalc-boot')) return;
  document.documentElement.setAttribute('data-hcalc-boot', '1');

  // Aguarda Angular/DOM do PJe estabilizar
  function aguardarPJe(cb, tentativas) {
    tentativas = tentativas || 0;
    if (tentativas > 40) return; // timeout ~8s

    var pronto =
      document.querySelector('pje-cabecalho') ||
      document.querySelector('li.tl-item-container') ||
      document.querySelector('[class*="processo"]');

    if (pronto) {
      cb();
    } else {
      setTimeout(function () {
        aguardarPJe(cb, tentativas + 1);
      }, 200);
    }
  }

  // Chama init do overlay/botão depois que o PJe estiver pronto
  aguardarPJe(function () {
    if (window.hcalcInitBotao) {
      window.hcalcInitBotao();
    } else {
      console.error('[hcalc] hcalcInitBotao não encontrado — verifique @require / ordem dos arquivos');
    }
  });
})();
```

**Checklist dessa parte:**

- Confirmar se `hcalcInitBotao` está exposto em `hcalc-overlay.js` (por ex.: `window.hcalcInitBotao = initializeBotao;`).
- Garantir que não há outro userscript interferindo no mesmo seletor de `pje-cabecalho` / timeline.

***

## 2. Expor corretamente o inicializador do botão em `hcalc-overlay.js`

No início de `hcalc-overlay.js` você tem `initializeBotao()` mas não publica nada no `window`.

No final do IIFE de `hcalc-overlay.js`, adicione:

```js
  // Expor API pública para o userscript loader
  window.hcalcInitBotao = initializeBotao;
})();
```

Assim, o `hcalc.user.js` pode chamar `window.hcalcInitBotao()` depois que o PJe carregar.

***

## 3. Garantir HTML do botão + input file (para o PDF)

Dentro da função `initializeBotao` em `hcalc-overlay.js` hoje está:

```js
// Injeta APENAS botão + input file (sem overlay)
document.body.insertAdjacentHTML('beforeend', ` `);
const btn = document.getElementById('btn-abrir-homologacao');
```

Esse template string está vazio, então **nenhum botão nem input** é criado. Ajuste para algo como:

```js
document.body.insertAdjacentHTML(
  'beforeend',
  `
  <button id="btn-abrir-homologacao" type="button">
    Homologar Cálculos
  </button>
  <input
    id="input-planilha-pdf"
    type="file"
    accept="application/pdf"
    style="display:none"
  />
  `
);
const btn = document.getElementById('btn-abrir-homologacao');
```

Checklist:

- Id do botão: `btn-abrir-homologacao` (igual ao CSS).
- Id do input de arquivo: `input-planilha-pdf` (é o que o código já tenta buscar).
- `type="file"` e `accept="application/pdf"`.

***

## 4. Fluxo de clique do botão e seleção do PDF

Dentro do `btn.onclick` (em `initializeBotao`), o fluxo já está quase certo:

```js
btn.onclick = async () => {
  if (!window.__hcalcOverlayInitialized) {
    dbg('Primeiro clique: carregando overlay completo (lazy init)...');
    initializeOverlay();
    // initializeOverlay substitui btn.onclick com o handler completo
  }

  // FASE 1: ainda não há planilha carregada
  if (!window.hcalcState.planilhaCarregada) {
    dbg('FASE 1: abrindo file picker.');
    document.getElementById('input-planilha-pdf').click();
    return;
  }

  // FASE 3: overlay já inicializado e planilha carregada
  btn.click();
};
```

Pontos para checar:

1. Em `initializeOverlay`, você precisa registrar o `change` do input:

   ```js
   const fileInput = document.getElementById('input-planilha-pdf');
   if (fileInput && !fileInput._hcalcBound) {
     fileInput._hcalcBound = true;
     fileInput.addEventListener('change', async (e) => {
       const file = e.target.files;
       if (!file) return;

       try {
         await carregarPDFJSSeNecessario(); // retorna true, mas mantém semântica
         const dados = await processarPlanilhaPDF(file);
         // Atualiza estado
         window.hcalcState.planilhaExtracaoData = dados;
         window.hcalcState.planilhaCarregada = !!dados && !!dados.sucesso;

         // Atualizar card/resumo (função já deve existir no overlay)
         if (window.hcalcAtualizarResumoPlanilha) {
           window.hcalcAtualizarResumoPlanilha(dados);
         }
       } catch (e2) {
         err('Erro ao processar planilha PDF:', e2);
         window.hcalcState.planilhaCarregada = false;
       }
     });
   }
   ```

2. Certificar que `window.hcalcState` foi criado (vem de `hcalc-core.js`).

***

## 5. Erro ao carregar/processar o PDF (lado do worker)

Sua estrutura de PDF está assim:

- `hcalc-pdf.js`:
  - expõe `window.carregarPDFJSSeNecessario = carregarPDFJSSeNecessario;`
  - expõe `window.processarPlanilhaPDF = processarPlanilhaPDF;`
  - cria `createPdfWorkerBlob()` e um `Worker` com `importScripts` para pdf.js.

Checklist para evitar erro:

1. **Domínio do PDF.js**: você já tem:

   ```js
   // @connect cdnjs.cloudflare.com
   ```

   Isso é suficiente para o `importScripts('https://cdnjs.cloudflare.com/...')` dentro do Worker.

2. **Estado do Worker**:

   Em `processarPlanilhaPDF`, você já faz:

   ```js
   if (!window.hcalcState._pdfWorkerUrl) {
     window.hcalcState._pdfWorkerUrl = criarPdfWorkerBlob();
   }
   const worker = new Worker(window.hcalcState._pdfWorkerUrl);
   ```

   Verifique:

   - `window.hcalcState` existe (garantido por `hcalc-core.js`).
   - Nenhum erro de CSP bloqueando `new Worker(blobUrl)`; se houver, o console mostrará.

3. **Tratativa de erro minimamente robusta**:

   Certifique que seu `worker.onerror` realmente loga o erro:

   ```js
   worker.onerror = (e) => {
     console.error('[HCalc Worker] Erro no worker:', e.message, e);
     worker.terminate();
     reject(new Error(e.message));
   };
   ```

4. **Validação de retorno**:

   O worker retorna sempre `{ sucesso: true/false, ... }`. Depois de `resolve(dadosValidados)`, você atualiza `hcalcState.planilhaCarregada`. Se não marcar isso como `true`, o botão sempre cairá na “FASE 1” de novo.

***

## 6. Checklist rápido de depuração

Na aba `/detalhe`, abra o console e execute:

1. Ver se o script bootou:

   ```js
   document.documentElement.getAttribute('data-hcalc-boot')
   // Deve ser "1"
   ```

2. Ver se o init está exposto:

   ```js
   typeof window.hcalcInitBotao
   // Deve ser "function"
   ```

3. Ver estado:

   ```js
   window.hcalcState
   ```

4. Depois de selecionar o PDF:

   ```js
   window.hcalcState.planilhaCarregada
   window.hcalcState.planilhaExtracaoData
   ```

Se alguma dessas etapas falhar, me diga exatamente:

- O erro que aparece no console (texto completo).
- Em qual linha/arquivo (`hcalc-core.js`, `hcalc-pdf.js` ou `hcalc-overlay.js`).  