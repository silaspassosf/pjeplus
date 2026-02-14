# 🔧 Módulo Fix - Utilitários Selenium & PJe Core

**Versão:** 1.0  
**Data:** 29 de Janeiro de 2026  
**Status:** 🔴 CRÍTICO - Refatoração Urgente

---

## 📋 Visão Geral

O módulo **Fix** é a camada fundamental do PJePlus, fornecendo utilitários base para automação Selenium e interação com o sistema PJe. É usado por **todos os outros módulos** do projeto.

### Responsabilidades
- ✅ Operações Selenium base (espera, clique, preenchimento)
- ✅ Criação e gestão de WebDrivers
- ✅ Gestão de sessões e cookies
- ✅ Navegação e filtros PJe
- ✅ Extração de documentos
- ✅ Sistema GIGS (atividades)
- ✅ Formulários e campos

### Módulos Dependentes
- **Prazo** - Usa drivers, selenium base, gigs
- **PEC** - Usa drivers, selenium base, documentos
- **SISB** - Usa drivers, selenium base, formulários
- **Mandado** - Usa drivers, selenium base, documentos
- **atos** - Usa drivers, selenium base

---

## 🚨 Problema Atual

### Estado Crítico
O módulo Fix está com **7.055 linhas** distribuídas em apenas **4 arquivos principais**:

| Arquivo | Linhas | Responsabilidades | Status |
|---------|--------|-------------------|--------|
| **core.py** | 2915 | **7 responsabilidades misturadas** | 🔴 CRÍTICO |
| **extracao.py** | 2127 | Documentos, BNDT, GIGS, indexação | 🔴 CRÍTICO |
| **utils.py** | 2013 | Utilitários diversos, formatação | 🔴 CRÍTICO |
| **variaveis.py** | 897 | Constantes, configurações | 🟡 MODERADO |

### Responsabilidades Misturadas em core.py

**O arquivo core.py (2915 linhas) viola o Single Responsibility Principle ao misturar:**

1. 🔵 **Selenium Base** (wait, click, fill) → selenium_base/
2. 🟢 **Criação de Drivers** → drivers/
3. 🟡 **Sessões e Cookies** → session/
4. 🟠 **Navegação e Filtros** → navigation/
5. 🔴 **Documentos** → documents/
6. 🟣 **Autenticação** → session/
7. 🟤 **GIGS** → gigs/

### Impacto na Manutenção por IA

**Problema:**
- IA precisa ler 2915 linhas para encontrar 1 função
- Consome 8000-12000 tokens só para localizar código
- Tempo de localização: 5-10 minutos

**Solução:**
- Dividir em 31 arquivos especializados
- IA consulta INDEX.md (50 tokens) e vai direto ao arquivo
- Tempo de localização: 30-60 segundos ✅

---

## 🎯 Arquitetura Proposta (Pós-Refatoração)

```
Fix/
├── __init__.py                         # Public API (100 linhas)
├── README.md                           # Este arquivo
│
├── selenium_base/                      # 🔵 Operações Selenium fundamentais
│   ├── __init__.py
│   ├── wait_operations.py              # 150 linhas
│   │   └── wait(), wait_for_visible(), wait_for_clickable()
│   │       aguardar_e_clicar(), esperar_elemento()
│   │
│   ├── element_interaction.py          # 180 linhas
│   │   └── safe_click(), preencher_campo()
│   │       scroll_para_elemento(), get_element_text()
│   │
│   ├── retry_logic.py                  # 120 linhas
│   │   └── com_retry() [decorator]
│   │       buscar_seletor_robusto()
│   │
│   └── smart_selection.py              # 150 linhas
│       └── selecionar_opcao()
│           escolher_opcao_inteligente()
│           encontrar_elemento_inteligente()
│
├── drivers/                            # 🟢 Gestão de drivers
│   ├── __init__.py
│   ├── factory.py                      # 200 linhas
│   │   └── criar_driver() [Factory pattern]
│   │       get_driver_config()
│   │
│   ├── config_pc.py                    # 100 linhas
│   │   └── criar_driver_PC()
│   │       get_chrome_options_pc()
│   │
│   ├── config_vt.py                    # 100 linhas
│   │   └── criar_driver_VT()
│   │       get_chrome_options_vt()
│   │
│   ├── config_sisb.py                  # 100 linhas
│   │   └── criar_driver_SISB()
│   │
│   └── lifecycle.py                    # 80 linhas
│       └── finalizar_driver()
│           cleanup_driver_resources()
│
├── session/                            # 🟡 Gestão de sessão e cookies
│   ├── __init__.py
│   ├── cookies_manager.py              # 120 linhas
│   │   └── salvar_cookies_sessao()
│   │       carregar_cookies_sessao()
│   │
│   ├── session_validator.py            # 100 linhas
│   │   └── verificar_e_aplicar_cookies()
│   │       validar_sessao()
│   │
│   └── auth.py                         # 150 linhas
│       └── credencial()
│           login_cpf()
│           fazer_login()
│
├── navigation/                         # 🟠 Navegação e filtros
│   ├── __init__.py
│   ├── filters.py                      # 180 linhas
│   │   └── aplicar_filtro_100()
│   │       filtro_fase()
│   │
│   ├── phase_filter.py                 # 250 linhas
│   │   └── filtrofases()
│   │
│   └── url_helpers.py                  # 80 linhas
│       └── esperar_url_conter()
│           verificar_url_mudou()
│
├── documents/                          # 🔴 Manipulação de documentos
│   ├── __init__.py
│   ├── extraction.py                   # 200 linhas
│   │   └── extrair_documento()
│   │       extrair_texto_completo()
│   │
│   ├── sequential_search.py            # 150 linhas
│   │   └── buscar_documentos_sequenciais()
│   │
│   ├── bndt.py                         # 180 linhas
│   │   └── BNDT_apagar()
│   │       BNDT_operacoes()
│   │
│   └── indexing.py                     # 150 linhas
│       └── indexar_documentos()
│           criar_indice_documentos()
│
├── gigs/                               # 🟣 Sistema GIGS
│   ├── __init__.py
│   ├── creator.py                      # 200 linhas
│   │   └── criar_gigs()
│   │       validar_dados_gigs()
│   │
│   ├── minuta.py                       # 150 linhas
│   │   └── gigs_minuta()
│   │       gerar_minuta_gigs()
│   │
│   ├── validator.py                    # 120 linhas
│   │   └── validar_gigs()
│   │
│   └── templates.py                    # 100 linhas
│       └── get_template_observacao()
│           templates_predefinidos()
│
├── forms/                              # 🟤 Manipulação de formulários
│   ├── __init__.py
│   ├── prazo_fields.py                 # 150 linhas
│   │   └── preencher_campos_prazo()
│   │
│   ├── multiple_fields.py              # 120 linhas
│   │   └── preencher_multiplos_campos()
│   │
│   └── validators.py                   # 100 linhas
│       └── validar_campo()
│           validar_formulario()
│
└── utils/                              # ⚪ Utilitários gerais
    ├── __init__.py
    ├── formatters.py                   # 150 linhas
    │   └── formatar_data()
    │       formatar_cpf()
    │       formatar_cnpj()
    │
    ├── parsers.py                      # 120 linhas
    │   └── parse_numero_processo()
    │       parse_valor_monetario()
    │
    ├── constants.py                    # 80 linhas
    │   └── TIMEOUTS, SELETORES, URLS
    │
    └── helpers.py                      # 100 linhas
        └── funções auxiliares gerais
```

---

## 📊 Resultado Esperado

### Métricas

| Métrica | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| **Número de arquivos** | 4 | 31 | +675% |
| **Total de linhas** | 7055 | ~4500 | -36% (elimina duplicação) |
| **Linhas por arquivo (média)** | 1764 | 145 | **-92%** ✅ |
| **Arquivo maior** | 2915 | 250 | **-91%** ✅ |
| **Tokens IA (localização)** | 8000-12000 | 500-2000 | **-85%** ✅ |
| **Tempo localização** | 5-10 min | 30-60s | **-90%** ✅ |

### Benefícios

✅ **Single Responsibility Principle** - Cada arquivo tem 1 responsabilidade clara  
✅ **Fácil manutenção por IA** - Localização instantânea via INDEX.md  
✅ **Testabilidade** - Arquivos pequenos são mais fáceis de testar  
✅ **Reusabilidade** - Componentes bem definidos podem ser reutilizados  
✅ **Baixo acoplamento** - Dependências claras e unidirecionais  
✅ **Alta coesão** - Funções relacionadas agrupadas logicamente  

---

## 🔧 API Pública (Fix/__init__.py)

### Compatibilidade Reversa

O arquivo `__init__.py` manterá a API pública atual funcionando, importando das novas localizações:

```python
# Fix/__init__.py - Public API

# Selenium Base Operations
from .selenium_base.wait_operations import (
    wait,
    wait_for_visible,
    wait_for_clickable,
    aguardar_e_clicar,
    esperar_elemento
)

from .selenium_base.element_interaction import (
    safe_click,
    preencher_campo,
    scroll_para_elemento
)

from .selenium_base.retry_logic import (
    com_retry,
    buscar_seletor_robusto
)

from .selenium_base.smart_selection import (
    selecionar_opcao,
    escolher_opcao_inteligente,
    encontrar_elemento_inteligente
)

# Drivers
from .drivers.factory import criar_driver
from .drivers.config_pc import criar_driver_PC
from .drivers.config_vt import criar_driver_VT
from .drivers.lifecycle import finalizar_driver

# Session & Auth
from .session.auth import credencial, login_cpf
from .session.cookies_manager import (
    salvar_cookies_sessao,
    carregar_cookies_sessao
)

# Documents
from .documents.extraction import extrair_documento
from .documents.sequential_search import buscar_documentos_sequenciais
from .documents.bndt import BNDT_apagar

# GIGS
from .gigs.creator import criar_gigs
from .gigs.minuta import gigs_minuta

# Forms
from .forms.prazo_fields import preencher_campos_prazo
from .forms.multiple_fields import preencher_multiplos_campos

# Navigation
from .navigation.filters import aplicar_filtro_100, filtro_fase
from .navigation.phase_filter import filtrofases

# Mantém imports antigos funcionando:
# from Fix import aguardar_e_clicar  ← CONTINUA FUNCIONANDO
```

### Código Cliente Não Precisa Mudar

```python
# Código existente continua funcionando
from Fix import aguardar_e_clicar, safe_click, criar_driver_PC

# Novo código pode usar imports específicos (opcional)
from Fix.selenium_base.wait_operations import aguardar_e_clicar
from Fix.drivers.config_pc import criar_driver_PC
```

---

## 📝 Funções Principais

### 🔵 Selenium Base

#### aguardar_e_clicar()
```python
def aguardar_e_clicar(
    driver, 
    seletor, 
    log=False, 
    timeout=10, 
    by=By.CSS_SELECTOR, 
    usar_js=True, 
    retornar_elemento=False, 
    debug=None
) -> Optional[WebElement]:
    """
    Aguarda elemento ficar clicável e clica nele.
    Função mais usada do projeto.
    
    Args:
        driver: WebDriver do Selenium
        seletor: Seletor CSS/XPATH do elemento
        log: Se True, loga operação
        timeout: Tempo máximo de espera (segundos)
        by: Tipo de seletor (By.CSS_SELECTOR, By.XPATH)
        usar_js: Se True, usa JavaScript para clicar
        retornar_elemento: Se True, retorna o elemento
        
    Returns:
        WebElement se retornar_elemento=True, None caso contrário
    """
```

**Usado por:** Todos os módulos  
**Localização após refatoração:** `Fix/selenium_base/wait_operations.py`

---

#### safe_click()
```python
def safe_click(
    driver, 
    selector_or_element, 
    timeout=10, 
    by=None, 
    log=False
) -> bool:
    """
    Clica em elemento com tratamento de erros e retry automático.
    
    Args:
        driver: WebDriver
        selector_or_element: Seletor CSS ou WebElement
        timeout: Timeout em segundos
        by: Tipo de seletor
        log: Se True, loga operação
        
    Returns:
        True se clicou com sucesso, False caso contrário
    """
```

**Localização após refatoração:** `Fix/selenium_base/element_interaction.py`

---

#### com_retry()
```python
def com_retry(
    func, 
    max_tentativas=3, 
    backoff_base=2, 
    log=False, 
    *args, 
    **kwargs
) -> Any:
    """
    Decorator para retry automático com backoff exponencial.
    
    Args:
        func: Função a ser executada
        max_tentativas: Número máximo de tentativas
        backoff_base: Base para backoff exponencial
        log: Se True, loga tentativas
        
    Returns:
        Resultado da função se sucesso
        
    Raises:
        Exception: Se todas as tentativas falharem
    """
```

**Localização após refatoração:** `Fix/selenium_base/retry_logic.py`

---

### 🟢 Drivers

#### criar_driver_PC()
```python
def criar_driver_PC(headless=False) -> WebDriver:
    """
    Cria driver Chrome configurado para PC.
    
    Args:
        headless: Se True, executa em modo headless
        
    Returns:
        WebDriver configurado
    """
```

**Localização após refatoração:** `Fix/drivers/config_pc.py`

---

### 🟡 Session & Auth

#### login_cpf()
```python
def login_cpf(driver, cpf=None, senha=None) -> bool:
    """
    Faz login no PJe usando CPF e senha.
    
    Args:
        driver: WebDriver
        cpf: CPF para login (opcional, usa credencial() se None)
        senha: Senha (opcional)
        
    Returns:
        True se login bem-sucedido
    """
```

**Localização após refatoração:** `Fix/session/auth.py`

---

### 🔴 Documents

#### extrair_documento()
```python
def extrair_documento(driver, link_documento) -> str:
    """
    Extrai texto completo de documento PJe.
    
    Args:
        driver: WebDriver
        link_documento: Link/elemento do documento
        
    Returns:
        Texto extraído do documento
    """
```

**Localização após refatoração:** `Fix/documents/extraction.py`

---

### 🟣 GIGS

#### criar_gigs()
```python
def criar_gigs(
    driver, 
    tipo_atividade, 
    observacao, 
    prazo_dias=None
) -> bool:
    """
    Cria atividade GIGS no PJe.
    
    Args:
        driver: WebDriver
        tipo_atividade: Tipo da atividade
        observacao: Texto da observação
        prazo_dias: Prazo em dias (opcional)
        
    Returns:
        True se criou com sucesso
    """
```

**Localização após refatoração:** `Fix/gigs/creator.py`

---

## 🔗 Dependências

### Externas
- `selenium` - WebDriver e automação browser
- `selenium.webdriver.common.by` - Tipos de seletores
- `selenium.webdriver.support.ui` - WebDriverWait
- `selenium.webdriver.support.expected_conditions` - Condições de espera

### Internas
- **Nenhuma** (Fix é a camada base)

---

## 🎯 Casos de Uso Típicos

### Caso 1: Clicar em botão com retry
```python
from Fix import aguardar_e_clicar

# Aguarda botão e clica (com retry automático)
aguardar_e_clicar(driver, "#botao-salvar", timeout=15)
```

### Caso 2: Preencher formulário
```python
from Fix import preencher_campo, preencher_campos_prazo

# Preencher campo texto
preencher_campo(driver, "input[name='observacao']", "Texto aqui")

# Preencher campos de prazo
preencher_campos_prazo(driver, valor=30)
```

### Caso 3: Selecionar dropdown
```python
from Fix import selecionar_opcao

# Seleciona opção em dropdown
selecionar_opcao(driver, "#tipo-ato", "Despacho", exato=True)
```

### Caso 4: Criar driver e fazer login
```python
from Fix import criar_driver_PC, login_cpf

# Cria driver
driver = criar_driver_PC(headless=False)

# Faz login
login_cpf(driver)
```

### Caso 5: Extrair documento
```python
from Fix import extrair_documento

# Extrai texto de documento
texto = extrair_documento(driver, link_documento)
```

---

## 🚀 Plano de Implementação

### Fase 1: Preparação ✅
- [x] Criar README.md (este arquivo)
- [x] Criar INDEX.md global
- [ ] Criar templates de docstring
- [ ] Mapear todas as funções de core.py

### Fase 2: Estrutura de Pastas
- [ ] Criar estrutura de diretórios
- [ ] Criar arquivos __init__.py
- [ ] Criar arquivos vazios com docstrings

### Fase 3: Extração (core.py → múltiplos arquivos)
- [ ] Extrair funções selenium_base
- [ ] Extrair funções drivers
- [ ] Extrair funções session
- [ ] Extrair funções navigation
- [ ] Atualizar imports

### Fase 4: Extração (extracao.py, utils.py)
- [ ] Extrair funções documents
- [ ] Extrair funções gigs
- [ ] Extrair funções forms
- [ ] Extrair funções utils

### Fase 5: Integração
- [ ] Atualizar Fix/__init__.py (API pública)
- [ ] Atualizar imports em Prazo, PEC, SISB, Mandado, atos
- [ ] Testes de regressão

### Fase 6: Validação
- [ ] Executar testes completos
- [ ] Verificar performance
- [ ] Documentação final

---

## ⚠️ Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Quebrar código existente | Média | Alto | Manter compatibilidade reversa via __init__.py |
| Imports circulares | Baixa | Alto | Arquitetura em camadas, Fix não importa nada interno |
| Performance degradada | Baixa | Médio | Lazy loading, benchmarks |
| Tempo maior que estimado | Média | Médio | Fases incrementais, pode parar a qualquer momento |

---

## 📚 Referências

- [Análise Arquitetura Projeto](../ANALISE_ARQUITETURA_PROJETO.md)
- [Prompt Copilot](../prompt_copilot_pjplus.md)
- [INDEX.md](../INDEX.md)
- [project_manifest.json](../project_manifest.json)

---

**Última Atualização:** 29/01/2026  
**Mantido por:** GitHub Copilot (Claude Sonnet 4.5)  
**Versão:** 1.0
