# 🚀 Atualizador Unificado PjePlus v2.0

**UM ÚNICO ARQUIVO** para sincronização completa do projeto PjePlus entre múltiplas máquinas.
**Inclui resolução inteligente de conflitos integrada.**

## ⚡ Novo e Melhorado

- **📦 TUDO EM UM ARQUIVO**: Não precisa mais de `resolver_conflitos.bat`
- **🎯 5 MODOS COMPLETOS**: Desde instalação até resolução de conflitos
- **🧠 RESOLUÇÃO INTELIGENTE**: Estratégias automáticas por tipo de arquivo
- **⚡ ULTRA OTIMIZADO**: Baseado nas melhorias do auto_commit (sem GC lento)
- **� MENU INTERATIVO**: Execução contínua com opção de repetir

## 🎮 Como Usar

### Execução Simples
```bash
atualizador_unificado.bat
```

### Continuação Após Backup
```bash
# Na pasta raiz do projeto
proximos_passos.bat

# Ou diretamente
atualizar\continuar_atualizacao.bat
```

### 📋 Modos Disponíveis

| Modo | Tempo | Descrição |
|------|-------|-----------|
| **[1] RÁPIDO** ⚡ | 30s | Pull + backup simples |
| **[2] AVANÇADO** 🔧 | 2-5min | Commit + pull + resolução automática |
| **[3] CONFLITOS** �️ | 1-3min | Apenas resolução de conflitos existentes |
| **[4] SETUP** 📦 | 5-10min | Primeira instalação completa |
| **[5] RESET** 🛡️ | 1-2min | Reset forçado (perde mudanças locais) |

### 🔄 Scripts de Continuação

| Script | Uso | Descrição |
|--------|-----|-----------|
| **proximos_passos.bat** | Pasta raiz | Continua atualização após backup criado |
| **continuar_atualizacao.bat** | Pasta atualizar | Script de continuação detalhado |

## 🧠 Resolução Inteligente de Conflitos

### Estratégias Automáticas por Tipo:

| Tipo | Estratégia | Lógica |
|------|------------|--------|
| **`.py`** | Inteligente | Críticos (m1.py, main.py) → Local / Outros → Remoto |
| **`.json`** | Remoto | Configurações sempre atualizadas |
| **`.md`** | Remoto | Documentação sempre atualizada |
| **`.bat`** | Local | Scripts locais preservados |
| **`.txt`** | Merge | Tentativa de merge automático |
| **Outros** | Remoto | Padrão: versão remota |

### Resolução Manual Disponível:
- **Preferir todas versões remotas**
- **Preferir todas versões locais**  
- **Edição manual arquivo por arquivo**

## 🔧 Detecção Automática

- **📍 Auto-localização**: Detecta se está no diretório do projeto
- **⚙️ Configuração flexível**: Permite pasta customizada
- **🔍 Verificação inteligente**: Valida repositório Git antes de operar

## 📦 Backups Inteligentes

### Backup Rápido (Modo 1):
- Apenas arquivos essenciais: `*.py`, `*.json`, `*.bat`

### Backup Completo (Modos 2, 5):  
- Todos os arquivos exceto: `.git`, `backups`, `node_modules`, `__pycache__`

### Estrutura:
```
backups/
├── backup_rapido_YYYYMMDD_HHMMSS/
├── backup_avancado_YYYYMMDD_HHMMSS/
└── backup_reset_YYYYMMDD_HHMMSS/
```

## 🎯 Fluxo de Uso Recomendado

### 🏠 **Máquina Principal (Desenvolvimento)**
```bash
# Uso diário
[1] RÁPIDO

# Quando há mudanças locais importantes  
[2] AVANÇADO
```

### 💻 **Outras Máquinas (Sincronização)**
```bash
# Primeira vez
[4] SETUP

# Atualizações normais
[1] RÁPIDO

# Quando há conflitos
[3] CONFLITOS
```

### 🚨 **Situações de Emergência**
```bash
# Quando tudo deu errado
[5] RESET
```

### 🔄 **Continuação de Processo**
```bash
# Quando o backup já foi criado e você precisa continuar
proximos_passos.bat
```

## ✨ Otimizações Implementadas

### � Performance
- **Removido**: `git gc --aggressive` (super lento)
- **Mantido**: `git gc --auto` (rápido e inteligente)
- **Otimizado**: Backups seletivos por necessidade
- **Melhorado**: Menu responsivo e reutilizável

### 🧠 Inteligência
- **Estratégias por tipo de arquivo**
- **Detecção automática de arquivos críticos**
- **Resolução de conflitos em cascata**
- **Fallback para resolução manual**

### �️ Segurança  
- **Backup antes de qualquer operação destrutiva**
- **Confirmações para operações perigosas**
- **Preservação de arquivos críticos**
- **Histórico completo de operações**

## 🚨 Resolução de Problemas

| Problema | Solução |
|----------|---------|
| "Não é repositório Git" | Use **[4] SETUP** |
| "Conflitos de merge" | Use **[3] CONFLITOS** |
| "Muitas mudanças locais" | Use **[2] AVANÇADO** ou **[5] RESET** |
| "Erro de conexão" | Verifique internet e URL |

---

**🎉 RESULTADO: Resolução de conflitos 100% integrada em um único arquivo otimizado!**

**⚡ Baseado nas otimizações do auto_commit.bat - sem compressão lenta desnecessária**