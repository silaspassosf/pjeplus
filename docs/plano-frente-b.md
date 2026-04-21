# Plano Frente B — Consolidar `Fix/` (89 → 18 arquivos)

## Overview

Reduzir `Fix/` de 89 arquivos Python (~16.5k linhas) para 18 arquivos via merge por domínio. Nenhum código é reescrito — apenas movido e concatenado. Stubs sem lógica são eliminados. O `__init__.py` mantém retrocompatibilidade dos imports externos.

**Meta:** ≤ 20 arquivos totais em `Fix/` (excluindo `__pycache__`).

## Decisões de Arquitetura

- **Não dividir** arquivos que já passam de 600 linhas — trade-off consciente para reduzir file count
- **`selenium_base/` é achatado** no root — única forma de chegar ≤ 20 total
- **`__init__.py` centraliza** todos os re-exports para que imports externos não quebrem
- **Nenhuma lógica de negócio** é alterada — mover e concatenar apenas
- **Backup obrigatório** antes de qualquer merge

## Estrutura Final Alvo

```
Fix/
├── __init__.py          (~250 l)   API pública re-exports
├── core.py              (~2.300 l) Core + debug + abas + headless + forms
├── log.py               (~676 l)   Log + exceptions + log_cleaner
├── extracao.py          (~1.700 l) Extração + BNDT + gigs
├── extraction.py        (~700 l)   Indexação de processos
├── progress.py          (~800 l)   Progresso unificado
├── drivers.py           (~1.000 l) Driver lifecycle + paths + login
├── session.py           (~730 l)   Cookies + auth
├── navigation.py        (~635 l)   Filtros + sigilo + navegação
├── documents.py         (~770 l)   Busca de documentos
├── variaveis.py         (~1.056 l) Variáveis completo
├── utils.py             (~900 l)   Formatting/sleep/error/collect
├── utils_editor.py      (~650 l)   Editor + collect + timeline
├── selectors.py         (~550 l)   Selectors + angular + smart_finder
├── selenium.py          (~1.200 l) element_interaction + driver_operations
├── selenium_wait.py     (~800 l)   wait_operations + retry_logic + click_operations
├── selenium_select.py   (~670 l)   smart_selection + field_operations
└── js_helpers.py        (~115 l)   js_helpers
```

**Total: 18 arquivos** ✅

## Task List

---

### Phase 0: Safety Net

## Task B0: Backup e validação de baseline

**Descrição:** Antes de qualquer merge, garantir que o estado atual compila limpo e criar backup de rollback.

**Acceptance criteria:**
- [ ] `Fix/backup_pre_merge/` criado com cópia completa de `Fix/`
- [ ] `py -m py_compile` passa em todos os arquivos atuais de `Fix/`
- [ ] 6 imports críticos passam (ver abaixo)

**Verificação:**
```bash
# Criar backup
cp -r Fix/ Fix/backup_pre_merge/

# Compilar tudo
py -m py_compile Fix/*.py Fix/**/*.py

# 6 imports críticos
py -c "from Fix.core import finalizar_driver"
py -c "from Mandado.processamento_api import processar_mandados_devolvidos_api"
py -c "from PEC.orquestrador import executar_fluxo_novo_simplificado"
py -c "from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b"
py -c "from Triagem.runner import run_triagem"
py -c "from Peticao.pet import run_pet"
```

**Dependências:** Nenhuma  
**Arquivos:** `Fix/backup_pre_merge/` (novo)  
**Escopo:** XS

---

### Checkpoint 0: Safety Net
- [ ] Backup existe
- [ ] Todos os 6 imports críticos passam antes de qualquer mudança

---

### Phase 1: Eliminar Stubs

## Task B1: Remover stubs sem lógica real

**Descrição:** 11 arquivos são stubs que apenas re-exportam de caminhos novos já estabelecidos. Eliminá-los reduz ruído sem quebrar nada (os imports que importavam deles devem ter migrado).

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
Fix/progress.py              ← stub (não o subpacote)
Fix/legacy/extracao_analise.py
Fix/legacy/progress_models.py
```

**Acceptance criteria:**
- [ ] 11 arquivos acima deletados (ou movidos para `_archive/`)
- [ ] Nenhum dos 6 imports críticos quebrou
- [ ] `py -c "import x"` limpo

**Verificação:**
```bash
py -c "import x"
py -c "from Fix.core import finalizar_driver"
# (todos 6 imports críticos)
```

**Dependências:** B0  
**Arquivos:** 11 arquivos deletados  
**Escopo:** S

---

### Checkpoint 1: Após Eliminação de Stubs
- [ ] 6 imports críticos passam
- [ ] `py -c "import x"` limpo

---

### Phase 2: Merges de Grupos Pequenos

## Task B2: Merge `log.py` (log + exceptions + log_cleaner)

**Descrição:** Concatenar `log_cleaner.py` e `exceptions.py` ao final de `log.py`. Deletar os dois arquivos fontes.

**Fontes → Destino:**
| Fonte | Ação |
|-------|------|
| `Fix/log.py` | Base (~523 l) |
| `Fix/log_cleaner.py` | Append (~122 l) |
| `Fix/exceptions.py` | Append (~31 l) |

**Acceptance criteria:**
- [ ] `Fix/log.py` contém todo o conteúdo dos 3 arquivos
- [ ] `Fix/log_cleaner.py` e `Fix/exceptions.py` deletados
- [ ] Todos os símbolos públicos dos 3 arquivos importáveis via `Fix.log`

**Verificação:**
```bash
py -m py_compile Fix/log.py
py -c "from Fix.log import get_logger; print('OK')"
py -c "from Fix.exceptions import PJeException; print('OK')"  # via __init__.py
```

**Dependências:** B1  
**Arquivos:** `Fix/log.py` (modificado), 2 deletados  
**Escopo:** S

---

## Task B3: Merge `js_helpers.py` (selenium_base → root)

**Descrição:** Mover `Fix/selenium_base/js_helpers.py` para `Fix/js_helpers.py`. Atualizar imports internos que referenciam `Fix.selenium_base.js_helpers`.

**Acceptance criteria:**
- [ ] `Fix/js_helpers.py` existe no root
- [ ] `Fix/selenium_base/js_helpers.py` deletado
- [ ] `Fix/selenium_base/__init__.py` atualizado para não re-exportar de `js_helpers`

**Verificação:**
```bash
py -m py_compile Fix/js_helpers.py
py -c "from Fix.js_helpers import executar_script_js; print('OK')"
```

**Dependências:** B1  
**Arquivos:** `Fix/js_helpers.py` (novo), 1 deletado  
**Escopo:** XS

---

## Task B4: Merge `progress.py` (subpacote → root)

**Descrição:** Consolidar `progress/monitoramento.py` + `progress/models.py` + `progress/__init__.py` em `Fix/progress.py` root. Deletar subpacote `Fix/progress/`.

**Acceptance criteria:**
- [ ] `Fix/progress.py` contém todo o conteúdo do subpacote
- [ ] `Fix/progress/` deletado
- [ ] Imports existentes via `Fix.progress.*` funcionam via `__init__.py`

**Verificação:**
```bash
py -m py_compile Fix/progress.py
py -c "from Fix.progress import carregar_progresso, salvar_progresso; print('OK')"
```

**Dependências:** B1  
**Arquivos:** `Fix/progress.py` (novo root), subpacote deletado  
**Escopo:** S

---

## Task B5: Merge `extraction.py` (subpacote → root)

**Descrição:** Mover `extraction/indexacao.py` + `extraction/__init__.py` para `Fix/extraction.py` root. Deletar subpacote.

**Acceptance criteria:**
- [ ] `Fix/extraction.py` no root com conteúdo completo
- [ ] `Fix/extraction/` deletado
- [ ] Imports via `Fix.extraction` funcionam

**Verificação:**
```bash
py -m py_compile Fix/extraction.py
py -c "from Fix.extraction import indexar_processo; print('OK')"
```

**Dependências:** B1  
**Arquivos:** `Fix/extraction.py` (novo root), subpacote deletado  
**Escopo:** S

---

### Checkpoint 2: Após Grupos Pequenos (B2–B5)
- [ ] `py -m py_compile Fix/*.py` sem erros
- [ ] 6 imports críticos passam
- [ ] `py -c "import x"` limpo

---

### Phase 3: Merges de Subpacotes Médios

## Task B6: Merge `drivers.py` + `session.py`

**Descrição:** Consolidar subpacotes `drivers/` e `session/` em arquivos root únicos, incluindo `utils_drivers.py`, `utils_paths.py`, `utils_login.py` em `drivers.py` e `utils_cookies.py` em `session.py`.

**Fontes → `Fix/drivers.py`:**
- `Fix/drivers/__init__.py` + `Fix/drivers/factory.py`
- `Fix/utils_drivers.py`, `Fix/utils_paths.py`, `Fix/utils_login.py`

**Fontes → `Fix/session.py`:**
- `Fix/session/__init__.py` + `Fix/session/manager.py`
- `Fix/utils_cookies.py`

**Acceptance criteria:**
- [ ] `Fix/drivers.py` e `Fix/session.py` existem no root
- [ ] Subpacotes `Fix/drivers/` e `Fix/session/` deletados
- [ ] `utils_drivers.py`, `utils_paths.py`, `utils_login.py`, `utils_cookies.py` deletados

**Verificação:**
```bash
py -m py_compile Fix/drivers.py Fix/session.py
py -c "from Fix.drivers import criar_driver_PC; print('OK')"
py -c "from Fix.session import carregar_cookies; print('OK')"
py -c "from Fix.core import finalizar_driver"  # import crítico
```

**Dependências:** B1  
**Arquivos:** 2 novos root, 2 subpacotes + 4 utils deletados  
**Escopo:** M

---

## Task B7: Merge `navigation.py` + `documents.py`

**Descrição:** Consolidar subpacotes `navigation/` (3 arquivos) e `documents/` (3 arquivos) em arquivos root únicos.

**Fontes → `Fix/navigation.py`:**
- `Fix/navigation/__init__.py`, `Fix/navigation/filtros.py`, `Fix/navigation/sigilo.py`

**Fontes → `Fix/documents.py`:**
- `Fix/documents/__init__.py`, `Fix/documents/busca.py`, `Fix/documents/download.py`

**Acceptance criteria:**
- [ ] `Fix/navigation.py` e `Fix/documents.py` existem no root
- [ ] Subpacotes `Fix/navigation/` e `Fix/documents/` deletados

**Verificação:**
```bash
py -m py_compile Fix/navigation.py Fix/documents.py
py -c "from Fix.navigation import aplicar_filtros; print('OK')"
py -c "from Fix.documents import buscar_documento; print('OK')"
```

**Dependências:** B1  
**Escopo:** M

---

## Task B8: Merge `extracao.py` (extração + BNDT + gigs)

**Descrição:** Consolidar `extracao_conteudo.py`, `extracao_bndt.py` e subpacote `gigs/` em `Fix/extracao.py`. O shim `Fix/extracao.py` atual é substituído pelo conteúdo real.

**Fontes → `Fix/extracao.py`:**
- `Fix/extracao_conteudo.py` (base, ~579 l)
- `Fix/extracao_bndt.py` (append, ~444 l)
- `Fix/gigs/__init__.py` + `Fix/gigs/creation.py` (append, ~598 l)

**Acceptance criteria:**
- [ ] `Fix/extracao.py` com conteúdo completo (~1.700 l)
- [ ] `extracao_conteudo.py`, `extracao_bndt.py` deletados
- [ ] Subpacote `Fix/gigs/` deletado

**Verificação:**
```bash
py -m py_compile Fix/extracao.py
py -c "from Fix.extracao import extrair_texto_processo; print('OK')"
py -c "from Fix.extracao import criar_gig; print('OK')"
```

**Dependências:** B1  
**Escopo:** M

---

### Checkpoint 3: Após Subpacotes Médios (B6–B8)
- [ ] `py -m py_compile Fix/*.py`
- [ ] 6 imports críticos passam
- [ ] Contagem de arquivos em `Fix/` está caindo conforme esperado

---

### Phase 4: Merges Grandes

## Task B9: Merge `utils.py` consolidado

**Descrição:** Consolidar 10 utils menores no `Fix/utils.py` existente. `utils_editor.py` fica separado (conteúdo demais). `selectors.py` é criado separado na Task B10.

**Fontes → `Fix/utils.py`:**
- Base: `Fix/utils.py` (facade atual)
- Append: `utils_formatting.py`, `utils_sleep.py`, `utils_error.py`, `utils_tempo.py`
- Append: `utils_recovery.py`, `utils_observer.py`, `utils_driver_legacy.py`
- Append: `converters.py`, `utils_collect.py`, `Fix/scripts/loader.py`

**Acceptance criteria:**
- [ ] `Fix/utils.py` contém todo o conteúdo dos 10 arquivos fonte
- [ ] 10 arquivos fonte deletados (incluindo `Fix/scripts/`)
- [ ] Imports históricos via `Fix.utils.*` funcionam

**Verificação:**
```bash
py -m py_compile Fix/utils.py
py -c "from Fix.utils import formatar_data, limpar_texto; print('OK')"
py -c "from Fix.utils import sleep_humano; print('OK')"
```

**Dependências:** B1  
**Escopo:** L

---

## Task B10: Criar `Fix/selectors.py` (angular + selectors + smart_finder)

**Descrição:** Criar `Fix/selectors.py` consolidando `utils_angular.py` (com fix A1 já aplicado), `utils_selectors.py`, `selectors_pje.py`, `element_wait.py` e `smart_finder.py`.

**Acceptance criteria:**
- [ ] `Fix/selectors.py` existe com ~550 l
- [ ] 5 arquivos fonte deletados
- [ ] `SmartFinder` e `aguardar_angular_estavel` importáveis via `Fix.selectors`

**Verificação:**
```bash
py -m py_compile Fix/selectors.py
py -c "from Fix.selectors import SmartFinder, aguardar_angular_estavel; print('OK')"
```

**Dependências:** A1 (fix Angular deve estar aplicado antes), B1  
**Escopo:** M

---

## Task B11: Criar `Fix/utils_editor.py` consolidado

**Descrição:** Consolidar `utils_editor.py` (base), `utils_collect_content.py` e `utils_collect_timeline.py` em `Fix/utils_editor.py`.

**Acceptance criteria:**
- [ ] `Fix/utils_editor.py` com ~650 l
- [ ] `utils_collect_content.py` e `utils_collect_timeline.py` deletados

**Verificação:**
```bash
py -m py_compile Fix/utils_editor.py
py -c "from Fix.utils_editor import abrir_editor, coletar_timeline; print('OK')"
```

**Dependências:** B1  
**Escopo:** S

---

## Task B12: Consolidar `variaveis.py` completo

**Descrição:** Unificar `variaveis.py`, `variaveis_client.py`, `variaveis_helpers.py`, `variaveis_painel.py` e `variaveis_resolvers.py` em `Fix/variaveis.py`.

**Acceptance criteria:**
- [ ] `Fix/variaveis.py` com ~1.056 l
- [ ] 4 arquivos fonte deletados
- [ ] Todas as variáveis e resolvers importáveis via `Fix.variaveis`

**Verificação:**
```bash
py -m py_compile Fix/variaveis.py
py -c "from Fix.variaveis import SELETORES_PJE, resolver_vara; print('OK')"
```

**Dependências:** B1  
**Escopo:** M

---

### Phase 5: Achatar `selenium_base/`

## Task B13: Criar `Fix/selenium.py` (element_interaction + driver_operations)

**Descrição:** Mover `selenium_base/element_interaction.py` e `selenium_base/driver_operations.py` para `Fix/selenium.py`.

**Acceptance criteria:**
- [ ] `Fix/selenium.py` com ~1.200 l
- [ ] 2 arquivos fonte removidos de `selenium_base/`
- [ ] Imports via `Fix.selenium_base.*` preservados em `__init__.py`

**Verificação:**
```bash
py -m py_compile Fix/selenium.py
py -c "from Fix.selenium import aguardar_e_clicar; print('OK')"
```

**Dependências:** B0  
**Escopo:** M

---

## Task B14: Criar `Fix/selenium_wait.py` (wait + retry + click)

**Descrição:** Mover `selenium_base/wait_operations.py`, `selenium_base/retry_logic.py` (com A2 já aplicado) e `selenium_base/click_operations.py` para `Fix/selenium_wait.py`.

**Acceptance criteria:**
- [ ] `Fix/selenium_wait.py` com ~800 l
- [ ] 3 arquivos removidos de `selenium_base/`
- [ ] `com_retry`, `CircuitBreaker`, `aguardar_mutacao_async` importáveis via `Fix.selenium_wait`

**Verificação:**
```bash
py -m py_compile Fix/selenium_wait.py
py -c "from Fix.selenium_wait import com_retry, CircuitBreaker, aguardar_mutacao_async; print('OK')"
```

**Dependências:** A2, A3, B0  
**Escopo:** M

---

## Task B15: Criar `Fix/selenium_select.py` (smart_selection + field_operations)

**Descrição:** Mover `selenium_base/smart_selection.py` e `selenium_base/field_operations.py` para `Fix/selenium_select.py`. Deletar `Fix/selenium_base/` (agora vazio).

**Acceptance criteria:**
- [ ] `Fix/selenium_select.py` com ~670 l
- [ ] `Fix/selenium_base/` deletado (todos arquivos migrados)
- [ ] `selecionar_opcao`, `preencher_campo` importáveis via `Fix.selenium_select`

**Verificação:**
```bash
py -m py_compile Fix/selenium_select.py
py -c "from Fix.selenium_select import selecionar_opcao, preencher_campo; print('OK')"
```

**Dependências:** B13, B14  
**Escopo:** S

---

### Phase 6: Merge `core.py` + Atualizar `__init__.py`

## Task B16: Expandir `Fix/core.py` com módulos auxiliares

**Descrição:** Acrescentar ao `Fix/core.py` o conteúdo de: `otimizacao_wrapper.py`, `debug_interativo.py`, `debug_assinatura.py`, `assinatura_cookies.py`, `movimento_helpers.py`, `infojud.py`, `timeline.py`, `native_host.py`, `abas.py`, `headless_helpers.py` e `forms/` (multi_fields + __init__).

**Acceptance criteria:**
- [ ] `Fix/core.py` com ~2.300 l contendo todo o conteúdo dos 11 fontes
- [ ] 11 arquivos fonte + `Fix/forms/` deletados
- [ ] `finalizar_driver`, `aguardar_e_clicar` ainda importáveis

**Verificação:**
```bash
py -m py_compile Fix/core.py
py -c "from Fix.core import finalizar_driver, aguardar_e_clicar, debug_interativo; print('OK')"
```

**Dependências:** B13, B14, B15  
**Escopo:** L

---

## Task B17: Atualizar `Fix/__init__.py` com re-exports consolidados

**Descrição:** Reescrever `Fix/__init__.py` para re-exportar todos os símbolos públicos dos novos módulos consolidados. Garantir que nenhum import externo quebra.

**Acceptance criteria:**
- [ ] Todos os símbolos previamente exportados pelo `__init__.py` antigo estão disponíveis
- [ ] Imports históricos do tipo `from Fix import aguardar_e_clicar` continuam funcionando
- [ ] 6 imports críticos de negócio passam

**Verificação:**
```bash
py -m py_compile Fix/__init__.py
# Todos 6 imports críticos:
py -c "from Fix.core import finalizar_driver"
py -c "from Mandado.processamento_api import processar_mandados_devolvidos_api"
py -c "from PEC.orquestrador import executar_fluxo_novo_simplificado"
py -c "from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b"
py -c "from Triagem.runner import run_triagem"
py -c "from Peticao.pet import run_pet"
py -c "import x"
```

**Dependências:** Todas as tarefas B2–B16  
**Escopo:** M

---

### Checkpoint Final: Frente B Completa
- [ ] `Fix/` tem ≤ 20 arquivos Python (excluindo `__pycache__`)
- [ ] `py -m py_compile Fix/*.py` sem erros
- [ ] Todos os 6 imports críticos passam
- [ ] `py -c "import x"` limpo
- [ ] Backup `Fix/backup_pre_merge/` intacto para rollback

## Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Nomes de símbolo duplicados no merge | Médio | Grep por `def ` e `class ` antes de concatenar; resolver conflitos manualmente |
| Import circular após consolidação | Alto | Rodar `py -m py_compile` após cada task; reverter e reorganizar se necessário |
| Side-effect em top-level de algum arquivo | Médio | Revisar cada arquivo antes do merge (top-level além de `import` e atribuição) |
| `__init__.py` incompleto | Alto | Manter lista de símbolos públicos do antigo `__init__.py` e confrontar com o novo |
| Arquivo final >2.000 linhas difícil de navegar | Baixo | Aceitável — trade-off consciente; usar comentários de seção `# === SEÇÃO ===` |

## Ordem de Execução Recomendada

```
B0 → B1 → [B2, B3, B4, B5 em paralelo] → checkpoint 2 →
[B6, B7, B8 em paralelo] → checkpoint 3 →
[B9, B10, B11, B12 em paralelo] → B13 → B14 → B15 → B16 → B17 → checkpoint final
```
