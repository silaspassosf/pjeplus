# Planejamento de Implementação: Responsabilidade de Reclamadas no HCalc

## Objetivo
Ajustar o overlay de responsabilidades do HCalc para tratar corretamente múltiplas reclamadas desde o início, mantendo o fluxo atual para um único passivo e adicionando controles específicos para cada reclamada extra.

## Escopo
- Overlay de responsabilidade em `Script/calc/BASE/hcalc-overlay.js`
- Controle e geração de texto em `Script/calc/BASE/hcalc-overlay-responsabilidades.js`
- Decisão usando texto de responsabilidade em `Script/calc/BASE/hcalc-overlay-decisao.js`
- Rascunho/restauração em `Script/calc/BASE/hcalc-overlay-draft.js`

## Tarefas detalhadas

### Task 1: UI de Responsabilidade por Reclamada
**Descrição:** modificar o overlay para suportar múltiplas reclamadas automaticamente.

**Alterações necessárias:**
- detectar quando há mais de uma reclamada em `window.hcalcPartesData.passivo`.
- manter o fluxo existente para 1 reclamada sem alterações.
- auto adicionar a primeira reclamada como `Principal`.
- criar um box para cada reclamada extra com nome preenchido automaticamente.
- nesse box, incluir:
  - radio `Solidária`
  - radio `Subsidiária` (selecionado por padrão)

**Arquivo principal:**
- `Script/calc/BASE/hcalc-overlay.js`
- `Script/calc/BASE/hcalc-overlay-responsabilidades.js`

**Critério de sucesso:**
- ao abrir overlay com 2+ reclamadas, aparece 1 principal + 1 box por reclamada extra.
- cada box extra contém o nome da reclamada e radios corretos.

---

### Task 2: Lógica de seleção Solidária / Subsidiária
**Descrição:** garantir comportamento condicional por box de reclamada.

**Alterações necessárias:**
- para cada box extra, on-change dos radios deve atualizar visibilidade das opções de período.
- se `Solidária` for selecionado:
  - esconder opções de período
  - não permitir carregar planilha de período diverso
- se `Subsidiária` for selecionado:
  - exibir opções `Período Integral` e `Período Diverso`
- se `Período Diverso` for marcado:
  - exibir botão/input para carregar planilha daquela reclamada.

**Arquivo principal:**
- `Script/calc/BASE/hcalc-overlay-responsabilidades.js`

**Critério de sucesso:**
- o estado de cada box é controlado isoladamente.
- apenas boxes subsidiárias mostram opções de período.
- `Período Diverso` permite carregamento da planilha.

---

### Task 3: Carregamento de planilha por Reclamada
**Descrição:** integrar o carregamento de PDF/planilha ao box de cada reclamada subsidiária renom.

**Alterações necessárias:**
- usar funções existentes de `carregarPDFJSSeNecessario()` e `processarPlanilhaPDF()`.
- associar a planilha carregada à reclamada específica.
- salvar no estado global `window.hcalcState.planilhasDisponiveis` ou similar.
- mostrar `idPlanilha` e `periodoCalculo` no box correspondente.
- manter compatibilidade com o rascunho.

**Arquivo principal:**
- `Script/calc/BASE/hcalc-overlay-responsabilidades.js`

**Critério de sucesso:**
- cada box diverso exibe os dados extraídos após o upload.
- os dados são armazenados e identificados por reclamada/ID.

---

### Task 4: Geração de texto de responsabilidades
**Descrição:** alterar a geração de texto para o agrupamento exigido na decisão.

**Alterações necessárias:**
- ajustar `gerarTextoResponsabilidades()` em `Script/calc/BASE/hcalc-overlay-responsabilidades.js`.
- garantir a saída com a seguinte ordem:
  1. devedoras solidárias
  2. subsidiárias período integral
  3. subsidiárias período diverso
- manter flexibilidade para omitir parágrafos vazio quando um grupo não existir.
- tratar o caso de 1 reclamada sem alterar o texto antigo.

**Arquivo principal:**
- `Script/calc/BASE/hcalc-overlay-responsabilidades.js`

**Critério de sucesso:**
- texto produzido tem sempre os parágrafos na ordem solicitada.
- nomes são listados corretamente e formatados como lista.

---

### Task 5: Consumo em Decisão e Rascunho
**Descrição:** garantir que o novo estado do overlay seja preservado e usado na geração da decisão.

**Alterações necessárias:**
- verificar se `Script/calc/BASE/hcalc-overlay-draft.js` salva/restaura dados de boxes extras e de períodos diversos.
- ajustar a serialização de `draft.periodos` se necessário para cada reclamada extra.
- confirmar que `Script/calc/BASE/hcalc-overlay-decisao.js` recebe e usa `respDados.textoIntro` corretamente.
- manter compatibilidade do template de decisão com grupos adicionais.

**Arquivos principais:**
- `Script/calc/BASE/hcalc-overlay-draft.js`
- `Script/calc/BASE/hcalc-overlay-decisao.js`

**Critério de sucesso:**
- overlay reconstruído corretamente a partir do draft.
- decisão ao gerar reutiliza o texto atualizado.

---

### Task 6: Validação manual
**Descrição:** testar os cenários reais e confirmar o comportamento final.

**Verificação:**
- abrir overlay com 1 reclamada e validar fluxo atual.
- abrir overlay com 2+ reclamadas e validar:
  - principal auto-add
  - boxes extras preenchidos
  - seleção solidária/subsidiária funcionando
  - carregamento de planilha por reclamada diverso
- gerar decisão e conferir o texto na ordem:
  1. solidárias
  2. subsidiárias integral
  3. subsidiárias diverso.

**Critério de sucesso:**
- fluxo com múltiplas reclamadas funciona sem regressão.
- decisão final apresenta agrupamento correto.

## Notas importantes
- o campo `responsabilidades` será alterado no overlay e na geração de decisão.
- com 1 reclamada, não deve haver mudança de comportamento visível.
- a primeira reclamada será tratada automaticamente como principal quando houver várias.
- a geração do texto deve seguir a ordem exata de parágrafos pedida.

## Arquivos afetados
- `Script/calc/BASE/hcalc-overlay.js`
- `Script/calc/BASE/hcalc-overlay-responsabilidades.js`
- `Script/calc/BASE/hcalc-overlay-decisao.js`
- `Script/calc/BASE/hcalc-overlay-draft.js`
