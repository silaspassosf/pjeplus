# PLANO — Modularização do alv.js (padrão hcalc.user.js)

**Versão do documento:** 1.0 (2026-08-31)
**Origem:** alv.js v0.4.2 (~2.850 linhas, monolítico)
**Objetivo:** transformar em `alv.user.js` (orquestrador simples) + módulos por competência em `Script/alvara/`, carregados via `@require` — mesmo padrão do `hcalc.user.js` → `Script/calc/BASE/*.js`.

---

## 1. Estado atual — mapa de competências do alv.js

| Bloco atual (alv.js) | Linhas aprox. | Competência |
|---|---|---|
| Header, INSTANCE guard, `isPaginaDetalhe`, `logDiagnostico/logAviso` | 1–60 | boot/orquestrador |
| `utils` (parseMoney, formatMoney, normalizeText, escapeHtml) | 60–130 | utilidades |
| `REGEX` + `firstMatch/allMatches` + `extrairValores` + `extrairReferenciaDeposito/extrairIdDepositoRelacionado/extrairProcessoDestino/extrairValorGenerico` | 130–440 | **extração da decisão** |
| `limparTextoExtraido`, `textoDe*`, `obterTextoDocumentoAtual`, `aguardarTextoDocumentoAtual`, `extrairDocumentoAtualLocal`, `obterTextoDecisao` | 445–755 | **extrator de documento** (fallback local) |
| `_xsrfToken/_apiHeaders/_apiGet/_shapePartes/_shapePeritos/buscarDadosProcesso/primeiraParte/primeiroAdvogado/preencherDestinatario/aplicarPreenchimentoAutomatico` | 755–1010 | **dados do processo (API)** |
| `STORAGE_KEY/criarEstado/salvarEstado/carregarEstado/aplicarMascara*/obterDadosDoCard/atualizarEstadoPeloOverlay` | 1010–1380 | **estado** |
| `campoDadosHtml/opcoesDestino/renderCard/estilos/abrirOverlay/aplicarValoresDosSelects/instalarEventos*` | 1380–2560 | **overlay (UI)** |
| `analisarDecisao` (fluxo de análise) | 2560–2680 | **orquestração de análise** |
| `criarBotao/removerElementosDaPagina/iniciar` (SPA routing, host fixo) | 2680–2870 | **boot/injeção** |
| exports `window.PjeAlvara` | final | contrato público |

---

## 2. Estrutura alvo

```
Script/
├── alv.user.js                      ← ORQUESTRADOR (boot, botão, rota SPA, analisarDecisao)
└── alvara/
    ├── utils.js                     ← utilidades (parseMoney, formatMoney, escapeHtml…)
    ├── extracao_decisao.js          ← REGEX + extrairValores + helpers de depósito/destino
    ├── extrator_documento.js        ← fallback local de extração (HTML/iframe/embed/seleção)
    ├── dados_processo.js            ← API pje-comum-api (/partes, /peritos) + preenchimento automático
    ├── estado.js                    ← criarEstado, storage, máscara, atualizarEstadoPeloOverlay
    ├── overlay.js                   ← renderCard, campoDadosHtml, opcoesDestino, estilos, eventos
    ├── analise.js                   ← analisarDecisao (cola extração → dados → estado → overlay)
    ├── extracao_siscondj.js         ← [NOVO] extração de dados DENTRO do SISCONDJ (fase 2)
    └── minuta.js                    ← [NOVO] início do processo seguinte: após "Criar alvarás",
                                        abre SISCONDJ e inicia a minuta (fase 2)
```

**Reuso do que já existe (não duplicar):**
- `Script/core/extrair.js` continua sendo o extrator primário via `@require` (PDF/pdf.js/API) — `extrator_documento.js` é só fallback.
- `Script/core/utils.js` (do loader pjetools) tem utilidades equivalentes — avaliar reuso na fase 0; se a assinatura bater, o módulo `utils.js` do alvará pode só reexportar.
- `hcalc-prep.js` continua sendo a referência da lógica de API (`/partes`, XSRF) já portada para `dados_processo.js`.

---

## 3. Contrato entre módulos

**Namespace global:** `window.Alv` (evitar colisão com `window.PjeAlvara`, que permanece como fachada de compatibilidade exposta pelo orquestrador).

```js
// Cada módulo registra seu bloco no namespace:
window.Alv = window.Alv || {};
window.Alv.utils      = { parseMoney, formatMoney, normalizeText, escapeHtml, sleep };
window.Alv.extracao   = { REGEX, extrairValores, extrairReferenciaDeposito, extrairProcessoDestino };
window.Alv.documento  = { obterTextoDecisao, extrairDocumentoAtualLocal, obterTextoDocumentoAtual };
window.Alv.dados      = { buscarDadosProcesso, aplicarPreenchimentoAutomatico };
window.Alv.estado     = { criarEstado, salvarEstado, carregarEstado, atualizarEstadoPeloOverlay, aplicarMascaraCampos };
window.Alv.overlay    = { abrirOverlay, instalarEventosOverlay, renderCard };
window.Alv.minuta     = { iniciarFluxoMinuta };        // fase 2 (SISCONDJ)
window.Alv.siscondj   = { extrairDadosSiscondj };        // fase 2 (SISCONDJ)
```

**Regras:**
1. Módulos **não** têm IIFE-guard de instância (só o `alv.user.js` tem `INSTANCE_KEY`).
2. Módulos só leem/escrevem em `window.Alv.*` e no `localStorage` via `estado.js` (única dona da `STORAGE_KEY`).
3. `analisarDecisao` (no `analise.js` ou no orquestrador) é a única que orquestra: `obterTextoDecisao → extrairValores → buscarDadosProcesso → criarEstado → abrirOverlay`.
4. **"Criar alvarás"** passa a chamar `Alv.minuta.iniciarFluxoMinuta(estado)` — que é o ponto de entrada da fase 2 (SISCONDJ). Enquanto a fase 2 não existe, o botão mantém o alert atual, mas o hook já fica preparado.
5. Logs: manter o padrão atual (só extração ativa, `logDiagnostico` no-op) — cada módulo usa os helpers recebidos de `Alv.utils` ou `console` direto nos pontos de extração.

---

## 4. Carregamento (padrão hcalc)

No `alv.user.js`, o `@require` carrega os módulos ANTES do corpo (garantia do Tampermonkey), na ordem de dependência:

```
// @require https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/extrair.js?v=<V>
// @require https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/utils.js?v=<V>
// @require https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/extracao_decisao.js?v=<V>
// @require https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/extrator_documento.js?v=<V>
// @require https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/dados_processo.js?v=<V>
// @require https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/estado.js?v=<V>
// @require https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/overlay.js?v=<V>
// @require https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/analise.js?v=<V>
// @require https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/extracao_siscondj.js?v=<V>
// @require https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/minuta.js?v=<V>
```

**Cache-busting:** mesmo esquema do hcalc (`?v=<número>`), bumpando TODOS os `?v=` juntos a cada release (o `alv.user.js` publica a versão corrente no comentário de topo: `// módulos ?v=42`).

---

## 5. Fases

### Fase 0 — Fundação (baixo risco)
- Criar `Script/alvara/` com `utils.js` e `extrator_documento.js` (movimento literal de código, sem mudança de comportamento).
- Definir `window.Alv` e a convenção de registro.
- **Validação:** `node --check` em todos; smoke test com stubs de DOM (mesma suíte que já usamos); paridade de `extrairValores` com casos de teste já gravados (decisão "à autora", depósito hex, honorários, perito).

### Fase 1 — Extração pura
- `extracao_decisao.js`: REGEX + helpers + `extrairValores`.
- É o módulo mais testável (funções puras) — mover primeiro e travar com os testes do console.
- **Validação:** matriz de testes existente (liberação à autora/exequente, parte de crédito → valor fixo, ids hex, honorários, perito, devolução, transferência).

### Fase 2 — Dados do processo + Estado
- `dados_processo.js` (API `/partes`, `/peritos`, preenchimento automático) e `estado.js` (storage + máscaras + atualizar pelo overlay).
- Ponto de atenção: `estado.js` vira a ÚNICA dona da `STORAGE_KEY`; `atualizarEstadoPeloOverlay` migra para cá junto com `obterDadosDoCard`.
- **Validação:** mesmo teste de node com mock de `/partes`/`/peritos` (advogado do autor, beneficiário, perito via endpoint e fallback TERCEIROS).

### Fase 3 — Overlay
- `overlay.js`: renderCard, campoDadosHtml, opcoesDestino, estilos, abrirOverlay, aplicarValoresDosSelects, instalarEventosOverlay/Remocao.
- Layout compacto v0.4.2 (560px, campos na ordem Nome→CPF→Agência→Conta→Banco, sem ID de depósito) vem junto, intacto.
- **Validação:** abrir overlay com 0, 1 e N verbas; adicionar verba manual; remover card; valor fixo readonly.

### Fase 4 — Orquestrador enxuto
- `alv.user.js` fica só com: header, INSTANCE guard, `isPaginaDetalhe`, criarBotao/host fixo, roteamento SPA, `analisarDecisao` (ou `analise.js`), exports `window.PjeAlvara` (fachada de compat mapeando `Alv.*`).
- **Meta de tamanho:** orquestrador ≤ 350 linhas.
- **Validação:** injeção de botão na rota /detalhe#documento, paridade total com v0.4.2 nos logs de extração, nenhum `prompt/confirm` na abertura.
- **Paridade:** manter o `alv.js` monolítico intocado até esta validação passar; só então aposentar (ou renomear para `alv.legacy.js`).

### Fase 5 — Stub SISCONDJ (preparação fase 2)
- `extracao_siscondj.js`: expõe `Alv.siscondj.extrairDadosSiscondj()` (stub — será implementada quando a fase 2 do SISCONDJ for definida; usar o padrão do `hcalc-prep` para API e do `gigs-plugin.js` para o que for DOM).
- `minuta.js`: expõe `Alv.minuta.iniciarFluxoMinuta(estado)` — recebe o estado consolidado (itens + dados do processo) e é o gancho chamado pelo botão "Criar alvarás". Implementação real (navegar SISCONDJ, preencher minuta) é a fase 2 do projeto; por ora o stub loga o estado recebido e mantém o alert atual.
- **Contrato do estado passado para a fase 2 (congelar agora):**
  ```js
  {
      processo: { numero, partes: { ativo, passivo, outros }, peritos },
      itens: [ { id, tipo, valor, valorFixo, destinoTipo, destinatarioNome,
                 destinatarioDocumento, dados: { banco, agencia, conta, tipoConta },
                 deposito, transferencia, siscon } ]
  }
  ```

---

## 6. Riscos e cuidados

| Risco | Mitigação |
|---|---|
| `@require` roda antes do corpo, mas módulos se referenciam em tempo de chamada (não no load) → sem problema de ordem, desde que nada se execute no top-level além do registro em `window.Alv` | Regra 2 do contrato |
| Duplicação `window.PjeAlvara` vs `window.Alv` | `PjeAlvara` vira fachada fina mantida pelo orquestrador; módulos nunca leem `PjeAlvara` |
| Cache do Tampermonkey com `@require` velho | Bump de `?v=` em TODOS os módulos a cada release; versão publicada no topo do `alv.user.js` |
| Duas cópias do userscript ativas | Mantém-se o `INSTANCE_KEY` guard + regra de manter 1 cópia no TM |
| `estado.js` sendo a única dona do storage | Nenhum outro módulo usa `STORAGE_KEY` diretamente |
| Regressão na extração | Matriz de testes node congelada (casos já gravados nesta memória de repo) roda antes de cada fase |

---

## 7. Ordem de execução recomendada

Fase 0 → 1 → 2 → 3 → 4 (paridade) → 5 (stubs) → [fase 2 SISCONDJ: implementação real de `minuta.js` + `extracao_siscondj.js`].

Cada fase é um commit independente e reversível; o monolítico só é aposentado na Fase 4, após paridade comprovada.
