# Restricted Copilot - Auto Compile & Fix

Esta versão do Restricted Copilot inclui funcionalidade de **compilação automática** que permite detectar e corrigir erros diretamente no terminal usando PowerShell.

## 🔧 Nova Funcionalidade: Auto-Compile & Fix

### Como Funciona

1. **Detecção Automática de Erros**: A extensão monitora logs de erro do workspace PjePlus
2. **Compilação Automática**: Executa comandos de validação adequados para cada tipo de arquivo
3. **Foco Automático**: Navega automaticamente para a linha do erro detectado
4. **Integração com Chat**: Oferece correções via @restricted no chat

### Comandos de Compilação Suportados

#### Python (.py)
```powershell
python -m py_compile "arquivo.py"
python -c "import ast; ast.parse(open('arquivo.py').read())"
```

#### JavaScript (.js)
```powershell
node --check "arquivo.js"
```

#### TypeScript (.ts)
```powershell
npx tsc --noEmit "arquivo.ts"
```

#### AutoHotkey (.ahk)
- Validação básica com mensagem informativa

### Como Usar

#### 1. Compilação Manual
- **Botão Direito** no editor → "🔧 Compile & Validate Current File"
- **Command Palette** (Ctrl+Shift+P) → "Restricted Copilot: Compile & Validate Current File"

#### 2. Detecção Automática
- A extensão monitora automaticamente logs de erro:
  - `pje_automacao.log`
  - `pje_automation.log`
  - `erro_fatal_selenium.log`
- Quando detecta erro, foca na linha correspondente
- Oferece opções: "Auto-Compile & Fix", "Analisar com @restricted", "Ignorar"

### Fluxo de Auto-Fix

1. **Erro Detectado** → Notificação aparece
2. **Escolha "Auto-Compile & Fix"** → Executa compilação automática
3. **Se há erros** → Foca na primeira linha com erro
4. **Análise com @restricted** → Use o chat para correção específica

### Exemplo de Uso no PjePlus

1. Abra `bacen.py` ou qualquer arquivo Python
2. Introduza um erro intencional (ex: `print(variavel_inexistente)`)
3. Clique direito → "🔧 Compile & Validate Current File"
4. A extensão detectará o erro e focará na linha
5. Use @restricted no chat para análise e correção

### Comandos PowerShell Utilizados

A extensão usa PowerShell para evitar problemas com `&&` e outros operadores:

```powershell
# Em vez de: python arquivo.py && echo "OK"
python arquivo.py
echo "OK"
```

### Integração com Terminal

- **Monitoramento**: Verifica logs a cada 3 segundos
- **Detecção de Padrões**: Reconhece erros Python, JavaScript, TypeScript e Selenium
- **Foco Automático**: Abre arquivo e navega para linha do erro
- **Chat Integration**: Conecta diretamente com @restricted para correções

### Configurações

As mesmas configurações do Restricted Copilot se aplicam:

```json
{
  "restrictedCopilot.restrictiveMode": true,
  "restrictedCopilot.inquisitiveMode": true,
  "restrictedCopilot.maxContextLines": 50
}
```

### Exemplo Prático

```python
# bacen.py com erro intencional
def processar_bacen():
    dados = obter_dados()
    print(variavel_inexistente)  # ← Erro aqui
    return dados
```

**Fluxo:**
1. Executar compilação manual ou detectar no log
2. Extensão foca na linha 3
3. Notificação: "🔴 ERRO DETECTADO: NameError: name 'variavel_inexistente' is not defined"
4. Opções: "Auto-Compile & Fix" | "Analisar com @restricted" | "Ignorar"
5. Use @restricted no chat: "Corrija este erro de variável"

---

## 🎯 Benefícios

- **Detecção Proativa**: Encontra erros antes da execução
- **Navegação Inteligente**: Leva direto à linha do problema
- **Correção Assistida**: Integração perfeita com chat @restricted
- **Suporte Multi-linguagem**: Python, JS, TS, AHK
- **PowerShell Otimizado**: Compatível com Windows/VS Code

## 📝 Próximos Passos

1. Teste a funcionalidade com seus arquivos Python do PjePlus
2. Use @restricted no chat para correções específicas
3. Aproveite a detecção automática de erros em logs
