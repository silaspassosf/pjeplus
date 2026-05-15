# Plano de Correcao: mov_sob (PEC) via Legado

## Objetivo
Corrigir o comportamento de `mov_sob`, chamado pelo modulo PEC para ajustar meses de sobrestamento em GIGS `xs/sob`, usando como referencia de comportamento a implementacao em `leg/`.

## Escopo
- Incluido: cadeia PEC que aciona `mov_sob`, parser de observacao (`xs`/`sob`), navegacao da tarefa, abertura de calendario, preenchimento de meses e confirmacao.
- Excluido: refatoracoes amplas de PEC, alteracao de contratos publicos e mudancas em modulos nao relacionados.

## Arquitetura/Dependencias
Fluxo alvo:
1. `PEC/regras_execucao.py` identifica regra de sobrestamento (`_sob_n`).
2. `_sob_n` chama `def_chip` e depois `mov_sob`.
3. `atos/movimentos_sobrestamento.py::mov_sob` abre tarefa, abre modal de prazo, preenche meses e confirma.

Arquivos base para comparacao legado:
- `leg/atos/movimentos_sobrestamento.py`
- `leg/PEC/regras_pec.py`

## Fase 1 - Diagnostico de divergencia com legado

### Task 1: Mapear chamadas reais do PEC para mov_sob
**Descricao:** Confirmar todos os caminhos do PEC que chamam `mov_sob` e quais formatos de observacao chegam (ex.: `sob 6`, `xs 6`, `xs sob 6`).

**Criterios de aceite:**
- [ ] Lista de callsites validada no modulo PEC.
- [ ] Amostra de observacoes reais capturada via log/trace.
- [ ] Identificada a variacao que falha no ambiente atual.

**Verificacao:**
- [ ] Conferencia estatica em `PEC/regras_execucao.py`.
- [ ] Execucao monitorada de 1 caso `xs` e 1 caso `sob`.

**Dependencias:** Nenhuma

**Arquivos provaveis:**
- `PEC/regras_execucao.py`
- `atos/movimentos_sobrestamento.py`

**Escopo estimado:** S


### Task 2: Comparar comportamento atual vs legado (mov_sob)
**Descricao:** Fazer diff funcional entre `atos/movimentos_sobrestamento.py` e `leg/atos/movimentos_sobrestamento.py` para identificar trechos que impactam robustez (detecao de aba, waits, confirmacao de sucesso, no-op por URL).

**Criterios de aceite:**
- [ ] Divergencias funcionais documentadas.
- [ ] Definido conjunto minimo de trechos a portar do legado.
- [ ] Confirmado que nao ha mudanca de assinatura publica.

**Verificacao:**
- [ ] Revisao lado a lado com checklist por etapa do fluxo (abrir tarefa, calendario, modal, prazo, prosseguir).

**Dependencias:** Task 1

**Arquivos provaveis:**
- `atos/movimentos_sobrestamento.py`
- `leg/atos/movimentos_sobrestamento.py`

**Escopo estimado:** S


## Checkpoint A (apos Fase 1)
- [ ] Causa raiz priorizada (parser, navegacao, ou confirmacao).
- [ ] Lista de alteracoes cirurgicas aprovada.


## Fase 2 - Correcao cirurgica orientada ao legado

### Task 3: Ajustar parser de observacao para xs/sob
**Descricao:** Garantir que `mov_sob` aceite de forma deterministica os formatos usados no PEC (`sob N`, `xs N`, `xs sob N`) sem quebrar comportamentos existentes.

**Criterios de aceite:**
- [ ] Parser extrai meses corretamente nos 3 formatos.
- [ ] Quando nao houver mes valido, retorno de falha explicita com log util.
- [ ] Sem alteracao de assinatura de `mov_sob`.

**Verificacao:**
- [ ] Teste rapido de parsing com entradas representativas.
- [ ] `py -m py_compile atos/movimentos_sobrestamento.py`.

**Dependencias:** Task 2

**Arquivos provaveis:**
- `atos/movimentos_sobrestamento.py`

**Escopo estimado:** S


### Task 4: Portar trechos de navegacao/confirmacao do legado
**Descricao:** Aplicar somente as partes do legado que aumentam confiabilidade na execucao do fluxo de sobrestamento (abrir tarefa correta, clicar calendario, preencher modal, confirmar e detectar sucesso).

**Criterios de aceite:**
- [ ] Fluxo executa ate clique em `Prosseguir` sem timeout espurio.
- [ ] Confirmacao de sucesso robusta (snackbar e/ou fechamento de modal).
- [ ] Sem regressao no comportamento de abertura de tarefa.

**Verificacao:**
- [ ] `py -m py_compile atos/movimentos_sobrestamento.py`.
- [ ] Execucao manual de 2 cenarios (um `xs`, um `sob`).

**Dependencias:** Task 3

**Arquivos provaveis:**
- `atos/movimentos_sobrestamento.py`

**Escopo estimado:** M


### Task 5: Ajustar chamada PEC para nao mascarar falha
**Descricao:** Revisar caminho `_sob_n` para garantir que a falha de `mov_sob` nao fique silenciosa e que o comportamento seja consistente com o legado.

**Criterios de aceite:**
- [ ] Resultado de `mov_sob` propagado corretamente no fluxo PEC.
- [ ] Logs de erro acionaveis em caso de falha.
- [ ] Sem impacto nos demais buckets de `regras_execucao`.

**Verificacao:**
- [ ] `py -m py_compile PEC/regras_execucao.py`.
- [ ] Teste manual de uma atividade que deve passar e outra que deve falhar.

**Dependencias:** Task 4

**Arquivos provaveis:**
- `PEC/regras_execucao.py`

**Escopo estimado:** S


## Checkpoint B (apos Fase 2)
- [ ] Fluxo PEC -> mov_sob funcional com observacao `xs/sob`.
- [ ] Meses de sobrestamento gravando no modal de prazo.
- [ ] Falhas deixando rastreabilidade clara em log.


## Fase 3 - Validacao final e seguranca de regressao

### Task 6: Validacao ponta a ponta com cenarios reais
**Descricao:** Rodar um conjunto minimo de cenarios reais para comprovar que a correcao resolve o caso reportado sem quebrar caminhos adjacentes.

**Criterios de aceite:**
- [ ] Cenario `xs sob N` concluido com sucesso.
- [ ] Cenario `sob N` concluido com sucesso.
- [ ] Cenario invalido falha de forma controlada e logada.

**Verificacao:**
- [ ] Execucao no fluxo PEC com processos de teste.
- [ ] Conferencia visual de valor de meses aplicado no modal.

**Dependencias:** Task 5

**Arquivos provaveis:**
- `atos/movimentos_sobrestamento.py`
- `PEC/regras_execucao.py`

**Escopo estimado:** S


## Riscos e mitigacoes
| Risco | Impacto | Mitigacao |
|---|---|---|
| Observacao chegar em formato nao previsto | Alto | Parser tolerante para `xs/sob` + erro explicito |
| No-op por URL mascarar problema real | Alto | Revisar regra de no-op e log de decisao |
| Diferencas sutis de timing UI PJe | Medio | Port cirurgico de waits do legado + fallback JS click |
| Regressao em fluxo PEC nao-sob | Medio | Limitar alteracoes aos callsites de `mov_sob` |


## Ordem de implementacao
1. Task 1
2. Task 2
3. Task 3
4. Task 4
5. Task 5
6. Task 6


## Pronto para execucao
- [ ] Plano aprovado
- [ ] Implementacao liberada