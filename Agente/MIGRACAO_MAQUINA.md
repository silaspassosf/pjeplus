# GUIA: Migração para Outra Máquina

## 📤 PASSO 1: Preparar na Máquina Atual

### Commit dos arquivos da extensão
```bash
cd "d:\PjePlus"
git add Agente/
git commit -m "feat: Restricted Copilot com Auto-Compile implementado

- Adicionada compilação automática para Python, JS, TS
- Detecção automática de erros em terminal/logs  
- Foco automático na linha do erro
- Integração completa com chat @restricted
- PowerShell otimizado para Windows
- Interface completa com menus contextuais"

git push origin main
```

### Arquivos que serão commitados:
```
PjePlus/Agente/
├── src/
│   ├── extension.ts
│   ├── terminalErrorDetector.ts  
│   ├── autoCompiler.ts
├── package.json
├── README.md
├── AUTO_COMPILE_GUIDE.md
├── IMPLEMENTACAO_CONCLUIDA.md
├── configuracao_pjeplus.json
├── instalar_extensao.bat
├── testar_auto_compile.bat
├── restricted-copilot-0.0.1.vsix (arquivo compilado)
└── dist/ (arquivos compilados)
```

## 📥 PASSO 2: Setup na Máquina Nova

### 1. Clone do repositório
```bash
git clone [seu-repo-pjeplus]
cd PjePlus
```

### 2. **OBRIGATÓRIO: Instalar a extensão**
```bash
cd Agente
code --install-extension restricted-copilot-0.0.1.vsix --force
```

### 3. **OPCIONAL: Recompilar (se necessário)**
```bash
npm install
npm run compile
npx vsce package
```

## ⚠️ **IMPORTANTE: Por que precisa instalar?**

### Código vs. Extensão Ativa
- **Git commit/push**: Salva o código-fonte da extensão
- **Instalação .vsix**: Ativa a extensão no VS Code

### O que acontece sem instalação:
❌ Arquivos estão lá, mas extensão não funciona  
❌ @restricted não aparece no chat  
❌ Menus contextuais não aparecem  
❌ Comandos não funcionam

### O que acontece COM instalação:
✅ Extensão ativa e funcionando  
✅ @restricted disponível no chat  
✅ Compilação automática funcionando  
✅ Detecção de erros ativa

## 🚀 **Automatização Completa**

### Script para máquina nova:
```batch
@echo off
echo Configurando Restricted Copilot na nova máquina...

echo 1. Navegando para pasta da extensão...
cd "PjePlus\Agente"

echo 2. Instalando extensão...
code --install-extension restricted-copilot-0.0.1.vsix --force

echo 3. Abrindo VS Code no workspace PjePlus...
code ".."

echo ✅ Setup concluído! Use @restricted no chat.
pause
```

## 📋 **Checklist para Nova Máquina**

### Pré-requisitos:
- [ ] Node.js instalado
- [ ] VS Code instalado  
- [ ] Git configurado
- [ ] Python instalado (para compilação .py)

### Processo:
- [ ] `git clone` do repositório
- [ ] `cd PjePlus/Agente`
- [ ] `code --install-extension restricted-copilot-0.0.1.vsix --force`
- [ ] Testar: abrir VS Code e verificar @restricted no chat
- [ ] Testar: botão direito → "🔧 Compile & Validate Current File"

### Verificação:
- [ ] @restricted aparece no GitHub Copilot Chat
- [ ] Menu contextual tem opções da extensão
- [ ] Command Palette tem comandos "Restricted Copilot"
- [ ] Teste com `teste_auto_compile.py` funciona
