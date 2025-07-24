# PROJETO DE REFATORAÇÃO - BACEN.PY

## ANÁLISE DO CÓDIGO ATUAL

### Estatísticas
- **Total de linhas**: 2.556 linhas
- **Total de funções**: 47 funções
- **Arquivo monolítico**: Concentra toda a lógica de automação SISBAJUD/BACEN

### Principais Funcionalidades Identificadas

1. **Configuração e Inicialização**
   - CONFIG global com configurações do sistema
   - Drivers e perfis Firefox/Chrome
   - Configurações de cookies e sessão

2. **Interface PJe**
   - Injeção de botões no PJe
   - Eventos JavaScript
   - Integração com dados do processo

3. **Automação SISBAJUD**
   - Login automático via cookies/AHK
   - Navegação e preenchimento de formulários
   - Processamento de bloqueios e minutas

4. **Gestão de Dados**
   - Extração e persistência de dados de processo
   - Salvamento/carregamento de cookies
   - Integração com arquivos JSON

5. **Interface Kaizen**
   - Menu interativo injetado no SISBAJUD
   - Automações específicas (nova minuta, consultas, etc.)
   - Preenchimento automático de campos

## PROPOSTA DE REFATORAÇÃO

### Estrutura Modular Proposta

```
d:\PjePlus\
├── sisb.py                     # ORQUESTRADOR PRINCIPAL
├── sisb_modulos/
│   ├── __init__.py
│   ├── config.py              # Configurações e constantes
│   ├── drivers.py             # Gestão de drivers Firefox/Chrome
│   ├── cookies.py             # Operações com cookies
│   ├── interface_pje.py       # Interface e injeções no PJe
│   ├── dados_processo.py      # Gestão de dados do processo
│   ├── sisbajud_core.py       # Núcleo da automação SISBAJUD
│   ├── kaizen_interface.py    # Interface Kaizen injetada
│   ├── preenchimento.py       # Preenchimento de formulários
│   ├── bloqueios.py           # Processamento de bloqueios
│   ├── minutas.py             # Operações com minutas
│   └── utils.py               # Utilitários e helpers
```

### Detalhamento dos Módulos

#### 1. `sisb.py` (Orquestrador Principal) - ~100 linhas
- **Função**: Ponto de entrada principal
- **Responsabilidades**:
  - Importar todos os módulos necessários
  - Executar `main()` principal
  - Gerenciar fluxos de execução
  - Tratamento de exceções globais

#### 2. `sisb_modulos/config.py` - ~150 linhas
- **Função**: Configurações e constantes
- **Responsabilidades**:
  - CONFIG global
  - Configurações de cores, valores padrão
  - Constantes do sistema
  - Validação de configurações

#### 3. `sisb_modulos/drivers.py` - ~400 linhas
- **Função**: Gestão de drivers Selenium
- **Responsabilidades**:
  - `driver_firefox_sisbajud()`
  - `criar_driver_firefox_sisb()`
  - Configuração de perfis Firefox
  - Gestão de sessões de driver

#### 4. `sisb_modulos/cookies.py` - ~200 linhas
- **Função**: Operações com cookies
- **Responsabilidades**:
  - `salvar_cookies_sisbajud()`
  - `carregar_cookies_sisbajud()`
  - Filtragem e validação de cookies
  - Gestão de sessões

#### 5. `sisb_modulos/interface_pje.py` - ~300 linhas
- **Função**: Interface e injeções no PJe
- **Responsabilidades**:
  - `injetar_botao_sisbajud_pje()`
  - `bind_eventos()`
  - `checar_evento()`
  - `prompt_js()`
  - Integração com PJe

#### 6. `sisb_modulos/dados_processo.py` - ~250 linhas
- **Função**: Gestão de dados do processo
- **Responsabilidades**:
  - `salvar_dados_processo_temp()`
  - `carregar_dados_processo_temp()`
  - `integrar_storage_processo()`
  - Persistência de dados

#### 7. `sisb_modulos/sisbajud_core.py` - ~350 linhas
- **Função**: Núcleo da automação SISBAJUD
- **Responsabilidades**:
  - `abrir_sisbajud_em_firefox_sisbajud()`
  - `executar_driver_sisbajud()`
  - `aguardar_login_manual_sisbajud()`
  - `tentar_login_automatico_ahk()`
  - Login e navegação base

#### 8. `sisb_modulos/kaizen_interface.py` - ~400 linhas
- **Função**: Interface Kaizen injetada
- **Responsabilidades**:
  - `injetar_menu_kaizen_sisbajud()`
  - `checar_kaizen_evento()`
  - `aguardar_tela_minuta_e_injetar_menu()`
  - `processar_evento_kaizen()`
  - Menu interativo

#### 9. `sisb_modulos/preenchimento.py` - ~400 linhas
- **Função**: Preenchimento de formulários
- **Responsabilidades**:
  - `kaizen_preencher_campos()`
  - `_preencher_juiz_solicitante()`
  - `_preencher_vara_juizo()`
  - `_preencher_numero_processo()`
  - `_preencher_tipo_acao()`
  - `_preencher_cpf_autor()`
  - `_preencher_nome_autor()`
  - `_preencher_teimosinha()`
  - `_preencher_endereco_opcoes()`
  - `escolher_opcao_sisbajud()`
  - `escolher_opcao_sisbajud_avancado()`

#### 10. `sisb_modulos/bloqueios.py` - ~300 linhas
- **Função**: Processamento de bloqueios
- **Responsabilidades**:
  - `processar_bloqueios()`
  - `_aplicar_cores_status_bloqueio()`
  - `_buscar_linhas_jun_2025()`
  - Automação de bloqueios

#### 11. `sisb_modulos/minutas.py` - ~250 linhas
- **Função**: Operações com minutas
- **Responsabilidades**:
  - `minuta_bloqueio()`
  - `minuta_endereco()`
  - `kaizen_nova_minuta()`
  - `kaizen_consultar_minuta()`
  - `kaizen_consultar_teimosinha()`
  - `kaizen_consulta_rapida()`

#### 12. `sisb_modulos/utils.py` - ~200 linhas
- **Função**: Utilitários e helpers
- **Responsabilidades**:
  - `dados_login()`
  - `obter_caminho_autohotkey()`
  - `monitor_janela_sisbajud()`
  - `monitorar_driver_sisbajud()`
  - Funções auxiliares

## VANTAGENS DA REFATORAÇÃO

### 1. **Modularidade**
- Cada módulo tem responsabilidade específica
- Fácil manutenção e debug
- Código mais organizado

### 2. **Reutilização**
- Módulos podem ser importados individualmente
- Funcionalidades reutilizáveis
- Testes unitários mais fáceis

### 3. **Escalabilidade**
- Fácil adicionar novas funcionalidades
- Modificações isoladas por módulo
- Menos risco de quebrar funcionalidades

### 4. **Manutenibilidade**
- Código mais legível
- Debugging mais eficiente
- Documentação por módulo

## PLANO DE IMPLEMENTAÇÃO

### Fase 1: Preparação
1. Criar estrutura de pastas `sisb_modulos/`
2. Criar arquivo `__init__.py`
3. Backup do `bacen.py` original

### Fase 2: Extração de Módulos
1. Extrair configurações → `config.py`
2. Extrair drivers → `drivers.py`
3. Extrair cookies → `cookies.py`
4. Extrair interface PJe → `interface_pje.py`
5. Extrair dados processo → `dados_processo.py`
6. Extrair core SISBAJUD → `sisbajud_core.py`
7. Extrair interface Kaizen → `kaizen_interface.py`
8. Extrair preenchimento → `preenchimento.py`
9. Extrair bloqueios → `bloqueios.py`
10. Extrair minutas → `minutas.py`
11. Extrair utilitários → `utils.py`

### Fase 3: Criação do Orquestrador
1. Criar `sisb.py` com imports e main()
2. Manter compatibilidade com execução original
3. Preservar todas as funcionalidades

### Fase 4: Teste e Validação
1. Testar cada módulo individualmente
2. Testar integração completa
3. Validar compatibilidade com scripts existentes

## COMPATIBILIDADE

### Importações Mantidas
- Todas as importações originais serão mantidas
- Dependências externas inalteradas
- Compatibilidade com `Fix.py` e `driver_config.py`

### Funcionalidades Preservadas
- Todas as 47 funções originais
- Fluxos de execução idênticos
- Variáveis globais mantidas
- Configurações preservadas

### Execução
- `python sisb.py` → Execução completa
- `python -m sisb_modulos.minutas` → Módulo específico
- Importação: `from sisb_modulos import minutas`

## CRONOGRAMA ESTIMADO

- **Análise e Planejamento**: 1 dia ✅
- **Criação da Estrutura**: 1 dia
- **Extração de Módulos**: 3 dias
- **Criação do Orquestrador**: 1 dia
- **Testes e Validação**: 2 dias
- **Documentação**: 1 dia

**Total**: 8 dias úteis

## PRÓXIMOS PASSOS

1. **Aprovar o projeto** de refatoração
2. **Criar estrutura** de pastas e arquivos
3. **Iniciar extração** módulo por módulo
4. **Testar integração** continuamente
5. **Documentar** cada módulo

---

*Este projeto mantém 100% da funcionalidade original do bacen.py, apenas reorganizando o código em módulos menores e mais gerenciáveis.*
