# Plano: Triagem/ sem dependência de aud.py

**Objetivo:** o módulo `Triagem/` (especialmente `runner.py`) deve ser completamente
autossuficiente — zero imports de `aud.py` ou `tr.py`.
Todos os símbolos necessários são copiados/adaptados **dentro** de `Triagem/`.

Arquivos existentes que continuam intocados: `service.py`, `regras.py`, `coleta.py`,
`utils.py`, `constants.py`, `preprocess.py`, `__init__.py`.

---

## Arquivos a criar

### 1. `Triagem/api.py` (~120 linhas)
**Origem:** `apiaud.py` (linhas 19–187)

Copiar e adaptar:
- `_normalizar_lista(dados)`
- `_JS_BUSCAR_TRIAGEM` (string JS inteira, linhas 53–121)
- `buscar_lista_triagem(driver)` — `execute_async_script` com o JS acima
- `_is_triagem_inicial(item)`
- `_numero_cnj(item)`
- `enriquecer_processo(item)` → classifica bucket A/B/C/D

**Ajustes:**
- Remover `criar_driver_e_logar` (não necessário aqui)
- Remover `executar_teste_lista_triagem` e `run_apiaud` (pertencem a `apiaud.py`)
- Manter `__all__` com os 5 símbolos usados pelo `runner.py`

**Imports necessários:**
```python
from typing import Any, Dict, List, Optional
from selenium.webdriver.remote.webdriver import WebDriver
```

---

### 2. `Triagem/citacao.py` (~100 linhas)
**Origem:** `aud.py` linhas 62–158 (`_FALHA_CITACAO` + `def_citacao`)

Copiar integralmente:
- `_FALHA_CITACAO` (dict constante)
- `def_citacao(driver, processo_info) -> dict`

**Imports necessários:**
```python
import re
from typing import Dict
from selenium.webdriver.remote.webdriver import WebDriver
from api.variaveis import PjeApiClient, session_from_driver
```

> `api.variaveis` é infraestrutura compartilhada do projeto — não pertence a `aud.py`,
> portanto importar diretamente é correto.

---

### 3. `Triagem/acoes.py` (~350 linhas)
**Origem:** `aud.py` linhas 159–274 (`acao_bucket_a`) + funções auxiliares
de audiência (linhas 973–1198)

Funções a copiar/adaptar:

| Função | Linhas em aud.py | Destino em acoes.py |
|---|---|---|
| `_abrir_nova_aba` | 973–999 | copiar integral |
| `desmarcar_100` | 1001–1060 | copiar integral |
| `remarcar_100_pos_aud` | 1062–1098 | copiar integral |
| `marcar_aud` | 1100–1193 | copiar integral |
| `acao_bucket_a` | 159–274 | copiar e trocar `from aud import X` → imports locais |
| `_acao_bucket_b` | inline em `indexar_e_processar_lista_aud` (aud.py ~561–611) | extrair e nomear `acao_bucket_b` |
| `_acao_bucket_c` | inline em `indexar_e_processar_lista_aud` (aud.py ~613–643) | extrair e nomear `acao_bucket_c` |
| `_acao_bucket_d` | inline em `indexar_e_processar_lista_aud` (aud.py ~645–670) | extrair e nomear `acao_bucket_d` |

**Imports necessários:**
```python
import time
import traceback
from typing import Dict, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from Fix.core import esperar_elemento, safe_click, preencher_campo
from Fix.headless_helpers import limpar_overlays_headless
from Fix.gigs import criar_gigs
from Fix.abas import trocar_para_nova_aba
from Triagem.citacao import def_citacao
```

**Atos externos** (mantidos como lazy imports dentro das funções):
```python
# dentro de acao_bucket_a:
from atos import ato_unap, ato_100
# dentro de acao_bucket_b:
from atos import ato_100
# dentro de acao_bucket_c:
from atos import mov_aud
from atos.wrappers_pec import pec_ord, pec_sum, pec_ordc, pec_sumc
# dentro de acao_bucket_d:
from atos import ato_ratif   # ou fallback gracioso se ImportError
```

---

### 4. `Triagem/driver.py` (~40 linhas)
**Origem:** `aud.py` linhas 680–719 (`criar_driver_e_logar`)

Copiar e simplificar — apenas lógica de criar/login sem referência a nada de `aud.py`:

```python
from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from Fix.utils import driver_pc, login_cpf

def criar_driver_e_logar(driver: Optional[WebDriver] = None) -> Optional[WebDriver]:
    if driver:
        return driver
    drv = driver_pc()
    if not drv:
        return None
    if not login_cpf(drv):
        try: drv.quit()
        except Exception: pass
        return None
    return drv
```

---

## Alterações em arquivos existentes

### `Triagem/runner.py` — substituir todos os imports de `aud.py`

| Import atual (em runner.py) | Substituir por |
|---|---|
| `from aud import acao_bucket_a` | `from Triagem.acoes import acao_bucket_a` |
| `from aud import def_citacao` | `from Triagem.citacao import def_citacao` |
| `from apiaud import buscar_lista_triagem, enriquecer_processo, _is_triagem_inicial` | `from Triagem.api import buscar_lista_triagem, enriquecer_processo, _is_triagem_inicial` |

Na função `_criar_driver_e_logar` dentro de `runner.py`:
- Substituir corpo por `from Triagem.driver import criar_driver_e_logar; return criar_driver_e_logar(driver)`

### `Triagem/__init__.py` — expor nova API pública

Adicionar exports:
```python
from .api import buscar_lista_triagem, enriquecer_processo, _is_triagem_inicial
from .citacao import def_citacao
from .acoes import acao_bucket_a, acao_bucket_b, acao_bucket_c, acao_bucket_d
from .runner import run_triagem
from .driver import criar_driver_e_logar
```

---

## Estimativa de linhas por arquivo final

| Arquivo | Estimativa |
|---|---|
| `Triagem/api.py` | ~120 |
| `Triagem/citacao.py` | ~100 |
| `Triagem/acoes.py` | ~350 |
| `Triagem/driver.py` | ~40 |
| `Triagem/runner.py` (ajustado) | ~380 |
| `Triagem/service.py` (sem mudança) | 241 |
| `Triagem/regras.py` (sem mudança) | 787 |
| `Triagem/coleta.py` (sem mudança) | 503 |

Todos abaixo de 600 linhas. `regras.py` (787) excede — pode ser dividido opcionalmente
em `regras_docs.py` (B1–B4), `regras_processo.py` (B5–B10) e `regras_texto.py` (B11–B14),
mas **não é obrigatório** para a independência de `aud.py`.

---

## Ordem de execução

```
1. Criar Triagem/api.py       ← sem dependências internas novas
2. Criar Triagem/citacao.py   ← sem dependências internas novas
3. Criar Triagem/driver.py    ← sem dependências internas novas
4. Criar Triagem/acoes.py     ← depende de citacao.py (criado no passo 2)
5. Editar Triagem/runner.py   ← substituir imports de aud.py pelos locais
6. Editar Triagem/__init__.py ← adicionar exports
7. Validar: py -m py_compile Triagem/api.py Triagem/citacao.py Triagem/driver.py Triagem/acoes.py Triagem/runner.py
```

---

## O que NÃO muda

- `aud.py` continua existindo e funcional (não deletar — tem `run_aud` usado diretamente)
- `apiaud.py` continua existindo (tem `run_apiaud` e `executar_teste_lista_triagem` próprios)
- `tr.py` não é referenciado em nenhum ponto (nunca foi dependência)

---

## Verificação final de dependências

Após execução, `grep -r "from aud" Triagem/` e `grep -r "import aud" Triagem/`
devem retornar zero resultados.
