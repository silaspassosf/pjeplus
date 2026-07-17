# RELATÓRIO DE MUDANÇAS - MÓDULO MANDADO
**Data:** 2025-11-04  
**Objetivo:** Estruturar módulo Mandado e integração com Fix modularizado

---

## 📋 PROBLEMA DE IMPORTS - CORREÇÃO DO LOGGER

### ⚠️ PROBLEMA IDENTIFICADO
Após modularizar Fix, o import `from log import logger` quebrou em múltiplos arquivos:
- `Fix/core.py` linha 23
- `Fix/utils.py` linha 23
- ORIGINAIS/atos.py linha 2 (herdado por Mandado via wrapper)

**Causa:** `log.py` da raiz era um arquivo que registrava execução, não um módulo logger.

---

### 🔧 SOLUÇÃO IMPLEMENTADA (3 CAMADAS)

#### Camada 1: Fix/log.py (NOVO MÓDULO)
**Arquivo criado:** `Fix/log.py` (68 linhas)

```python
"""Fix/log.py - Sistema de Logging para PJe Plus"""

import os
import logging
import sys

class PJELogger:
    """Logger estruturado com controle via PJEPLUS_DEBUG."""
    
    def __init__(self, nome='pjeplus'):
        self.logger = logging.getLogger(nome)
        self._configurar_nivel()
        self._configurar_formatador()
    
    def _configurar_nivel(self):
        debug_env = os.getenv('PJEPLUS_DEBUG', '0').lower()
        if debug_env in ('1', 'true', 'on'):
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
    
    def debug(self, mensagem): self.logger.debug(mensagem)
    def info(self, mensagem): self.logger.info(mensagem)
    def warning(self, mensagem): self.logger.warning(mensagem)
    def error(self, mensagem): self.logger.error(mensagem)

logger = PJELogger('pjeplus').logger
```

**Vantagens:**
- ✅ Centralizado em um lugar
- ✅ Configurável via variável ambiente
- ✅ Suporta DEBUG/INFO/WARNING/ERROR
- ✅ Reutilizável por todos os módulos

---

#### Camada 2: log.py (RAIZ) - COMPATIBILIDADE
**Arquivo modificado:** `d:\PjePlus\log.py`

```python
"""log.py (raiz) - Re-export de Fix.log para compatibilidade com código legado"""

from Fix.log import logger

__all__ = ['logger']
```

**Propósito:** Permitir que `from log import logger` continue funcionando em código legado que não foi migrado para modular.

**Benefício:** Zero breaking changes para código antigo.

---

#### Camada 3: Mandado/log.py - WRAPPER
**Arquivo criado:** `Mandado/log.py`

```python
"""Mandado/log.py - Re-export de Fix.log"""

from Fix.log import logger

__all__ = ['logger']
```

**Propósito:** ORIGINAIS/atos.py faz `from log import logger` (relativo), precisa resolver localmente.

---

### 🔄 CORREÇÃO CASCATA - SEQUÊNCIA

#### PASSO 1: Criar `Fix/log.py` (módulo real)
```bash
# Criar Fix/log.py com classe PJELogger
```

#### PASSO 2: Atualizar `Fix/core.py` (linha 23)
```python
# ANTES:
from log import logger

# DEPOIS:
from .log import logger  # ← Import relativo intra-módulo
```

#### PASSO 3: Atualizar `Fix/utils.py` (linha 23)
```python
# ANTES:
from log import logger

# DEPOIS:
from .log import logger  # ← Import relativo intra-módulo
```

#### PASSO 4: Criar `Mandado/log.py` wrapper
```python
from Fix.log import logger  # ← Import absoluto de Fix
__all__ = ['logger']
```

#### PASSO 5: Atualizar `log.py` raiz
```python
from Fix.log import logger  # ← Re-export de Fix para código legado
__all__ = ['logger']
```

---

### ✅ VALIDAÇÃO PÓS-CORREÇÃO

**Teste 1: Import de Fix.log direto**
```bash
py -c "from Fix.log import logger; print('✓ OK')"
```

**Teste 2: Import legado de raiz**
```bash
py -c "from log import logger; print('✓ OK')"
```

**Teste 3: Import de Mandado completo**
```bash
py -c "from Mandado import main; print('✓ Mandado.main importado')"
```

---

## 📋 ARQUIVOS CRIADOS/MODIFICADOS

### 1. Mandado/atos_wrapper.py (NOVO)
**Propósito:** Wrapper para importar funções de atos sem dependências de raiz

**Funções exportadas:**
- `ato_judicial`
- `ato_meios`
- `ato_pesquisas`
- `ato_crda`
- `ato_crte`
- `ato_bloq`
- `ato_idpj`
- `ato_termoE`
- `ato_termoS`
- `ato_edital`
- `pec_idpj`
- `mov_arquivar`
- `ato_meiosub`

**Importação:**
```python
from .atos_wrapper import (ato_judicial, ato_meios, ...)
```

---

### 2. Mandado/log.py (NOVO)
**Propósito:** Re-exportar logger de Fix.log para compatibilidade

**Antes:**
```python
import logging
logger = logging.getLogger('Mandado')
```

**Depois:**
```python
from Fix.log import logger
```

**Razão:** Centralizar logging em Fix.log

---

### 3. Fix/log.py (NOVO MÓDULO)
**Propósito:** Sistema de logging estruturado para todo o projeto

**Classe:** `PJELogger`
- `debug()` - Log DEBUG
- `info()` - Log INFO
- `warning()` - Log WARNING
- `error()` - Log ERROR

**Configuração via ambiente:**
- `PJEPLUS_DEBUG=0` (padrão): INFO + WARNING + ERROR
- `PJEPLUS_DEBUG=1`: DEBUG + INFO + WARNING + ERROR

**Exportação:**
```python
from Fix.log import logger
```

---

### 4. Mandado/core.py (MODIFICADO)
**Mudança:** Import de atos corrigido

**Antes:**
```python
from ORIGINAIS.atos import (ato_judicial, ...)
```

**Depois:**
```python
from .atos_wrapper import (ato_judicial, ...)
```

---

### 5. Mandado/processamento.py (MODIFICADO)
**Mudanças:**
1. Removido import `sleep` (não existe em Fix, usar `time.sleep`)
2. Removido import `driver_pc` (não usado)
3. Import de atos corrigido para usar wrapper
4. Import de atos de ORIGINAIS removido

**Antes:**
```python
from Fix import (
    sleep,
    driver_pc,
    ...
)
from ORIGINAIS.atos import (...)
```

**Depois:**
```python
from Fix import (
    navegar_para_tela,
    extrair_pdf,
    ...
)
from .atos_wrapper import (...)
```

---

### 6. Mandado/utils.py (MODIFICADO)
**Mudança:** Import de atos corrigido

**Antes:**
```python
from atos import (ato_judicial, ...)
```

**Depois:**
```python
from .atos_wrapper import (ato_judicial, ...)
```

---

### 7. Mandado/regras.py (MODIFICADO)
**Mudanças:**
1. Removido `sleep` e `driver_pc` dos imports Fix
2. Import de atos corrigido para usar wrapper

**Antes:**
```python
from Fix import (sleep, driver_pc, ...)
from atos import (...)
```

**Depois:**
```python
from Fix import (...)
from .atos_wrapper import (...)
```

---

## 🔧 IMPORTS ATUALIZADOS EM FIX

### Fix/core.py (MODIFICADO)
**Mudanças:**
1. Linha 23: `from log import logger` → `from .log import logger`
2. Adições:
   - `def preencher_campos_prazo()` - Preenche campos de prazo
   - Import de `login_cpf`, `login_manual`, `login_automatico` de `.utils`

**Reason:** Consolidar funções de preenchimento

---

### Fix/utils.py (MODIFICADO)
**Mudanças:**
1. Linha 23: `from log import logger` → `from .log import logger`
2. Adições:
   - `def login_pc()` - Login via AutoHotkey
   - `def obter_driver_padronizado()` - Driver Firefox padronizado
   - `def driver_pc()` - Wrapper para driver_pc
   - `def navegar_para_tela()` - Navegação robusta
   - `def is_browsing_context_discarded_error()` - Validação de erro
   - `def validar_conexao_driver()` - Validação de conexão
   - `import os` - Adicionado ao topo

**Reason:** Migrar funções não presentes no módulo Fix

---

### log.py (RAIZ) (MODIFICADO)
**Antes:** Arquivo que registrava execução
```python
# Última execução: 2025-11-04 12:22:43.825178
# Script: D:\PjePlus\-c
```

**Depois:** Re-export de Fix.log
```python
from Fix.log import logger
__all__ = ['logger']
```

---

## 📊 ESTRUTURA DO MANDADO (FINAL)

```
Mandado/
├── __init__.py           (exports públicos)
├── core.py              (setup, login, navegação, main)
├── processamento.py     (fluxos Argos e Outros)
├── regras.py            (estratégias - Strategy Pattern)
├── utils.py             (funções utilitárias)
├── atos_wrapper.py      (wrapper para atos de ORIGINAIS)
├── log.py               (re-export de Fix.log)
└── README.md            (documentação)
```

---

## ✅ STATUS DE IMPORTS

### Mandado/core.py
- ✅ Fix imports corrigidos
- ✅ atos imports corrigidos (wrapper)
- ✅ Log imports funcionando

### Mandado/processamento.py
- ✅ Removido `sleep` (não existe)
- ✅ Removido `driver_pc` (não usado)
- ✅ Fix imports corrigidos
- ✅ atos imports corrigidos (wrapper)

### Mandado/utils.py
- ✅ atos imports corrigidos (wrapper)

### Mandado/regras.py
- ✅ Removido `sleep` e `driver_pc`
- ✅ atos imports corrigidos (wrapper)

### Fix/core.py
- ✅ Import de log corrigido (from .log import logger)

### Fix/utils.py
- ✅ Import de log corrigido (from .log import logger)

---

## 🚀 APLICAR PARA OUTROS MÓDULOS

### Padrão de Correção (REPLICÁVEL)

**Para cada módulo X que precisa de correção:**

1. **Se o módulo importa de Fix:**
   ```python
   # Procurar por:
   from Fix import (sleep, driver_pc, ...)
   
   # Remover:
   sleep, driver_pc, logger (se houver)
   
   # Adicionar:
   Importar do Fix.log apenas se precisa de logger
   ```

2. **Se o módulo importa de log:**
   ```python
   # Trocar:
   from log import logger
   
   # Por:
   from Fix.log import logger  # (se módulo está em raiz)
   # Ou:
   from .log import logger  # (se módulo tem log.py local que re-export)
   ```

3. **Se o módulo importa de atos:**
   ```python
   # Trocar:
   from atos import (ato_judicial, ...)
   from ORIGINAIS.atos import (...)
   
   # Por (se é módulo/subpacote):
   from .atos_wrapper import (ato_judicial, ...)
   # Ou (se está em raiz):
   from ORIGINAIS.atos import (...)  # mas com Mandado/log.py wrapper
   ```

---

## 📝 NOTAS IMPORTANTES

- `sleep` não existe em Fix (usar `time.sleep`)
- `driver_pc` não é usado em Mandado (removido dos imports)
- `log.py` agora é um módulo dentro de Fix (Fix/log.py)
- `atos_wrapper.py` centraliza imports de ORIGINAIS/atos
- Todos os imports de Fix dentro de Mandado funcionam

---

**Status:** ✅ Completo  
**Última Atualização:** 2025-11-04 12:30 UTC

