# Plan 20: Consolidacao Final — Punch List do Projeto de Simplificacao

> **Data:** 2026-05-04
> **Status:** ~96% codigo concluido, ~4% bloqueado por ambiente real.
> **Commit de rollback:** `2ab0fca`
> **Base:** README.md, odx.md, 19-pruning-final.md, erase.md, lx10-audit-report.md, 16-granular-fix.md, 18-pos-xcode-gaps.md, git status atual

---

## Sumario Executivo

O projeto de simplificacao xcode esta em sua reta final. De ~235 arquivos .py no escopo original, o projeto foi reduzido e consolidado em ~180 arquivos (incluindo shims). Foram executados 19 planos numerados de 00 a 19, resultando em:

- 4 modulos de negocio totalmente consolidados (Mandado, Prazo, PEC, SISB)
- Runtime Fix consolidado em 3 novos nucleos (facade_publica, browser_suporte, diagnostico_runtime)
- ~1.215 prints migrados para logger estruturado
- ~70 shims criados e gerenciados em 10 ondas de cleanup
- 28+ arquivos deletados da raiz (PEC/, carta/, bianca/, SISB/, Prazo/, etc.)
- 0 emojis em saida de log
- `test_imports.py` verde (0/14 falhas)

**O que falta:** essencialmente 3 categorias:
1. **BLOQUEADO (ambiente real):** smoke tests, validacao de harness, Triagem T3
2. **PENDENTE (codigo):** FX4 step 1 (safe_click_no_scroll), limpeza de `__pycache__`, 35 prints em `Fix/variaveis.py`
3. **FUTURO (fora do escopo imediato):** 77 bare excepts, 396+ time.sleep nos monolitos congelados

---

## 1. O Que Foi Feito

### 1.1 Security & Runtime Base (Phase 1)
- [x] **Task 1:** Credencial hardcoded removida de `Fix/utils.py:415` → `$env:PJE_CPF` / `$env:PJE_SENHA`
- [x] **Task 2:** `os._exit` removido de `x.py:847` → shutdown cooperativo com finally/cleanup
- [x] **Task 3:** Contrato unico de log e progresso em `Fix/log.py`

### 1.2 API Gateway Core (Phase 2)
- [x] **Task 4:** API Gateway Core criado (`api/variaveis_client.py`)
- [x] **Task 5:** PEC e Triagem migrados para API Core
- [x] **Task 6:** Mandado e Prazo migrados para API Core

### 1.3 Flow Engine Unificado (Phase 3)
- [x] **Task 7:** Engine generico criado (`utilitarios_processamento.py`)
- [x] **Task 8:** Mandado, Prazo, PEC adaptados ao engine
- [x] **Task 9:** Triagem, Peticao adaptados + imports tardios removidos de `x.py`

### 1.4 Reducao de Arquivos (Phase 4)
- [x] **Task 10:** Facades e wrappers de compatibilidade consolidados
- [x] **Task 11:** 16 `time.sleep` substituidos por `WebDriverWait` em 6 arquivos
- [x] **Task 12:** Shell `x.py` afinado de ~930 para ~630 linhas

### 1.5 Pruning Estrutural (Phase 5 — Erase)
- [x] **Lote 0:** Imports mortos em PEC/, SISB/, Fix/
- [x] **Lote 1:** Facades/re-exports redundantes
- [x] **Lote 2:** Helpers mortos em Fix e utilitarios
- [x] **Lote 3:** Funcoes mortas em modulos de negocio
- [x] **Lote 4:** Exclusao de `PEC/core_main.py` (unico arquivo inteiro qualificado)

### 1.6 Unified Rules-Action (Phase 6)
- [x] **Task 17:** `core/rule_registry.py` criado com `RuleRegistry` + `adapt_action`
- [x] **Task 18-22:** RuleRegistry migrado para PEC, Triagem, Mandado, Prazo, Peticao

### 1.7 Consolidacao de Modulos

| Modulo | Arquivos (antes) | Arquivos (depois) | Entrypoints | Status |
|--------|:-:|:-:|------|--------|
| **Mandado** | 10 | 4 (entrada_api, fluxo_argos, apoio_fluxos, regras) | `entrada_api.processar_mandados_devolvidos_api` | 5/5 |
| **Prazo** | 18 | 6 (loop_orquestrador, loop_lote, loop_execucao_final, p2b_gateway, p2b_regras_execucao, p2b_documentos) | `loop_prazo`, `processar_gigs_sem_prazo_p2b` | 4/4 |
| **PEC** | 11+ | 4 (runtime_pec, regras_execucao, carta_execucao, anexos/core) | `orquestrador.executar_fluxo_novo_simplificado` | 5/5 |
| **Triagem** | 12+ | 4 base (runtime_triagem, analise_execucao, coleta, regras) + dom | `runner.run_triagem`, `dom.run_dom` | 2/3 (T3 pendente) |
| **Peticao** | 8+ | 3 (runtime_pet, regras_execucao, suporte_pet) + congelados | `pet.run_pet` | 1/1 |
| **SISB** | 25+ | 7 (core, facades_contratos, ordens_dados_navegacao, ordens_execucao, relatorios_integracao, batch, performance) + subpacotes | `core.processar_ordem_sisbajud` | 5/5 |
| **Fix** | 40+ | 8 estruturais (4 congelados + 3 consolidados + 1 estabilizado) + 18 shims | Interface compartilhada | FX1/FX2/FX3 pronto; FX4 parcial |
| **atos/** | ~30 | 26 (mantidos) | Wrappers e regras | Protegido |

### 1.8 Fix — Consolidacao do Runtime (FX1-FX4)

| Nucleo | Arquivo | Origem | Linhas | Status |
|--------|---------|--------|:------:|--------|
| FX1 | `facade_publica.py` | 14+ shims (drivers, progress, scripts, element_wait, smart_finder, exceptions, documents, navigation, gigs, variaveis_*, selectors_pje, movimento_helpers) | ~595 | [x] |
| FX2 | `browser_suporte.py` | abas.py + headless_helpers.py + otimizacao_wrapper.py | ~560 | [x] |
| FX3 | `diagnostico_runtime.py` | log.py + debug_interativo.py + utils_observer.py + utils_tempo.py | ~403 | [x] |
| FX4 | Shims finais | Reduzir __init__, scripts, drivers, progress, selenium_base a shims; safe_click_no_scroll | — | [~] Parcial |

### 1.9 Gaps Corrigidos (G1-G5)

| Gap | Descricao | Severidade | Status |
|-----|-----------|:----------:|--------|
| G1 | 22 bare `except Exception` em `Fix/core.py` | Alta | [x] Logging adicionado (2 commits) |
| G2 | 16 `time.sleep` fixos em 6 arquivos | Media | [x] Substituidos por WebDriverWait |
| G3 | ~105 emojis em `logger.*()` | Media | [x] Removidos (SISB, Mandado, PEC, atos) |
| G4 | Bare `except:` em `x.py:195` (resetar_driver) | Alta | [x] Corrigido |
| G5 | `run_dom()` fora do FLOW_HANDLERS | Baixa | [x] Integrado como opcao H |

---

## 2. Metricas Finais

| Metrica | Valor | Fonte |
|---------|:-----:|-------|
| Arquivos .py no escopo original | ~235 | ODX |
| Arquivos .py ativos (estimado) | ~180 | Git status + glob |
| Arquivos deletados da raiz | 28+ | Git status |
| Thin shims criados | 35+ (14 Prazo, 8 Mandado, 12 SISB, 18 Fix, 5+ Peticao/Triagem) | ODX |
| Thin shims deletados em cleanup | ~70 (10 ondas W01-W10) | README |
| Prints migrados para logger | ~1.215+ | README, lx10-audit |
| Prints remanescentes (produção) | 0 (excluindo TUI/testes) | README Section 9.3 |
| Prints remanescentes (TUI/testes) | 63 (diagnostico_runtime/DebugInterativo) + 16 (f.py) + 5 (t3.py) + 3 (testpet.py) | Intencional |
| Prints NAO migrados (pendentes) | 35 em Fix/variaveis.py | Lx-10 pendente |
| Funcoes mortas removidas | 150+ | ODX |
| Imports mortos removidos | 800+ | ODX |
| Emojis em saida de log | 0 | README Section 9.3 |
| `test_imports.py` | 0/14 falhas (verde) | Confirmado |
| `time.sleep` nos 4 monolitos congelados | ~373 (core.py: 34, extracao.py: 77, utils.py: 52, variaveis.py: 0, browser_suporte.py: 16, facade_publica.py: 1) | Grep 2026-05-04 |
| Bare `except` sem logging (fora core.py) | ~55 espalhados | Grep 2026-05-04 |
| Arquivos consolidados criados | 10+ (entrada_api, fluxo_argos, apoio_fluxos, facades_contratos, ordens_dados_navegacao, ordens_execucao, relatorios_integracao, facade_publica, browser_suporte, diagnostico_runtime) | Contagem direta |

---

## 3. Tarefas Restantes

### 3.1 BLOQUEADO (requer ambiente real com driver)

Estas tarefas nao podem ser validadas sem acesso a um ambiente PJe real com Selenium WebDriver.

| ID | Tarefa | Descricao | Prioridade | Estimativa | Depende de | Gate |
|:--:|--------|-----------|:----------:|:----------:|:----------:|------|
| **G6** | Smoke tests Task 1+2 | Executar fluxo B com `$env:PJE_CPF`/`$env:PJE_SENHA` e validar Ctrl+C (shutdown cooperativo) | **Critica** | 1h | Nenhuma | Fluxo B roda sem credencial hardcoded; Ctrl+C encerra sem `os._exit` |
| **SMK-1** | Smoke fluxo A | Bloco completo: Mandado → Prazo → P2B → PEC | **Critica** | 2h | G6 | Cadeia completa executa sem erro |
| **SMK-2** | Smoke fluxo B | Mandado isolado | Alta | 30min | G6 | `processar_mandados_devolvidos_api()` OK |
| **SMK-3** | Smoke fluxo C | Prazo isolado | Alta | 30min | G6 | `loop_prazo()` OK |
| **SMK-4** | Smoke fluxo D | P2B isolado | Alta | 30min | G6 | `processar_gigs_sem_prazo_p2b()` OK |
| **SMK-5** | Smoke fluxo E | PEC isolado | Alta | 30min | G6 | `executar_fluxo_novo_simplificado()` OK |
| **SMK-6** | Smoke fluxo F | Triagem isolada | Alta | 30min | G6 | `run_triagem()` OK |
| **SMK-7** | Smoke fluxo G | Peticao isolada | Alta | 30min | G6 | `run_pet()` OK |
| **SMK-8** | Smoke fluxo H | Analise DOM | Media | 30min | G6 | `run_dom()` OK |
| **ERASE-3** | Validacao erase.md Fase 3 | Executar harness `f.py` em ambiente real ate relatorio/juntada | Alta | 1h | G6 | `processar_ordem_sisbajud` executa completamente com todas as etapas |
| **T3** | Triagem T3 — facades finais + pruning | Consolidar `__init__.py` em facade fina, reduzir shims de `runner.py`, `service.py`, `acoes.py`, `citacao.py` | Media | 2h | SMK-6 | `test_imports.py` verde; Triagem __init__.py vira facade fina |

### 3.2 PENDENTE (pode ser feito agora, sem ambiente real)

| ID | Tarefa | Descricao | Prioridade | Estimativa | Depende de | Gate |
|:--:|--------|-----------|:----------:|:----------:|:----------:|------|
| **FX4-1** | safe_click_no_scroll → browser_suporte.py | Mover `safe_click_no_scroll` de `selenium_base/click_operations.py` para `browser_suporte.py` e criar shim | **Em andamento** | 30min | Nenhuma | `py test_imports.py` verde; `from Fix.browser_suporte import safe_click_no_scroll` funciona |
| **FX4-2** | Converter errors.py para facade_publica | Unificar `Fix/errors.py` (classes reais) e `Fix/exceptions.py` (shim); garantir que facade_publica seja o unico source de excecoes | Baixa | 15min | Nenhuma | `from Fix.errors import *` continua funcionando via shim |
| **Lx-VAR** | Migrar 35 prints em Fix/variaveis.py | Converter para logger estruturado conforme regras R1-R5 | Media | 30min | Nenhuma | `grep -c "print(" Fix/variaveis.py` = 0 |
| **CACHE** | Limpar `__pycache__` de todos os modulos | Remover diretorios `__pycache__` do projeto | Baixa | 5min | Nenhuma | Nenhum `__pycache__` existe |
| **CORE** | Verificar `core/resultado_execucao.py` | Confirmar que `ResultadoExecucao` e usado por todos os handlers e nao conflita com `core/` | Baixa | 15min | Nenhuma | Compilacao OK |
| **PRUNE-1** | Remover `import traceback` redundante do topo de `x.py` | Task 1 de 19-pruning-final.md | Baixa | 5min | Nenhuma | `py -m py_compile x.py` OK |
| **PRUNE-2** | Confirmar estado de arquivos 19-pruning-final | Verificar git status — ha arquivos ` D` (unstaged delete) e `D ` (staged delete). Confirmar que Tasks 2-14 estao completas conforme planejado | Media | 15min | Nenhuma | `git status` limpo para os arquivos-alvo |
| **PRUNE-3** | Commit do pruning 19 pendente | Staging e commit dos arquivos ja deletados que ainda estao como ` D` (unstaged) | Media | 15min | PRUNE-2 | `git status` sem ` D` dos arquivos-alvo |

### 3.3 EM ANDAMENTO (background tasks)

| ID | Tarefa | Quem | Status | Notas |
|:--:|--------|:----:|:------:|-------|
| **FX1** | Criar facade_publica.py a partir de 14+ shims | Agente | [x] Concluido | Arquivo existe com ~595 linhas; todos os shims apontam para ele |
| **FX4-1** | Mover safe_click_no_scroll para browser_suporte.py | Agente | [~] Rodando agora | Step 1 da FX4 |

### 3.4 FUTURO (fora do escopo imediato da simplificacao)

Estes itens sao deliberadamente excluidos do escopo do projeto xcode, mas registrados para governanca futura.

| ID | Item | Escopo | Impacto | Esforco Estimado |
|:--:|------|--------|:-------:|:----------------:|
| **FUT-1** | 77 bare `except` generalizados | Fora de `Fix/core.py` (que ja foi tratado — G1), ha ~55 bare excepts espalhados | Erros silenciosos em producao | 4-8h |
| **FUT-2** | 396+ `time.sleep` nos 4 monolitos congelados | `Fix/core.py` (34), `Fix/extracao.py` (77), `Fix/utils.py` (52), `Fix/browser_suporte.py` (16), demais modulos | Latencias arbitrarias, flaky tests | 20-40h |
| **FUT-3** | Reabrir monolitos congelados | `Fix/core.py` (3258), `Fix/extracao.py` (2117), `Fix/utils.py` (2013), `Fix/variaveis.py` (1138) | Arquivos muito grandes, dificuldade de manutencao | 30-60h |
| **FUT-4** | Framework de testes Selenium | Infraestrutura de CI com driver real | Qualidade e regressao | 20-40h |
| **FUT-5** | Tipos formais (TypedDict) | `normalizar_resultado()` com `Dict[str, Any]` | Seguranca de tipos | 4-8h |
| **FUT-6** | Consolidar Fix/selenium_base/ | 5 arquivos (click_operations, retry_logic, wait_operations, element_interaction, __init__) que importam dos monolitos congelados | Clareza arquitetural | 2-4h |

---

## 4. Tabela de Arquivos por Modulo (Antes vs Depois da Simplificacao)

### 4.1 Mandado/

| Antes | Depois | Status |
|-------|--------|--------|
| `processamento_api.py` + `utils.py` + `utils_intimacao.py` | `entrada_api.py` (618) | Consolidado |
| `processamento_argos.py` + `processamento_anexos.py` | `fluxo_argos.py` (671) | Consolidado |
| `processamento_outros.py` + `utils_sigilo.py` + `utils_lembrete.py` + `atos_wrapper.py` | `apoio_fluxos.py` (785) | Consolidado |
| `regras.py` | `regras.py` (618) | Congelado |
| `processamento_fluxo.py` | Shim | Mantido |
| `core.py` | Mantido | Independente |
| `__init__.py` | Limpo | Facade |

**Resultado:** 10 arquivos → 4 base + 1 shim + 2 independentes.
**Deletados:** atos_wrapper.py, processamento_anexos.py, processamento_api.py, processamento_argos.py, processamento_fluxo.py, processamento_outros.py, utils.py, utils_intimacao.py, utils_lembrete.py, utils_sigilo.py.

### 4.2 Prazo/

| Antes | Depois | Status |
|-------|--------|--------|
| `__init__.py` + `loop_base.py` + `loop_helpers.py` + `loop_api.py` + `loop_ciclo1.py` | `loop_orquestrador.py` (~554) | Consolidado |
| `loop_ciclo1_filtros.py` + `loop_ciclo1_movimentacao.py` + `loop_ciclo2_selecao.py` | `loop_lote.py` (~553) | Consolidado |
| `loop_ciclo2_processamento.py` + `loop_ciclo3.py` | `loop_execucao_final.py` (~514) | Consolidado |
| `fluxo_api.py` + `p2b_api.py` + `p2b_fluxo.py` + `p2b_fluxo_helpers.py` | `p2b_gateway.py` (~506) | Consolidado |
| `p2b_core.py` + `criteria_matcher.py` | `p2b_regras_execucao.py` (~527) | Consolidado |
| `p2b_fluxo_documentos.py` + `p2b_fluxo_regras.py` | `p2b_documentos.py` (~633) | Consolidado |
| +14 thin shims | Shim | Mantidos |

**Resultado:** 18 arquivos → 6 base + 14 shims.
**Deletados:** criteria_matcher.py, fluxo_api.py, loop_api.py, loop_base.py, loop_ciclo1.py, loop_ciclo1_filtros.py, loop_ciclo1_movimentacao.py, loop_ciclo2_processamento.py, loop_ciclo2_selecao.py, loop_ciclo3.py, loop_helpers.py, p2b_api.py, p2b_fluxo.py, p2b_fluxo_documentos.py, p2b_fluxo_helpers.py, p2b_fluxo_regras.py, p2b_prazo.py, t3.py.

### 4.3 PEC/

| Antes | Depois | Status |
|-------|--------|--------|
| `orquestrador.py` + `api_client.py` + `helpers.py` + `core_progresso.py` + `carta_formatacao.py` + `carta_utils.py` | `runtime_pec.py` (~570) | Consolidado |
| `regras_pec.py` + `sobrestamento.py` | `regras_execucao.py` (~509) | Consolidado |
| `carta.py` + `carta_ecarta.py` | `carta_execucao.py` (~569) | Consolidado |
| `anexos/core.py` | `anexos/core.py` (>600) | Congelado |
| `core_navegacao.py`, `core_pos_carta.py`, `prescricao.py` | Mantidos | Congelados |

**Resultado:** 11+ arquivos → 4 base + congelados.
**Deletados:** ajuste_gigs.py, carta.py, carta_ecarta.py, core.py, core_main.py, core_recovery.py, processamento.py, processamento_buckets.py, processamento_fluxo.py, processamento_indexacao.py, processamento_listas.py, sisbajud_driver.py.

### 4.4 Triagem/

| Antes | Depois | Status |
|-------|--------|--------|
| `runner.py` + `api.py` + `driver.py` + `constants.py` | `runtime_triagem.py` (505) | Consolidado (T1) |
| `service.py` + `acoes.py` + `preprocess.py` + `citacao.py` + `utils.py` | `analise_execucao.py` (902) | Consolidado (T2) |
| `coleta.py` | `coleta.py` (540) | Congelado |
| `regras.py` | `regras.py` (876) | Congelado |
| `dom.py` | `dom.py` (918) | Congelado (opcao H) |
| `runner.py` | Shim (1 linha) | T3 pendente |

**Pendente (T3):** `__init__.py` → facade fina; verificar se service.py, acoes.py, citacao.py, api.py, driver.py, constants.py viram shims.

### 4.5 Peticao/

| Antes | Depois | Status |
|-------|--------|--------|
| `pet.py` + `orquestrador.py` + `api_client.py` + `progresso.py` + `core/utils/utils.py` + `core/utils/observer.py` | `runtime_pet.py` (701) | Consolidado (PT1) |
| `regras.py` + `atos/wrappers.py` | `regras_execucao.py` (~563) | Consolidado |
| `core/log.py` + `consolida_delete.py` | `suporte_pet.py` (~505) | Consolidado |
| `core/extracao/extracao.py` | Congelado (514) | Mantido |
| `helpers/helpers.py` | Congelado (603) | Mantido |

### 4.6 SISB/

| Antes | Depois | Status |
|-------|--------|--------|
| `__init__.py` + `processamento.py` + `processamento/__init__.py` + `standards.py` + `s_orquestrador.py` + todos `__init__.py` de subpacotes | `facades_contratos.py` (662) + 12 shims | Consolidado (SX1) |
| `ordens/processor.py` + `navigation/navigator.py` | `ordens_dados_navegacao.py` (590) | Consolidado (SX2) |
| `processamento_ordens_processamento.py` + `validation/processor.py` | `ordens_execucao.py` (510) | Consolidado (SX3) |
| `relatorios/generator.py` + `integration/pje_integration.py` | `relatorios_integracao.py` (598) | Consolidado (SX4) |
| `core.py` | `core.py` (1123) | Congelado |
| `batch.py` | Mantido | Preservado |
| `performance.py` | Mantido | Preservado |

**Deletados:** standards.py, s_orquestrador.py, processamento.py (plano), integration/, minutas/, navigation/, ordens/, relatorios/, series/, validation/, processamento_ordens_processamento.py.

### 4.7 Fix/ (Runtime)

| Antes | Depois | Status |
|-------|--------|--------|
| 14+ shims (drivers, progress, scripts, element_wait, smart_finder, exceptions, documents, navigation, gigs, variaveis_*, selectors_pje, movimento_helpers) | `facade_publica.py` (~595) | Consolidado (FX1) |
| `abas.py` + `headless_helpers.py` + `otimizacao_wrapper.py` | `browser_suporte.py` (~560) | Consolidado (FX2) |
| `log.py` + `debug_interativo.py` + `utils_observer.py` + `utils_tempo.py` | `diagnostico_runtime.py` (~403) | Consolidado (FX3) |
| `monitoramento_progresso_unificado.py` | Estabilizado (592) | Mantido |
| `core.py`, `extracao.py`, `utils.py`, `variaveis.py` | Congelados | 4 monolitos |
| `errors.py` | Mantido | Fonte de excecoes |
| `selenium_base/*` | Mantido (5 arquivos) | Fora do escopo |

**Estrutura final do Fix/:**
```
Fix/
  core.py (3258) CONGELADO
  extracao.py (2117) CONGELADO
  utils.py (2013) CONGELADO
  variaveis.py (1138) CONGELADO
  facade_publica.py (~595) NOVO — facade principal
  browser_suporte.py (~560) NOVO — suporte de browser
  diagnostico_runtime.py (~403) NOVO — diagnostico/instrumentacao
  monitoramento_progresso_unificado.py (592) ESTAVEL
  errors.py (17) FONTE — excecoes
  __init__.py FACADE — reexporta de facade_publica + diagnostico_runtime
  selenium_base/ (5) FORA DE ESCOPO — compatibilidade
  [18 shims apontando para facade_publica, browser_suporte, diagnostico_runtime]
```

---

## 5. Dependencias entre Tarefas Restantes

```
                    FUTURO (fora de escopo)
                    ┌──────────────────────────────────┐
                    │ FUT-1: 77 bare excepts           │
                    │ FUT-2: 396+ time.sleep           │
                    │ FUT-3: Reabrir monolitos         │
                    │ FUT-4: Testes Selenium           │
                    │ FUT-5: TypedDict                 │
                    │ FUT-6: selenium_base/            │
                    └──────────────────────────────────┘
                              ▲
                              │ (decisao de escopo)
                    ┌──────────────────────────────────┐
                    │     FX4-1: safe_click_no_scroll  │ ← EM ANDAMENTO
                    │     Lx-VAR: Fix/variaveis.py     │
                    │     PRUNE-1..3: pruning final    │
                    │     CACHE: __pycache__           │
                    │     CORE: resultado_execucao.py  │
                    └──────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────────────────────┐
                    │ G6 → SMK-1..8 → ERASE-3 → T3    │ ← BLOQUEADO (ambiente real)
                    └──────────────────────────────────┘
```

---

## 6. Gates Finais de Aceitacao

### 6.1 Gate de Codigo (pode ser verificado agora)

- [ ] `test_imports.py` — 0/14 falhas (verde)
- [ ] `py -m py_compile Fix/*.py` — todos compilam
- [ ] `py -m py_compile Mandado/*.py` — todos compilam
- [ ] `py -m py_compile Prazo/*.py` — todos compilam
- [ ] `py -m py_compile PEC/*.py` — todos compilam
- [ ] `py -m py_compile Triagem/*.py` — todos compilam
- [ ] `py -m py_compile Peticao/*.py` — todos compilam
- [ ] `py -m py_compile SISB/*.py` — todos compilam
- [ ] `py -m py_compile x.py` — compila
- [ ] Zero `print()` em producao (excluindo TUI/testes) — 35 prints em Fix/variaveis.py precisam migrar
- [ ] Zero emojis em saida de log

### 6.2 Gate de Ambiente Real (requer driver)

- [ ] G6: Smoke Task 1 (fluxo B com `$env:PJE_CPF` / `$env:PJE_SENHA`)
- [ ] G6: Smoke Task 2 (Ctrl+C = shutdown cooperativo sem `os._exit`)
- [ ] SMK-1: Fluxo A completo (Mandado → Prazo → P2B → PEC)
- [ ] SMK-2: Fluxo B (Mandado isolado)
- [ ] SMK-3: Fluxo C (Prazo isolado)
- [ ] SMK-4: Fluxo D (P2B isolado)
- [ ] SMK-5: Fluxo E (PEC isolado)
- [ ] SMK-6: Fluxo F (Triagem isolada)
- [ ] SMK-7: Fluxo G (Peticao isolada)
- [ ] SMK-8: Fluxo H (Analise DOM)
- [ ] ERASE-3: Harness `f.py` executa ate relatorio/juntada
- [ ] T3: Triagem facades finais e pruning validados
- [ ] Sem segredos hardcoded (confirmado por smoke)

### 6.3 Gate de Regressao

- [ ] 3 execucoes consecutivas de fluxo B sem flake
- [ ] 3 execucoes consecutivas de fluxo E sem flake
- [ ] 3 execucoes consecutivas de fluxo F sem flake
- [ ] Degradacao de desempenho < 15% vs baseline `2ab0fca`

---

## 7. Checklist de Arquivos Deletados (19-pruning-final)

### Phase 1: x.py micro-correcao
- [ ] Task 1: `import traceback` redundante removido do topo de `x.py`

### Phase 2: Prazo (CONCLUIDO via git)
- [x] Task 2: `Prazo/p2b_prazo.py` deletado
- [x] Task 3: `Prazo/t3.py` deletado

### Phase 3: SISB (CONCLUIDO via git)
- [x] Task 4: `SISB/standards.py` deletado
- [x] Task 5: `SISB/s_orquestrador.py` deletado
- [x] Task 6: `SISB/processamento.py` (plano) deletado
- [x] Task 7: `SISB/series/` e `SISB/minutas/` deletados

### Phase 4: PEC (CONCLUIDO via git)
- [x] Task 8: `PEC/core.py` deletado
- [x] Task 9: `PEC/core_recovery.py` deletado
- [x] Task 10: 5x `PEC/processamento_*.py` deletados
- [x] Task 11: `PEC/sisbajud_driver.py` e `PEC/ajuste_gigs.py` deletados
- [x] Task 12: `PEC/carta.py` e `PEC/carta_ecarta.py` deletados

### Phase 5: Pastas raiz (CONCLUIDO via git)
- [x] Task 13: `carta/` raiz deletado
- [x] Task 14: `bianca/` deletado

**Nota:** Status do git mostra alguns arquivos como ` D` (unstaged delete) e outros como `D ` (staged delete). Todos os arquivos-alvo estao deletados do filesystem. Pendente: unificar staging e commit.

---

## 8. Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|:------------:|:-------:|-----------|
| Smoke test falha em fluxo que nunca foi executado apos refatoracao | Media | Critico | Executar canario (fluxo B primeiro); reverter commit especifico se falhar |
| Regressao de import apos pruning de shim | Baixa | Alto | `test_imports.py` como gate obrigatorio antes de todo commit |
| time.sleep removido causa timing diferente em ambiente lento | Media | Medio | Manter sleeps nos monolitos congelados; substituir apenas nos consolidados |
| facade_publica.py perde compatibilidade com import legado | Baixa | Alto | Todos os 14+ shims apontam para facade_publica; `test_imports.py` valida contratos |
| `Fix.utils_sleep` nao existe mais, mas `SISB.core` ainda faz lazy import | Media | Medio | Harness `f.py` tem shim local; solucao definitiva requer refatoracao do import em SISB |

---

## 9. Artefatos do Projeto

### 9.1 Planos Executados (00 a 19)

| Plano | Conteudo | Status |
|:-----:|----------|:------:|
| 00 | Mapa de execucao real do x.py | Concluido |
| 01 | Revisao geral e achados | Concluido |
| 02 | Arquitetura alvo (nucleo enxuto) | Concluido |
| 03 | Plano de fases incrementais | Concluido |
| 04 | Matriz de dependencias | Concluido |
| 05 | Politica de testes e rollout | Concluido |
| 06 | Consolidacao de funcoes e pruning | Concluido |
| 07 | Analise granular do x.py | Concluido |
| 08 | Unified Rules-Action Orchestration | Concluido |
| 09 | Plano atos/anexos unificacao | Concluido |
| 10 | Padronizacao de logs | Concluido |
| 11 | Granular Mandado | Concluido |
| 12 | Granular Prazo | Concluido |
| 13 | Granular PEC | Concluido |
| 14 | Granular Triagem | Concluido |
| 15 | Granular Peticao | Concluido |
| 16 | Granular Fix (FX1-FX4) | FX1, FX2, FX3 concluidos; FX4 parcial |
| 17 | Granular SISB | Concluido |
| 18 | Gaps pos-refatoracao (G1-G6) | G1-G5 concluidos; G6 pendente |
| 19 | Pruning final (14 tasks) | Tasks 2-14 concluidas; Task 1 pendente |

### 9.2 Arquivos de Suporte

| Arquivo | Conteudo |
|---------|----------|
| `erase.md` | Plano completo de limpeza com fases e auditoria AST |
| `lx10-audit-report.md` | Auditoria final de prints e emojis |
| `odx.md` | Dashboard de implementacao e progresso global |
| `README.md` | Visao geral do projeto de simplificacao |

---

## 10. Resumo de 10 Segundos

```
Concluido: 96% — 19 planos executados, ~235 → ~180 arquivos,
            ~1215 prints migrados, 0 emojis, 0/14 test_imports.

Bloqueado: Smoke tests (G6, SMK-1..8, ERASE-3, T3) — requer ambiente real.

Pendente:  FX4-1 (safe_click_no_scroll), Lx-VAR (35 prints em Fix/variaveis.py),
           PRUNE-1..3 (commit pruning), CACHE (__pycache__), CORE (resultado_execucao.py).

Futuro:    77 bare excepts, 396+ time.sleep, reabrir 4 monolitos congelados,
           framework de testes Selenium.
```
