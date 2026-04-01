# Correção: `aplicar_filtro_100` — Ciclo 2 silenciosamente falhando

**Data:** 31/03/2026  
**Módulo afetado:** `Fix/navigation/filters.py`  
**Sintoma:** Função não executa nada, não loga nada, retorna apenas "todas tentativas falharam"  
**Impacto:** Ciclo 2 do loop em `Prazo/` não aplica filtro de 100 itens → processa menos processos do que deveria

---

## Causa Raiz

### Incompatibilidade de nome de parâmetro em `com_retry`

`Fix/navigation/filters.py` importa `com_retry` **diretamente** de:
```python
from Fix.selenium_base.retry_logic import com_retry
```

A assinatura em `retry_logic.py`:
```python
def com_retry(func, max_tentativas=3, backoff_base=2, log_enabled=False, *args, **kwargs)
```

Mas a chamada em `filters.py` (linha 244):
```python
resultado = com_retry(_selecionar, max_tentativas=3, backoff_base=1.5, log=True)
```

> `log=True` → vai para `**kwargs` → repassado a `_selecionar(log=True)` → `TypeError` em toda tentativa  
> `log_enabled=False` (default) → erro nunca é logado  
> 3 tentativas, todas falham silenciosamente → retorna `None` → `aplicar_filtro_100` retorna `False`

### Por que outros módulos funcionam?

`Fix/core.py` tem um wrapper que TRADUZ o parâmetro:
```python
def com_retry(func, max_tentativas=3, backoff_base=2, log=False, *args, **kwargs):
    return _com_retry_impl(func, ..., log_enabled=log, ...)
```

Todos os outros módulos (`Prazo/loop_ciclo1_movimentacao.py`, `Peticao/pet*.py`) importam via `Fix.core` e por isso funcionam. Apenas `Fix/navigation/filters.py` importa diretamente da implementação.

---

## Arquivos afetados

| Arquivo | Linha | Mudança |
|---|---|---|
| `Fix/navigation/filters.py` | 244 | `log=True` → `log_enabled=True` |

---

## Patch

### `Fix/navigation/filters.py` — linha 244

**Antes:**
```python
resultado = com_retry(_selecionar, max_tentativas=3, backoff_base=1.5, log=True)
```

**Depois:**
```python
resultado = com_retry(_selecionar, max_tentativas=3, backoff_base=1.5, log_enabled=True)
```

---

## Verificação

```bash
py -m py_compile Fix/navigation/filters.py
py -c "from Fix.navigation.filters import aplicar_filtro_100; print('OK')"
```

---

## Risco de regressão

**Nenhum.** A mudança é idêntica em comportamento — apenas passa o argumento pelo nome correto.  
Não altera lógica, não altera assinaturas públicas, não afeta outros módulos.

---

## Status

- [x] Causa raiz identificada  
- [x] Patch definido  
- [x] Patch aplicado — `Fix/navigation/filters.py` linha 244  
- [x] Verificação de compilação: `OK`  
