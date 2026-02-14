# Módulo Prazo - Sistema de Processamento de Prazos PJe

## 📋 Visão Geral

O **Módulo Prazo** é um sistema modularizado para processamento automatizado de prazos no sistema PJe (Poder Judiciário Eletrônico). Resultado de uma refatoração completa seguindo o guia unificado de otimização IA.

## 🏗️ Arquitetura

### Estrutura do Módulo
```
Prazo/
├── __init__.py           # Interface principal do módulo
├── p2b_core.py          # Utilitários e constantes (280 linhas)
├── p2b_fluxo.py         # Orchestrator fluxo_pz (362 linhas)
├── p2b_prazo.py         # Funções fluxo_prazo (276 linhas)
├── p2b_fluxo_helpers.py # Helpers especializados (316 linhas)
└── loop.py              # Loop principal de execução
```

### Padrão de Design
- **Orchestrator + Helpers**: Separação clara entre coordenação e execução
- **Modularização**: Cada arquivo < 500 linhas
- **Type Hints**: Documentação completa com tipos
- **Responsabilidade Única**: Cada módulo tem propósito específico

## 📊 Métricas de Refatoração

| Aspecto | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| **fluxo_pz** | 761 linhas | 40 linhas | **95% redução** |
| **fluxo_prazo** | 149 linhas | 35 linhas | **77% redução** |
| **Aninhamento** | 6 níveis | 2 níveis | **67% redução** |
| **Arquivos** | 1 monolítico | 5 especializados | **Modularização** |

## 🚀 Como Usar

### Execução Completa (Loop + P2B)
```bash
# Método 1: Via módulo Python
py -m Prazo

# Método 2: Via script executável
py executar_prazo.py

# Método 3: Importando no código
from Prazo import executar_loop_principal
executar_loop_principal()
```

### Fluxo de Execução Integrado
```
main() → loop_prazo(driver) → fluxo_prazo(driver) → fluxo_pz(driver)
  │              │                    │                    │
  │              │                    │                    └─ Processa documento individual
  │              │                    └─ Itera lista de processos
  │              └─ Processamento em lote (Painéis 14 e 8)
  └─ Configuração inicial (driver + login)
```

### Uso das Funções Principais
```python
# Processamento de prazo individual
from Prazo import fluxo_pz
fluxo_pz(driver)

# Processamento em lote
from Prazo import fluxo_prazo
fluxo_prazo(driver)

# Loop completo integrado
from Prazo import executar_loop_principal
executar_loop_principal()  # Loop → Prazo completo
```

### Utilitários Disponíveis
```python
from Prazo import (
    normalizar_texto, gerar_regex_geral, parse_gigs_param,
    carregar_progresso_p2b, marcar_processo_executado_p2b
)
```

## 🔧 Dependências

- **Fix**: Utilitários Selenium e automação
- **atos**: Ações processuais
- **carta**: Cartas precatórias
- **pje**: Funções específicas do PJe
- **progresso_unificado**: Sistema de progresso

## ✅ Validações

- ✅ Sintaxe Python válida
- ✅ Imports funcionais
- ✅ Limite 500 linhas por arquivo
- ✅ Padrão Orchestrator + Helpers
- ✅ Type hints completos
- ✅ Documentação Google Style

## 📝 Funcionalidades

### fluxo_pz()
- Extração de texto de documentos
- Análise de regras de negócio
- Criação de GIGS parametrizadas
- Execução de atos processuais
- Fechamento automático de abas

### fluxo_prazo()
- Indexação de processos da lista
- Filtragem de processos já executados
- Processamento em lote otimizado
- Gerenciamento de abas múltiplas
- Tratamento de erros robusto
- **Chama fluxo_pz() para cada processo**

### executar_loop_principal() (main)
- **Loop completo integrado: loop.py → p2b**
- Configuração inicial (driver + login)
- Loop contínuo de processamento em lote:
  - Painel 14 (Análise)
  - Painel 8 (Cumprimento de providências)
- **Executa fluxo_prazo() ao final**
- Monitoramento de progresso
- Tratamento de interrupções
- Logging detalhado

## 🛠️ Desenvolvimento

### Adicionando Novas Regras
1. Adicionar regex em `REGEX_PATTERNS` (p2b_core.py)
2. Criar helper em módulo apropriado
3. Registrar na função de processamento

### Testando Mudanças
```bash
# Validar sintaxe
py -m py_compile Prazo/*.py

# Testar imports
py -c "from Prazo import fluxo_pz, fluxo_prazo"
```

## 📈 Benefícios da Refatoração

- **Manutenibilidade**: Código mais fácil de entender e modificar
- **Testabilidade**: Funções isoladas facilitam testes unitários
- **Reutilização**: Componentes modulares podem ser reutilizados
- **Performance**: Redução de complexidade ciclomática
- **Escalabilidade**: Arquitetura preparada para novas funcionalidades

## 🔄 Migração

Para migrar código existente que usava `p2b.py`:
```python
# Antes
from p2b import fluxo_pz, fluxo_prazo

# Depois
from Prazo import fluxo_pz, fluxo_prazo
```

## 📚 Referências

- [Guia de Refatoração IA Unificado](GUIA_REFATORACAO_IA_UNIFICADO_v2.md)
- [Análise de Otimização AI](ANALISE_OTIMIZACAO_AI.md)
- [Relatório de Consolidação](RELATORIO_CONSOLIDACAO_FIX.txt)

---

**Versão**: 2.0.0
**Data**: Novembro 2025
**Refatoração**: Completa com IA</content>
<parameter name="filePath">d:\PjePlus\Prazo\README.md