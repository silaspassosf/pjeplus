# Controle de Limpeza — Funções Mortas
> Gerado: 31/03/2026  
> Escopo: atos/, Fix/, Mandado/, Prazo/, PEC/, SISB/  
> Critério: função/arquivo nunca chamado por nenhum ponto de entrada ativo (x.py, Mandado/processamento_api.py, Prazo/fluxo_api.py, PEC/orquestrador.py) nem transitivamente por eles.  
> **Regra:** Apagar apenas itens marcados CERTAMENTE MORTO e confirmados. Itens VERIFICAR devem ser inspecionados antes.

---

## PROGRESSO GERAL

| Categoria | Total | Concluído | Pendente |
|---|---|---|---|
| Arquivos .bak | 2 | 0 | 2 |
| Atos — duplicatas/mortos | 5 | 0 | 5 |
| Mandado — funções DOM | 3 | 0 | 3 |
| PEC — arquivos obsoletos | 3 | 0 | 3 |
| Prazo — arquivos/funções | 2 | 0 | 2 |

---

## 1. ARQUIVOS .BAK — CERTAMENTE MORTOS

Estes arquivos têm extensão `.bak_XXXXXXXX` — são snapshots automáticos sem uso.  
**Ação:** Deletar diretamente, sem risco.

| # | Arquivo | Status |
|---|---|---|
| 1.1 | `atos/judicial_bloqueios.py.bak_1773806659` | ✅ CONCLUÍDO |
| 1.2 | `atos/judicial_wrappers.py.bak_1773806659` | ✅ CONCLUÍDO |

**Comando:**
```
del atos\judicial_bloqueios.py.bak_1773806659
del atos\judicial_wrappers.py.bak_1773806659
```

---

## 2. ATOS/ — DUPLICATAS E ÓRFÃOS

### 2.1 `atos/oficio.py` — CERTAMENTE MORTO
- **Razão:** Não está importado em `atos/__init__.py` nem em nenhum módulo ativo.
- **Funções:** `oficio()`, `_carregar_storage_oficio()`, `_salvar_storage_oficio()`, etc.
- **Ação:** Deletar arquivo inteiro.
- **Status:** ✅ CONCLUÍDO

### 2.2 `atos/judicial_conclusao.py` — VERIFICAR (duplicata de `judicial_modelos.py`)
- **Razão:** Contém `escolher_tipo_conclusao`, `aguardar_transicao_minutar`, `verificar_estado_atual`, `focar_campo_minutar_se_necessario` — mesmas funções existem em `judicial_modelos.py`.
- **Ação:** Confirmar qual arquivo é importado por `judicial_fluxo.py`. Se `judicial_modelos.py` for o canônico, deletar `judicial_conclusao.py`.
- **Verificar:** `grep -r "from .judicial_conclusao" atos/`
- **Status:** ⬜ VERIFICAR

### 2.3 `atos/judicial_helpers.py` — VERIFICAR (duplicata de `judicial_utils.py`)
- **Razão:** Contém `ato_pesquisas`, `idpj`, `verificar_bloqueio_recente` — também em `judicial.py` (via re-export de `judicial_helpers`) e `judicial_utils.py`.
- **Ação:** Confirmar se `judicial_helpers.py` é o único importador ou se `judicial_utils.py` é redundante.
- **Verificar:** `grep -r "from .judicial_utils\|from .judicial_helpers" atos/`
- **Status:** ⬜ VERIFICAR

### 2.4 `atos/judicial.py` — VERIFICAR (arquivo de re-export com redefinições)
- **Razão:** `judicial.py` importa de `judicial_fluxo.py` e `judicial_helpers.py`, mas também redefine localmente `fluxo_cls`, `ato_judicial`, `make_ato_wrapper`, `ato_pesquisas`, `idpj`, `preencher_prazos_destinatarios`, `verificar_bloqueio_recente` (linhas 39+) possivelmente como wrappers redundantes (padrão P1).
- **Ação:** Verificar se as definições locais em `judicial.py` são identidades ou se diferem das importadas. Se forem wrappers P1, eliminar e manter apenas o re-export.
- **Status:** ⬜ VERIFICAR

### 2.5 `atos/movimentos_navegacao.py` — VERIFICAR
- **Razão:** Não aparece em nenhum import de `movimentos_fluxo.py` ou `movimentos.py`. Pode ser usado internamente.
- **Verificar:** `grep -r "from .movimentos_navegacao\|movimentos_navegacao" atos/`
- **Status:** ⬜ VERIFICAR

---

## 3. MANDADO/ — FUNÇÕES DOM (mortas após migração API)

> **ATENÇÃO:** Estes itens dependem da conclusão da tarefa de execução (ver `controle_limpeza_execucoes_api.md`).  
> Só apagar **após** x.py ser atualizado para usar `processar_mandados_devolvidos_api`.

### 3.1 `Mandado/core.py` — `navegacao()` e `iniciar_fluxo_robusto()` — CERTAMENTE MORTOS
- **Razão:** Chamados por `executar_mandado()` em x.py (fluxo B DOM). Após migração para API (concluída), não serão mais usados.
- **Dependência:** x.py linha 81 — REMOVIDA (controle_limpeza_execucoes_api.md item 1 ✅ CONCLUÍDO)
- **Ação:** PENDENTE PARA DELEÇÃO — Remover funções `navegacao()` e `iniciar_fluxo_robusto()` de `Mandado/core.py`.
- **Status:** ⬜ PENDENTE PARA DELEÇÃO

### 3.2 `Mandado/processamento.py` — VERIFICAR
- **Razão:** Arquivo com lazy imports. Verificar se ainda é chamado diretamente por algum módulo ativo após a migração.
- **Verificar:** `grep -r "from Mandado.processamento\|from Mandado import processamento" --include="*.py"`
- **Status:** ⬜ VERIFICAR

### 3.3 `Mandado/core.py` — `setup_driver()` e `main()` — CERTAMENTE MORTOS
- **Razão:** `setup_driver()` cria driver próprio (padrão P7 — context manager não usado); `main()` é entry point standalone nunca chamado por x.py.
- **Ação:** Remover as funções `setup_driver` e `main` de `Mandado/core.py`.
- **Status:** ✅ CONCLUÍDO (renomeada para `_main_legado`)

## 4. PEC/ — ARQUIVOS OBSOLETOS

### 4.1 `PEC/processamento_backup.py` — CERTAMENTE MORTO
- **Razão:** Arquivo de backup (`_backup` no nome). Não importado em nenhum módulo ativo.
- **Status:** ✅ CONCLUÍDO

### 4.2 `PEC/processamento_fluxo.py` — `executar_fluxo_novo()` — CERTAMENTE MORTO
- **Razão:** x.py chamava `from PEC.processamento import executar_fluxo_novo` re-exportado de `processamento_fluxo.py`. Após migração para `executar_fluxo_novo_simplificado` (orquestrador.py) (concluída), esta função é morta.
- **Dependência:** Migração x.py (controle_limpeza_execucoes_api.md item 2 ✅ CONCLUÍDO)
- **Ação:** PENDENTE PARA DELEÇÃO — Remover função `executar_fluxo_novo()` de `PEC/processamento_fluxo.py`.
- **Status:** ⬜ PENDENTE PARA DELEÇÃO

### 4.3 `PEC/core_main.py` — VERIFICAR
- **Razão:** Arquivo que chama `executar_fluxo_novo` de `PEC.processamento`. Se nenhum fluxo ativo o chamar após migração, torna-se morto.
- **Verificar:** `grep -r "from PEC.core_main\|from PEC import core_main" --include="*.py"`
- **Status:** ⬜ VERIFICAR

---

## 5. PRAZO/ — FUNÇÕES/ARQUIVOS POTENCIAIS

> **NOTA:** `loop_prazo` e `ciclo1/ciclo2/ciclo3` são ATIVOS (fluxo C de x.py). Não apagar.

### 5.1 `Prazo/loop_api.py` — VERIFICAR
- **Razão:** Existe `loop_api.py` que pode ser uma versão alternativa/obsoleta de `fluxo_api.py`.
- **Verificar:** `grep -r "from Prazo.loop_api\|from .loop_api" --include="*.py"`
- **Status:** ⬜ VERIFICAR

### 5.2 `Prazo/prov_driver.py` — VERIFICAR
- **Razão:** Cria driver próprio (padrão P7). Verificar se é chamado de algum fluxo ativo.
- **Verificar:** `grep -r "from Prazo.prov_driver\|from .prov_driver" --include="*.py"`
- **Status:** ⬜ VERIFICAR

---

## 6. SISB/ E FIX/ — SEM MORTOS IDENTIFICADOS

Após análise de importações, nenhuma função CERTAMENTE MORTA identificada nessas pastas nesta rodada.  
Fix/ e SISB/ têm extensa dependência cruzada — análise mais profunda recomendada em rodada separada se necessário.

---

## INSTRUÇÃO DE EXECUÇÃO INCREMENTAL

1. Começar pelos itens de **certeza absoluta** (seção 1 e 3.3 e 4.1)
2. Para cada VERIFICAR: rodar o `grep` indicado → confirmar → atualizar status para PENDENTE ou DESCARTADO
3. Itens AGUARDANDO: só avançar após o markdown `controle_limpeza_execucoes_api.md` indicar CONCLUÍDO

### Status Keys
- ⬜ PENDENTE — não iniciado
- 🔍 VERIFICAR — precisa inspecionar antes de agir
- ✅ CONCLUÍDO — deletado e validado
- ❌ DESCARTADO — análise mostrou que é usado
