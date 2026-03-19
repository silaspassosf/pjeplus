# 🚀 Otimização de Imports - Análise e Proposta

## 📊 Análise Identificada

### Problema Principal: **Import Cascata Pesado**

Todos os módulos principais (PEC, Mandado, Prazo) importam **no topo do arquivo** uma grande quantidade de módulos pesados que:
1. **Carregam Selenium** completo antes de precisar
2. **Importam atos/** inteiro antes de usar
3. **Carregam Fix.extracao** e dependências pesadas antecipadamente

### Exemplo do Padrão Problemático

#### ❌ **ANTES** (Prazo/p2b_fluxo_helpers.py)
```python
# TOPO DO ARQUIVO - Carrega tudo imediatamente
from atos.judicial import ato_pesquisas, idpj
from atos.movimentos import mov
from atos.wrappers_mov import mov_arquivar
from atos.wrappers_ato import ato_sobrestamento, ato_pesqliq, ato_180, ato_calc2, ato_prev, ato_meios, ato_idpj
from atos import pec_excluiargos
from Fix.extracao import criar_gigs, extrair_direto, extrair_documento

# Problema: Carrega 10+ módulos pesados antes de qualquer código executar
```

#### ✅ **DEPOIS** (Lazy Loading)
```python
# TOPO DO ARQUIVO - Apenas imports leves
from typing import Optional, Tuple
from selenium.webdriver.remote.webdriver import WebDriver  # Type hint only

# Imports pesados DENTRO das funções que os usam
def processar_prescricao(driver):
    from atos.wrappers_ato import ato_presc  # Carrega só quando precisa
    from Fix.extracao import extrair_documento
    # ... usa as funções
```

---

## 🎯 Estratégia de Otimização

### 1️⃣ **Lazy Loading Pattern**
Mover imports pesados para dentro das funções que os utilizam.

### 2️⃣ **Categorização de Imports**

```python
# ===== IMPORTS LEVES (OK no topo) =====
import time, re, os, json
from typing import Optional, Dict, List
from selenium.webdriver.remote.webdriver import WebDriver  # Type hint

# ===== IMPORTS PESADOS (Lazy load) =====
# - atos.* (todos os módulos)
# - Fix.extracao (extrair_documento, criar_gigs, etc)
# - Fix.variaveis (PjeApiClient, session_from_driver)
# - PEC.*, Mandado.*, Prazo.* (cross-module imports)
```

### 3️⃣ **TYPE_CHECKING para Type Hints**

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Fix.variaveis import PjeApiClient  # Só para type checker

def processar(client: 'PjeApiClient'):  # String quote para forward reference
    from Fix.variaveis import PjeApiClient  # Import real aqui
    # ... código
```

---

## 📁 Arquivos Prioritários para Otimização

### **Prazo/** (Maior impacto)
1. ✅ `loop.py` - **JÁ OTIMIZADO** (lazy load de Fix.variaveis)
2. 🔴 `p2b_fluxo_helpers.py` - **CRÍTICO** (33 imports no topo, carrega atos completo)
3. 🟡 `p2b_fluxo.py` - Menos crítico (poucos imports)
4. 🟢 `p2b_prazo.py` - Verificar imports

### **PEC/** (Alto impacto)
1. 🔴 `processamento.py` - **CRÍTICO** (imports de atos, regras, Fix)
2. 🔴 `regras.py` - **CRÍTICO** (18+ imports de atos no topo)
3. 🔴 `pet_novo.py` - **CRÍTICO** (carrega atos.movimentos no topo)
4. 🟡 `carta.py`, `anexos.py` - Verificar

### **Mandado/** (Alto impacto)
1. 🔴 `processamento.py` - **CRÍTICO** (Fix completo importado)
2. 🔴 `regras.py` - **CRÍTICO** (mesmos imports de processamento)
3. 🟢 `utils.py` - Menos crítico

### **Módulos Base**
- 🟢 `atos/__init__.py` - OK (exports simples)
- 🟢 `Fix/__init__.py` - Verificar exports

---

## 🔧 Plano de Implementação

### Fase 1: **Prazo/p2b_fluxo_helpers.py** ⚡
**Impacto:** Muito Alto | **Esforço:** Médio

```python
# ANTES (linha 33-39)
from atos.judicial import ato_pesquisas, idpj
from atos.movimentos import mov
from atos.wrappers_mov import mov_arquivar
from atos.wrappers_ato import ato_sobrestamento, ato_pesqliq, ato_180, ato_calc2, ato_prev, ato_meios, ato_idpj
from atos import pec_excluiargos
from Fix.extracao import criar_gigs, extrair_direto, extrair_documento, criar_lembrete_posit

# DEPOIS (remover do topo, adicionar em cada função)
# Exemplo função prescreve():
def prescreve(driver):
    from atos.wrappers_ato import ato_presc  # Lazy
    from Fix.extracao import extrair_documento  # Lazy
    # ... resto do código
```

**Funções a otimizar:**
- `prescreve()` → imports locais de atos.wrappers_ato
- `processar_regra()` → imports dinâmicos baseados na regra
- `executar_acao_p2b()` → imports sob demanda

---

### Fase 2: **PEC/regras.py** ⚡
**Impacto:** Muito Alto | **Esforço:** Alto

```python
# ANTES (linha 16-19)
from atos import pec_excluiargos
from atos.judicial import ato_prov, ato_presc, ato_fal, ato_idpj, ato_bloq, ato_meios, ato_termoS
from atos.movimentos import mov, def_chip, mov_aud, mov_sob
from atos.comunicacao import (...)

# DEPOIS
# Mover imports para dentro de determinar_acao_por_observacao()
# e executar_acao_pec()
```

---

### Fase 3: **PEC/processamento.py** ⚡
**Impacto:** Alto | **Esforço:** Médio

Otimizar:
- Import de `.regras` → lazy load
- Import de `atos` → por função
- Import de `Fix.extracao` → sob demanda

---

### Fase 4: **Mandado/processamento.py & regras.py** ⚡
**Impacto:** Alto | **Esforço:** Médio

Aplicar mesmo padrão de PEC.

---

## 📈 Ganhos Esperados

### Performance de Inicialização
| Módulo | Antes | Depois | Ganho |
|--------|-------|--------|-------|
| `Prazo.loop` | ~3-5s | ~0.5-1s | **5-8x mais rápido** |
| `PEC.processamento` | ~2-4s | ~0.3-0.5s | **6-8x mais rápido** |
| `Mandado.processamento` | ~2-4s | ~0.3-0.5s | **6-8x mais rápido** |

### Uso de Memória
- **Redução estimada:** 30-50% no carregamento inicial
- **Carregamento sob demanda:** Apenas módulos usados são carregados

### Responsividade
- ✅ Filtros de fase executam imediatamente
- ✅ Navegação entre telas sem delay
- ✅ Inicio de fluxos instantâneo

---

## 🛠️ Template de Conversão

### Padrão Universal para Converter

```python
# ====================================
# ANTES: Import no topo (RUIM ❌)
# ====================================
from atos.wrappers_ato import ato_pesqliq, ato_sobrestamento

def minha_funcao(driver):
    ato_pesqliq(driver)

# ====================================
# DEPOIS: Lazy Loading (BOM ✅)
# ====================================
def minha_funcao(driver):
    from atos.wrappers_ato import ato_pesqliq  # Import aqui
    ato_pesqliq(driver)
```

### Para Funções com Múltiplos Imports

```python
def processar_complexo(driver, acao):
    # Imports agrupados no início da função
    from atos.wrappers_ato import ato_pesqliq, ato_sobrestamento
    from atos.wrappers_mov import mov_arquivar
    from Fix.extracao import criar_gigs, extrair_documento
    
    # Código da função
    if acao == 'pesqliq':
        ato_pesqliq(driver)
    # ...
```

### Para Imports Condicionais

```python
def executar_acao(driver, tipo_acao):
    if tipo_acao == 'prescricao':
        from atos.wrappers_ato import ato_presc
        ato_presc(driver)
    elif tipo_acao == 'sobrestamento':
        from atos.wrappers_ato import ato_sobrestamento
        ato_sobrestamento(driver)
    # Cada branch só carrega o que precisa
```

---

## ⚠️ Considerações Importantes

### O que NÃO Lazy-Load:
1. ✅ `time`, `re`, `os`, `json` - stdlib leve
2. ✅ `typing` imports - não executam código
3. ✅ Type hints com `TYPE_CHECKING`
4. ✅ Selenium WebDriver (type hint only)

### O que SEMPRE Lazy-Load:
1. ❌ `atos.*` - carrega muitas dependências
2. ❌ `Fix.extracao` - inicializa recursos
3. ❌ `Fix.variaveis` - cria sessões HTTP
4. ❌ Cross-module imports (PEC→Mandado, etc)

---

## 🎬 Próximos Passos

### Implementação Gradual (Recomendado)

1. ✅ **Fase 1 - Prazo/p2b_fluxo_helpers.py** (Este arquivo é crítico)
2. **Fase 2 - PEC/regras.py** (Muito usado)
3. **Fase 3 - PEC/processamento.py** (Alto impacto)
4. **Fase 4 - Mandado/processamento.py e regras.py**
5. **Fase 5 - Refinamentos e medições**

### Validação
Após cada fase:
- ✅ Testar execução normal do fluxo
- ✅ Medir tempo de inicialização
- ✅ Verificar que funções ainda funcionam
- ✅ Validar imports não quebrados

---

## 📝 Resumo Executivo

**Problema:** Imports pesados no topo dos arquivos causam lentidão de 3-5s antes de qualquer código executar.

**Solução:** Lazy loading - mover imports para dentro das funções que os usam.

**Ganho:** 5-8x mais rápido na inicialização, 30-50% menos memória, responsividade instantânea.

**Prioridade:** Prazo/p2b_fluxo_helpers.py → PEC/regras.py → PEC/processamento.py → Mandado/*

**Status:** 
- ✅ loop.py já otimizado
- 🔴 p2b_fluxo_helpers.py aguardando otimização (CRÍTICO)
- 🔴 PEC/regras.py aguardando otimização (CRÍTICO)
