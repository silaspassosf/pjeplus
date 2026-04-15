# Limpeza Cirúrgica do Repositório via Call Graph

## Problem Statement
Como mapear, a partir de x.py, todo código _realmente_ alcançável nos 7 fluxos (mandado, prazo, p2b, pec, triagem, pet, bloco-completo) e deletar o resto com segurança — em 315 arquivos, 2.6 MB, sem quebrar nenhuma execução real?

## Recommended Direction
Dois estágios sequenciais. **Estágio 1** identifica e arquiva arquivos inteiros nunca importados transitivamente a partir de `x.py` (único entry point). **Estágio 2** roda `vulture` nos sobreviventes para caçar funções mortas dentro de módulos vivos. Um `_archive/` datado com manifesto garante rollback instantâneo via `git restore`.

**Racional:** divide o problema em dois menores. Estágio 1 (nível de módulo, ~30 min) entrega 60–70% do ganho. Estágio 2 só analisa o que sobrou — menos ruído, menos falsos positivos.

## Key Assumptions to Validate
- [ ] x.py é o ÚNICO entry point — confirmado pelo usuário. Nenhum script externo (AHK, PS, cron) importa módulos de negócio diretamente.
- [ ] Imports lazy/condicionais (dentro de `try/except` ou `if`) devem ser rastreados — já identificados em `executar_triagem` e `executar_pet` em x.py, onde os imports são feitos dentro da função.
- [ ] `__init__.py` de pacotes só vai para archive se TODOS os `.py` do mesmo diretório forem arquivados.
- [ ] `import *` em qualquer módulo: marca o módulo-fonte como live por segurança (conservador).

## Context: Entry Points Confirmados em x.py

| Função            | Módulos chamados                                        |
|-------------------|---------------------------------------------------------|
| executar_mandado  | `Mandado.processamento_api.processar_mandados_devolvidos_api` |
| executar_prazo    | `Prazo` (`loop_prazo`)                                  |
| executar_p2b      | `Prazo.fluxo_api` (lazy import interno)                 |
| executar_pec      | `PEC.orquestrador.executar_fluxo_novo_simplificado`     |
| executar_triagem  | `Triagem.runner.run_triagem` (**lazy import**)          |
| executar_pet      | `Peticao.pet.run_pet` (**lazy import**)                 |
| executar_bloco_completo | todos os acima                                    |
| (base)            | `Fix.core`, `Fix.utils`, `Fix.drivers`, `Fix.smart_finder` |
| (base)            | `monitor.py` → `Fix.debug_interativo` (lazy condicional)|

---

## MVP Scope

### Phase 0: Safety Net

#### Task 0.1 — Verificar estado git limpo ✅ CONCLUÍDA
**Commit:** `0a86d47` — `chore: salvar estado antes da limpeza de modulos mortos` (44 arquivos)

---

#### Task 0.2 — Criar estrutura `_archive/` ✅ CONCLUÍDA
- `_archive/README.md` criado com instruções de rollback via `git restore`

---

### Phase 1: Import Graph — Nível de Módulo

#### Task 1.1 — Escrever `tools/scan_live_modules.py` ✅ CONCLUÍDA
- 257 arquivos vivos detectados. Todos os 5 checks críticos passam.
- **Fix crítico:** `encoding="utf-8-sig"` para BOM em `Fix/utils.py`. Fallback regex para multi-line imports com parênteses.
- `Triagem/runner.py` e `Peticao/pet.py` capturados via lazy-import traversal.

---

#### Task 1.2 — Escrever `tools/archive_dead.py` ✅ CONCLUÍDA
- Executado. **60 arquivos** movidos para `_archive/20260415_024013/` com `_manifest.json`.
- Inclui: `SISB/core.backup_20260206/`, `Prazo/loop.py`, `Prazo/prov*.py`, `atos/judicial_bloqueios.py` etc.
- (Primeira execução arquivou 77 arquivos errados — revertido após fix do BOM e re-executado.)

---

#### Task 1.3 — Validar imports após arquivamento ✅ CONCLUÍDA
Todos os 7 imports de validação **passam**:
- `import x` ✅
- `from Fix.core import finalizar_driver` ✅
- `from Mandado.processamento_api import processar_mandados_devolvidos_api` ✅
- `from PEC.orquestrador import executar_fluxo_novo_simplificado` ✅
- `from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b` ✅
- `from Triagem.runner import run_triagem` ✅
- `from Peticao.pet import run_pet` ✅

---

### Checkpoint 1 ✅ PASSOU

---

### Phase 2: Vulture — Nível de Função

#### Task 2.1 — Instalar vulture e gerar relatório inicial ✅ CONCLUÍDA
- vulture 2.16 instalado
- `tools/vulture_report.txt` gerado (114 linhas)
- Achados: ~90% unused imports, ~10% unused variables (na prática todos são parâmetros de função)

---

#### Task 2.2 — Criar whitelist vulture para falsos positivos ✅ CONCLUÍDA
- `tools/vulture_whitelist.py` criado
- Whitelisted: re-exports em `Fix/utils.py` (angular/selectors/collect/sleep), `NoSuchWindowException`, variáveis AHK, `TYPE_CHECKING`, `get_all_variables`, `padrao_liq`
- `tools/vulture_report_filtered.txt` gerado (114 linhas — whitelist via list-assignment não suprime; itens documentados)

---

#### Task 2.3 — Revisão manual e remoção de funções mortas 🔄 EM ANDAMENTO

**Slice 1 ✅ Commit `62fa6a1`** — 5 arquivos, -18 linhas:
- `Fix/extraction/indexacao.py`: removeu `Set` de typing
- `Fix/log_cleaner.py`: removeu `Iterable` de typing
- `x.py`: removeu `import signal`
- `Mandado/processamento.py`: removeu bloco `PEC.core_progresso` (6 aliases: carregar_progresso, salvar_progresso, extrair_numero_processo, verificar_acesso_negado, processo_ja_executado, marcar_processo_executado) + 3 funções privadas (`_aguardar_icone_plus`, `_buscar_icone_plus_direto`, `_extrair_resultado_sisbajud`)
- `Prazo/loop_ciclo1_movimentacao.py`: removeu 3 linhas unreachable após `return "error"`

**Slice 2 — PENDENTE** (itens a verificar com grep antes de remover):
- `Mandado/regras.py:40` — `NoSuchWindowException` (import para except não usado)
- `Mandado/regras.py:119` — `salvar_progresso` (alias não chamado)
- `Mandado/utils.py:40` — `NoSuchWindowException`
- `Mandado/utils.py:112` — `salvar_progresso`
- `SISB/core.py:47` — `processamento` (import não chamado no arquivo)
- `Fix/utils.py` re-exports — grep para confirmar zero callers diretos de cada nome
- `PEC/core.py:11` — `verificar_e_recuperar_acesso_negado` (1 hit — pode ser só definição)

**Confirmados NÃO remover:**
- `ato_gen` (4 hits reais), `ato_ceju` (11 hits reais) em `Peticao/pet.py`
- Todos "unused variables" do vulture em `Fix/progress*.py` são parâmetros de funções stub

**Comando de validação após cada slice:**
```powershell
@("import x","from Fix.core import finalizar_driver","from Mandado.processamento_api import processar_mandados_devolvidos_api","from PEC.orquestrador import executar_fluxo_novo_simplificado","from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b","from Triagem.runner import run_triagem","from Peticao.pet import run_pet") | ForEach-Object { $r = py -c $_ 2>&1; if ($LASTEXITCODE -eq 0) { "OK  $_" } else { "FAIL  $_" } }
```

---

### Checkpoint 2 — Fim da Fase de Funções
- [ ] Relatório vulture revisado e anotado
- [ ] `py -c "import x"` limpo
- [ ] Todos os 7 imports de validação ainda passam
- [ ] `py -m py_compile` limpo em todos os arquivos editados

---

### Phase 3: Final Validation

#### Task 3.1 — Scan de imports órfãos ⏳ PENDENTE
**Descrição:** Após remover funções, detectar linhas `from X import Y` onde `Y` não existe mais.

**Acceptance criteria:**
- [ ] `py tools/scan_orphan_imports.py` sem exceção
- [ ] Zero ImportErrors latentes encontrados

**Dependencies:** Task 2.3 | **Files:** `tools/scan_orphan_imports.py` | **Scope:** S

---

#### Task 3.2 — Commit de limpeza ⏳ PENDENTE
**Acceptance criteria:**
- [ ] `git diff --stat` mostra apenas remoções/edições
- [ ] Mensagem de commit descreve quantos arquivos/funções removidos

**Dependencies:** Task 3.1 | **Scope:** XS

---

## Not Doing (and Why)
- **AST call graph completo (V1)** — complexidade alta, falsos negativos difíceis de depurar; vulture cobre o caso de uso com menos risco
- **Coverage.py com mocks Selenium** — infra de mock é trabalhosa, cobertura condicional nunca seria 100%; import graph estático é suficiente como primeira passagem
- **Deletar direto sem archive** — rollback deve ser trivial; `_archive/` datado é o parachute

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Lazy import não capturado pelo BFS | Alto | Scanner percorre AST de **todas** as funções, não só o nível de módulo |
| `__init__.py` arquivado quebrando pacote | Alto | Regra especial: só arquiva se TODOS os `.py` do pacote forem dead |
| Vulture falso positivo (callback/decorator) | Médio | Whitelist + grep manual antes de qualquer remoção |
| Arquivo arquivado era necessário | Médio | `git restore <path>` + re-run das 7 validações |
| Imports circulares confundem o BFS | Baixo | Set `visited` no BFS previne loop infinito |

## Open Questions (resolvidas)
- ~~Triagem e Peticao são ativos?~~ **Sim** — menus F e G em x.py, imports lazy dentro das funções `executar_triagem` e `executar_pet`.
- ~~Existem outros entry points?~~ **Não** — somente x.py (monitor.py tem apenas um import lazy de Fix.debug_interativo).
