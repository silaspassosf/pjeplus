# 📊 Mapeamento de Funções - Fix/core.py

**Arquivo:** Fix/core.py  
**Linhas:** 2915  
**Total de Funções:** 52  
**Data:** 29/01/2026

---

## 🎯 Objetivo

Este documento mapeia todas as funções de `Fix/core.py` e as organiza por categoria de responsabilidade, preparando o terreno para a refatoração granular.

---

## 📦 Categorias de Responsabilidade

### 🔵 1. Selenium Base - Operações de Espera (→ selenium_base/wait_operations.py)

**Responsabilidade:** Esperar elementos ficarem disponíveis/visíveis/clicáveis

| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `wait()` | 44 | Espera genérica por elemento | ⭐⭐⭐ |
| `wait_for_visible()` | 63 | Espera elemento ficar visível | ⭐⭐⭐ |
| `wait_for_clickable()` | 84 | Espera elemento ficar clicável | ⭐⭐⭐ |
| `esperar_elemento()` | 288 | Espera elemento com texto opcional | ⭐⭐⭐ |
| `aguardar_e_clicar()` | 366 | **MAIS USADA** - Aguarda e clica | ⭐⭐⭐⭐⭐ |
| `esperar_url_conter()` | 2248 | Espera URL conter substring | ⭐⭐ |

**Total:** 6 funções  
**Linhas estimadas:** ~200 linhas

---

### 🔵 2. Selenium Base - Interação com Elementos (→ selenium_base/element_interaction.py)

**Responsabilidade:** Clicar, preencher, interagir com elementos

| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `safe_click()` | 105 | Clique com tratamento de erros | ⭐⭐⭐⭐ |
| `preencher_campo()` | 973 | Preenche input com eventos JS | ⭐⭐⭐⭐ |
| `_clicar_botao_movimentar()` | 463 | Clica botão "Movimentar" PJe | ⭐⭐ |
| `_clicar_botao_tarefa_processo()` | 504 | Clica botão tarefas | ⭐⭐ |
| `_tentar_click_padrao()` | 2766 | Estratégia click padrão | ⭐ |
| `_tentar_click_javascript()` | 2784 | Estratégia click JS | ⭐ |
| `_tentar_click_actionchains()` | 2800 | Estratégia ActionChains | ⭐ |
| `_tentar_click_javascript_avancado()` | 2817 | Estratégia JS avançada | ⭐ |

**Total:** 8 funções  
**Linhas estimadas:** ~250 linhas

---

### 🔵 3. Selenium Base - Retry Logic (→ selenium_base/retry_logic.py)

**Responsabilidade:** Lógica de retry e busca robusta

| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `com_retry()` | 1167 | **Decorator** para retry automático | ⭐⭐⭐⭐ |
| `buscar_seletor_robusto()` | 212 | Busca seletor com fallbacks | ⭐⭐⭐⭐ |

**Total:** 2 funções  
**Linhas estimadas:** ~150 linhas

---

### 🔵 4. Selenium Base - Seleção Inteligente (→ selenium_base/smart_selection.py)

**Responsabilidade:** Seleção de dropdowns e estratégias inteligentes

| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `selecionar_opcao()` | 609 | Seleciona opção em dropdown | ⭐⭐⭐⭐ |
| `escolher_opcao_inteligente()` | 1220 | Seleção com múltiplas estratégias | ⭐⭐⭐ |
| `encontrar_elemento_inteligente()` | 1268 | Busca com estratégias fallback | ⭐⭐⭐ |

**Total:** 3 funções  
**Linhas estimadas:** ~200 linhas

---

### 🟢 5. Drivers - Criação e Gestão (→ drivers/)

**Responsabilidade:** Criar e gerenciar WebDrivers Chrome

#### drivers/config_pc.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `criar_driver_PC()` | 1485 | Cria driver Chrome para PC | ⭐⭐⭐⭐ |
| `criar_driver_sisb_pc()` | 1574 | Cria driver SISB (PC) | ⭐⭐⭐ |

#### drivers/config_vt.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `criar_driver_VT()` | 1520 | Cria driver Chrome para VT | ⭐⭐⭐ |

#### drivers/config_notebook.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `criar_driver_notebook()` | 1543 | Cria driver para notebook | ⭐⭐ |
| `criar_driver_sisb_notebook()` | 1638 | Cria driver SISB (notebook) | ⭐⭐ |

#### drivers/lifecycle.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `finalizar_driver()` | 1663 | Finaliza driver e libera recursos | ⭐⭐⭐ |

**Total:** 6 funções  
**Linhas estimadas:** ~400 linhas (dividido em 4 arquivos)

---

### 🟡 6. Session - Cookies e Autenticação (→ session/)

**Responsabilidade:** Gestão de sessões, cookies e login

#### session/cookies_manager.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `salvar_cookies_sessao()` | 1694 | Salva cookies em JSON | ⭐⭐⭐ |
| `carregar_cookies_sessao()` | 1831 | Carrega cookies de JSON | ⭐⭐⭐ |

#### session/session_validator.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `verificar_e_aplicar_cookies()` | 1903 | Verifica e aplica cookies | ⭐⭐⭐ |

#### session/auth.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `credencial()` | 1724 | **PRINCIPAL** - Gerencia credenciais e login | ⭐⭐⭐⭐⭐ |

**Total:** 4 funções  
**Linhas estimadas:** ~300 linhas (dividido em 3 arquivos)

---

### 🟠 7. Navigation - Filtros e Navegação (→ navigation/)

**Responsabilidade:** Aplicar filtros e navegar no PJe

#### navigation/filters.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `aplicar_filtro_100()` | 1998 | Aplica filtro 100 processos | ⭐⭐⭐ |
| `filtro_fase()` | 2049 | Aplica filtro de fase | ⭐⭐⭐ |

#### navigation/phase_filter.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `filtrofases()` | 2104 | Filtro complexo de fases | ⭐⭐⭐⭐ |

**Total:** 3 funções  
**Linhas estimadas:** ~250 linhas (dividido em 2 arquivos)

---

### 🔴 8. Documents - Extração de Documentos (→ documents/)

**Responsabilidade:** Buscar e extrair documentos do PJe

#### documents/sequential_search.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `buscar_documentos_sequenciais()` | 2571 | Busca docs sequenciais | ⭐⭐⭐⭐ |

#### documents/search_by_pole.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `buscar_documentos_polo_ativo()` | 2660 | Busca docs polo ativo (v1) | ⭐⭐⭐ |
| `buscar_documentos_polo_ativo()` | 2848 | Busca docs polo ativo (v2 - **DUPLICADO**) | ⚠️ |

#### documents/mandado_search.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `buscar_ultimo_mandado()` | 2441 | Busca último mandado | ⭐⭐ |
| `buscar_mandado_autor()` | 2486 | Busca mandado do autor | ⭐⭐ |
| `buscar_documento_argos()` | 2965 | Busca documento Argos | ⭐⭐⭐ |

#### documents/validation.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `verificar_documento_decisao_sentenca()` | 2270 | Verifica se é decisão/sentença | ⭐⭐ |

**Total:** 7 funções (1 duplicada - precisa consolidar)  
**Linhas estimadas:** ~400 linhas (dividido em 4 arquivos)

---

### 🟣 9. Forms - Formulários (→ forms/)

**Responsabilidade:** Preencher campos e formulários

#### forms/prazo_fields.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `preencher_campos_prazo()` | 1051 | Preenche campos de prazo (dias) | ⭐⭐⭐⭐ |

#### forms/multiple_fields.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `preencher_multiplos_campos()` | 1084 | Preenche dict de campos | ⭐⭐⭐ |

**Total:** 2 funções  
**Linhas estimadas:** ~150 linhas (dividido em 2 arquivos)

---

### 🟤 10. UI Helpers - Helpers de Interface (→ ui_helpers/)

**Responsabilidade:** Helpers específicos de UI PJe

#### ui_helpers/sigilo.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `visibilidade_sigilosos()` | 2289 | Gerencia visibilidade dados sigilosos | ⭐⭐⭐ |

#### ui_helpers/buttons.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `criar_botoes_detalhes()` | 2381 | Cria botões de detalhes | ⭐ |

**Total:** 2 funções  
**Linhas estimadas:** ~150 linhas (dividido em 2 arquivos)

---

### ⚪ 11. Utils - Utilitários Gerais (→ utils_refactored/)

**Responsabilidade:** Logging, config, helpers

#### utils_refactored/logging.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `_log_info()` | 29 | Log informação | ⭐⭐ |
| `_log_error()` | 33 | Log erro | ⭐⭐ |
| `_audit()` | 37 | Log auditoria | ⭐ |

#### utils_refactored/config.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `exibir_configuracao_ativa()` | 1979 | Exibe config ativa | ⭐ |

#### utils_refactored/timing.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `smart_sleep()` | 3193 | Sleep inteligente | ⭐ |
| `sleep()` | 3196 | Sleep simples | ⭐ |

#### utils_refactored/helpers.py
| Função | Linha | Descrição | Prioridade |
|--------|-------|-----------|------------|
| `js_base()` | 1393 | Scripts JS base | ⭐⭐ |

**Total:** 7 funções  
**Linhas estimadas:** ~200 linhas (dividido em 4 arquivos)

---

### 📊 12. Classes Auxiliares

#### utils_refactored/collectors.py
| Classe/Função | Linha | Descrição | Prioridade |
|---------------|-------|-----------|------------|
| `ErroCollector` | 1300 | Coletor de erros | ⭐ |
| `SimpleConfig` | 3168 | Config simples | ⭐ |

**Total:** 2 classes  
**Linhas estimadas:** ~100 linhas

---

## 📈 Resumo por Categoria

| Categoria | Funções | Arquivos Alvo | Linhas Est. | Prioridade |
|-----------|---------|---------------|-------------|------------|
| **Selenium Base** | 19 | 4 arquivos | ~800 | ⭐⭐⭐⭐⭐ |
| **Drivers** | 6 | 4 arquivos | ~400 | ⭐⭐⭐⭐ |
| **Session** | 4 | 3 arquivos | ~300 | ⭐⭐⭐⭐ |
| **Navigation** | 3 | 2 arquivos | ~250 | ⭐⭐⭐ |
| **Documents** | 7 | 4 arquivos | ~400 | ⭐⭐⭐⭐ |
| **Forms** | 2 | 2 arquivos | ~150 | ⭐⭐⭐ |
| **UI Helpers** | 2 | 2 arquivos | ~150 | ⭐⭐ |
| **Utils** | 9 | 5 arquivos | ~300 | ⭐⭐ |
| **TOTAL** | **52** | **26 arquivos** | **~2750** | - |

**Nota:** Linhas totais estimadas (~2750) são menores que as originais (2915) porque:
- Eliminação de duplicação
- Remoção de comentários excessivos
- Código mais conciso e focado

---

## 🚨 Problemas Identificados

### 1. Duplicação de Código
- `buscar_documentos_polo_ativo()` aparece **2 vezes** (linhas 2660 e 2848)
- **AÇÃO:** Consolidar em uma única implementação

### 2. Funções Privadas Inconsistentes
- Algumas funções começam com `_` (privadas) mas são usadas externamente
- **AÇÃO:** Revisar e decidir quais devem ser públicas

### 3. Responsabilidades Mal Distribuídas
- `credencial()` faz **muita coisa** (linha 1724) - mais de 100 linhas
- **AÇÃO:** Considerar quebrar em sub-funções

---

## 🎯 Ordem de Implementação Recomendada

### Fase 1: Base Foundation (Dia 1-2)
1. ✅ **selenium_base/** - Mais usadas, base de tudo
   - wait_operations.py
   - element_interaction.py
   - retry_logic.py
   - smart_selection.py

### Fase 2: Infrastructure (Dia 2-3)
2. ✅ **drivers/** - Criação de drivers
   - factory.py
   - config_pc.py
   - config_vt.py
   - lifecycle.py

3. ✅ **session/** - Sessões e auth
   - auth.py
   - cookies_manager.py
   - session_validator.py

### Fase 3: Features (Dia 3-4)
4. ✅ **navigation/** - Filtros
5. ✅ **documents/** - Extração docs
6. ✅ **forms/** - Formulários

### Fase 4: Cleanup (Dia 4-5)
7. ✅ **ui_helpers/** - UI específica
8. ✅ **utils_refactored/** - Utilitários
9. ✅ Atualizar **Fix/__init__.py** - API pública

---

## 📋 Checklist de Refatoração

### Por Arquivo a Criar:
- [ ] Criar arquivo com docstring padronizada
- [ ] Copiar funções relacionadas
- [ ] Ajustar imports internos
- [ ] Remover dependências desnecessárias
- [ ] Adicionar type hints
- [ ] Adicionar testes unitários (opcional)
- [ ] Atualizar __init__.py da categoria
- [ ] Atualizar Fix/__init__.py (API pública)
- [ ] Atualizar INDEX.md com nova localização

---

## 🔗 Dependências Entre Categorias

```
selenium_base/  (BASE - sem dependências internas)
    ↓
drivers/  (usa selenium_base indiretamente)
    ↓
session/  (usa selenium_base)
    ↓
navigation/  (usa selenium_base)
    ↓
documents/  (usa selenium_base, navigation)
    ↓
forms/  (usa selenium_base)
    ↓
ui_helpers/  (usa selenium_base)
```

**Regra de Ouro:** Dependências sempre de cima para baixo. NUNCA circular.

---

## 📝 Template de Docstring para Arquivos Novos

```python
"""
@module: Fix.{categoria}.{arquivo}
@responsibility: {Descrição clara da responsabilidade}
@depends_on: {Lista de dependências}
@used_by: {Quem usa este módulo}
@entry_points: {Funções principais}
@tags: #{tag1} #{tag2} #{tag3}
@created: 2026-01-29
@refactored_from: Fix/core.py lines {inicio}-{fim}
"""
```

---

**Última Atualização:** 29/01/2026  
**Status:** ✅ Mapeamento Completo  
**Próximo Passo:** Iniciar extração fase 1 (selenium_base/)
