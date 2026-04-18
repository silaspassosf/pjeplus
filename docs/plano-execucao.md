# Plano de Execução — PJePlus Performance & Headless
> Gerado em 18/04/2026 · Baseline: análise profunda do repositório atual

---

## Controle de Progresso

- **Última atualização:** 2026-04-18
- **Status geral:** In progress — Fase 1 ativa
- **Progresso por fase:**
  - [x] Fase 1 — Desbloqueadores Headless
    - [x] P1: Centralizar download prefs (`Fix/drivers/lifecycle.py`)
    - [x] P2: Fallback profile path (`Fix/drivers/lifecycle.py`)
    - [x] P3: Remover `implicitly_wait` (drivers) — COMPLETED 2026-04-18
      - Nota: `implicitly_wait(10)` removido de todos os criadores de driver em `Fix/drivers/lifecycle.py`
  - [ ] Fase 2 — Eliminar `time.sleep` (módulos críticos)
  - [ ] Fase 3 — Consolidação `Fix/` (merge e flatten)
  - [ ] Fase 4 — Código morto (vulture slices)
  - [ ] Fase 5 — CI / GitHub Actions (sanity workflow)

---

## Estado Real (Baseline 18/04/2026)

### Já implementado (documentação desatualizada)

| Item | Arquivo | Observação |
|------|---------|-----------|
| `aguardar_angular_estavel` (A1) | `Fix/utils_angular.py` | `getAllAngularTestabilities` + `whenStable` + guard |
| `CircuitBreaker` (A2) | `Fix/selenium_base/retry_logic.py` L271–303 | `cb_sisbajud` e `cb_pje_api` exportados |
| `aguardar_mutacao_async` (A3) | `Fix/selenium_base/wait_operations.py` L386 | Opt-in, sem substituir global |
| `headless_helpers` | `Fix/headless_helpers.py` | `click_headless_safe`, `limpar_overlays_headless` |
| `driver_session` context manager | `Fix/drivers/lifecycle.py` L11 | Suporta `headless=True` |
| 60 arquivos mortos arquivados | `_archive/20260415_024013/` | Fase 1 Frente C ✅ |
| Vulture slices 1–3 | commits `62fa6a1`, `a8c483e` | -26 linhas de código morto |

### Gaps confirmados (pendentes de implementação)

| Gap | Impacto | Fase |
|-----|---------|------|
| Download prefs ausentes do driver factory quando `headless=True` | 🔴 Bloqueador CI | 1 |
| Profile path hardcoded (`C:\SeleniumProfilePC`) — falha em Linux/CI | 🔴 Bloqueador CI | 1 |
| `implicitly_wait(10)` em todos os drivers dobra timeouts silenciosamente | 🟠 Alto | 1 |
| 15+ `time.sleep` em `Fix/extracao_bndt.py` | 🟠 Alto | 2 |
| 15+ `time.sleep` em `atos/comunicacao_*` | 🟠 Alto | 2 |
| `Fix/` com 89 arquivos e 12 subpacotes (vs. 18 alvo) | 🟡 Médio | 3 |
| Vulture slices 4+ e scan de imports órfãos | 🟡 Médio | 4 |
| Workflow CI/GitHub Actions | 🟡 Médio | 5 |

### Validação de baseline (rodar antes de iniciar qualquer fase)

```powershell
@(
  "import x",
  "from Fix.core import finalizar_driver",
  "from Mandado.processamento_api import processar_mandados_devolvidos_api",
  "from PEC.orquestrador import executar_fluxo_novo_simplificado",
  "from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b",
  "from Triagem.runner import run_triagem",
  "from Peticao.pet import run_pet"
) | ForEach-Object {
    $r = py -c $_ 2>&1
    if ($LASTEXITCODE -eq 0) { "OK   $_" } else { "FAIL $_`n$r" }
}
```

Todos os 7 devem retornar `OK` antes de qualquer mudança.

---

## Decisões de Arquitetura

- **Ordem das fases é obrigatória:** Fase 2 depende de Fase 1 estável. Fase 3 deve vir depois de Fase 2 (baseline limpo para validação de merges). Fase 5 só inicia após Fase 1 estar completa.
- **`utils_observer.py` usa polling de 50ms deliberadamente** — `execute_async_script` quebra com `"Document was unloaded"` em overlays Angular CDK/mat-select. Não substituir globalmente.
- **`aguardar_mutacao_async`** é opt-in apenas para contextos sem CDK overlay.
- **Sem reescrita de lógica de negócio** — apenas substituição de timing.
- **Máx. 5 arquivos por commit** em Fase 2 para rollback fácil.
- **Backup obrigatório** antes de qualquer merge da Fase 3.

---

## Fase 1 — Desbloqueadores Headless

> Pré-requisito para CI. Sem esta fase, qualquer tentativa de `headless=True` trava silenciosamente.

---

### Task P1: Centralizar download prefs headless no driver factory

**Descrição:** `browser.helperApps.neverAsk.saveToDisk` existe apenas em `x.py` (linha 159). Quando `criar_driver_PC(headless=True)` é chamado diretamente (API, CI), downloads travam sem exceção e sem log. Extrair as prefs de download para função privada `_aplicar_prefs_download_headless` e chamá-la em todos os drivers quando `headless=True`.

**Acceptance criteria:**
- [ ] `_aplicar_prefs_download_headless(options)` criada em `Fix/drivers/lifecycle.py` com MIME types: `application/pdf`, `application/octet-stream`, `text/csv`, `application/zip`
- [ ] Chamada dentro de `criar_driver_PC`, `criar_driver_VT` e `criar_driver_notebook` quando `headless=True`
- [ ] `pdfjs.disabled` = `True` incluído (impede abertura inline de PDF)
- [ ] `browser.download.manager.showWhenStarting` = `False` incluído

**Verificação:**
```bash
py -m py_compile Fix/drivers/lifecycle.py
py -c "from Fix.drivers.lifecycle import criar_driver_PC; print('OK')"
```

**Dependências:** Nenhuma

**Arquivos:**
- `Fix/drivers/lifecycle.py`

**Escopo:** XS — 1 arquivo, ~20 linhas novas

---

### Task P2: Fallback de profile path para ambiente sem Windows

**Descrição:** `FIREFOX_PROFILE_PC = r'C:\SeleniumProfilePC'` é hardcoded. Em Linux/CI, a criação do `FirefoxProfile` falha antes mesmo de iniciar. Adicionar fallback para `tempfile.mkdtemp()` quando o caminho raiz não existir.

**Acceptance criteria:**
- [ ] `_resolver_profile_path(base_path)` criada: retorna `base_path` se o diretório pai existe, senão `tempfile.mkdtemp(prefix="pjeplus_profile_")`
- [ ] Usada em `criar_driver_PC`, `criar_driver_VT`, `criar_driver_notebook` antes de `FirefoxProfile(...)`
- [ ] Log de warning quando fallback é acionado: `[DRIVER/WARN] Profile path indisponivel — usando temp`

**Verificação:**
```bash
py -m py_compile Fix/drivers/lifecycle.py
py -c "from Fix.drivers.lifecycle import criar_driver_PC; print('OK')"
```

**Dependências:** Nenhuma (independente de P1)

**Arquivos:**
- `Fix/drivers/lifecycle.py`

**Escopo:** XS — 1 arquivo, ~15 linhas

---

### Task P3: Remover `implicitly_wait` de todos os drivers

**Descrição:** `driver.implicitly_wait(10)` ao final de `criar_driver_PC` (e demais) faz o geckodriver esperar 10s implícitos antes de reportar `NoSuchElementException` — o que, combinado com `WebDriverWait(driver, N)`, dobra silenciosamente o timeout real de cada falha de elemento. Em headless, onde falhas de renderização são mais frequentes, isso acumula minutos por lote.

**Acceptance criteria:**
- [ ] Linha `driver.implicitly_wait(10)` removida de `criar_driver_PC`
- [ ] Mesma linha removida de `criar_driver_VT`, `criar_driver_notebook`, `criar_driver_sisb_pc`, `criar_driver_sisb_notebook`
- [ ] Nenhum caller na base usa `implicitly_wait` diretamente após essa remoção
- [ ] 7 imports críticos continuam passando

**Verificação:**
```bash
py -m py_compile Fix/drivers/lifecycle.py
# Confirmar ausência:
Select-String -Path Fix/drivers/lifecycle.py -Pattern "implicitly_wait"
# Deve retornar zero resultados
py -c "import x; print('OK')"
```

**Dependências:** P1, P2 (aplicar P3 após os outros para confirmar baseline)

**Arquivos:**
- `Fix/drivers/lifecycle.py`

**Escopo:** XS — 1 arquivo, remoção de 5 linhas

---

### Checkpoint Fase 1

```powershell
# Compilar driver factory
py -m py_compile Fix/drivers/lifecycle.py

# 7 imports críticos
@("import x","from Fix.core import finalizar_driver",
  "from Mandado.processamento_api import processar_mandados_devolvidos_api",
  "from PEC.orquestrador import executar_fluxo_novo_simplificado",
  "from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b",
  "from Triagem.runner import run_triagem",
  "from Peticao.pet import run_pet"
) | ForEach-Object {
    $r = py -c $_ 2>&1
    if ($LASTEXITCODE -eq 0) { "OK   $_" } else { "FAIL $_`n$r" }
}

# Confirmar ausência de implicitly_wait
Select-String -Path Fix\drivers\lifecycle.py -Pattern "implicitly_wait"
# Esperado: zero resultados

# Confirmar presença de prefs download
Select-String -Path Fix\drivers\lifecycle.py -Pattern "neverAsk"
# Esperado: pelo menos 1 resultado
```

- [ ] Todos os 7 imports OK
- [ ] Zero ocorrências de `implicitly_wait` em `lifecycle.py`
- [ ] `neverAsk.saveToDisk` presente em `_aplicar_prefs_download_headless`
- [ ] `_resolver_profile_path` presente e testável via import

---

## Fase 2 — Eliminar `time.sleep` nos Módulos de Negócio

> Cada sleep substituído por `aguardar_renderizacao_nativa` ou `aguardar_angular_estavel`. Sem reescrita de lógica.
> **Regra:** máx. 5 arquivos por commit. Compilar cada arquivo após edição.

---

### Task S1: `Fix/extracao_bndt.py` — 15+ sleeps

**Descrição:** Arquivo com maior concentração de sleeps no projeto (15+, valores 0.1–1.0s). Maioria é espera de elemento DOM após interação. Em lote SISBAJUD de 20 processos, acumula 20–40s de sleep puro. Substituir por `aguardar_renderizacao_nativa` ou `aguardar_colecao_sync` conforme contexto de cada ponto.

**Acceptance criteria:**
- [ ] Zero `time.sleep` restantes no arquivo (exceto se comentado como `# TODO` com justificativa)
- [ ] Cada sleep substituído por chamada a `aguardar_renderizacao_nativa(driver, seletor, modo, timeout)` ou `aguardar_colecao_sync` com seletor específico do contexto
- [ ] `py -m py_compile Fix/extracao_bndt.py` limpo
- [ ] `from Fix.extracao_bndt import *` sem ImportError

**Verificação:**
```bash
py -m py_compile Fix/extracao_bndt.py
Select-String -Path Fix\extracao_bndt.py -Pattern "time\.sleep"
# Esperado: zero resultados
py -c "import Fix.extracao_bndt; print('OK')"
```

**Dependências:** Fase 1 completa

**Arquivos:**
- `Fix/extracao_bndt.py`

**Escopo:** M — 1 arquivo, ~15 substituições pontuais

---

### Task S2: `atos/comunicacao_preenchimento.py` — 6 sleeps

**Descrição:** Todos os 6 sleeps têm comentário `# legado: pausa para Angular renderizar`. São esperas após `mat-select` abrir ou popular opções — caso de uso ideal para `aguardar_angular_estavel(driver, timeout=3)` que já existe em `Fix/utils_angular.py`.

**Acceptance criteria:**
- [ ] 6 sleeps substituídos por `aguardar_angular_estavel(driver, timeout=3)` ou `aguardar_renderizacao_nativa` com seletor da opção esperada
- [ ] Import de `aguardar_angular_estavel` ou `aguardar_renderizacao_nativa` adicionado ao topo do arquivo
- [ ] `import time` removido se não houver mais usos
- [ ] `py -m py_compile atos/comunicacao_preenchimento.py` limpo

**Verificação:**
```bash
py -m py_compile atos/comunicacao_preenchimento.py
Select-String -Path atos\comunicacao_preenchimento.py -Pattern "time\.sleep"
py -c "from atos.comunicacao_preenchimento import *; print('OK')"
```

**Dependências:** Fase 1 completa (independente de S1)

**Arquivos:**
- `atos/comunicacao_preenchimento.py`

**Escopo:** S — 1 arquivo, 6 substituições + atualização de imports

---

### Task S3: `atos/comunicacao_finalizacao.py` — 9 sleeps

**Descrição:** 9 sleeps com valores de 0.1s a 1.0s. Ao contrário de S2, este arquivo já tem `MutationObserver` em uso (`# Aguardar dialog fechar via MutationObserver — sem polling nem time.sleep` na linha 684). Os sleeps restantes precisam de análise individual — alguns são esperas de UI (substituíveis), outros podem ser guards de race condition (requerer verificação manual antes de remover).

**Acceptance criteria:**
- [ ] Cada sleep classificado como: (a) substituível por observer, (b) guard necessário documentado com comentário explicativo
- [ ] Sleeps substituíveis (categoria a) removidos e substituídos por `aguardar_renderizacao_nativa`
- [ ] Sleeps que permanecem têm comentário `# GUARD: <motivo específico>`
- [ ] `py -m py_compile atos/comunicacao_finalizacao.py` limpo

**Verificação:**
```bash
py -m py_compile atos/comunicacao_finalizacao.py
# Confirmar que sleeps remanescentes têm comentário GUARD:
Select-String -Path atos\comunicacao_finalizacao.py -Pattern "time\.sleep"
# Para cada resultado: verificar se linha seguinte ou anterior tem "# GUARD:"
py -c "from atos.comunicacao_finalizacao import *; print('OK')"
```

**Dependências:** Fase 1 completa (independente de S1, S2)

**Arquivos:**
- `atos/comunicacao_finalizacao.py`

**Escopo:** M — 1 arquivo, 9 pontos de análise + edições

---

### Task S4: `Fix/gigs/__init__.py` e `Fix/abas.py` — 5 sleeps menores

**Descrição:** 3 sleeps em `gigs/__init__.py` (0.2s–1.0s, esperas de dropdown Angular) e 2 sleeps em `abas.py` (0.1s–0.3s, esperas de aba carregar). Substituições diretas.

**Acceptance criteria:**
- [ ] `gigs/__init__.py`: 3 sleeps substituídos por `aguardar_renderizacao_nativa` com seletor do dropdown/option
- [ ] `abas.py`: 2 sleeps substituídos por `aguardar_renderizacao_nativa` ou lógica de espera de aba via `window.handles`
- [ ] Ambos compilam limpos e importam sem erro

**Verificação:**
```bash
py -m py_compile Fix/gigs/__init__.py Fix/abas.py
Select-String -Path Fix\gigs\__init__.py,Fix\abas.py -Pattern "time\.sleep"
py -c "from Fix.gigs import *; from Fix.abas import *; print('OK')"
```

**Dependências:** Fase 1 completa

**Arquivos:**
- `Fix/gigs/__init__.py`
- `Fix/abas.py`

**Escopo:** S — 2 arquivos, 5 substituições

---

### Task S5: `Fix/documents/search.py` — 4 sleeps

**Descrição:** 4 sleeps (1s–2s) em busca de documentos. São as esperas mais longas em valor absoluto. Substituir por `aguardar_renderizacao_nativa` com seletor do resultado de busca esperado.

**Acceptance criteria:**
- [ ] 4 sleeps removidos e substituídos por `aguardar_renderizacao_nativa` ou `aguardar_colecao_sync`
- [ ] Timeout explícito configurado (≥ o valor do sleep original)
- [ ] `py -m py_compile Fix/documents/search.py` limpo

**Verificação:**
```bash
py -m py_compile Fix/documents/search.py
Select-String -Path Fix\documents\search.py -Pattern "time\.sleep"
py -c "from Fix.documents.search import *; print('OK')"
```

**Dependências:** Fase 1 completa

**Arquivos:**
- `Fix/documents/search.py`

**Escopo:** S — 1 arquivo, 4 substituições

---

### Checkpoint Fase 2

```powershell
# Zero sleeps nos arquivos trabalhados
$alvo = @(
  "Fix\extracao_bndt.py",
  "atos\comunicacao_preenchimento.py",
  "Fix\gigs\__init__.py",
  "Fix\abas.py",
  "Fix\documents\search.py"
)
Select-String -Path $alvo -Pattern "time\.sleep"
# Esperado: zero (ou apenas linhas com "# GUARD:")

# Compilar todos
py -m py_compile ($alvo -join " ")

# 7 imports críticos
@("import x","from Fix.core import finalizar_driver",
  "from Mandado.processamento_api import processar_mandados_devolvidos_api",
  "from PEC.orquestrador import executar_fluxo_novo_simplificado",
  "from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b",
  "from Triagem.runner import run_triagem",
  "from Peticao.pet import run_pet"
) | ForEach-Object {
    $r = py -c $_ 2>&1
    if ($LASTEXITCODE -eq 0) { "OK   $_" } else { "FAIL $_`n$r" }
}
```

- [ ] Zero `time.sleep` não justificados nos 5 arquivos trabalhados
- [ ] Todos os 7 imports críticos OK
- [ ] `py -m py_compile` limpo em todos os arquivos editados

---

## Fase 3 — Consolidação de `Fix/` (89 → 18 arquivos)

> **Pré-condição:** Fases 1 e 2 concluídas e validadas.
> **Regra:** backup obrigatório antes do primeiro merge. Nunca pular o backup.
> **Nunca reescrever lógica** — apenas mover e concatenar.

---

### Task B0: Backup e validação de baseline pré-merge

**Descrição:** Criar snapshot de rollback de `Fix/` e confirmar que todos os 7 imports críticos passam antes de qualquer merge.

**Acceptance criteria:**
- [ ] `Fix/backup_pre_merge/` criado com cópia completa de `Fix/`
- [ ] `py -m py_compile` passa em todos os `.py` de `Fix/`
- [ ] 7 imports críticos passam
- [ ] Contagem de arquivos documentada como baseline (`dir Fix/ | Measure-Object`)

**Verificação:**
```bash
Copy-Item -Recurse Fix Fix\backup_pre_merge
py -m py_compile (Get-ChildItem Fix\*.py -Recurse | Select-Object -Expand FullName)
# 7 imports críticos (ver bloco de validação acima)
(Get-ChildItem Fix\*.py -Recurse | Measure-Object).Count
# Documentar esse número
```

**Dependências:** Fases 1 e 2 completas

**Arquivos:**
- `Fix/backup_pre_merge/` (novo — cópia)

**Escopo:** XS — operação de cópia, sem edição de código

---

### Task B1: Eliminar 11 stubs sem lógica real

**Descrição:** 11 arquivos são stubs que apenas re-exportam de caminhos já estabelecidos. Deletar ou mover para `_archive/` para reduzir contagem sem alterar nenhuma lógica.

**Stubs a eliminar:**
```
Fix/extracao_analise.py
Fix/extracao_documento.py
Fix/extracao_indexacao.py
Fix/extracao_indexacao_fluxo.py
Fix/extracao_processo.py
Fix/monitoramento_progresso_unificado.py
Fix/progresso_unificado.py
Fix/progress_models.py
Fix/progress.py              ← stub (não o subpacote Fix/progress/)
Fix/legacy/extracao_analise.py
Fix/legacy/progress_models.py
```

**Acceptance criteria:**
- [ ] 11 arquivos acima não existem em `Fix/` (movidos para `_archive/` ou deletados)
- [ ] 7 imports críticos passam após remoção
- [ ] `py -c "import x"` limpo

**Verificação:**
```bash
# Confirmar ausência
Get-ChildItem Fix\extracao_analise.py, Fix\progresso_unificado.py 2>$null
# Esperado: zero resultados

py -c "import x; print('OK')"
# 7 imports críticos
```

**Dependências:** B0

**Arquivos:** 11 arquivos deletados/arquivados

**Escopo:** S — deleção de stubs, zero lógica alterada

---

### Task B2: Merge `log.py` ← `log_cleaner.py` + `exceptions.py`

**Descrição:** Concatenar `log_cleaner.py` e `exceptions.py` ao final de `log.py`. Após merge, deletar os arquivos fonte. Todos os símbolos públicos dos 3 arquivos devem ser importáveis via `Fix.log`.

**Acceptance criteria:**
- [ ] `Fix/log.py` contém todo o conteúdo dos 3 arquivos
- [ ] `Fix/log_cleaner.py` e `Fix/exceptions.py` deletados
- [ ] `from Fix.log import get_module_logger` funciona
- [ ] `from Fix.log import PJeException` funciona (ou via `Fix/__init__.py`)
- [ ] `from Fix.log import resumir_excecao, filtrar_log_arquivo` funciona

**Verificação:**
```bash
py -m py_compile Fix/log.py
py -c "from Fix.log import get_module_logger, resumir_excecao; print('OK')"
py -c "import x; print('OK')"
```

**Dependências:** B1

**Arquivos:** `Fix/log.py` (modificado), 2 deletados

**Escopo:** S — concatenação + deleção

---

### Task B3: Merge `progress/` subpacote → `Fix/progress.py` root

**Descrição:** Consolidar `progress/monitoramento.py` + `progress/models.py` + `progress/__init__.py` em `Fix/progress.py` root. Deletar subpacote `Fix/progress/`.

**Acceptance criteria:**
- [ ] `Fix/progress.py` contém todo o conteúdo do subpacote
- [ ] `Fix/progress/` deletado
- [ ] `from Fix.progress import carregar_progresso, salvar_progresso` funciona
- [ ] `Fix/__init__.py` atualizado se necessário

**Verificação:**
```bash
py -m py_compile Fix/progress.py
py -c "from Fix.progress import carregar_progresso, salvar_progresso; print('OK')"
py -c "import x; print('OK')"
```

**Dependências:** B1

**Arquivos:** `Fix/progress.py` (novo root), `Fix/progress/` deletado

**Escopo:** S — merge de subpacote

---

### Task B4: Merge `selenium_base/` → 3 arquivos flat

**Descrição:** Achatar o subpacote `Fix/selenium_base/` em 3 arquivos no root:
- `selenium.py` ← `element_interaction.py` + `driver_operations.py`
- `selenium_wait.py` ← `wait_operations.py` + `retry_logic.py` + `click_operations.py`
- `selenium_select.py` ← `smart_selection.py` + `field_operations.py`
- `js_helpers.py` ← `js_helpers.py` (mover para root)

**Acceptance criteria:**
- [ ] 4 arquivos novos no root de `Fix/`
- [ ] `Fix/selenium_base/` deletado
- [ ] `Fix/__init__.py` re-exporta todos os símbolos públicos dos 4 arquivos
- [ ] `from Fix.selenium_base.retry_logic import CircuitBreaker, cb_sisbajud` ainda funciona via `Fix/__init__.py`
- [ ] `from Fix.selenium_base.wait_operations import aguardar_mutacao_async` ainda funciona via alias

**Verificação:**
```bash
py -m py_compile Fix/selenium.py Fix/selenium_wait.py Fix/selenium_select.py Fix/js_helpers.py
py -c "from Fix.selenium_base.retry_logic import CircuitBreaker; print('OK')"
py -c "from Fix.selenium_base.wait_operations import aguardar_mutacao_async; print('OK')"
py -c "import x; print('OK')"
```

**Dependências:** B2, B3

**Arquivos:** 4 novos, `Fix/selenium_base/` deletado, `Fix/__init__.py` atualizado

**Escopo:** L — maior merge, risco mais alto. Fazer por último dentro de B.

---

### Task B5: Merge grupos menores (documents, navigation, session, extraction, drivers)

**Descrição:** Achatar os subpacotes restantes:
- `documents.py` ← `documents/__init__.py` + `documents/busca.py` + `documents/download.py` + `documents/search.py`
- `navigation.py` ← `navigation/__init__.py` + `navigation/filtros.py` + `navigation/sigilo.py`
- `session.py` ← `session/__init__.py` + `session/manager.py` + `utils_cookies.py`
- `extraction.py` ← `extraction/indexacao.py` + `extraction/__init__.py`
- `drivers.py` ← `drivers/__init__.py` + `drivers/factory.py` + `utils_drivers.py` + `utils_paths.py` + `utils_login.py` + `drivers/lifecycle.py`

**Acceptance criteria:**
- [ ] 5 arquivos novos no root de `Fix/`
- [ ] Subpacotes correspondentes deletados
- [ ] Todos os símbolos públicos re-exportados via `Fix/__init__.py`
- [ ] 7 imports críticos passam após cada subgrupo (commitar um por vez)

**Verificação (após cada subgrupo):**
```bash
py -m py_compile Fix/<novo_arquivo>.py
py -c "import x; print('OK')"
# 7 imports críticos
```

**Dependências:** B4

**Arquivos:** 5 novos, múltiplos subpacotes deletados, `Fix/__init__.py` atualizado

**Escopo:** L — executar em 5 sub-commits, um por subpacote

---

### Task B6: Merge arquivos utils e core grandes

**Descrição:** Último grupo — arquivos maiores e de maior uso:
- `utils.py` ← `utils_formatting.py` + `utils_sleep.py` + `utils_error.py` + `utils_tempo.py` + `utils_recovery.py` + `utils_observer.py` + `utils_driver_legacy.py` + `converters.py` + `utils_collect.py` + `scripts/loader.py`
- `utils_editor.py` ← `utils_editor.py` + `utils_collect_content.py` + `utils_collect_timeline.py`
- `selectors.py` ← `utils_angular.py` + `utils_selectors.py` + `selectors_pje.py` + `element_wait.py` + `smart_finder.py`
- `core.py` ← absorver `otimizacao_wrapper.py` + `debug_interativo.py` + `debug_assinatura.py` + `assinatura_cookies.py` + `movimento_helpers.py` + `infojud.py` + `abas.py` + `headless_helpers.py` + `forms/__init__.py` + `forms/multi_fields.py`

**Acceptance criteria:**
- [ ] `Fix/` com ≤ 20 arquivos `.py` (excluindo `__pycache__`)
- [ ] `py -m py_compile Fix/*.py` limpo
- [ ] 7 imports críticos passam
- [ ] `Fix/backup_pre_merge/` ainda existe como rollback

**Verificação:**
```bash
(Get-ChildItem Fix\*.py | Measure-Object).Count
# Esperado: ≤ 20

py -m py_compile (Get-ChildItem Fix\*.py | Select-Object -Expand FullName)
py -c "import x; print('OK')"
# 7 imports críticos completos
```

**Dependências:** B5

**Arquivos:** múltiplos merges, `Fix/__init__.py` finalizado

**Escopo:** XL — dividir em 4 sub-commits (utils, selectors, utils_editor, core)

---

### Checkpoint Fase 3

```powershell
# Contar arquivos
(Get-ChildItem Fix\*.py | Measure-Object).Count
# Esperado: ≤ 20

# Compilar tudo
py -m py_compile (Get-ChildItem Fix\*.py -Recurse | Select-Object -Expand FullName)

# Imports que usavam caminhos antigos (via __init__.py)
py -c "from Fix.selenium_base.retry_logic import CircuitBreaker; print('CircuitBreaker OK')"
py -c "from Fix.utils_angular import aguardar_angular_estavel; print('Angular OK')"
py -c "from Fix.headless_helpers import click_headless_safe; print('Headless OK')"

# 7 imports críticos
@("import x","from Fix.core import finalizar_driver",
  "from Mandado.processamento_api import processar_mandados_devolvidos_api",
  "from PEC.orquestrador import executar_fluxo_novo_simplificado",
  "from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b",
  "from Triagem.runner import run_triagem",
  "from Peticao.pet import run_pet"
) | ForEach-Object {
    $r = py -c $_ 2>&1
    if ($LASTEXITCODE -eq 0) { "OK   $_" } else { "FAIL $_`n$r" }
}
```

- [ ] `Fix/` tem ≤ 20 arquivos `.py`
- [ ] `py -m py_compile` limpo em todos os arquivos de `Fix/`
- [ ] Imports de caminhos antigos (compat) funcionam via `Fix/__init__.py`
- [ ] Todos os 7 imports críticos OK
- [ ] `Fix/backup_pre_merge/` existe

---

## Fase 4 — Código Morto Restante (Vulture Slices 4+)

> **Pré-condição:** Fase 3 concluída (evitar que vulture aponte código que será movido no merge).

---

### Task C0: Gerar relatório vulture atualizado pós-merge

**Descrição:** Após os merges da Fase 3, o relatório vulture anterior aponta para arquivos que não existem mais. Gerar relatório fresco com a estrutura nova.

**Acceptance criteria:**
- [ ] `tools/vulture_report_latest.txt` gerado com confiança ≥ 80%
- [ ] Relatório exclui `_archive/`, `Fix/backup_pre_merge/`, `ref/`, `aider-env/`
- [ ] Whitelist atualizada para caminhos novos (remoção de refs a arquivos eliminados)

**Verificação:**
```bash
py -m vulture Fix/ atos/ SISB/ Prazo/ PEC/ Mandado/ Peticao/ Triagem/ `
   tools/vulture_whitelist.py `
   --min-confidence 80 `
   --exclude "_archive,Fix/backup_pre_merge,ref,aider-env" `
   | Out-File tools/vulture_report_latest.txt

(Get-Content tools\vulture_report_latest.txt).Count
# Documentar como baseline pós-merge
```

**Dependências:** Fase 3 completa

**Arquivos:** `tools/vulture_report_latest.txt`, `tools/vulture_whitelist.py` (revisão)

**Escopo:** XS

---

### Task C4: Slice 4 — Imports mortos em `atos/`, `SISB/`

**Descrição:** Remover declarações `import` nunca referenciadas em até 5 arquivos de `atos/` e `SISB/`. Filtrar por confiança ≥ 90% do relatório.

**Acceptance criteria:**
- [ ] Imports unused removidos em até 5 arquivos
- [ ] Nenhum `NameError` ao importar os módulos modificados
- [ ] 7 imports críticos passam

**Verificação:**
```bash
grep "unused import" tools\vulture_report_latest.txt | Select-String "atos|SISB" | Select-Object -First 20
# Editar até 5 arquivos
py -m py_compile <arquivos_editados>
py -c "import x; print('OK')"
git add -p && git commit -m "chore: vulture slice 4 - unused imports atos/SISB"
```

**Dependências:** C0

**Escopo:** S — até 5 arquivos

---

### Task C5: Slice 5 — Imports mortos em `Mandado/`, `Peticao/`, `Triagem/`, `Prazo/`, `PEC/`

**Acceptance criteria:**
- [ ] Imports unused removidos em até 5 arquivos
- [ ] `from Triagem.runner import run_triagem` passa
- [ ] `from Peticao.pet import run_pet` passa

**Verificação:**
```bash
py -m py_compile <arquivos_editados>
py -c "from Triagem.runner import run_triagem; from Peticao.pet import run_pet; print('OK')"
git commit -m "chore: vulture slice 5 - unused imports módulos de negócio"
```

**Dependências:** C4 · **Escopo:** S

---

### Task C6: Scan de imports órfãos

**Descrição:** Executar `tools/scan_orphan_imports.py` (Task 3.1 de `limpar-repositorio.md`, ainda pendente). Detectar `from X import Y` onde `Y` não existe mais após os merges.

**Acceptance criteria:**
- [ ] `py tools/scan_orphan_imports.py` executa sem exceção
- [ ] Zero `ImportError` latentes identificados
- [ ] Qualquer órfão encontrado: corrigido antes de prosseguir

**Verificação:**
```bash
py tools/scan_orphan_imports.py
# Saída esperada: "0 imports órfãos encontrados"
```

**Dependências:** C5 · **Escopo:** XS

---

### Checkpoint Fase 4

```powershell
# Relatório vulture atual
py -m vulture Fix/ atos/ SISB/ Prazo/ PEC/ Mandado/ Peticao/ Triagem/ `
   tools/vulture_whitelist.py --min-confidence 80 `
   --exclude "_archive,Fix/backup_pre_merge,ref,aider-env" `
   | Out-File tools/vulture_report_final.txt

(Get-Content tools\vulture_report_final.txt).Count
# Comparar com baseline de C0 — deve ser menor

py -c "import x; print('OK')"
py tools/scan_orphan_imports.py
```

- [ ] Contagem de achados menor que baseline C0
- [ ] Scan de imports órfãos: 0 encontrados
- [ ] 7 imports críticos OK

---

## Fase 5 — CI / GitHub Actions

> **Pré-condição:** Fases 1 e 3 concluídas. Profile fallback e download prefs devem estar funcionando.

---

### Task CI1: Workflow básico headless

**Descrição:** Criar `.github/workflows/pjeplus-sanity.yml` para validação de sintaxe e imports a cada push. Não requer credenciais PJe — apenas valida que o código importa sem erros.

**Acceptance criteria:**
- [ ] Workflow executa em `ubuntu-latest`
- [ ] Step de sanity: `py -m py_compile Fix/*.py` e 7 imports críticos
- [ ] Variáveis `PJEPLUS_HEADLESS=1` e `PJEPLUS_TIME=1` definidas como env
- [ ] Workflow passa no primeiro run sem credenciais PJe

**Verification:**
```yaml
# .github/workflows/pjeplus-sanity.yml
env:
  PJEPLUS_HEADLESS: "1"
  PJEPLUS_TIME: "1"
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: "3.11"
  - run: pip install -r requirements.txt
  - name: Sanity compile
    run: python -m py_compile Fix/*.py atos/*.py
  - name: Import check
    run: |
      python -c "from Fix.core import finalizar_driver"
      python -c "from Fix.drivers.lifecycle import criar_driver_PC"
```

**Dependências:** Fase 1 completa (profile fallback e download prefs)

**Arquivos:**
- `.github/workflows/pjeplus-sanity.yml` (novo)

**Escopo:** S — 1 arquivo YAML

---

### Task CI2: `requirements.txt` para CI

**Descrição:** `requirements.txt` atualmente pode não existir ou estar incompleto para ambiente Linux. Garantir que `selenium`, `geckodriver-autoinstaller` (ou equivalente) e demais deps estão listados.

**Acceptance criteria:**
- [ ] `requirements.txt` na raiz com todas as dependências Python do projeto
- [ ] `pip install -r requirements.txt` funciona em ambiente Linux limpo
- [ ] Não inclui `keyring` como obrigatório (é opcional — CI não tem keyring configurado)

**Verificação:**
```bash
# Testar em ambiente virtual limpo
py -m venv test_env
test_env\Scripts\activate
pip install -r requirements.txt
py -c "from Fix.core import finalizar_driver; print('OK')"
deactivate
Remove-Item -Recurse test_env
```

**Dependências:** CI1

**Arquivos:**
- `requirements.txt`

**Escopo:** S — 1 arquivo

---

### Checkpoint Fase 5

- [ ] `.github/workflows/pjeplus-sanity.yml` passa no GitHub Actions
- [ ] `PJEPLUS_HEADLESS=1` ativo no workflow
- [ ] `PJEPLUS_TIME=1` ativo no workflow
- [ ] `requirements.txt` instalável em Linux limpo
- [ ] Nenhuma credencial hardcoded no workflow

---

## Resumo Executivo

| Fase | Objetivo | Tasks | Risco | Esforço |
|------|----------|-------|-------|---------|
| 1 — Desbloqueadores Headless | Habilitar `headless=True` sem travamento | P1, P2, P3 | Baixo | ~1h |
| 2 — Eliminar `time.sleep` | -20–40s por lote SISBAJUD | S1–S5 | Médio | ~3h |
| 3 — Consolidar `Fix/` | 89 → ≤18 arquivos, imports limpos | B0–B6 | Alto | ~8h |
| 4 — Código morto | Superfície menor, imports saudáveis | C0, C4–C6 | Baixo | ~2h |
| 5 — CI | Validação automática a cada push | CI1, CI2 | Baixo | ~1h |

**Ordem obrigatória:** 1 → 2 → 3 → 4 → 5

**Paralelizável:**
- P1, P2 são independentes entre si (mesma fase, mesmo arquivo — fazer sequencial)
- S1, S2, S3, S4, S5 são independentes entre si (arquivos distintos, fazer em paralelo se houver múltiplos agentes)
- C4 e C5 são independentes entre si

**Não paralelizar:**
- Fase 3 (merges de Fix/) deve ser estritamente sequencial — B0 → B1 → B2 → B3 → B4 → B5 → B6

---

## Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| `aguardar_renderizacao_nativa` não cobre todos os casos do sleep substituído | Médio | Adicionar timeout guard; testar em 2 fluxos reais antes de commitar |
| Merge de Fase 3 quebra import circular | Alto | Commitar por subgrupo; validar 7 imports após cada merge; rollback via `Fix/backup_pre_merge/` |
| `utils_observer.py` com `execute_async_script` quebraria Angular CDK | Alto | **Não substituir** — polling de 50ms é escolha deliberada documentada |
| `keyring` falha silenciosa em CI | Baixo | Task P2 adiciona fallback antes do `FirefoxProfile` |
| Vulture falso-positivo remove API pública | Médio | Confiança mínima 80%; revisar manualmente antes de deletar |

## Questões Abertas

- `scan_orphan_imports.py` (Task C6) existe em `tools/`? Se não, criar antes da Fase 4.
- `requirements.txt` existe na raiz? Se sim, está completo para Linux?
- Qual a versão mínima do geckodriver para Firefox headless moderno (≥ 115 ESR)?
