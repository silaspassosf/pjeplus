# PJePlus — Sugestão de Otimizações (Review via idx.md)

> **Gerado em:** 13/04/2026  
> **Base:** `idx.md` + `reta3.md` + auditoria cirúrgica do repositório atual  
> **Filosofia:** cirúrgico, zero perda de comportamento funcional

---

## Status dos Artefatos reta3

| Artefato | Status | Observação |
|---|---|---|
| `Fix/exceptions.py` | ✅ Implementado | Hierarquia completa. `contexto` sem default em `ElementoNaoEncontradoError` (parâmetro obrigatório — considerar default `""`) |
| `Fix/scripts/__init__.py` | ⚠️ Bug leve | `Path(pasta / nome_arquivo)` falha se `pasta` for `str` (já é quando chamado sem arg). Corrigir para `Path(pasta) / nome_arquivo` |
| `Fix/drivers/lifecycle.py` | ⚠️ Parcial | `logger = logging.getLogger(__name__)` em vez de `get_module_logger`. Bloco `import logging` aparece **depois** de `yield driver` (import deslocado — P8 invertido) |
| `Fix/sessionpool.py` | ✅ Presente | Não auditado em detalhe |
| `Fix/progress.py` | ✅ Presente | Não auditado em detalhe |
| `Fix/log.py` | ✅ Implementado | `EmojiValidator` presente. `get_module_logger` disponível |
| `Fix/smartfinder.py` | ✅ Presente | Não auditado em detalhe |
| `Fix/headlesshelpers.py` | ✅ Presente | Não auditado em detalhe |
| `driver_session` em `x.py` | ✅ Aplicado | Import feito dentro de função (linha 896) — viola P8 |

---

## Itens Abertos por Prioridade

---

### 🔴 CRÍTICO — Rompe headless / diagnóstico em produção

#### C1 — Bug em `Fix/scripts/__init__.py` linha 8

```python
# ATUAL — falha quando pasta é str
_cache[chave] = Path(pasta / nome_arquivo).read_text(encoding="utf-8")

# CORRETO
_cache[chave] = (Path(pasta) / nome_arquivo).read_text(encoding="utf-8")
```

**Impacto:** qualquer módulo que chame `carregar_js(nome, str_path)` recebe `TypeError` silencioso. Remove a utilidade do loader inteiro.

---

#### C2 — P3 ainda vigente em `atos/` — 20+ ocorrências

Arquivos com `return False` após `except`:

| Arquivo | Linhas |
|---|---|
| `atos/judicial_bloqueios.py` | 62, 210, 220 |
| `atos/comunicacao_preenchimento.py` | 51, 64, 82, 84, 110, 135 |
| `atos/comunicacao_finalizacao.py` | 91, 110, 117, 128 |
| `atos/core.py` | 60, 143, 191, 311, 359 |

**Problema:** falhas silenciosas impossibilitam diagnóstico remoto (cloud / GitHub Actions). O log só mostra que o fluxo parou, nunca por quê.

**Ação:** substituir por `raise ElementoNaoEncontradoError(seletor, contexto)` ou `raise NavegacaoError(msg)` das exceções já em `Fix/exceptions.py`. Os orquestradores já capturam `PJePlusError`.

---

### 🟠 IMPORTANTE — Impacta performance e confiabilidade headless

#### I1 — P4: `time.sleep` maciço em `atos/comunicacao_preenchimento.py`

**12 ocorrências** de `time.sleep(0.3–1.5)` — concentradas em preenchimento de campos Angular. Em headless, a rede pode ser mais lenta ou mais rápida; sleeps fixos causam race conditions silenciosos ou desperdício de tempo.

**Substitutos disponíveis (já no Fix):**

```python
# Para aguardar campo Angular responder:
from Fix.utils_observer import aguardar_renderizacao_nativa
aguardar_renderizacao_nativa(driver, seletor_campo, modo='aparecer', timeout=4)

# Para aguardar elemento clicável:
from Fix.selenium_base.wait_operations import wait_for_clickable
wait_for_clickable(driver, seletor, timeout=5)
```

**Hotspot principal:** `comunicacao_preenchimento.py` linhas 47, 50, 134, 233, 240, 262, 284, 295, 312, 315, 362, 378, 385.

---

#### I2 — P5: JS inline em módulos ativos (não `ref/`)

| Arquivo | Ocorrências | Tamanho estimado |
|---|---|---|
| `SISB/Core/utils_web.py` | 2 | 30–80 linhas cada |
| `SISB/processamento_campos_reus.py` | 3 | 20–40 linhas cada |
| `SISB/processamento/ordens_acao.py` | 1 | ~15 linhas |
| `PEC/anexos/anexos_juntador_metodos.py` | 2 | 40–60 linhas cada |
| `PEC/core_progresso.py` | 1 | ~20 linhas |

**Ação:** extrair para `SISB/scripts/` e `PEC/scripts/`, carregar via `carregar_js()` (depois de corrigir C1). Variáveis Python → `arguments[0]`, nunca f-string dentro do JS.

---

#### I3 — P1 semi-aplicado em `Fix/core.py`

Os imports foram movidos para o topo (✅), mas o arquivo ainda contém dezenas de wrappers de uma linha:

```python
def wait(driver, selector, timeout=10, by=By.CSS_SELECTOR):
    """Wrapper para Fix.selenium_base.wait_operations.wait."""
    return _wait_impl(driver, selector, timeout=timeout, by=by)
```

O alias `_wait_impl` reduz o overhead de lookup, mas o wrapper em si não adiciona valor — qualquer traceback ainda passa por ele, dificultando leitura do stack.

**Ação preferida (não urgente):** converter gradualmente para re-exportação pura no `__init__.py`:

```python
# Fix/__init__.py — sem wrapper
from Fix.selenium_base.wait_operations import wait, wait_for_visible, wait_for_clickable
```

Manter compatibilidade: qualquer `from Fix.core import wait` continua funcionando se `__init__.py` re-exportar. Aplicar arquivo por arquivo, não tudo de uma vez.

---

#### I4 — P8 resolvido ao contrário em `Fix/drivers/lifecycle.py`

```python
# ATUAL — import DEPOIS do yield (erro de posicionamento)
        yield driver
    finally:
        ...
import logging           # ← aqui, no final do arquivo
logger = logging.getLogger(__name__)
```

Além disso, usa `logging.getLogger` em vez de `get_module_logger`. Em log centralizado isso significa que as mensagens do lifecycle não passam pelo filtro de emoji do `PJePlusLogger`.

**Fix:**

```python
# Topo do arquivo
from Fix.log import get_module_logger
logger = get_module_logger(__name__)
```

---

#### I5 — Import de `driver_session` dentro de função em `x.py` linha 896

```python
# ATUAL (viola P8)
def _ciclo_de_sessao(...):
    from Fix.drivers import driver_session   # ← lazy import
    with driver_session(...) as driver:
        ...
```

**Fix:** mover para o topo de `x.py` junto dos outros imports.

---

### 🟡 SUGESTÃO — Melhoria de qualidade sem urgência funcional

#### S1 — `ElementoNaoEncontradoError` exige `contexto` (sem default)

```python
# ATUAL — parâmetro obrigatório dificulta adoção
class ElementoNaoEncontradoError(PJePlusError):
    def __init__(self, seletor: str, contexto: str):   # sem default

# SUGERIDO — adoção mais fácil
    def __init__(self, seletor: str, contexto: str = ""):
```

---

#### S2 — `Fix/core.py` importa `WebDriverWait`/`EC`/`ActionChains` diretamente

```python
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
```

Esses imports existem por compatibilidade com funções antigas ainda no arquivo. Se P1 for resolvido gradualmente (I3), eles podem ser removidos junto com as funções que os usam. Não remover antes.

---

#### S3 — `Fix/drivers/lifecycle.py`: docstring final (`"""`) solta após `import logging`

Artefato de edição — há uma `"""` solta no final do arquivo que pode causar `SyntaxWarning` dependendo do contexto de chamada. Verificar com `py -m py_compile Fix/drivers/lifecycle.py`.

---

#### S4 — CI / GitHub Actions ainda não configurado

`idx.md` seção 4 define os passos de CI mas nenhum workflow `.github/workflows/*.yml` foi encontrado. Sugere-se ao menos um workflow de sanity:

```yaml
# .github/workflows/sanity.yml
name: Sanity
on: [push, pull_request]
jobs:
  compile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt --quiet
      - run: py -m py_compile Fix/core.py Fix/exceptions.py Fix/scripts/__init__.py Fix/drivers/lifecycle.py
        env:
          PJEPLUS_TIME: "1"
```

---

## Ordem de Aplicação Recomendada

```
1. C1  — Fix/scripts/__init__.py (1 linha, risco zero)
2. I4  — Fix/drivers/lifecycle.py logger + import (2 linhas)
3. I5  — x.py mover import para topo (1 linha)
4. S1  — Fix/exceptions.py default de contexto (1 caractere)
5. S3  — Fix/drivers/lifecycle.py remover """ solta
6. C2  — atos/: substituir return False por exceções (arquivo por arquivo)
7. I1  — atos/comunicacao_preenchimento.py: sleep → aguardar_renderizacao_nativa
8. I2  — SISB/ + PEC/: extrair JS para arquivos .js (depende de C1 corrigido)
9. I3  — Fix/core.py: wrappers → re-exportações (baixa urgência, alto impacto futuro)
10. S4 — Criar .github/workflows/sanity.yml
```

---

## Resumo Executivo

| Categoria | Quantidade | Esforço estimado |
|---|---|---|
| Bug ativo (C1, S3) | 2 | < 5 min cada |
| Padrão P3 return False | 20+ instâncias | 2–4h (atos/ completo) |
| Padrão P4 time.sleep | 20+ instâncias | 3–5h (comunicacao*) |
| Padrão P5 JS inline | 9 instâncias ativas | 4–6h (SISB + PEC) |
| P1/P8 wrappers lazy | parcialmente resolvido | 2–3h (se decidir finalizar) |

O menor invest com maior retorno: **C1 + I4 + I5 + S1** — menos de 30 minutos, zero risco, e desbloqueiam o loader JS e o diagnóstico correto de lifecycle.
