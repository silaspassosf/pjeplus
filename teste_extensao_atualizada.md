# Teste da Extensão Restricted Copilot Atualizada

## Verificações:

### 1. Contexto expandido para 300 linhas
- Teste: Selecionar código e usar @x no chat
- Esperado: Análise de até 300 linhas

### 2. Diretrizes PjePlus mantidas
- ❌ Não criar arquivos de teste
- ❌ Não criar relatórios
- ✅ PowerShell apenas (py script.py)

### 3. Comportamento restrito mantido
- 🔒 Modo Restritivo: SEMPRE ATIVO
- ❓ Modo Inquisitivo: SEMPRE ATIVO

## Como testar:
1. Abrir um arquivo Python (.py)
2. Selecionar uma função grande (100+ linhas)
3. Usar @x no chat: "analise esta função"
4. Verificar se analisa até 300 linhas
5. Tentar pedir criação de arquivo de teste (deve ser bloqueado)

## Status:
✅ Extensão reinstalada: pjeplus.restricted-copilot
✅ Contexto: 50 → 300 linhas
✅ Diretrizes PjePlus: Mantidas
✅ Atalho: @x ativo
