# ODX — Ordem De Execucao / Implementation Dashboard

> Atualizado: 2026-05-03 | Base: 20 docs de plano em xcode/

## Progresso global por fase

| Fase | Plano | Progresso | Entregas principais |
|------|-------|-----------|---------------------|
| Fase 0 — Diagnostico | 00, 01, 02, 04, 07 | 100% | Mapa x.py, achados, arquitetura alvo, matriz de dependencias |
| Fase 1 — Governanca | 03, 05, 06 | 100% | Plano incremental, politica de testes, consolidacao e pruning |
| Fase 2 — Unificacao | 08, 09 | 100% | RuleRegistry, plano atos/anexos |
| Fase 3 — Padronizacao | 10 | **100%** | Logs: todas as ondas Lx concluidas; 0 prints ativos fora TUI/testes |
| Fase 4 — Granular | 11, 12, 13, 14, 15, 16, 17 | **96%** | Mandado 5/5, Prazo 4/4, PEC 5/5, Triagem **2/3**, Peticao 1/1, Fix 1/X, SISB 5/5 |
| Fase 5 — Erase | erase.md | **70%** | Limpeza parcial; f.py harness criado; pendente smoke real |
| Fase 6 — Gaps (18) | 18 | **83%** | G1, G2, G3, G4, G5 concluidos; G6 pendente |

## Progresso por modulo

### x.py (orquestrador)
- [x] G1-G6: menu tipado, FLOW_HANDLERS, main linear, shutdown, wrapper unificado
- [x] Task 12: Shell afinado — reduzido de ~930 para ~630 linhas
- [x] Lx-2: 98 prints migrados para logger; zero prints ativos
- [x] **G5**: run_dom() integrado — opcao "H" no menu
- [x] **G4**: bare except em resetar_driver() corrigido

### Fix/ (runtime compartilhado)
- [x] Lx-1: CustomFormatter com formatos por nivel
- [x] Lx-3 a Lx-6, Lx-9 parcial: ~400 prints migrados (utils, extracao, core, abas, variaveis parcial)
- [x] Phase 5 Lotes 0-3: pruning de imports mortos, funcoes mortas removidas
- [x] Erase: 4 funcoes removidas, 11 ja extintas; test_imports.py verde (0/14)
- [x] 16-granular-fix.md — selectors_pje.py 105→55 linhas; demais areas ok
- [x] Lx-10: prints migrados (ondas anteriores); modulo limpo
- [x] **G1**: 22 bare `except Exception` com logging adicionado em core.py

### Mandado/
- [x] M1+M2+M3: docstrings, section headers, marcadores LEGADO, separadores Etapas 0-5
- [x] M4: apoio_fluxos.py consolidado
- [x] MX1: entrada_api.py (618 linhas)
- [x] MX2: fluxo_argos.py (671 linhas)
- [x] MX3: apoio_fluxos.py (785 linhas)
- [x] **M5**: Shims finais — processamento_fluxo → thin shim, __init__.py limpo
- [x] Lx: zero prints, zero emojis em print (modulo limpo)

### Prazo/
- [x] P1+P2+P3: loop_orquestrador.py e p2b_gateway.py consolidados
- [x] P4: 14 thin shims, 2 satelites, __init__.py limpo, checar_prox preservado
- [x] Lx-10: prints migrados (Wave 4); modulo limpo

### PEC/
- [x] E1+E2+E3: docstrings, marcadores LEGADO, runtime headers, grafo de imports, section headers
- [x] E4+E5: carta_execucao.py consolidado
- [x] Phase 5 Lote 0-4: imports mortos, funcoes mortas, utils_login/utils_cookies deletados
- [x] Lx-10: prints migrados (ondas anteriores); modulo limpo

### Triagem/
- [x] Phase 5 Lote 2: _processar_processo removido de runner.py
- [x] Phase 6 Task 19: alerta_registry + runner.py limpo
- [x] Lx-10: prints migrados (ondas anteriores); modulo limpo
- [x] **T1**: runtime_triagem.py (505 linhas) — consolidado
- [x] **T2**: analise_execucao.py (902 linhas) — consolidado (service + acoes + preprocess + citacao + utils)
- [ ] T3: facades finais + pruning (__init__.py + runner.py shims) — depende de smoke real

### Peticao/
- [x] Phase 5 Lotes 0-4: imports mortos, funcoes mortas, utils_login/utils_cookies deletados
- [x] Phase 6 Task 22: peticao_registry com 5 buckets; pet.py limpo
- [x] Lx-10: prints migrados (ondas anteriores); modulo limpo
- [x] **PT1**: runtime_pet.py (701 linhas) — consolidado

### SISB/
- [x] SX1: facades_contratos.py (662 linhas), 12 shims
- [x] SX2: ordens_dados_navegacao.py (590 linhas)
- [x] SX3: ordens_execucao.py (510 linhas)
- [x] **SX4**: relatorios_integracao.py (598 linhas)
- [x] **SX5**: pruning estrutural — imports mortos removidos, helpers/core/series congelados

### atos/
- [x] Lx-10 Ondas 1-2: 3 prints migrados (movimentos_chips, fimsob, sobrestamento)
- [x] Lx-10: movimentos_fluxo.py limpo (onda 2)
- [x] Protegidos: wrappers_pec, wrappers_mov, wrappers_ato como facades de compatibilidade
- [x] **G3**: emojis removidos de logger calls (~105 em 16 arquivos)

## Metricas consolidadas

| Metrica | Valor |
|---------|-------|
| Arquivos .py no escopo | ~235 |
| Prints migrados para logger | ~1.215+ |
| Prints remanescentes | ~0 (excluindo TUI/f.py/testes) |
| Emojis em print() remanescentes | ~0 |
| Funcoes mortas removidas | 150+ |
| Imports mortos removidos | 800+ |
| Arquivos deletados da raiz | 28 |
| Thin shims criados | 35+ (Prazo 14, Mandado 8+, SISB 12+, Fix 2+) |
| Modulos com 0 prints ativos | Mandado, carta, SISB, PEC, Triagem, Peticao, atos |
| test_imports.py | 0/14 falhas (verde) |
| Arquivos consolidados criados | 7 (entrada_api, fluxo_argos, apoio_fluxos, facades_contratos, ordens_dados_navegacao, ordens_execucao, relatorios_integracao) |

## Dependencias criticas entre tarefas restantes

```
Mandado M5 ──► (independente)
SISB SX4+SX5 ──► (independente)
Fix granular ──► (independente)
Lx-10 Ondas 4-7 ──► (independente)
                      │
                      ▼
              Smoke tests manuais (todos acima precisam estar concluidos)
                      │
                      ▼
              run_dom() integration (depende de smoke passar)
```

## Lote 3 — Concluido (2026-05-03)

| Agente | Tarefa | Escopo | Status |
|--------|--------|-------|--------|
| J | Mandado M5 | processamento_fluxo → thin shim, __init__.py limpo | ✅ |
| K | SISB SX4+SX5 | relatorios_integracao.py + pruning | ✅ |
| L | Fix granular | selectors_pje.py 105→55 linhas | ✅ |
| M | Lx-10 Ondas 4-7 | Prazo 15 prints finais; demais ondas ja limpas | ✅ |

## Lote 4 — Concluido (2026-05-03)

| Agente | Tarefa | Escopo | Status |
|--------|--------|-------|--------|
| N | Triagem T1 | runtime_triagem.py (505 linhas) + print→logger em regras.py | ✅ |
| O | Peticao PT1 | runtime_pet.py (701 linhas) + 4 thin shims | ✅ |

## Lote 5 — Concluido (2026-05-04)

| Agente | Tarefa | Escopo | Status |
|--------|--------|-------|--------|
| P | Triagem T2 | analise_execucao.py (902 linhas), 5 thin shims | ✅ |
| Q | G2 Waits | 16 time.sleep → WebDriverWait em 6 arquivos | ✅ |
| R | Facades audit | 9 __init__.py revisados, 2 ajustados, test_imports verde | ✅ |

## Gate de conclusao da refatoracao

- [ ] Todos os modulos com 0 prints ativos (exceto TUI e testes)
- [ ] test_imports.py verde (0 falhas)
- [ ] Smoke manual fluxos A-G em ambiente real
- [ ] Nenhum arquivo .py acima de 800 linhas fora dos 4 congelados (core.py, extracao.py, utils.py, variaveis.py)

## Fase 8 — Fechamento Pos-Refatoracao ([18-pos-xcode-gaps.md](18-pos-xcode-gaps.md))

Gaps genuinos identificados apos conclusao projetada de todos os planos xcode.

- [x] G4: bare except x.py:195 — trocado por `except Exception as e:` + logger.warning
- [x] G1: Fix/core.py — 22 bare `except Exception` com logging adicionado
- [x] G3: Emojis em logger.*() — ~105 removidos em 16 arquivos (SISB, Mandado, PEC, atos)
- [x] G5: run_dom() — opcao "H" no FLOW_HANDLERS do x.py
- [ ] G6: Smoke tests Task 1+2 (fluxo B com env vars + Ctrl+C) — requer ambiente real
- [x] G2: Waits padronizados — 16 time.sleep substituidos em 6 arquivos (x.py, Prazo, SISB, Fix)
- [x] Facades publicas estaveis em todos os __init__.py de modulo (9 modulos auditados)
- [ ] erase.md Fase 3 concluida com validacao real
