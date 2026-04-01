# Plano 1 — Dependências e Imports

**Status:** Diagnóstico concluído — patches prontos para aplicação incremental  
**Risco:** Baixo (re-exportações e remoção de duplicatas)  
**Modelo alvo:** GPT-4.1 via PJE.md (Surgical Mode)

---

## Diagnóstico

### Problema central
`from Fix.log import logger` em todos os módulos (`atos/`, `Prazo/`, `Peticao/`) importa
**um único objeto logger global**. Isso significa que log de `comunicacao_navigation.py`
aparece no mesmo stream sem identificação de origem.

### Outros padrões identificados
| # | Padrão | Onde | Impacto |
|---|---|---|---|
| A | `import time` + `time.sleep()` nos bloco de execução de `x.py` | `x.py` linhas ~10-20 | Race condition, não headless-safe |
| B | `from Fix.smart_finder import SmartFinder` instanciado sem driver | `Prazo/loop_ciclo2_*.py` `_SF = SmartFinder()` | Cache carregado mas `driver=None` — find_element vai dar erro silencioso |
| C | `logging.getLogger(__name__)` em paralelo ao `Fix/log.py` | `x.py` importa `logging` diretamente | Dois sistemas de log concorrentes |
| D | `from Fix.core import finalizar_driver as finalizar_driver_fix` — alias `_fix` | `x.py` | Alias desnecessário, ofusca rastreamento |

---

## Etapas Incrementais

### Etapa 1.1 — Remover `time.sleep()` de `x.py` (bloco de execução)

**Arquivo:** `x.py`  
**Impacto:** Zero na lógica; `resetar_driver` já aguarda estado estável.

<!-- pjeplus:apply -->
## Alteração Proposta

```
arquivo: x.py
operacao: replace
ancora: "_executar_mandado_bloco"
```

```python
# ANTES
def _executar_mandado_bloco(driver):
    resultado = executar_mandado(driver)
    resetar_driver(driver)
    time.sleep(3)
    return resultado

def _executar_prazo_bloco(driver):
    resultado = executar_prazo(driver)
    resetar_driver(driver)
    time.sleep(3)
    return resultado

def _executar_p2b_bloco(driver):
    resultado = executar_p2b(driver)
    resetar_driver(driver)
    time.sleep(3)
    return resultado
```

```python
# DEPOIS
def _executar_mandado_bloco(driver):
    resultado = executar_mandado(driver)
    resetar_driver(driver)
    return resultado

def _executar_prazo_bloco(driver):
    resultado = executar_prazo(driver)
    resetar_driver(driver)
    return resultado

def _executar_p2b_bloco(driver):
    resultado = executar_p2b(driver)
    resetar_driver(driver)
    return resultado
```

---

### Etapa 1.2 — Corrigir instanciação do SmartFinder sem driver

**Arquivos:** `Prazo/loop_ciclo2_selecao.py`, `Prazo/loop_ciclo2_processamento.py`  
**Problema:** `_SF = SmartFinder()` cria instância com `driver=None`; `_SF.find_element()` chamado
depois sem garantia de que `set_driver()` foi chamado.  
**Fix:** Usar `get_sf(driver)` — padrão lazy que garante o driver correto a cada chamada.

<!-- pjeplus:apply -->
## Alteração Proposta

```
arquivo: Prazo/loop_ciclo2_selecao.py
operacao: replace
ancora: "_SF = SmartFinder()"
```

```python
# ANTES
from Fix.smart_finder import SmartFinder

# Reuse SmartFinder instance
_SF = SmartFinder()
```

```python
# DEPOIS
from Fix.smart_finder import SmartFinder

def _get_sf(driver):
    """Retorna SmartFinder com driver atualizado a cada chamada."""
    sf = SmartFinder(driver)
    return sf
```

*(Aplicar o mesmo padrão em `loop_ciclo2_processamento.py`)*

---

### Etapa 1.3 — Eliminar import `logging` duplicado de `x.py`

**Arquivo:** `x.py`  
**Ação:** Substituir `import logging` + `logging.getLogger(...)` pelo padrão centralizado.

<!-- pjeplus:apply -->
## Alteração Proposta

```
arquivo: x.py
operacao: replace
ancora: "import logging"
```

```python
# ANTES (bloco de imports em x.py)
import logging
```

```python
# DEPOIS
from Fix.log import logger as _logger_xpy
```

> **Nota para Surgical Mode:** substituir todas as chamadas `logging.getLogger(...)` e
> `logger = logging.getLogger(...)` em `x.py` pelo `_logger_xpy` acima.

---

## Verificação Final

```bash
py -m py_compile x.py
py -m py_compile Prazo/loop_ciclo2_selecao.py
py -m py_compile Prazo/loop_ciclo2_processamento.py
```
