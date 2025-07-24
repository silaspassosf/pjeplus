# Projeto de Refatoração - listaexec2.py

## Análise do Arquivo Original

**Arquivo:** `listaexec2.py`
**Total de linhas:** 3,166 linhas
**Objetivo:** Dividir em arquivos menores (máximo 450 linhas cada) mantendo exatamente a mesma execução

## Estrutura Atual Identificada

### Funções Principais (3 funções top-level):
1. `buscar_medidas_executorias()` - Linhas 8-135 (128 linhas)
2. `salvar_alvaras_processados_no_arquivo()` - Linhas 136-179 (44 linhas) 
3. `listaexec()` - Linhas 180-3235 (3056 linhas) - **FUNÇÃO GIGANTE**

### Análise da Função `listaexec()`:
A função `listaexec()` contém várias sub-funções aninhadas que podem ser extraídas:

#### Sub-funções identificadas dentro de `listaexec()`:
- `alvara()` - Processa alvarás individuais
- `extrair_dados_alvara()` - Extrai dados específicos do alvará
- `normalizar_data()` - Normaliza datas
- `extrair_autor_processo()` - Extrai autor do processo
- `normalizar_nome()` - Normaliza nomes para comparação
- `converter_valor_para_float()` - Converte valores
- `formatar_valor_brasileiro()` - Formata valores
- `salvar_dados_alvara()` - Salva dados no arquivo
- `pagamento()` - Lógica de pagamentos (com suas próprias sub-funções)
- Várias outras funções auxiliares

## Projeto de Divisão Simples

### Estrutura Proposta (6 arquivos):

```
listaexec.py                    # Arquivo principal (≤450 linhas)
├── buscar_medidas.py          # Busca de medidas (≤450 linhas)
├── alvara_core.py             # Funções principais de alvará (≤450 linhas)
├── alvara_utils.py            # Utilitários de alvará (≤450 linhas)
├── pagamento.py               # Lógica de pagamentos (≤450 linhas)
└── file_utils.py              # Funções de arquivo (≤450 linhas)
```

### Conteúdo de Cada Arquivo:

#### 1. `listaexec.py` (Principal)
```python
# Importações
import re, json, time
from datetime import datetime
from selenium.webdriver.common.by import By
from Fix import extrair_documento, criar_gigs

# Importar funções dos módulos
from buscar_medidas import buscar_medidas_executorias
from alvara_core import processar_alvara
from pagamento import processar_pagamentos
from file_utils import salvar_alvaras_processados_no_arquivo

def listaexec(driver, log=True):
    """Função principal - apenas orchestração"""
    try:
        # 1. Buscar medidas
        medidas = buscar_medidas_executorias(driver, log)
        
        # 2. Processar alvarás encontrados
        alvaras_processados = []
        for medida in medidas:
            if 'alvará' in medida['nome'].lower():
                resultado = processar_alvara(driver, medida, log)
                if resultado:
                    alvaras_processados.append(resultado)
        
        # 3. Processar pagamentos se houver alvarás
        if alvaras_processados:
            processar_pagamentos(driver, alvaras_processados, log)
        
        return medidas
        
    except Exception as e:
        if log:
            print(f'[LISTA-EXEC][ERRO] {e}')
        return []
```

#### 2. `buscar_medidas.py`
```python
# Contém apenas a função buscar_medidas_executorias()
# Linhas 8-135 do arquivo original
# ~128 linhas
```

#### 3. `alvara_core.py`
```python
# Contém a função principal alvara() e funções relacionadas:
# - processar_alvara() (renomeada de alvara())
# - extrair_dados_alvara()
# - processar_modal_extração()
# ~400-450 linhas
```

#### 4. `alvara_utils.py`
```python
# Contém funções utilitárias de alvará:
# - normalizar_data()
# - extrair_autor_processo()
# - normalizar_nome()
# - converter_valor_para_float()
# - formatar_valor_brasileiro()
# - salvar_dados_alvara()
# ~300-400 linhas
```

#### 5. `pagamento.py`
```python
# Contém toda a lógica de pagamentos:
# - processar_pagamentos() (função principal)
# - todas as sub-funções de pagamento do original
# - funções de análise e comparação
# ~400-450 linhas
```

#### 6. `file_utils.py`
```python
# Contém funções de arquivo:
# - salvar_alvaras_processados_no_arquivo() (já existe)
# - outras funções de I/O se necessário
# ~100-200 linhas
```

## Plano de Execução

### Passo 1: Extrair buscar_medidas.py
- Copiar função `buscar_medidas_executorias()` (linhas 8-135)
- Manter imports necessários

### Passo 2: Extrair file_utils.py  
- Copiar função `salvar_alvaras_processados_no_arquivo()` (linhas 136-179)

### Passo 3: Dividir a função listaexec() gigante
- Identificar onde começam e terminam as sub-funções
- Extrair para alvara_core.py, alvara_utils.py, pagamento.py
- Manter apenas a orchestração no listaexec.py principal

### Passo 4: Ajustar imports
- Cada arquivo tem apenas os imports que precisa
- Arquivo principal importa das outras funções

### Passo 5: Testar
- Garantir que `from listaexec import listaexec` funciona igual

## Princípios da Refatoração

1. **ZERO mudanças de lógica** - apenas mover código
2. **Manter exata mesma interface** - `listaexec(driver, log=True)`
3. **Preservar todos os imports originais** onde necessário
4. **Não alterar nomes de funções internas** (apenas extrair)
5. **Cada arquivo ≤ 450 linhas**
6. **Fácil de testar** - substituir `listaexec2.py` por `listaexec.py`

## Resultado Esperado

```python
# Uso continua idêntico:
from listaexec import listaexec
resultado = listaexec(driver, log=True)
# Funciona exatamente igual ao listaexec2.py
```

**Benefícios:**
- Código organizado em módulos lógicos
- Arquivos menores e mais gerenciáveis  
- Facilita manutenção futura
- Zero impacto na funcionalidade existente
