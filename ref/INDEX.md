# 🗺️ PJePlus - Índice de Navegação Rápida

**Versão:** 1.0  
**Data:** 29 de Janeiro de 2026  
**Propósito:** Localização instantânea de código para manutenção assistida por IA

---

## 📋 Como Usar Este Índice

**Para IA/Copilot:**
1. Busque a função desejada por nome ou descrição
2. Veja o caminho exato do arquivo
3. Consulte dependências e casos de uso
4. Leia apenas o arquivo específico (reduz tokens em 90%)

**Para Desenvolvedores:**
- Use Ctrl+F para buscar função/conceito
- Veja contexto completo antes de editar
- Consulte dependências para entender impacto

---

## 🎯 Módulos Principais

### 🔧 Fix - Utilitários Selenium & PJe Core
**📁 Localização:** `/Fix/`  
**🎯 Propósito:** Funções base para automação Selenium e interação com PJe  
**📊 Status:** 🔴 CRÍTICO - Precisa refatoração (core.py: 2915 linhas)  
**🏷️ Tags:** `#selenium` `#webdriver` `#pje-core` `#utilities`

#### 📄 Fix/core.py (237 linhas) - ✅ REFATORADO

**Status:** ✅ **CONCLUÍDO** - Convertido para wrapper
**Funções delegadas:**
- `wait*` → `Fix.selenium_base.wait_operations`
- `safe_click`, `aguardar_e_clicar` → `Fix.selenium_base.element_interaction`
- `selecionar_opcao`, `preencher_*` → `Fix.extracao`
- `buscar_*` → `Fix.documents.search`
- `smart_sleep`, `sleep` → `Fix.utils`

**Compatibilidade:** ✅ Wrapper mantém todas as APIs originais
- `escolher_opcao_inteligente()` - Seleção com múltiplas estratégias
- `encontrar_elemento_inteligente()` - Busca com estratégias fallback

**Grupo 4: Retry Logic**
- `com_retry()` - Decorator para retry automático com backoff

**Grupo 5: Drivers**
- `criar_driver_PC()` - Cria driver Chrome para PC (headless opcional)
- [NOTA: Outras funções criar_driver_* em outros arquivos]

**Grupo 6: Botões Específicos PJe**
- `_clicar_botao_movimentar()` - Clica botão "Movimentar"
- `_clicar_botao_tarefa_processo()` - Clica botão tarefas

**Grupo 7: JavaScript Helpers**
- `js_base()` - Scripts JS base para manipulação DOM

**📦 Dependências:**
- `selenium.webdriver`
- `selenium.webdriver.common.by`
- `selenium.webdriver.support.ui`

**🔗 Usado por:** Praticamente todos os módulos (Prazo, PEC, SISB, Mandado, atos)

**🎯 Casos de Uso:**
```python
# Clique robusto com retry automático
from Fix.core import aguardar_e_clicar
aguardar_e_clicar(driver, "#botao-salvar")

# Preenchimento de campo com eventos
from Fix.core import preencher_campo
preencher_campo(driver, "input[name='prazo']", "30")

# Seleção inteligente em dropdown
from Fix.core import selecionar_opcao
selecionar_opcao(driver, "#tipo-ato", "Despacho")
```

---

#### 📄 Fix/extracao.py (160 linhas) - ✅ REFATORADO

**Status:** ✅ **CONCLUÍDO** - Convertido para wrapper
**Funções delegadas:**
- `safe_click`, `aguardar_e_clicar` → `Fix.selenium_base.element_interaction`
- `selecionar_opcao`, `preencher_*` → `Fix.selenium_base.element_interaction`
- `com_retry` → `Fix.selenium_base.retry_logic`
- GIGS functions → `Fix.gigs`

**Compatibilidade:** ✅ Wrapper mantém todas as APIs originais

#### 📄 Fix/utils.py (106 linhas) - ✅ REFATORADO

**Status:** ✅ **CONCLUÍDO** - Dividido em 9 módulos especializados
- **utils_error.py** (80 linhas) - `ErroCollector` classe e métodos
- **utils_formatting.py** (120 linhas) - Formatação de dados
- **utils_login.py** (150 linhas) - Autenticação e login
- **utils_cookies.py** (60 linhas) - Gerenciamento de cookies
- **utils_drivers.py** (100 linhas) - Criação de drivers
- **utils_collect.py** (120 linhas) - Coleta de dados
- **utils_sleep.py** (120 linhas) - Esperas e sleeps
- **utils_angular.py** (100 linhas) - Funções Angular
- **utils_selectors.py** (150 linhas) - Seletores CSS

**Compatibilidade:** ✅ Wrapper mantém todas as APIs originais

#### 📄 atos/judicial.py (118 linhas) - ✅ REFATORADO

**Status:** ✅ **CONCLUÍDO** - Convertido para wrapper
**Funções delegadas:** `ato_judicial`, `make_ato_wrapper` → módulos especializados

#### 📄 atos/comunicacao.py (209 linhas) - ✅ REFATORADO

**Status:** ✅ **CONCLUÍDO** - Convertido para wrapper
**Funções delegadas:** Funções de comunicação → módulos especializados

#### 📄 atos/movimentos.py (13 linhas) - ✅ REFATORADO

**Status:** ✅ **CONCLUÍDO** - Arquivo de imports
**Imports de:** `movimentos_fluxo`, `movimentos_sobrestamento`, etc.

---

### ⏱️ Prazo - Processamento de Prazos em Lote
**📁 Localização:** `/Prazo/`  
**🎯 Propósito:** Automação de análise e processamento de prazos processuais  
**📊 Status:** 🟡 MODERADO - loop.py precisa refatoração (1253 linhas)  
**🏷️ Tags:** `#prazos` `#batch` `#decisao` `#gigs`

#### 📄 Prazo/loop.py (1253 linhas) - ARQUIVO PRINCIPAL
[TODO: Mapear entry points]

#### 📄 Prazo/p2b_prazo.py
**Entry Points:**
- `fluxo_prazo()` - Fluxo principal de processamento
- `aplicar_filtro_atividades_xs()` - Aplica filtro de atividades
- `_indexar_processos_lista()` - Indexa processos da lista
- `_filtrar_processos_nao_executados()` - Filtra já executados
- `_processar_lista_processos()` - Processa lista completa
- `_processar_processo_individual()` - Processa um processo

**📦 Dependências:** Fix, atos
**🔗 Usado por:** Loop principal de prazos

---

#### 📄 Prazo/p2b_fluxo_helpers.py (902 linhas)
**Entry Points:**
- `_encontrar_documento_relevante()` - Busca documento de decisão
- `_extrair_texto_documento()` - Extrai texto de documento

---

#### 📄 Prazo/prov.py (750 linhas)
**Entry Points:**
- `criar_driver()` - Cria driver (VT ou PC)
- `fluxo_prov()` - Fluxo de providências
- `navegacao_prov()` - Navegação específica prov
- `selecionar_e_processar()` - Seleciona processos
- `aplicar_xs_e_registrar()` - Aplica XS e registra

---

### 📋 PEC - Processamento de Petições (Workflow)
**📁 Localização:** `/PEC/`  
**🎯 Propósito:** Orquestração e workflow de processamento de petições  
**📊 Status:** 🟡 MODERADO - processamento.py e regras.py precisam refatoração  
**🏷️ Tags:** `#workflow` `#processamento` `#orquestracao` `#peticao`

#### 📄 PEC/processamento.py (1622 linhas)
[TODO: Mapear entry points]

#### 📄 PEC/regras.py (1615 linhas)
[TODO: Mapear entry points]

#### 📄 PEC/carta.py (990 linhas)
[TODO: Mapear entry points]

#### 📁 PEC/anexos/ (Subpasta)
**📄 PEC/anexos/core.py** (1284 linhas - movido de anexos.py)
- Processamento e validação de anexos
- [TODO: Quebrar em arquivos menores]

---

### 📝 Peticao - Análise de Petições Eletrônicas (NOVO)
**📁 Localização:** `/Peticao/`  
**🎯 Propósito:** Análise e triagem de petições iniciais trabalhistas  
**📊 Status:** 🔴 CRÍTICO - Consolidação pendente (pet2 vs pet_novo)  
**🏷️ Tags:** `#peticao` `#analise` `#competencia` `#emenda`

#### ⚠️ PROBLEMA: Duplicação Crítica
- `pet.py` - Versão original
- `pet2.py` (1690 linhas) - Versão intermediária
- `pet_novo.py` (1626 linhas) - Versão mais recente
- **~80% código duplicado entre pet2 e pet_novo**
- **AÇÃO:** Consolidar em arquitetura unificada (fase futura)

**Nota:** Módulo isolado para facilitar refatoração posterior

---

### 🏛️ atos - Atos Judiciais e Comunicações
**📁 Localização:** `/atos/`  
**🎯 Propósito:** Wrappers para criação de atos judiciais e comunicações processuais  
**📊 Status:** ✅ **REFATORADO** - judicial.py (118 linhas), comunicacao.py (209 linhas)  
**🏷️ Tags:** `#ato` `#minuta` `#comunicacao` `#judicial`

#### 📄 atos/judicial.py (118 linhas) - ✅ REFATORADO

**Status:** ✅ **CONCLUÍDO** - Convertido para wrapper
**Funções delegadas:** `ato_judicial`, `make_ato_wrapper` → módulos especializados

#### 📄 atos/comunicacao.py (209 linhas) - ✅ REFATORADO

**Status:** ✅ **CONCLUÍDO** - Convertido para wrapper
**Funções delegadas:** Funções de comunicação → módulos especializados

#### 📄 atos/movimentos.py (13 linhas) - ✅ REFATORADO

**Status:** ✅ **CONCLUÍDO** - Arquivo de imports
**Imports de:** `movimentos_fluxo`, `movimentos_sobrestamento`, etc.
**Entry Points:**
- `fluxo_cls()` - Fluxo de conclusão
- `esperar_insercao_modelo()` - Aguarda inserção de modelo
- `ato_judicial()` - **[FUNÇÃO PRINCIPAL]** Cria ato judicial
- `make_ato_wrapper()` - Factory para criar wrappers de atos

**🎯 Casos de Uso:**
```python
from atos.judicial import ato_judicial
# Cria ato judicial com modelo específico
ato_judicial(driver, conclusao_tipo="Despacho", modelo_nome="Despacho Intimação")
```

---

#### 📄 atos/comunicacao.py (1386 linhas)
[TODO: Mapear entry points]

#### 📄 atos/movimentos.py (1092 linhas)
**Entry Points:**
- `mov_simples()` - Movimento simples
- `mov()` - Movimento genérico completo
- `mov_arquivar()` - Movimento de arquivamento
- `mov_exec()` - Movimento de execução
- `mov_aud()` - Movimento de audiência
- `mov_prazo()` - Movimento de prazo
- `mov_sob()` - Movimento de sobrestamento
- `mov_fimsob()` - Movimento fim sobrestamento
- `def_chip()` - Definição CHIP
- `despacho_generico()` - Despacho genérico

---

#### 📄 atos/wrappers_ato.py (418 linhas)
**Entry Points:**
- `_inserir_relatorio_conciso_sisbajud()` - Insere relatório SISBAJUD em ato

---

#### 📄 atos/wrappers_utils.py
**Entry Points:**
- `visibilidade_sigilosos()` - Gerencia visibilidade de dados sigilosos
- `executar_visibilidade_sigilosos_se_necessario()` - Executa se necessário

---

### 💰 SISB - Integração com SISBAJUD
**📁 Localização:** `/SISB/`  
**🎯 Propósito:** Integração com SISBAJUD para bloqueio judicial  
**📊 Status:** 🔴 CRÍTICO - helpers.py com 3551 linhas (MAIOR ARQUIVO)  
**🏷️ Tags:** `#sisbajud` `#bloqueio` `#judicial` `#api`

#### 📄 SISB/helpers.py (3551 linhas) - 🚨 MAIOR ARQUIVO DO PROJETO 🚨
**7+ RESPONSABILIDADES MISTURADAS:**

**Grupo 1: Validação**
- `_validar_dados()` - Valida dados do processo

**Grupo 2: Preenchimento Formulário**
- `_preencher_campos_iniciais()` - Preenche campos iniciais
- `_processar_reus_otimizado()` - Processa lista de réus

**Grupo 3: Minuta**
- `_salvar_minuta()` - Salva minuta
- `_gerar_relatorio_minuta()` - Gera relatório de minuta
- `_protocolar_minuta()` - Protocola minuta
- `_criar_minuta_agendada_por_copia()` - Cria minuta por cópia
- `_criar_minuta_agendada()` - Cria minuta agendada

**Grupo 4: Ordens e Séries**
- `_carregar_dados_ordem()` - Carrega dados de ordem
- `_filtrar_series()` - Filtra séries por data
- `_voltar_para_lista_ordens_serie()` - Navegação volta
- `_voltar_para_lista_principal()` - Navegação principal
- `_navegar_e_extrair_ordens_serie()` - Navega e extrai
- `_extrair_ordens_da_serie()` - Extrai ordens

**Grupo 5: Fluxos e Ações**
- `_aplicar_acao_por_fluxo()` - Aplica ação por tipo fluxo

**Grupo 6: Bloqueios**
- `_identificar_ordens_com_bloqueio()` - Identifica bloqueios
- `_agrupar_dados_bloqueios()` - Agrupa dados
- `extrair_dados_bloqueios_processados()` - **[PÚBLICA]** Extrai dados
- `gerar_relatorio_bloqueios_processados()` - **[PÚBLICA]** Gera relatório completo
- `gerar_relatorio_bloqueios_conciso()` - **[PÚBLICA]** Gera relatório conciso

**🎯 Funções Públicas (API):**
```python
from SISB.helpers import (
    extrair_dados_bloqueios_processados,
    gerar_relatorio_bloqueios_processados,
    gerar_relatorio_bloqueios_conciso
)
```

---

#### 📄 SISB/utils.py (1490 linhas) - PRECISA REFATORAÇÃO ⚠️
[TODO: Mapear funções]

#### 📄 SISB/processamento.py (1480 linhas) - PRECISA REFATORAÇÃO ⚠️
[TODO: Mapear funções]

#### 📄 SISB/core.py (1107 linhas) - PRECISA REFATORAÇÃO ⚠️
[TODO: Mapear funções]

---

### 📜 Mandado - Processamento de Mandados
**📁 Localização:** `/Mandado/`  
**🎯 Propósito:** Processamento de mandados judiciais (Argos, oficial justiça)  
**📊 Status:** 🟡 MODERADO - processamento.py (1138 linhas)  
**🏷️ Tags:** `#mandado` `#oficial-justica` `#argos` `#pesquisa-patrimonial`

#### 📄 Mandado/processamento.py (1138 linhas)
**Entry Points:**
- `_identificar_tipo_anexo()` - Identifica tipo de anexo
- `_aguardar_icone_plus()` - Aguarda ícone plus (sigilo)
- `_buscar_icone_plus_direto()` - Busca direta ícone
- `_localizar_modal_visibilidade()` - Localiza modal
- `_processar_modal_visibilidade()` - Processa modal
- `_extrair_resultado_sisbajud()` - Extrai resultado SISB

---

#### 📄 Mandado/regras.py (420 linhas)
**Entry Points:**
- `estrategia_defiro_instauracao()` - Regra: deferimento instauração
- `estrategia_despacho_argos()` - Regra: despacho Argos
- `estrategia_infojud()` - Regra: Infojud
- `estrategia_decisao_manifestar()` - Regra: decisão manifestar
- `estrategia_tendo_em_vista_que()` - Regra: tendo em vista
- `aplicar_regras_argos()` - **[PRINCIPAL]** Aplica todas regras

---

#### 📄 Mandado/utils.py (690 linhas)
**Entry Points:**
- `lembrete_bloq()` - Cria lembrete de bloqueio
- `fechar_intimacao()` - Fecha intimação
- `retirar_sigilo()` - Remove sigilo de documento
- `retirar_sigilo_fluxo_argos()` - Remove sigilo fluxo Argos
- `retirar_sigilo_certidao_devolucao_primeiro()` - Sigilo certidão
- `retirar_sigilo_demais_documentos_especificos()` - Sigilo docs específicos
- `retirar_sigilo_documentos_especificos()` - Sigilo docs

---

## 🔍 Busca Rápida por Conceito

### Selenium / WebDriver
- **Criar driver:** `Fix.core.criar_driver_PC()`, `Prazo.prov.criar_driver()`
- **Clicar elemento:** `Fix.core.aguardar_e_clicar()`, `Fix.core.safe_click()`
- **Esperar elemento:** `Fix.core.wait()`, `Fix.core.esperar_elemento()`
- **Preencher campo:** `Fix.core.preencher_campo()`
- **Selecionar dropdown:** `Fix.core.selecionar_opcao()`

### Atos Judiciais
- **Criar ato:** `atos.judicial.ato_judicial()`
- **Criar movimento:** `atos.movimentos.mov()`
- **Sigilo:** `atos.wrappers_utils.visibilidade_sigilosos()`

### SISBAJUD
- **Extrair bloqueios:** `SISB.helpers.extrair_dados_bloqueios_processados()`
- **Gerar relatório:** `SISB.helpers.gerar_relatorio_bloqueios_processados()`
- **Relatório conciso:** `SISB.helpers.gerar_relatorio_bloqueios_conciso()`

### Prazos
- **Processar prazos:** `Prazo.p2b_prazo.fluxo_prazo()`
- **Providências:** `Prazo.prov.fluxo_prov()`

### Mandados
- **Aplicar regras Argos:** `Mandado.regras.aplicar_regras_argos()`
- **Retirar sigilo:** `Mandado.utils.retirar_sigilo()`

---

## 📊 Estatísticas do Projeto

### Arquivos Problemáticos (>500 linhas)

| Prioridade | Arquivo | Linhas | Status |
|-----------|---------|--------|--------|
| 🔴 CRÍTICO | SISB/helpers.py | 3551 | Precisa dividir em 8-10 arquivos |
| ✅ CONCLUÍDO | Fix/core.py | 237 | Refatorado (wrapper) |
| ✅ CONCLUÍDO | Fix/extracao.py | 160 | Refatorado (wrapper) |
| ✅ CONCLUÍDO | Fix/utils.py | 106 | Dividido em 9 módulos |
| ✅ CONCLUÍDO | atos/judicial.py | 118 | Refatorado (wrapper) |
| ✅ CONCLUÍDO | PEC/pet2.py | 1690 | **DUPLICADO** - movido p/ Peticao/ |
| ✅ CONCLUÍDO | PEC/pet_novo.py | 1626 | **DUPLICADO** - movido p/ Peticao/ |
| ✅ CONCLUÍDO | PEC/processamento.py | 62 | Refatorado (wrapper) |
| ✅ CONCLUÍDO | PEC/regras.py | 57 | Refatorado (wrapper) |
| 🟡 MODERADO | SISB/utils.py | 1490 | Precisa refatoração |
| 🟡 MODERADO | SISB/processamento.py | 842 | Precisa refatoração |
| ✅ CONCLUÍDO | atos/comunicacao.py | 209 | Refatorado (wrapper) |
| 🟡 MODERADO | PEC/anexos/core.py | 1284 | Movido de anexos.py |

**Total:** 21 arquivos precisam refatoração (33% do projeto)

**Nota:** pet.py, pet2.py, pet_novo.py movidos para módulo Peticao separado; anexos.py → PEC/anexos/core.py

---

## 🎯 Roadmap de Refatoração

### Fase 1: Preparação ✅
- [x] Criar INDEX.md
- [x] Criar project_manifest.json
- [ ] Criar README.md por módulo
- [ ] Mapear todas as funções

### Fase 2: Fix (PRIORIDADE) ✅
- [x] Dividir core.py → selenium_base/, drivers/, session/ (wrapper criado)
- [x] Dividir extracao.py → documents/, gigs/ (wrapper criado)
- [x] Dividir utils.py → 9 módulos especializados (utils_*.py)
- [x] Atualizar Fix/__init__.py

### Fase 3: atos ✅
- [x] Refatorar judicial.py, comunicacao.py, movimentos.py (wrappers criados)

### Fase 4: PEC ✅
- [x] Consolidar pet2.py + pet_novo.py (movidos para Peticao/)
- [x] Dividir regras.py, processamento.py (wrappers criados)

### Fase 5: Prazo ✅
- [x] Dividir loop.py → 6 módulos especializados

### Fase 6: SISB 🔄
- [ ] Dividir helpers.py → validation/, extraction/, transformation/, etc.
- [ ] Refatorar processamento.py (842 linhas restantes)

---

## 📝 Convenções

### Nomenclatura de Arquivos
- `val_*.py` → Validador
- `ext_*.py` → Extrator
- `ui_*.py` → Interface UI
- `api_*.py` → Cliente API
- `rule_*.py` → Regra de negócio
- `flow_*.py` → Fluxo/Workflow

### Tamanho Alvo
- **Ideal:** 100-200 linhas
- **Máximo:** 300 linhas
- **Atual:** Média de 620 linhas 😱

---

**Última Atualização:** 29/01/2026  
**Mantido por:** GitHub Copilot (Claude Sonnet 4.5)  
**Versão:** 1.0 - Inicial (mapeamento parcial)

---

## 🚨 ATENÇÃO PARA IA/COPILOT

**Quando procurar uma função:**
1. ✅ Consulte ESTE arquivo primeiro (50 tokens)
2. ✅ Vá direto ao arquivo indicado (500 tokens)
3. ❌ NÃO leia arquivos aleatoriamente (8000 tokens desperdiçados)

**Economia esperada:** -90% de tokens por operação
