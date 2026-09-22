# xcode — Plano de Simplificacao do Projeto PjePlus

> **Status:** Refatoracao estrutural ~96% concluida. Restam apenas smoke tests manuais em ambiente real.
> **Atualizado:** 2026-05-04 | **Base:** 25+ documentos de plano e auditoria

---

## Sumario Executivo

O diretorio `xcode/` e o centro de governanca da simplificacao do projeto PjePlus. Todo o trabalho de refatoracao foi planejado, executado e auditado a partir daqui. O orquestrador `x.py` e a raiz de tudo — toda decisao de cortar, consolidar ou congelar e validada pelo grafo de execucao real enraizado nele.

### Metricas consolidadas

| Metrica | Valor |
|---------|-------|
| Arquivos .py no escopo | ~235 |
| Prints migrados para logger | ~1.215+ |
| Prints remanescentes em producao | 0 |
| Funcoes mortas removidas | 150+ |
| Imports mortos removidos | 800+ |
| Arquivos deletados da raiz | 28 |
| Thin shims criados | 70+ |
| Modulos com 0 prints ativos | Mandado, carta, SISB, PEC, Triagem, Peticao, atos |
| `test_imports.py` | 0/14 falhas (verde) |

---

## 1. Diagnostico Inicial (Fase 0)

### 1.1 Mapa de execucao real

O orquestrador `x.py` expoe 7 fluxos via menu (A-G) + opcao H (analise DOM). Cada fluxo tem um entrypoint bem definido:

| Fluxo | Descricao | Entrypoint real |
|-------|-----------|-----------------|
| A | Bloco completo | Mandado → Prazo → P2B → PEC |
| B | Mandado isolado | `Mandado.processamento_api.processar_mandados_devolvidos_api()` |
| C | Prazo isolado | `Prazo.loop_prazo()` |
| D | P2B isolado | `Prazo.fluxo_api.processar_gigs_sem_prazo_p2b()` |
| E | PEC isolado | `PEC.orquestrador.executar_fluxo_novo_simplificado()` |
| F | Triagem isolada | `Triagem.runner.run_triagem()` |
| G | Peticao isolada | `Peticao.pet.run_pet()` |
| H | Analise DOM | `Triagem.dom.run_dom()` |

### 1.2 Achados criticos da revisao inicial

**Critical (corrigido):**
- **Credencial hardcoded** em `Fix/utils.py:415` → movida para `$env:PJE_CPF` / `$env:PJE_SENHA` (Task 1)
- **`os._exit`** em `x.py:847` → substituido por shutdown cooperativo com finally/cleanup (Task 2)

**Required (corrigido):**
- **Imports tardios** em `x.py` (linhas 624, 649, 675) → movidos para o topo (Task 9)
- **Duplicacao de cliente API JS com XSRF** em Mandado, Prazo, PEC, Triagem → API Gateway Core unificado (Tasks 4-6)
- **Mistura de print e logging** → ~1.215 prints migrados para logger estruturado (Fase 3)
- **Sleeps e waits heterogeneos** → 16 `time.sleep` substituidos por `WebDriverWait` (G2)

**Optional (corrigido):**
- **x.py concentrava responsabilidades demais** → reduzido de ~930 para ~630 linhas (Task 12)

---

## 2. Arquitetura Alvo (Fase 1-2)

### 2.1 Quatro nucleos

```
┌─────────────────────────────────────────────────────┐
│                  x.py (shell)                       │
│  menu → FLOW_HANDLERS → _executar_fluxo → resumo    │
└──────────────┬──────────────────────────────────────┘
               │
    ┌──────────┼──────────┬──────────┬──────────┐
    ▼          ▼          ▼          ▼          ▼
 Runtime    API        Flow       Rule       Modulos
 Core       Gateway    Engine     Registry   Negocio
```

1. **Runtime Core** (`Fix/core.py`): driver, login, shutdown, telemetria
2. **API Gateway Core** (`api/variaveis_client.py`): fetch autenticado com XSRF + paginacao
3. **Flow Engine Core** (`utilitarios_processamento.py`): pipeline `run_batch(items, should_skip, open_item, execute_item, persist_result)`
4. **Rule Registry** (`core/rule_registry.py`): `RuleRegistry` com `register(pattern, bucket, action)` + `match(observacao)`

### 2.2 Principios

- API-first sempre que endpoint autenticado existir
- Browser DOM apenas para etapa que exige interacao visual
- Um unico pipeline por processo reutilizado em todos os modulos
- Um unico runtime de driver, login, logging e progresso
- Contratos simples e parametrizaveis antes de criar funcao isolada

---

## 3. Plano de Fases (Fase 1-6)

### Phase 1: Seguranca e Base de Runtime — CONCLUIDA

| Task | Descricao | Status |
|------|-----------|--------|
| 1 | Remover credencial hardcoded → `PJE_CPF`/`PJE_SENHA` via env | [x] Codigo, [~] Smoke |
| 2 | Shutdown cooperativo (remover `os._exit`) | [x] Codigo, [~] Smoke |
| 3 | Contrato unico de log e progresso (`Fix/log.py`) | [x] |

### Phase 2: API Core Unificado — CONCLUIDA

| Task | Descricao | Status |
|------|-----------|--------|
| 4 | Criar API Gateway Core (`api/variaveis_client.py`) | [x] |
| 5 | Migrar PEC e Triagem para API Core | [x] |
| 6 | Migrar Mandado e Prazo para API Core | [x] |

### Phase 3: Flow Engine Unificado — CONCLUIDA

| Task | Descricao | Status |
|------|-----------|--------|
| 7 | Criar engine generico (`utilitarios_processamento.py`) | [x] |
| 8 | Adaptar Mandado, Prazo e PEC ao engine | [x] |
| 9 | Adaptar Triagem e Peticao ao engine + remover imports tardios | [x] |

### Phase 4: Reducao de Arquivos — CONCLUIDA

| Task | Descricao | Status |
|------|-----------|--------|
| 10 | Consolidar facades e wrappers de compatibilidade | [x] |
| 11 | Padronizar waits e remover sleeps nos caminhos ativos | [x] |
| 12 | Afinar shell do `x.py` (driver code → `Fix/core.py`) | [x] |

### Phase 5: Pruning Estrutural — CONCLUIDA

| Lote | Escopo | Status |
|------|--------|--------|
| Lote 0 | Imports mortos (PEC/, SISB/, Fix/) | [x] |
| Lote 1 | Facades/re-exports redundantes | [x] |
| Lote 2 | Helpers mortos em Fix e utilitarios | [x] |
| Lote 3 | Funcoes mortas em modulos de negocio | [x] |
| Lote 4 | Exclusao de arquivo inteiro (so `PEC/core_main.py` qualificou) | [x] |

### Phase 6: Unified Rules-Action — CONCLUIDA

| Task | Descricao | Status |
|------|-----------|--------|
| 17 | Criar `core/rule_registry.py` com `RuleRegistry` + `adapt_action` | [x] |
| 18 | Migrar PEC para RuleRegistry | [x] |
| 19 | Criar `Triagem/regras.py` + migrar | [x] |
| 20 | Criar `Mandado/regras.py` + migrar | [x] |
| 21 | Criar `Prazo/regras.py` + migrar | [x] |
| 22 | Criar `Peticao/regras.py` + migrar | [x] |

### Plano complementar: Atos + Anexos

Unificacao dos dominios `atos/` (judicial, comunicacao, movimentos) e `PEC/anexos/` sob nucleo comum. Quatro fases, 8 tasks. A facade `PEC/anexos` foi preservada como compatibilidade; `atos/anexos` tornou-se o owner funcional.

---

## 4. Padronizacao de Logs (Fase 3)

### 4.1 Regras absolutas

1. **Sem emojis** — `✅❌⚠️🔄ℹ️` substituidos por texto limpo
2. **Mensagens diretas** — passos intermediarios bem-sucedidos sao removidos ou viram `logger.debug()`
3. **Sucesso silencioso** — INFO/DEBUG suprimidos em producao; so resumo final visivel
4. **Erro localizado** — `logger.error("ERRO em <funcao>: %s: %s", type(e).__name__, e)`

### 4.2 Formatos de log

```
# INFO (producao):
HH:MM:SS [modulo] mensagem

# ERROR (producao, inclui funcName):
HH:MM:SS [modulo] ERRO em <funcao>: ExcType: mensagem
```

### 4.3 Regras de transformacao (R1-R5)

| Regra | Cenario | Transformacao |
|-------|---------|---------------|
| R1 | Sucesso simples | Remover ou `logger.debug()` |
| R2 | Aviso/retry | `logger.warning()` |
| R3 | Erro final | `logger.error()` com tipo + origem |
| R4 | Resumo de bloco | `logger.info()` com formato limpo |
| R5 | Encapsulador | Nao loga — so relanca ou retorna |

### 4.4 Ondas de migracao (Lx-1 a Lx-10)

| Onda | Escopo | Prints migrados |
|------|-------|-----------------|
| Lx-1 | `Fix/log.py` — CustomFormatter com formatos por nivel | — |
| Lx-2 | `x.py` — 98 prints | 98 |
| Lx-3 | `Fix/utils.py` + `Fix/extracao.py` — 288 prints | 288 |
| Lx-4 | `Fix/core.py` — 245 prints (retry logic, multi-strategy clicks) | 245 |
| Lx-5 | `carta/carta.py` + `carta/anexos.py` — ~244 prints | 244 |
| Lx-6 | `Fix/abas.py` — ~69 prints | 69 |
| Lx-7 | `Triagem/coleta.py` + `acoes.py` + `runner.py` — ~113 prints | 113 |
| Lx-8 | `PEC/processamento_buckets.py` + `PEC/anexos/` + `Peticao/helpers` — ~92 prints | 92 |
| Lx-9 | `SISB/processamento_ordens_processamento.py` + `Fix/variaveis.py` — ~69 prints | 69 |
| Lx-10 | Audit final: 7 ondas adicionais, ~145 prints | 145 |

**Total: ~1.215 prints migrados, 0 prints ativos em producao.**

*Excecoes intencionais (NAO migrar):* `Fix/debug_interativo.py` (63, TUI), `f.py` (16, script de teste), `Prazo/t3.py` (5, teste), `Peticao/testpet.py` (3, teste).

---

## 5. Granularizacao Modular (Fase 4)

### 5.1 Visao geral

Cada modulo de negocio foi submetido a duas etapas: **refino** (cercar superficie, documentar) e **consolidacao** (fundir arquivos pequenos em unidades de 400-800 linhas). Monolitos acima de 600 linhas foram **congelados** — nao quebrados nem movidos.

### 5.2 Mandado — 5/5 concluido

**Entrypoint real:** `Mandado.entrada_api.processar_mandados_devolvidos_api()`

| Arquivo final | Origem | Linhas |
|---------------|--------|--------|
| `entrada_api.py` | `processamento_api.py` + `utils.py` + `utils_intimacao.py` | 618 |
| `fluxo_argos.py` | `processamento_argos.py` + `processamento_anexos.py` | 671 |
| `apoio_fluxos.py` | `processamento_outros.py` + `utils_sigilo.py` + `utils_lembrete.py` + `atos_wrapper.py` | 785 |
| `regras.py` | Congelado | 618 |

**Resultado:** De 10 arquivos no caminho real para 4. `processamento_fluxo.py` virado thin shim.

### 5.3 Prazo — 4/4 concluido

**Entrypoints reais:** `Prazo.loop_prazo()` (fluxo C) e `Prazo.p2b_gateway.processar_gigs_sem_prazo_p2b()` (fluxo D)

| Arquivo final | Origem | Linhas |
|---------------|--------|--------|
| `loop_orquestrador.py` | `__init__.py` + `loop_base.py` + `loop_helpers.py` + `loop_api.py` + `loop_ciclo1.py` | ~554 |
| `loop_lote.py` | `loop_ciclo1_filtros.py` + `loop_ciclo1_movimentacao.py` + `loop_ciclo2_selecao.py` | ~553 |
| `loop_execucao_final.py` | `loop_ciclo2_processamento.py` + `loop_ciclo3.py` | ~514 |
| `p2b_gateway.py` | `fluxo_api.py` + `p2b_api.py` + `p2b_fluxo.py` + `p2b_fluxo_helpers.py` | ~506 |
| `p2b_regras_execucao.py` | `p2b_core.py` + `criteria_matcher.py` | ~527 |
| `p2b_documentos.py` | `p2b_fluxo_documentos.py` + `p2b_fluxo_regras.py` | ~633 |

**Resultado:** De 18 arquivos para 6. 14 thin shims criados. `checar_prox` preservado (dependencia de `Mandado/regras.py`).

### 5.4 PEC — 5/5 concluido

**Entrypoint real:** `PEC.orquestrador.executar_fluxo_novo_simplificado()`

| Arquivo final | Origem | Linhas |
|---------------|--------|--------|
| `runtime_pec.py` | `orquestrador.py` + `api_client.py` + `helpers.py` + `core_progresso.py` + `carta_formatacao.py` + `carta_utils.py` | ~570 |
| `regras_execucao.py` | `regras_pec.py` + `sobrestamento.py` | ~509 |
| `carta_execucao.py` | `carta.py` + `carta_ecarta.py` | ~569 |
| `anexos/core.py` | Congelado | >600 |

**Resultado:** De 11 arquivos para 4. `processamento_*` removidos do centro estrutural.

### 5.5 Triagem — 2/3 concluido (T3 pendente)

**Entrypoint real:** `Triagem.runner.run_triagem()`

| Arquivo final | Origem | Linhas |
|---------------|--------|--------|
| `runtime_triagem.py` | `runner.py` + `api.py` + `driver.py` + `constants.py` | 505 |
| `analise_execucao.py` | `service.py` + `acoes.py` + `preprocess.py` + `citacao.py` + `utils.py` | 902 |
| `coleta.py` | Mantido como esta | 540 |
| `regras.py` | Congelado | 876 |

**Nota:** `dom.py` (918 linhas) esta fora do caminho do handler F. Foi integrado como opcao H no menu (G5). T3 (facades finais) depende de smoke real.

### 5.6 Peticao — 1/1 concluido

**Entrypoint real:** `Peticao.pet.run_pet()`

| Arquivo final | Origem | Linhas |
|---------------|--------|--------|
| `runtime_pet.py` | `pet.py` + `orquestrador.py` + `api_client.py` + `progresso.py` + `core/utils/utils.py` + `core/utils/observer.py` | 701 |
| `regras_execucao.py` | `regras.py` + `atos/wrappers.py` | ~563 |
| `suporte_pet.py` | `core/log.py` + `consolida_delete.py` | ~505 |
| `core/extracao/extracao.py` | Congelado | 514 |
| `helpers/helpers.py` | Congelado | 603 |

### 5.7 Fix (runtime compartilhado) — 1/X concluido

**Monolitos congelados:** `core.py` (3258), `extracao.py` (2117), `utils.py` (2013), `variaveis.py` (1138)

| Arquivo final | Origem | Linhas alvo |
|---------------|--------|-------------|
| `core.py` | Congelado | 3258 |
| `extracao.py` | Congelado | 2117 |
| `utils.py` | Congelado | 2013 |
| `variaveis.py` | Congelado | 1138 |
| `monitoramento_progresso_unificado.py` | Estabilizado | 592 |
| `facade_publica.py` | `__init__.py` + `drivers/*` + `progress/*` + `scripts/*` + `element_wait.py` + `smart_finder.py` + `exceptions.py` + `selectors_pje.py` + `movimento_helpers.py` | ~595 |
| `browser_suporte.py` | `abas.py` + `headless_helpers.py` + `otimizacao_wrapper.py` | ~560 |
| `diagnostico_runtime.py` | `log.py` + `debug_interativo.py` + `utils_observer.py` + `utils_tempo.py` | ~403 |

### 5.8 SISB — 5/5 concluido

**Entrypoint real (via PEC):** `SISB.core.processar_ordem_sisbajud()`

| Arquivo final | Origem | Linhas |
|---------------|--------|--------|
| `core.py` | Congelado | 1123 |
| `helpers.py` | Facade congelada | 56 |
| `series/processor.py` | Congelado | 744 |
| `facades_contratos.py` | `__init__.py` + `processamento.py` + `processamento/__init__.py` + `standards.py` + `s_orquestrador.py` + todos `__init__.py` de subpacotes | 662 |
| `ordens_dados_navegacao.py` | `ordens/processor.py` + `navigation/navigator.py` | 590 |
| `ordens_execucao.py` | `processamento_ordens_processamento.py` + `validation/processor.py` | 510 |
| `relatorios_integracao.py` | `relatorios/generator.py` + `integration/pje_integration.py` | 598 |

**Nota:** `s_orquestrador.py` nao e entrypoint estrutural — e apenas compatibilidade residual. O entrypoint real e `core.processar_ordem_sisbajud`.

---

## 6. Limpeza de Codigo Morto (Fase 5 — Erase)

### 6.1 Metodologia

A limpeza segue criterios rigorosos. Um simbolo so pode ser removido se passar todos os gates:

1. Sem referencias por uso direto
2. Sem chamada indireta (getattr, string dispatch, import lazy)
3. Fora da superficie publica necessaria para import baseline
4. Fora da superficie executada por fluxos A-G de `x.py`
5. Sem impacto em smoke/compile/import

**Regra de ouro:** Nada e apagado so por AST local. A exclusao exige prova de nao alcance no grafo real enraizado em `x.py`.

### 6.2 Triagem AST inicial

| Metrica | Valor |
|---------|-------|
| Arquivos analisados | 248 |
| Funcoes nao utilizadas | 153 |
| Imports mortos | 1.143 |
| Arquivos com funcoes mortas | 50 |
| Arquivos com imports mortos | 68 |

### 6.3 Fases do Erase

| Fase | Escopo | Status |
|------|--------|--------|
| FASE 1 | Baseline de import e compatibilidade | [x] |
| FASE 2 | Funcoes mortas em Fix/ | [x] |
| FASE 3 | Funcoes mortas em modulos de negocio | [x] Codigo, [ ] Validacao real |
| FASE 4 | Arquivos potencialmente inteiros para remocao | [x] |
| FASE 5 | `x.py` como raiz: importado vs executado por fluxo | [x] |

### 6.4 Falsos positivos conhecidos

- `fechar_driver_safely` — usada via import local em `finalizar_driver()` — NAO remover
- `wrappers_pec.py` — `make_comunicacao_wrapper(...)` sao usados por PEC — NAO remover
- `SISB/batch.py`, `SISB/performance.py` — importados por `facades_contratos.py` — NAO remover

---

## 7. Gaps Pos-Refatoracao (Fase 6)

### 7.1 Gaps identificados e status

| # | Gap | Severidade | Esforco | Status |
|---|-----|-----------|---------|--------|
| G1 | `Fix/core.py`: 22 bare `except Exception` sem log | Alta | 3-5h | [x] Corrigido |
| G2 | `time.sleep` fixos → `WebDriverWait` (16 em 6 arquivos) | Media | 2-4h | [x] Corrigido |
| G3 | Emojis em `logger.*()` (~105 ocorrencias) | Media | 2-3h | [x] Corrigido |
| G4 | Bare `except:` em `x.py:195` (`resetar_driver`) | Alta | 15min | [x] Corrigido |
| G5 | `run_dom()` fora do FLOW_HANDLERS | Baixa | 1-2h | [x] Integrado (opcao H) |
| G6 | Smoke tests Task 1+2 (fluxo B com env vars + Ctrl+C) | Alta | 1h | [ ] Pendente |

### 7.2 Politica de waits

**Regra formalizada:** Nunca `time.sleep(N)` em caminho de producao. Sempre `WebDriverWait` com condicao explicita ou `Fix.core.wait()`.

### 7.3 Politica de logs

**Regra formalizada:** Zero emojis em saida de log. Zero `print()` em caminho de producao. Todo erro logado com `ExcType: mensagem` na funcao real de origem.

---

## 8. Pruning Final (Fase 7)

### 8.1 Arquivos removidos

| Fase | Arquivos | Descricao |
|------|----------|-----------|
| Phase 1 | `x.py` | `import traceback` redundante no topo |
| Phase 2 | `Prazo/p2b_prazo.py`, `Prazo/t3.py` | Legado fora do grafo ativo |
| Phase 3 | `SISB/standards.py`, `SISB/s_orquestrador.py`, `SISB/processamento.py` (plano), `SISB/series/`, `SISB/minutas/` | Duplicatas de `facades_contratos.py` |
| Phase 4 | `PEC/core.py`, `PEC/core_recovery.py`, 5x `PEC/processamento_*.py`, `PEC/sisbajud_driver.py`, `PEC/ajuste_gigs.py`, `PEC/carta.py`, `PEC/carta_ecarta.py` | Substituidos por `runtime_pec.py`, `carta_execucao.py` |
| Phase 5 | `carta/` (raiz), `bianca/` | Sem importadores ativos |

### 8.2 Arquivos explicitamente NAO removidos

| Arquivo | Motivo |
|---------|--------|
| `SISB/batch.py` | Importado por `facades_contratos.py` |
| `SISB/performance.py` | Importado por `facades_contratos.py` |
| `PEC/core_navegacao.py` | Re-exportado por `PEC/__init__.py` |
| `PEC/core_pos_carta.py` | Re-exportado por `PEC/__init__.py` |
| `PEC/carta_execucao.py` | Importado por `regras_pec.py` |
| `Prazo/p2b_fluxo_lazy.py` | Importado por `p2b_gateway.py` |
| `Prazo/p2b_fluxo_prescricao.py` | Importado por `p2b_gateway.py` |
| `Fix/debug_interativo.py` | Usado por `tools/monitor.py` |

### 8.3 Shim Cleanup Waves

10 ondas de limpeza de shims executadas (W01-W10):
- **W01-W04:** Prazo (16), Triagem (4), Peticao (5), Mandado (10) — 35 shims deletados
- **W05-W10:** Fix/ (11), Fix/drivers/ + Fix/progress/ + Fix/scripts/ (5+3), atos/anexos/ (6), SISB/ (13+5), PEC/regras.py, Fix/errors.py
- **Total: ~70 shims deletados**

---

## 9. Governanca

### 9.1 Estrategia de verificacao (4 camadas)

| Camada | Comando | Quando |
|--------|---------|--------|
| Sanidade estatica | `py -m py_compile <arquivos>` + `py test_imports.py` | Obrigatorio em toda tarefa |
| Contrato de API | Chamadas com sessao autenticada, validar cardinalidade | Por modulo |
| Smoke funcional | Executar 1 caso curto por fluxo | Antes de merge |
| Regressao de desempenho | 3 execucoes antes/depois; max 15% degradacao | Pos-refatoracao |

### 9.2 Politica de rollout

**Ordem de canario:** Fluxo B e E primeiro → C e D depois → F e G por ultimo.

**Feature flags sugeridas:** `USE_API_GATEWAY_CORE`, `USE_FLOW_ENGINE_CORE`, `USE_RUNTIME_CORE`

**Reversao:** Por tarefa, nao por fase. Fallback para implementacao anterior via flag.

### 9.3 Gate final de aceitacao

- [x] Todos os fluxos A-H acionaveis no menu de `x.py`
- [~] Sem segredos hardcoded (codigo concluido, pendente smoke)
- [x] Sem import tardio no caminho principal
- [x] API fetch unificado nos modulos orquestrados
- [x] Contrato de resultado e log padronizados
- [x] `test_imports.py` verde (0/14 falhas)
- [x] Nenhum `print()` em producao (excluindo TUI/testes)
- [x] Nenhum emoji em saida de log
- [x] `RuleRegistry` em todos os modulos (PEC, Triagem, Mandado, Prazo, Peticao)
- [ ] Smoke tests manuais em ambiente real (todos os fluxos)

### 9.4 O que falta

1. **Smoke tests manuais** — requer ambiente real com driver (todos os fluxos A-H)
2. **`erase.md` Fase 3** — validacao em ambiente real do harness `f.py`
3. **G6** — Smoke de Task 1 (fluxo B com `$env:PJE_CPF`/`$env:PJE_SENHA`) e Task 2 (Ctrl+C)
4. **Triagem T3** — facades finais e pruning (depende de smoke real)

### 9.5 O que deliberadamente NAO entra

- TypedDict formal para `normalizar_resultado()` — `Dict[str, Any]` com contrato documentado e aceitavel
- Consolidacao de `Fix/core.py`, `Fix/utils.py` ou `Fix/extracao.py` — monolitos estabilizados
- Refatoracao de `Triagem/dom.py` ou `Triagem/regras.py` — congelados
- Framework de testes Selenium — sem infraestrutura de CI com driver real
- `f.py` e `debug_interativo.py` — scripts de desenvolvimento, nao producao

---

## 10. Referencias

### 10.1 Arquivos de saida

| Arquivo | Conteudo |
|---------|----------|
| `odx.md` | Dashboard de implementacao, progresso global, dependencias |
| `erase.md` | Plano completo de limpeza com inventario AST e fases |
| `lx10-audit-report.md` | Auditoria final de prints e emojis (232 prints, 145 a migrar) |
| `19-pruning-final.md` | Plano de pruning final com 14 tasks e lista de falsos positivos |
| `shim/` | Registro das 10 ondas de shim cleanup com progresso detalhado |

### 10.2 Dados brutos (tools/)

- `erase_output.txt` — Funcoes mortas por arquivo
- `erase_imports_output.txt` — Imports mortos por arquivo
- `erase_analysis_results.json` — JSON com dados completos (used_by, line numbers)

### 10.3 Commit de rollback

`2ab0fca` — commit anterior as edicoes de limpeza. Usar como referencia em caso de regressao.

### 10.4 Como usar com LLM menor

- Entregar este README como contexto completo
- Executar tarefas da fase atual conforme secao 9
- Validar com `py -m py_compile` e `py test_imports.py` ao final de cada tarefa
- Nao pular checkpoints entre fases
- Smoke manual requer ambiente real com driver — nao executar sem
