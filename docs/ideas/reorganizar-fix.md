# Reorganizar `Fix/` — Plano Atualizado (Consolidação Agressiva)

## Problem Statement
How Might We: Como reduzir a pasta `Fix/` para **no máximo 20 arquivos** sem reescrever lógica, eliminando o máximo de módulos possível mesmo que alguns passem um pouco de 600 linhas?

## Contexto Atual (pós-Fase 1)
- `Fix/` contém **89 arquivos Python** e **~16.5k linhas** de código
- **71 arquivos reais** (implementação)
- **9 stubs** (deprecados, apenas re-exportam)
- **~10 `__init__.py`** (re-export em subpacotes)
- 12 subpacotes/diretórios: `selenium_base/`, `drivers/`, `session/`, `navigation/`, `documents/`, `extraction/`, `progress/`, `gigs/`, `forms/`, `scripts/`, `legacy/`

## Requisitos do dono (atualizados)
- **NÃO dividir arquivos grandes (>600)** — deixar como estão
- **Consolidação agressiva** — reduzir Fix total para **≤20 arquivos**
- Limite de ~600 linhas por arquivo é **soft** (pode passar um pouco se necessário)
- Eliminar o máximo de arquivos possível
- Manter compatibilidade com imports existentes

## Decisão: Estratégia Única (Aggressive Merge)

Em vez de fases incrementais, aplicar **consolidação direta por domínio**:

### Regras de Consolidação

1. **Remover todos os stubs** (12 arquivos) — callers já usam os novos caminhos
2. **Eliminar subpacotes pequenos** — mergear `drivers/`, `session/`, `navigation/`, `documents/`, `extraction/`, `progress/`, `gigs/`, `forms/`, `scripts/` no root
3. **Merge por domínio** — agrupar arquivos relacionados em módulos maiores
4. **Manter `selenium_base/`** como único subpacote (9 files, já bem organizado)
5. **Meta final: ~19 arquivos** (root + selenium_base)

---

## Mapa de Consolidação (89 → ~19 arquivos)

### GRUPO 1: `Fix/log.py` (LOG + Exception + Cleanup)
| Arquivo | Linhas | Ação |
|---|---|---|
| `log.py` | 523 | **Base** |
| `log_cleaner.py` | 122 | **Merge** → append |
| `exceptions.py` | 31 | **Merge** → append |
| **TOTAL** | **~676** | 1 arquivo |

### GRUPO 2: `Fix/extracao.py` (Extração completa)
| Arquivo | Linhas | Ação |
|---|---|---|
| `extracao_conteudo.py` | 579 | **Base** |
| `extracao_bndt.py` | 444 | **Merge** → append |
| `extracao.py` (shim) | 133 | **Merge** → conteúdo real |
| `extracao_analise.py` (stub) | 39 | **Eliminar** |
| `extracao_documento.py` (stub) | 20 | **Eliminar** |
| `extracao_processo.py` (stub) | 20 | **Eliminar** |
| **TOTAL** | **~1,156** | Dividir em 2 partes se necessário, ou manter 1 |

Se passar muito de 1200: separar `extracao_bndt` como `Fix/bndt.py` (~444 lines)

### GRUPO 3: `Fix/extraction.py` (Indexação)
| Arquivo | Linhas | Ação |
|---|---|---|
| `extraction/indexacao.py` | 663 | **Mover** → `Fix/extraction.py` |
| `extraction/__init__.py` | 39 | **Merge** → append |
| `extracao_indexacao.py` (stub) | 37 | **Eliminar** |
| `extracao_indexacao_fluxo.py` (stub) | 19 | **Eliminar** |
| **TOTAL** | **~702** | 1 arquivo |

### GRUPO 4: `Fix/progress.py` (Progresso)
| Arquivo | Linhas | Ação |
|---|---|---|
| `progress/monitoramento.py` | 710 | **Mover** → `Fix/progress.py` |
| `progress/models.py` | 86 | **Merge** → append |
| `progress/__init__.py` | 72 | **Merge** → append |
| `monitoramento_progresso_unificado.py` (stub) | 46 | **Eliminar** |
| `progresso_unificado.py` (stub) | 16 | **Eliminar** |
| `progress_models.py` (stub) | 21 | **Eliminar** |
| `progress.py` (stub) | 68 | **Eliminar** |
| **TOTAL** | **~796** | 1 arquivo (passa de 600 mas é aceitável) |

### GRUPO 5: `Fix/utils.py` (Utils consolidado)
| Arquivo | Linhas | Ação |
|---|---|---|
| `utils.py` (facade) | 346 | **Base** |
| `utils_formatting.py` | 133 | **Merge** |
| `utils_login.py` | 307 | **Merge** |
| `utils_cookies.py` | 216 | **Merge** |
| `utils_drivers.py` | 242 | **Merge** |
| `utils_paths.py` | 179 | **Merge** |
| `utils_sleep.py` | 172 | **Merge** |
| `utils_error.py` | 80 | **Merge** |
| `utils_angular.py` | 315 | **Merge** |
| `utils_selectors.py` | 230 | **Merge** |
| `utils_editor.py` | 432 | **Merge** |
| `utils_collect.py` | 209 | **Merge** |
| `utils_collect_content.py` | 238 | **Merge** |
| `utils_collect_timeline.py` | 222 | **Merge** |
| `utils_recovery.py` | 77 | **Merge** |
| `utils_tempo.py` | 31 | **Merge** |
| `utils_observer.py` | 54 | **Merge** |
| `utils_driver_legacy.py` | 65 | **Merge** |
| `converters.py` | 182 | **Merge** |
| `selectors_pje.py` | 111 | **Merge** |
| `element_wait.py` | 225 | **Merge** |
| `smart_finder.py` | 317 | **Merge** |
| **TOTAL** | **~4,000** | **Dividir em 3-4 sub-grupos** |

Divisão proposta:
- `Fix/utils.py` (~800): formatting, cookies, sleep, error, tempo, recovery, observer, driver_legacy, converters
- `Fix/utils_drivers.py` (~420): drivers, paths, login (driver lifecycle)
- `Fix/utils_editor.py` (~432): editor, collect, collect_content, collect_timeline (kept separate)
- `Fix/utils_selectors.py` (~550): selectors_pje, angular, selectors, element_wait, smart_finder

### GRUPO 6: `Fix/core.py` (Central facade)
| Arquivo | Linhas | Ação |
|---|---|---|
| `core.py` | 446 | **Manter** — já é o facade central |
| `otimizacao_wrapper.py` | 95 | **Merge** → append |
| `debug_interativo.py` | 363 | **Merge** → append |
| `debug_assinatura.py` | 57 | **Merge** → append |
| `assinatura_cookies.py` | 97 | **Merge** → append |
| `movimento_helpers.py` | 132 | **Merge** → append |
| `infojud.py` | 84 | **Merge** → append |
| `timeline.py` | 361 | **Merge** → append |
| `native_host.py` | 92 | **Merge** → append |
| **TOTAL** | **~1,630** | Dividir se necessário |

### GRUPO 7: `Fix/variaveis.py` (Variáveis consolidado)
| Arquivo | Linhas | Ação |
|---|---|---|
| `variaveis.py` | 24 | **Merge** |
| `variaveis_client.py` | 222 | **Merge** |
| `variaveis_helpers.py` | 376 | **Merge** |
| `variaveis_painel.py` | 151 | **Merge** |
| `variaveis_resolvers.py` | 307 | **Merge** |
| **TOTAL** | **~1,056** | Dividir em 2 se necessário |

### GRUPO 8: Subpacotes — mergear no root ou manter

| Subpacote | Arquivos | Linhas | Decisão |
|---|---|---|---|
| `drivers/` (2 files) | 2 | 565 | **Merge** → root `Fix/drivers.py` |
| `session/` (2 files) | 2 | 517 | **Merge** → root `Fix/session.py` |
| `navigation/` (3 files) | 3 | 635 | **Merge** → root `Fix/navigation.py` |
| `documents/` (3 files) | 3 | 769 | **Merge** → root `Fix/documents.py` |
| `gigs/` (2 files) | 2 | 598 | **Merge** → root `Fix/gigs.py` |
| `forms/` (2 files) | 2 | 120 | **Merge** → root `Fix/core.py` ou `Fix/utils.py` |
| `scripts/` (1 file) | 1 | 13 | **Merge** → `Fix/utils.py` |
| `legacy/` (5 files) | 5 | ~1,022 | **Review** — 2 stubs eliminar, 3 reais mergear |

### GRUPO 9: `selenium_base/` — MANTER como subpacote
| Arquivo | Linhas | Ação |
|---|---|---|
| `__init__.py` | 125 | **Manter** |
| `element_interaction.py` | 665 | **Manter** (não dividir) |
| `smart_selection.py` | 610 | **Manter** (não dividir) |
| `wait_operations.py` | 383 | **Manter** |
| `driver_operations.py` | 420 | **Manter** |
| `retry_logic.py` | 267 | **Manter** |
| `click_operations.py` | 140 | **Manter** |
| `js_helpers.py` | 102 | **Manter** |
| `field_operations.py` | 59 | **Manter** |
| **TOTAL** | **~2,771** | **9 arquivos** — subpacote coeso, sem mudanças |

### GRUPO 10: `abas.py` — standalone
| Arquivo | Linhas | Ação |
|---|---|---|
| `abas.py` | 383 | **Manter** — já é autocontido |
| `headless_helpers.py` | 273 | **Manter** — dependência comum |

---

## Estrutura Final Proposta (~19 arquivos)

```
Fix/
├── __init__.py              # API pública consolidated (~250 lines)
├── core.py                  # Core facade + debug + helpers (~1,600)
├── log.py                   # Log + exceptions + cleaner (~676)
├── extracao.py              # Extração de documentos (~1,100)
├── extraction.py            # Indexação de processos (~700)
├── progress.py              # Progresso unificado (~800)
├── drivers.py               # Driver lifecycle (~565)
├── session.py               # Cookies e auth (~517)
├── navigation.py            # Filtros e navegação (~635)
├── documents.py             # Busca de documentos (~770)
├── gigs.py                  # GIGS creation (~598)
├── variaveis.py             # Variáveis consolidado (~1,000)
├── utils.py                 # Utils formatting/cookies/sleep (~800)
├── utils_drivers.py         # Utils driver/paths/login (~420)
├── utils_editor.py          # Utils editor/collect (~430)
├── utils_selectors.py       # Utils selectors/angular/smart (~550)
├── abas.py                  # Tab management (383)
├── headless_helpers.py      # Headless-safe helpers (273)
│
└── selenium_base/           # MANTIDO como subpacote (9 arquivos)
    ├── __init__.py
    ├── element_interaction.py
    ├── smart_selection.py
    ├── wait_operations.py
    ├── driver_operations.py
    ├── retry_logic.py
    ├── click_operations.py
    ├── js_helpers.py
    └── field_operations.py
```

**Total: 18 arquivos root + 9 subpacote = 27 arquivos**

Para chegar em **≤20**, mergear mais no root:
- `headless_helpers.py` → `Fix/core.py` (+273)
- `abas.py` → `Fix/core.py` (+383)
- `gigs.py` → `Fix/extracao.py` (+598)

**Resultado final: ~19 arquivos root + 9 subpacote = 28 NO — still too many**

### Ajuste final para ≤20 total

A única forma de chegar em ≤20 total é **também achatar selenium_base**:

```
Fix/
├── __init__.py              # API pública (~250)
├── core.py                  # Core + debug + abas + headless (~2,300)
├── log.py                   # Log + exceptions + cleaner (~676)
├── extracao.py              # Extração + gigs + BNDT (~1,700)
├── extraction.py            # Indexação (~700)
├── progress.py              # Progresso (~800)
├── drivers.py               # Driver lifecycle + utils_drivers (~1,000)
├── session.py               # Cookies/auth + utils_cookies (~730)
├── navigation.py            # Filtros (~635)
├── documents.py             # Busca (~770)
├── variaveis.py             # Variáveis (~1,056)
├── utils.py                 # Utils formatting/sleep/error (~600)
├── utils_editor.py          # Editor + collect (~650)
├── utils_selectors.py       # Selectors + smart_finder (~550)
├── selenium_core.py         # selenium_base flattatenado (~1,200)
├── selenium_helpers.py      # selenium_base restante (~1,500)
├── forms.py                 # Multi-fields (120) → merge em utils
└── scripts.py               # JS loader (13) → merge em utils
```

Hmm, ainda passa de 20. A abordagem mais agressiva:

### PLANO FINAL: ~18 arquivos total

Merge selenium_base helpers em utils:

| # | Arquivo | Conteúdo | ~Linhas |
|---|---|---|---|
| 1 | `__init__.py` | API pública | 250 |
| 2 | `core.py` | Core + debug + abas + headless + forms | 2,300 |
| 3 | `log.py` | Log + exceptions + cleaner | 676 |
| 4 | `extracao.py` | Extração + gigs + BNDT | 1,700 |
| 5 | `extraction.py` | Indexação | 700 |
| 6 | `progress.py` | Progresso | 800 |
| 7 | `drivers.py` | Drivers + paths + login | 1,000 |
| 8 | `session.py` | Cookies + auth | 730 |
| 9 | `navigation.py` | Filtros + sigilo | 635 |
| 10 | `documents.py` | Busca de documentos | 770 |
| 11 | `variaveis.py` | Variáveis completo | 1,056 |
| 12 | `utils.py` | Utils formatting/sleep/error/collect | 900 |
| 13 | `utils_editor.py` | Editor + collect + timeline | 650 |
| 14 | `selectors.py` | Selectors + angular + smart_finder | 550 |
| 15 | `selenium.py` | selenium_base flattened (core ops) | 1,200 |
| 16 | `selenium_wait.py` | selenium_base (wait/retry/click) | 800 |
| 17 | `selenium_select.py` | selenium_base (selection/robust) | 670 |
| 18 | `js_helpers.py` | JS helpers + scripts | 115 |

**TOTAL: 18 arquivos** ✅

---

## Processo de Execução

### Passo 1: Backup
- Copiar toda `Fix/` para `Fix/backup_pre_merge/`

### Passo 2: Eliminar stubs (12 arquivos)
- `extracao_analise.py`, `extracao_documento.py`, `extracao_indexacao.py`, `extracao_indexacao_fluxo.py`, `extracao_processo.py`
- `monitoramento_progresso_unificado.py`, `progresso_unificado.py`, `progress_models.py`, `progress.py`
- `legacy/extracao_analise.py`, `legacy/progress_models.py`
- **Nota:** Stubs podem ser simplesmente removidos já que os novos caminhos existem

### Passo 3: Mergear subpacotes no root
- `drivers/`, `session/`, `navigation/`, `documents/`, `extraction/`, `progress/`, `gigs/`, `forms/`

### Passo 4: Consolidar por grupo
- Para cada grupo acima: copiar conteúdo dos arquivos fonte para o arquivo destino
- Atualizar imports no arquivo consolidado
- Rodar `py -m py_compile` e `tools/check_imports.py`

### Passo 5: Achatar selenium_base
- Mesclar 9 arquivos em 3 arquivos root-level
- Atualizar todos os imports que referenciam `Fix.selenium_base.*`

### Passo 6: Atualizar `__init__.py`
- Re-exportar tudo dos novos módulos consolidados

### Passo 7: Validação final
- `py -m py_compile Fix/**/*.py`
- `py tools/check_imports.py`
- Smoke test manual

---

## Critérios de Aceitação

- [ ] **Fix/ tem ≤20 arquivos** (excluindo `__pycache__`)
- [ ] `py -m py_compile` passa em todos
- [ ] `tools/check_imports.py` reporta 0 erros
- [ ] Imports legados funcionam via `__init__.py`
- [ ] Nenhum código foi reescrito (apenas movido/merged)
- [ ] Backup pré-merge existe em `Fix/backup_pre_merge/`

## Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Arquivo >2000 lines difícil de manter | Alta | Aceitável — é trade-off conscious para reduzir file count |
| Conflito de nomes públicos | Média | Script detecta duplicatas antes do merge |
| Side-effects top-level quebram | Baixa | Revisão manual pré-merge para cada caso |
| Import circular | Média | Verificar após cada merge |
| Perda de código no merge | Baixa | Backup obrigatório antes |

---

## Not Doing
- Refatoração profunda de funções/algoritmos
- Reescrever lógica de negócio
- Dividir arquivos grandes (>600) — **deixar como estão**

## Status
- [x] Fase 1: Pacotes `progress/` e `extraction/` criados (executado)
- [ ] Fase 2: Consolidação agressiva para ≤20 arquivos (pendente)

---
Plano atualizado em 15/abr/2026. Inventário: 89 arquivos, ~16.5k linhas.
