---
description: >
  Padrões operacionais, bugs conhecidos e soluções para o loop de prazos em Prazo/.
  Inclui ciclos 1/2/3, filtros, SmartFinder, seleção em lote e movimentação.
applyTo: "Prazo/**/*.py"
---

# Skill: Prazo — Loop de Prazos (Ciclos 1/2/3)

## Estrutura de Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `Prazo/loop.py` | Orquestrador — importa de todos os ciclos |
| `Prazo/loop_base.py` | Imports compartilhados (WebDriver, logger, constantes) |
| `Prazo/loop_ciclo1.py` | Ciclo 1: abertura suitcase, movimentação |
| `Prazo/loop_ciclo1_filtros.py` | Ciclo 1: filtros fases/tarefas |
| `Prazo/loop_ciclo1_movimentacao.py` | Ciclo 1: movimentação em lote + com_retry |
| `Prazo/loop_ciclo2_selecao.py` | Ciclo 2: seleção de processos (livre/GIGS) |
| `Prazo/loop_ciclo2_processamento.py` | Ciclo 2: atividade xs, movimentação lote |
| `Prazo/loop_ciclo3.py` | Ciclo 3: painel cumprimento providências |

## Filtros do Ciclo 2

### Ordem correta (preservar esta ordem para evitar regressão):
1. Aplicar `filtrofases` primeiro (reduz número de itens)
2. Depois `aplicar_filtro_100` (define 100 por página)

> ⚠️ Legado (`ref/Prazo/loop.py`) usa esta ordem. A ordem inversa funciona mas é menos eficiente.

### Import correto de `aplicar_filtro_100`

```python
# VIA loop_base.py (correto — usa wrapper Fix.core que traduz parametros):
from .loop_base import aplicar_filtro_100

# ERRADO para novos usos diretos em Fix/navigation/:
# from Fix.selenium_base.retry_logic import com_retry
# → chamar com log=True causa TypeError silencioso (VEJA BUG #001 abaixo)
```

## Bugs Conhecidos

### BUG #001 — `aplicar_filtro_100` retorna False silenciosamente (RESOLVIDO em 31/03/2026)

**Sintoma:** Ciclo 2 não executa filtro 100; nenhum log; "todas tentativas falharam"

**Causa raiz:**
```python
# Fix/navigation/filters.py importava com_retry direto da implementação:
from Fix.selenium_base.retry_logic import com_retry
# retry_logic.com_retry usa log_enabled (não log)
# Chamada com log=True → vai para **kwargs → _selecionar(log=True) → TypeError silencioso
```

**Fix aplicado:**
```python
# Fix/navigation/filters.py linha 244
# ANTES:
resultado = com_retry(_selecionar, max_tentativas=3, backoff_base=1.5, log=True)
# DEPOIS:
resultado = com_retry(_selecionar, max_tentativas=3, backoff_base=1.5, log_enabled=True)
```

**Regra derivada:**
- Sempre importar `com_retry` via `Fix.core` (tem wrapper que traduz `log → log_enabled`)
- Se importar direto de `Fix.selenium_base.retry_logic`, usar `log_enabled=True` (não `log=True`)

## Seleção em Lote — Scripts JS

| Constante | Script | Função |
|---|---|---|
| `SCRIPT_SELECAO_LIVRES` | Seleciona processos sem GIGS | `_ciclo2_processar_livres` |
| `SCRIPT_SELECAO_NAO_LIVRES` | Seleciona max N processos com GIGS | `_ciclo2_selecionar_nao_livres` |

Definidos em `Prazo/loop_base.py`. Não duplicar.

## SmartFinder no Loop

```python
from Fix.smart_finder import buscar

# Uso correto:
el = buscar(driver, 'ciclo2_mat_select_combobox', [
    "mat-select[role='combobox']",
    "//mat-select"
])
```

Não usar `_get_sf(driver).find(...)` (padrão antigo — removido no Plano 4).

## Sincronização entre Ciclos

Ver `Prazo/CORRECAO_SINCRONIZACAO_CICLOS.md` — os aguardos entre fases são críticos.  
**Não remover** os pontos de sincronização sem validação em produção.
