# Plano Frente C — Limpeza de Código Morto (vulture)

## Overview

Remover funções, imports e variáveis mortas dos módulos vivos usando `vulture`. A Fase 1 (arquivos mortos) já foi concluída — 60 arquivos arquivados em `_archive/20260415_024013/`. Esta frente cobre a Fase 2: limpeza dentro dos módulos que sobreviveram.

**Pré-condição:** Frente B deve estar concluída antes de novos slices de vulture em `Fix/` (para não remover código que será movido).

## Estado Atual

| Fase | Status | Resultado |
|------|--------|-----------|
| Fase 1 — Módulos mortos | ✅ Concluída | 60 arquivos arquivados |
| Fase 2 — Slice 1 | ✅ Concluído | 5 arquivos, -18 linhas |
| Fase 2 — Slice 2 | ✅ Concluído | 5 edições, -7 linhas |
| Fase 2 — Slice 3 | ✅ Concluído | 1 edição, -1 linha |
| Fase 2 — Slices 4+ | 🔄 Pendente | — |

## Decisões de Arquitetura

- **Nunca remover** itens da whitelist (`tools/vulture_whitelist.py`)
- **Confiança mínima 80%** — ignorar achados abaixo disso
- **Lote de 5 edições** por slice para manter rollback fácil
- **Não tocar `Fix/`** enquanto Frente B não estiver concluída
- **Commit após cada slice** com mensagem `chore: vulture slice N`

## Task List

---

### Phase 0: Preparação

## Task C0: Gerar relatório vulture atualizado

**Descrição:** Após Frente B concluída (Fix/ consolidada), gerar novo relatório vulture com o código atual. O relatório anterior pode referenciar arquivos que já foram removidos ou mergeados.

**Acceptance criteria:**
- [ ] `tools/vulture_report_latest.txt` gerado com confiança ≥ 80%
- [ ] Relatório exclui `_archive/`, `Fix/backup_pre_merge/`, `ref/`, `aider-env/`
- [ ] Whitelist aplicada

**Verificação:**
```bash
py -m vulture Fix/ atos/ SISB/ Prazo/ PEC/ Mandado/ Peticao/ Triagem/ \
   tools/vulture_whitelist.py \
   --min-confidence 80 \
   --exclude "_archive,Fix/backup_pre_merge,ref,aider-env" \
   > tools/vulture_report_latest.txt

wc -l tools/vulture_report_latest.txt   # baseline de linhas
```

**Dependências:** Frente B concluída  
**Arquivos:** `tools/vulture_report_latest.txt`  
**Escopo:** XS

---

## Task C1: Atualizar `tools/vulture_whitelist.py`

**Descrição:** Revisar whitelist contra os novos módulos consolidados. Itens que faziam referência a arquivos eliminados na Frente B devem ser removidos ou atualizados para os novos paths.

**Acceptance criteria:**
- [ ] Whitelist sem referências a arquivos que não existem mais
- [ ] Re-exports em `Fix/__init__.py` ainda whitelistados
- [ ] `py -m vulture ... tools/vulture_whitelist.py` não emite erro de sintaxe

**Verificação:**
```bash
py -m py_compile tools/vulture_whitelist.py
py -m vulture tools/vulture_whitelist.py  # deve retornar 0 achados
```

**Dependências:** C0  
**Arquivos:** `tools/vulture_whitelist.py`  
**Escopo:** S

---

### Checkpoint 0: Relatório Base Validado
- [ ] `vulture_report_latest.txt` gerado e revisado superficialmente
- [ ] Whitelist atualizada e sem erros
- [ ] Total de achados documentado (baseline para medir progresso)

---

### Phase 1: Slices de Limpeza

> **Regra de execução:** cada task abaixo é um slice independente. Executar um de cada vez, commitar, validar, então prosseguir.

---

## Task C4: Slice 4 — Imports mortos em módulos de negócio

**Descrição:** Identificar e remover `import` declarados mas nunca referenciados nos módulos `atos/`, `SISB/`, `Prazo/`, `PEC/`. Focar nos achados de alta confiança (≥ 90%) do relatório.

**Acceptance criteria:**
- [ ] Imports unused removidos em até 5 arquivos
- [ ] Nenhum `NameError` ao importar os módulos modificados
- [ ] 6 imports críticos passam

**Processo de execução:**
```bash
# 1. Filtrar apenas unused imports do relatório
grep "unused import" tools/vulture_report_latest.txt | head -20

# 2. Editar os arquivos (máximo 5 por slice)
# 3. Compilar cada arquivo editado
py -m py_compile <arquivo_editado>

# 4. Validar imports críticos
py -c "import x"

# 5. Commitar
git add -p && git commit -m "chore: vulture slice 4 - unused imports"
```

**Dependências:** C1  
**Arquivos:** até 5 arquivos de `atos/`, `SISB/`, `Prazo/`, `PEC/`  
**Escopo:** S

---

## Task C5: Slice 5 — Imports mortos em `Mandado/`, `Peticao/`, `Triagem/`

**Descrição:** Mesma estratégia de C4, aplicada aos módulos restantes.

**Acceptance criteria:**
- [ ] Imports unused removidos em até 5 arquivos
- [ ] `py -c "from Triagem.runner import run_triagem"` passa
- [ ] `py -c "from Peticao.pet import run_pet"` passa

**Verificação:**
```bash
py -m py_compile <arquivos_editados>
py -c "from Triagem.runner import run_triagem; from Peticao.pet import run_pet; print('OK')"
git commit -m "chore: vulture slice 5 - unused imports mandado/peticao/triagem"
```

**Dependências:** C4  
**Escopo:** S

---

## Task C6: Slice 6 — Variáveis mortas e parâmetros não utilizados

**Descrição:** Remover variáveis atribuídas mas nunca lidas (confidence ≥ 90%). Parâmetros de função aparecem como falso-positivo frequente — só remover se certeza absoluta.

**Regras:**
- Não remover parâmetros de funções (são interface pública)
- Não remover variáveis precedidas de `_` (convenção de "intencional")
- Remover apenas variáveis locais claramente mortas (ex: resultado de chamada nunca usado)

**Acceptance criteria:**
- [ ] Até 5 variáveis mortas removidas
- [ ] Nenhuma quebra de lógica (revisar contexto de cada remoção)
- [ ] `py -c "import x"` limpo

**Verificação:**
```bash
py -m py_compile <arquivos_editados>
py -c "import x"
git commit -m "chore: vulture slice 6 - unused variables"
```

**Dependências:** C5  
**Escopo:** S

---

## Task C7: Slice 7 — Funções mortas confirmadas

**Descrição:** Remover funções que vulture marca como unused **e** que não aparecem em nenhuma string de seletor, decorador, ou metaprogramação. Verificar `git grep` antes de cada remoção.

**Regras:**
- Sempre fazer `git grep "nome_da_funcao"` antes de remover
- Se aparecer em qualquer lugar (inclusive comentários/docs), não remover
- Não remover funções prefixadas com `_` se estiverem em módulos de API pública

**Acceptance criteria:**
- [ ] Até 5 funções removidas com confirmação via `git grep`
- [ ] Nenhuma `AttributeError` ao importar os módulos modificados

**Verificação:**
```bash
# Para cada função candidata:
git grep "nome_da_funcao"   # deve retornar 0 resultados além do próprio def

py -m py_compile <arquivo>
py -c "import <modulo>; print('OK')"
git commit -m "chore: vulture slice 7 - dead functions"
```

**Dependências:** C6  
**Escopo:** M

---

### Checkpoint 1: Metade dos Slices
- [ ] Slices 4–7 concluídos e commitados
- [ ] 6 imports críticos passam
- [ ] Novo relatório vulture gerado — contagem de achados caiu

---

## Task C8: Slice 8 — Segunda rodada pós-checkpoint

**Descrição:** Gerar novo relatório vulture e executar mais um slice focado nos achados restantes de maior confiança.

```bash
py -m vulture Fix/ atos/ SISB/ Prazo/ PEC/ Mandado/ Peticao/ Triagem/ \
   tools/vulture_whitelist.py --min-confidence 80 \
   > tools/vulture_report_round2.txt
```

**Acceptance criteria:**
- [ ] Relatório round2 gerado
- [ ] Mais 5 itens removidos (imports, variáveis ou funções conforme achados)
- [ ] 6 imports críticos passam

**Dependências:** C7  
**Escopo:** S

---

### Checkpoint Final: Frente C Completa
- [ ] Relatório vulture final gerado
- [ ] Número de achados de alta confiança está em nível aceitável (< 20 itens)
- [ ] 6 imports críticos passam
- [ ] `py -c "import x"` limpo
- [ ] Todos os slices commitados com mensagens `chore: vulture slice N`
- [ ] `tools/vulture_report_latest.txt` atualizado com estado final

## Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Falso-positivo de vulture remove função usada via `getattr` | Alto | `git grep` obrigatório antes de cada remoção de função |
| Remoção de import usado em `TYPE_CHECKING` block | Médio | Revisar context de cada import antes de remover |
| Whitelist desatualizada após Frente B | Médio | Task C1 atualiza whitelist explicitamente |
| Slice toca `Fix/` antes de Frente B concluída | Alto | Pré-condição explícita: Frente B primeiro |

## Questões Abertas

- Quais módulos têm maior concentração de code morto no relatório atual? (Resposta determina ordem dos slices 4–7.)
- Há `getattr` ou metaprogramação que torna funções "mortas" no vulture mas vivas em runtime? Mapear antes de C7.
