# Plano 5 — Controle de Logs e Identificação de Origem

**Status:** Diagnóstico concluído — migração incremental por módulo  
**Risco:** Baixo (mudança de import, sem alterar lógica)  
**Modelo alvo:** GPT-4.1 via PJE.md (Surgical Mode)

---

## Diagnóstico

### Problema raiz

`Fix/log.py` linha 507 exporta:
```python
logger = logging.getLogger('Fix')
```

Todos os módulos fazem `from Fix.log import logger` e compartilham **o mesmo objeto logger**
com nome `'Fix'`. O `PJePlusFormatter` já inclui `module_name:function_name:line_number`
no output (linhas 124-135 de `log.py`) — mas `module_name` vem de `record.name`, que é
sempre `'Fix'`, nunca o arquivo real.

### Impacto

```
[2026-03-31 10:00:01.123] [ERROR] Fix:clicar_botao:42 Elemento não encontrado
[2026-03-31 10:00:01.456] [ERROR] Fix:processar:88 Timeout no PJe
```

Ambas as linhas mostram `Fix` como origem — impossível saber se veio de
`atos/comunicacao_navigation.py` ou `SISB/core.py`.

### O que já existe e funciona

`get_module_logger(module_name)` em `Fix/log.py` linha 283 — retorna um logger
nomeado com `module_name`. Se usado com `__name__`, o output seria:

```
[2026-03-31 10:00:01.123] [ERROR] atos.comunicacao_navigation:clicar_botao:42 Elemento nao encontrado
```

---

## Solução em 2 etapas

### Etapa 5.1 — Adicionar alias `getmodulelogger` em Fix/log.py

O modo instrucional usa `getmodulelogger` (sem underscore), mas a função real é
`get_module_logger`. Adicionar alias para tornar a migração idiomática.

<!-- pjeplus:apply -->
## Alteração Proposta

```
arquivo: Fix/log.py
operacao: insert_after
ancora: "logger = logging.getLogger('Fix')"
```

```python
# Alias sem underscore para adoção consistente nos módulos
getmodulelogger = get_module_logger
```

---

### Etapa 5.2 — Migrar módulos: trocar `logger` global por logger de módulo

**Padrão de migração** (aplicar arquivo por arquivo):

```python
# ANTES
from Fix.log import logger

# DEPOIS
from Fix.log import getmodulelogger
logger = getmodulelogger(__name__)
```

**Prioridade de migração** (por frequência de uso e criticidade de debug):

| Arquivo | Motivo de prioridade |
|---|---|
| `atos/comunicacao_navigation.py` | Arquivo aberto atualmente, erros de navegação frequentes |
| `atos/judicial_fluxo.py` | Fluxo crítico — erros aqui param tudo |
| `atos/judicial_helpers.py` | Chamado de múltiplos pontos |
| `SISB/core.py` | 1078 linhas — erros difíceis de localizar sem módulo correto |
| `Peticao/pet_novo.py` | Logger duplicado + `logging.getLogger(__name__)` raw |

> **Nota:** `Peticao/pet2.py` e `Peticao/pet_novo.py` usam `import logging; logger = logging.getLogger(__name__)` — esse padrão EVITA o `PJePlusFormatter` (sem validação de emoji,
> sem cores). Migrar para `getmodulelogger` os integra ao sistema centralizado.

---

### Patches por arquivo (Surgical Mode)

#### atos/comunicacao_navigation.py

<!-- pjeplus:apply -->
## Alteração Proposta

```
arquivo: atos/comunicacao_navigation.py
operacao: replace
ancora: "from Fix.log import logger"
```

```python
# ANTES
from Fix.log import logger
```

```python
# DEPOIS
from Fix.log import getmodulelogger
logger = getmodulelogger(__name__)
```

---

#### atos/judicial_fluxo.py

<!-- pjeplus:apply -->
## Alteração Proposta

```
arquivo: atos/judicial_fluxo.py
operacao: replace
ancora: "from Fix.log import logger"
```

```python
# ANTES
from Fix.log import logger
```

```python
# DEPOIS
from Fix.log import getmodulelogger
logger = getmodulelogger(__name__)
```

---

#### Peticao/pet_novo.py e pet2.py

<!-- pjeplus:apply -->
## Alteração Proposta

```
arquivo: Peticao/pet_novo.py
operacao: replace
ancora: "import logging\nlogger = logging.getLogger(__name__)"
```

```python
# ANTES
import logging
logger = logging.getLogger(__name__)
```

```python
# DEPOIS
from Fix.log import getmodulelogger
logger = getmodulelogger(__name__)
```

*(Mesmo patch para `Peticao/pet2.py`)*

---

## Comportamento resultante nos logs

Após migração, um erro em `atos/judicial_fluxo.py` função `executar_cls` linha 312:

```
[2026-03-31 10:00:01.123] [ERROR] atos.judicial_fluxo:executar_cls:312 Timeout aguardando botao save
```

Traceback completo com `exc_info=True` ainda disponível abaixo da linha.

---

## Script de diagnóstico (antes de migrar)

```bash
# Listar todos os arquivos que usam o logger global 'Fix'
py -c "
import pathlib, re
pattern = re.compile(r'from Fix\.log import logger\b')
for f in pathlib.Path('.').rglob('*.py'):
    if 'ref' in f.parts or 'ORIGINAIS' in f.parts:
        continue
    try:
        text = f.read_text(encoding='utf-8')
        if pattern.search(text):
            print(f)
    except Exception:
        pass
"
```

## Verificação por arquivo migrado

```bash
py -m py_compile atos/comunicacao_navigation.py
py -m py_compile atos/judicial_fluxo.py
py -m py_compile Peticao/pet_novo.py
```
