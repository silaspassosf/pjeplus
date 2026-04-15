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

#### Task 0.1 — Verificar estado git limpo
**Descrição:** Garantir que não há mudanças não commitadas antes de iniciar.

**Acceptance criteria:**
- [ ] `git status` retorna `nothing to commit, working tree clean`
- [ ] Ou usuário faz commit/stash antes de prosseguir

**Verification:** `git status`  
**Dependencies:** None | **Scope:** XS

---

#### Task 0.2 — Criar estrutura `_archive/`
**Descrição:** Criar pasta `_archive/` na raiz. Subdiretórios datados criados automaticamente pelo script. Decidir se `_archive/` vai para `.gitignore` (não rastreado) ou commitado (rastreado mas separado).

**Acceptance criteria:**
- [ ] `_archive/README.md` existe explicando reversibilidade via `git restore`
- [ ] Decisão `.gitignore` vs commit documentada no README

**Verification:** `Test-Path d:\PjePlus\_archive\README.md`  
**Dependencies:** Task 0.1 | **Scope:** XS

---

### Phase 1: Import Graph — Nível de Módulo

#### Task 1.1 — Escrever `tools/scan_live_modules.py`
**Descrição:** Script AST que faz BFS a partir de `x.py`, resolve todos os imports transitivos (incluindo **lazy imports dentro de funções**) para caminhos absolutos dentro das 8 pastas alvo, e produz `tools/live_modules.json`.

**Regras de resolução:**
- `from Fix.core import X` → `Fix/core.py`
- `from Triagem.runner import X` (lazy, dentro de função) → `Triagem/runner.py` — **deve ser capturado**
- `import *` → marca o módulo fonte como live, continua BFS
- Import não resolvível (string dinâmica, `importlib`) → marca o pacote inteiro como live (conservador)
- stdlib e third-party → ignorados

**Acceptance criteria:**
- [ ] Produz `tools/live_modules.json` com lista de caminhos relativos
- [ ] `x.py` sempre no live set
- [ ] `Triagem/runner.py` e `Peticao/pet.py` estão no live set (lazy imports)
- [ ] `Fix/core.py`, `Mandado/processamento_api.py`, `Prazo/loop_prazo.py` estão no live set
- [ ] Log mostra cada import resolvido / não-resolvido

**Verification:**
- [ ] `py tools/scan_live_modules.py` sem erro
- [ ] `tools/live_modules.json` é JSON válido
- [ ] Inspecionar manualmente os 5 arquivos acima no output

**Dependencies:** Task 0.2 | **Files:** `tools/scan_live_modules.py` | **Scope:** S (~120 linhas)

---

#### Task 1.2 — Escrever `tools/archive_dead.py`
**Descrição:** Lê `tools/live_modules.json`, encontra todos os `.py` nas 8 pastas que **não** estão no live set, e os move para `_archive/YYYYMMDD_HHMMSS/` preservando estrutura de diretório. Gera `_archive/YYYYMMDD_HHMMSS/_manifest.json`.

**Regra especial `__init__.py`:** só arquivado se TODOS os outros `.py` do mesmo diretório forem arquivados.

**Acceptance criteria:**
- [ ] Nenhum arquivo live é movido
- [ ] Arquivos dead movidos com estrutura preservada
- [ ] `_manifest.json` lista: path original, motivo (`not_reachable_from_x_py`), timestamp
- [ ] `--dry-run` imprime sem mover

**Verification:**
- [ ] `py tools/archive_dead.py --dry-run` mostra candidatos sem erros
- [ ] `Fix/core.py` NÃO aparece no dry-run
- [ ] `py tools/archive_dead.py` cria diretório datado

**Dependencies:** Task 1.1 | **Files:** `tools/archive_dead.py` | **Scope:** S (~100 linhas)

---

#### Task 1.3 — Validar imports após arquivamento
**Descrição:** Sequência de imports de validação para confirmar que nenhum arquivo vivo quebrou.

**Acceptance criteria:**
- [ ] `py -c "import x"` sem ImportError
- [ ] `py -c "from Fix.core import finalizar_driver"` sem erro
- [ ] `py -c "from Mandado.processamento_api import processar_mandados_devolvidos_api"` sem erro
- [ ] `py -c "from PEC.orquestrador import executar_fluxo_novo_simplificado"` sem erro
- [ ] `py -c "from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b"` sem erro
- [ ] `py -c "from Triagem.runner import run_triagem"` sem erro
- [ ] `py -c "from Peticao.pet import run_pet"` sem erro

**Dependencies:** Task 1.2 | **Files:** Nenhum | **Scope:** XS

---

### Checkpoint 1 — Fim da Fase de Módulos
- [ ] `tools/live_modules.json` gerado e revisado
- [ ] Arquivos mortos em `_archive/` com manifesto legível
- [ ] Todos os 7 imports de validação passam
- [ ] **Revisar manifesto manualmente** — confirmar que nada suspeito foi arquivado
- [ ] Rollback disponível: `git restore <path>` ou mover de volta de `_archive/`

---

### Phase 2: Vulture — Nível de Função

#### Task 2.1 — Instalar vulture e gerar relatório inicial
**Descrição:** Instalar `vulture` e rodar contra arquivos vivos (pós-Fase 1). Salvar em `tools/vulture_report.txt`.

**Acceptance criteria:**
- [ ] `py -m vulture --version` funciona
- [ ] `tools/vulture_report.txt` gerado com formato `arquivo:linha: função 'nome' is never used (confidence X%)`

**Verification:**
```
py -m pip install vulture
py -m vulture x.py atos Fix Mandado Prazo PEC SISB Triagem Peticao --min-confidence 80 > tools/vulture_report.txt
```

**Dependencies:** Checkpoint 1 | **Scope:** XS

---

#### Task 2.2 — Criar whitelist vulture para falsos positivos
**Descrição:** Vulture marca como mortas funções usadas via decorators, `getattr`, callbacks. Criar `tools/vulture_whitelist.py` com as exceções conhecidas do projeto (ex: wrappers via `make_ato_wrapper`, funções decoradas, dunders não óbvios).

**Acceptance criteria:**
- [ ] Segundo run com whitelist produz lista menor e mais precisa
- [ ] `tools/vulture_report_filtered.txt` gerado

**Verification:**
```
py -m vulture x.py tools/vulture_whitelist.py atos Fix Mandado Prazo PEC SISB Triagem Peticao --min-confidence 80 > tools/vulture_report_filtered.txt
```

**Dependencies:** Task 2.1 | **Files:** `tools/vulture_whitelist.py` | **Scope:** S

---

#### Task 2.3 — Revisão manual e remoção de funções mortas
**Descrição:** Para cada função ≥90% confidence no relatório filtrado: grep rápido para confirmar zero callers, remover do arquivo fonte, limpar imports órfãos nos arquivos que a referenciavam. Registrar em `_archive/YYYYMMDD/_funcoes_removidas.txt`.

**Processo por função:**
1. `grep -rn "nome_funcao" atos Fix Mandado Prazo PEC SISB Triagem Peticao` — confirmar 0 callers reais
2. Remover a definição
3. Remover linha `from X import nome_funcao` em outros arquivos
4. `py -m py_compile <arquivo>` para validar sintaxe

**Acceptance criteria:**
- [ ] Cada remoção validada com grep antes de deletar
- [ ] `py -m py_compile` limpo em cada arquivo editado
- [ ] `_funcoes_removidas.txt` lista arquivo:linha de cada função removida

**Dependencies:** Task 2.2 | **Scope:** M (iterativo)

---

### Checkpoint 2 — Fim da Fase de Funções
- [ ] Relatório vulture revisado e anotado
- [ ] `py -c "import x"` limpo
- [ ] Todos os 7 imports de validação ainda passam
- [ ] `py -m py_compile` limpo em todos os arquivos editados
- [ ] `_archive/` tem manifesto de módulos + lista de funções removidas

---

### Phase 3: Final Validation

#### Task 3.1 — Scan de imports órfãos
**Descrição:** Após remover funções, detectar linhas `from X import Y` onde `Y` não existe mais.

**Acceptance criteria:**
- [ ] `py tools/scan_orphan_imports.py` sem exceção
- [ ] Zero ImportErrors latentes encontrados

**Dependencies:** Task 2.3 | **Files:** `tools/scan_orphan_imports.py` | **Scope:** S

---

#### Task 3.2 — Commit de limpeza
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
