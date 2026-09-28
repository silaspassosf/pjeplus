# Lx-10: Audit Final de prints e emojis

> Data: 2026-05-03 | Escopo: Fix/, atos/, Prazo/, PEC/, Triagem/, Peticao/, SISB/, Mandado/, carta/, x.py, f.py
> Excluídos: __pycache__, test_*, tools/, .md, worktrees

---

## 1. print() -- contagem real (excluindo docstrings `>>>`)

| Diretorio | Total grep | Docstring | Real | Notas |
|-----------|-----------|-----------|------|-------|
| Fix/      | 120       | 13        | 107  | 63 sao do debug_interativo (intencionais) |
| atos/     | 8         | 0         | 8    | 5 no movimentos_fluxo |
| Prazo/    | 30        | 0         | 30   | 5 do t3.py (teste) |
| PEC/      | 17        | 0         | 17   | clipboard e juntada |
| Triagem/  | 22        | 1         | 21   | regras tem 10 |
| Peticao/  | 30        | 2         | 28   | 3 do testpet (teste) |
| SISB/     | 5         | 0         | 5    | apenas debug no core.py |
| Mandado/  | 0         | 0         | 0    | limpo |
| carta/    | 0         | 0         | 0    | limpo |
| x.py      | 1         | -         | 0    | apenas comentario |
| f.py      | 16        | 0         | 16   | script de teste |
| **Total** | **249**   | **16**    | **232** | |

---

## 2. File-by-file: prints remanescentes

### Fix/ (107 reais)

| Arquivo | Prints | Categoria |
|---------|--------|-----------|
| debug_interativo.py | 63 | INTERATIVO - menu de usuario (intencional) |
| variaveis.py | 22 | 6 com emoji, 13 docstring excluidas |
| monitoramento_progresso_unificado.py | 7 | baixo risco, migracao simples |
| selectors_pje.py | 7 | debug de seletores |
| otimizacao_wrapper.py | 6 | informacional |
| headless_helpers.py | 2 | fallback warning |

### atos/ (8)

| Arquivo | Prints | Categoria |
|---------|--------|-----------|
| movimentos_fluxo.py | 5 | 4 sao `print(msg)` em funcao log() |
| movimentos_chips.py | 1 | `print(msg)` em funcao log() |
| movimentos_fimsob.py | 1 | `print(msg)` em funcao log() |
| movimentos_sobrestamento.py | 1 | `print(msg)` em funcao log() |

### Prazo/ (30)

| Arquivo | Prints | Categoria |
|---------|--------|-----------|
| loop_orquestrador.py | 7 | erros e status |
| t3.py | 5 | **teste** (intencional) |
| loop_helpers.py | 4 | erros e status |
| p2b_regras_execucao.py | 4 | erros e status |
| loop_api.py | 3 | erros |
| loop_ciclo2_selecao.py | 2 | erros |
| loop_lote.py | 2 | erros |
| p2b_gateway.py | 2 | info |
| p2b_api.py | 1 | info |

### PEC/ (17)

| Arquivo | Prints | Categoria |
|---------|--------|-----------|
| anexos_configuracao.py | 8 | clipboard (5 com emoji) |
| anexos_juntador_base.py | 8 | wrapper juntada (3 com emoji) |
| anexos_sisbajud.py | 1 | debug condicional |

### Triagem/ (21)

| Arquivo | Prints | Categoria |
|---------|--------|-----------|
| regras.py | 10 | debug CEP, todos condicionais |
| service.py | 5 | inicializacao (4 com emoji) |
| citacao.py | 4 | erros |
| preprocess.py | 2 | debug fingerprint |

### Peticao/ (28)

| Arquivo | Prints | Categoria |
|---------|--------|-----------|
| pet.py | 8 | driver lifecycle |
| core/utils/utils.py | 8 | driver/login |
| consolida_delete.py | 6 | **script autonomo** (6 com emoji) |
| testpet.py | 3 | **teste** (intencional) |
| orquestrador.py | 2 | bucket info |
| core/log.py | 1 | erro |

### SISB/ (5)

| Arquivo | Prints | Categoria |
|---------|--------|-----------|
| core.py | 5 | debug handles, todos condicionais |

### f.py (16)

| Linha | Contexto |
|-------|----------|
| 176-259 | **teste integrado SISB** -- todos intencionais |

---

## 3. File-by-file: emojis

### Emojis em print() (precisam migrar junto com os prints)

| Arquivo | Emojis | Quais |
|---------|--------|-------|
| Fix/variaveis.py | 6 | ✅ ❌ ⚠️ ✓ ✅ ❌ |
| Fix/headless_helpers.py | 1 | ❌ |
| atos/movimentos_fluxo.py | 1 | 🔍 |
| Prazo/loop_api.py | 1 | ⚠️ |
| Prazo/loop_helpers.py | 2 | ✅ ⚠️ |
| PEC/anexos_configuracao.py | 5 | ✅ x4, ✗ |
| PEC/anexos_juntador_base.py | 3 | ✗ ✓ ✗ |
| Triagem/service.py | 4 | ⚠ x2, ℹ️, ▶ |
| Peticao/consolida_delete.py | 6 | ❌ x2, ⚠️, 📊, ✅, 📁 |
| **Total em print()** | **29** | |

### Emojis em logger.*() (ja estao no logging estruturado)

| Diretorio | Ocorrencias | Notas |
|-----------|-------------|-------|
| SISB/ | ~40 | `log_sisbajud()` e `logger.*()` |
| Prazo/ | ~34 | `logger.info/error/warning()` |
| Mandado/ | ~16 | `logger.info/error()` |
| PEC/ | ~15 | `logger.*()` em sobrestamento e indexacao |
| atos/ | ~16 | `logger.*()` em judicial_fluxo, etc |
| Peticao/ | ~3 | `logger.*()` |
| Fix/monitoramento_progresso_unificado.py | 26 | `_log_progresso()` (wrapper interno) |
| Fix/utils.py | 6 | `log_msg()` e JS strings |
| Fix/core.py | 4 | comentarios e JS strings |
| Fix/extracao.py | 3 | JS strings |

**Nota**: Emojis em `logger.*()` sao aceitaveis -- ja usam o sistema de logging. Emojis dentro de strings JavaScript injetadas (`execute_script`) sao codigo front-end, nao Python. Emojis em comentarios sao irrelevantes.

---

## 4. Categorias de risco

### Prints intencionais (NAO migrar -- manter como print)

| Arquivo | Qtde | Motivo |
|---------|------|--------|
| Fix/debug_interativo.py | 63 | Menu interativo de usuario (TUI) -- print e o proprio UI |
| f.py | 16 | Script de teste integrado |
| Prazo/t3.py | 5 | Script de teste |
| Peticao/testpet.py | 3 | Script de teste |

**Subtotal intencional: 87 prints** (37,5% do total)

### Easy wins (< 5 prints, baixo risco)

| Arquivo | Prints | Facilidade |
|---------|--------|------------|
| Fix/headless_helpers.py | 2 | 2 prints, 1 com emoji |
| atos/movimentos_chips.py | 1 | 1 print |
| atos/movimentos_fimsob.py | 1 | 1 print |
| atos/movimentos_sobrestamento.py | 1 | 1 print |
| PEC/anexos_sisbajud.py | 1 | condicional `if debug` |
| Peticao/core/log.py | 1 | 1 print |
| Peticao/orquestrador.py | 2 | 2 prints |
| Prazo/p2b_api.py | 1 | 1 print |
| Prazo/loop_ciclo2_selecao.py | 2 | 2 prints |
| Prazo/loop_lote.py | 2 | 2 prints |
| Prazo/p2b_gateway.py | 2 | 2 prints |
| Triagem/preprocess.py | 2 | 2 prints |
| SISB/core.py | 5 | debug condicional |

**Subtotal easy wins: 23 prints** (9,9% do total)

### Migracao cuidadosa (5-10 prints, risco medio)

| Arquivo | Prints | Observacao |
|---------|--------|------------|
| Fix/otimizacao_wrapper.py | 6 | 6 prints informacionais |
| Fix/selectors_pje.py | 7 | 7 prints debug seletor |
| Fix/monitoramento_progresso_unificado.py | 7 | wrapper `_log_progresso` + 5 header prints |
| atos/movimentos_fluxo.py | 5 | 4 sao `print(msg)` em log() |
| Prazo/loop_helpers.py | 4 | erros com emoji |
| Prazo/loop_api.py | 3 | erros com emoji |
| Prazo/p2b_regras_execucao.py | 4 | erros |
| PEC/anexos_configuracao.py | 8 | clipboard, 5 com emoji |
| PEC/anexos_juntador_base.py | 8 | wrapper, 3 com emoji |
| Triagem/citacao.py | 4 | erros API |
| Triagem/service.py | 5 | init, 4 com emoji |
| Peticao/core/utils/utils.py | 8 | driver lifecycle |

**Subtotal migracao cuidadosa: 69 prints** (29,7% do total)

### Complexo (10+ prints, risco alto)

| Arquivo | Prints | Observacao |
|---------|--------|------------|
| Fix/variaveis.py | 22 | 6 com emoji, logica densa |
| Triagem/regras.py | 10 | debug CEP condicional |
| Peticao/pet.py | 8 | driver lifecycle |
| Peticao/consolida_delete.py | 6 | script autonomo, 6 emojis |
| Prazo/loop_orquestrador.py | 7 | logica de orquestracao |

**Subtotal complexo: 53 prints** (22,8% do total)

---

## 5. Top 10 arquivos por numero de prints

| # | Arquivo | Prints | % do total | Risco |
|---|---------|--------|-----------|-------|
| 1 | Fix/debug_interativo.py | 63 | 27,2% | INTENCIONAL |
| 2 | Fix/variaveis.py | 22 | 9,5% | ALTO |
| 3 | f.py | 16 | 6,9% | INTENCIONAL (teste) |
| 4 | Triagem/regras.py | 10 | 4,3% | ALTO |
| 5 | PEC/anexos_configuracao.py | 8 | 3,4% | MEDIO |
| 6 | PEC/anexos_juntador_base.py | 8 | 3,4% | MEDIO |
| 7 | Peticao/pet.py | 8 | 3,4% | ALTO |
| 8 | Peticao/core/utils/utils.py | 8 | 3,4% | MEDIO |
| 9 | Fix/monitoramento_progresso_unificado.py | 7 | 3,0% | MEDIO |
| 10 | Fix/selectors_pje.py | 7 | 3,0% | MEDIO |

---

## 6. Sumario Executivo

### prints

| Metrica | Valor |
|---------|-------|
| Total de arquivos com print() | 27 |
| Total de prints (bruto, com docstring) | 249 |
| Total de prints (real, sem docstring) | 232 |
| Prints intencionais (nao migrar) | 87 (37,5%) |
| Prints a migrar | **145 (62,5%)** |

### emojis

| Metrica | Valor |
|---------|-------|
| Total de emojis em .py (logger + print + comentarios + JS) | ~196 |
| Emojis especificamente em print() | 29 (distribuidos em 9 arquivos) |
| Emojis em logger.*() | ~150+ (ja migrados, aceitaveis) |
| Emojis em comentarios/JS/outros | ~17 |

### Diretorios ja limpos

- Mandado/: 0 prints, 0 emojis em print (apenas logger.*())
- carta/: 0 prints, 0 emojis

---

## 7. Ordem de ataque recomendada

### Wave 1: Easy wins (23 prints, baixo risco)
1. Fix/headless_helpers.py -- 2 prints, 1 emoji
2. SISB/core.py -- 5 prints, 0 emoji
3. atos/movimentos_chips.py, fimsob.py, sobrestamento.py -- 3 prints, 0 emoji
4. Peticao/core/log.py, orquestrador.py -- 3 prints, 0 emoji
5. Prazo/p2b_api.py, loop_ciclo2_selecao.py, loop_lote.py, p2b_gateway.py -- 7 prints, 0 emoji
6. PEC/anexos_sisbajud.py -- 1 print, 0 emoji
7. Triagem/preprocess.py -- 2 prints, 0 emoji

### Wave 2: atos/movimentos_fluxo.py (5 prints, 1 emoji)
- Os 4 `print(msg)` em log() sao o padrao mais facil: substituir `print(msg)` por `logger.info(msg)`.

### Wave 3: PEC clipboard (16 prints, 8 emojis)
- anexos_configuracao.py (8 prints, 5 emojis)
- anexos_juntador_base.py (8 prints, 3 emojis)

### Wave 4: Prazo (20 prints, 4 emojis)
- loop_helpers.py, loop_api.py, loop_orquestrador.py, p2b_regras_execucao.py

### Wave 5: Peticao (16 prints, 6 emojis)
- utils.py (8), pet.py (8)

### Wave 6: Fix/ (42 prints, 7 emojis)
- variaveis.py (22, 6 emojis) -- maior arquivo de logica
- selectors_pje.py (7)
- otimizacao_wrapper.py (6)
- monitoramento_progresso_unificado.py (7) -- atencao: _log_progresso() ja e wrapper

### Wave 7: Triagem (16 prints, 4 emojis)
- regras.py (10)
- citacao.py (4)
- service.py (5, 4 emojis)

### Fim: Intencionais (Nao mexer)
- Fix/debug_interativo.py (63)
- f.py (16)
- Prazo/t3.py (5)
- Peticao/testpet.py (3)

---

## 8. Observacoes importantes

1. **debug_interativo.py (63 prints)**: E um debugger TUI interativo. As `print()` sao o proprio mecanismo de renderizacao do menu. Converter para logger quebraria a experiencia. Deve ser marcado como `# noqa` ou adicionado a lista de excecoes.

2. **f.py (16 prints)**: Script de teste de integracao do SISB. Prints sao o output visivel do teste. Pode ficar ou migrar quando houver um framework de teste real.

3. **Prazo/t3.py (5) e Peticao/testpet.py (3)**: Scripts de teste analogos.

4. **Emojis em logger.*()**: A maioria dos ~196 emojis encontrados estao em chamadas de `logger.info()`, `logger.error()`, `log_sisbajud()`, etc. Como ja usam o sistema de logging estruturado, emojis ai sao aceitaveis (embora nao ideais). A preocupacao real sao os **29 emojis em print()** que precisam migrar.

5. **`_log_progresso()` em monitoramento_progresso_unificado.py**: As 26 ocorrencias de emoji estao dentro de `_log_progresso()`, que e um wrapper de log interno. Nao sao prints diretos.

6. **Duas categorias de risco real**: (a) prints que sao o unico meio de saida (precisam de logger adicionado), (b) prints que duplicam logger (precisam apenas ser removidos).
