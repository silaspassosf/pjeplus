@echo off
echo ====================================
echo   RESTRICTED COPILOT - AUTO COMPILE
echo   Teste e Demonstracao
echo ====================================
echo.

echo 1. Verificando se a extensao esta instalada...
code --list-extensions | findstr restricted-copilot >nul
if %errorlevel% equ 0 (
    echo ✅ Restricted Copilot instalado
) else (
    echo ❌ Extensao nao encontrada. Instalando...
    code --install-extension restricted-copilot-0.0.1.vsix --force
)

echo.
echo 2. Abrindo VS Code no workspace PjePlus...
code "d:\PjePlus"

echo.
echo 3. Arquivo de teste criado: teste_auto_compile.py
echo.
echo ====================================
echo   COMO TESTAR A FUNCIONALIDADE
echo ====================================
echo.
echo 1. Abra o arquivo: teste_auto_compile.py
echo 2. Clique com botao direito no editor
echo 3. Selecione: "🔧 Compile & Validate Current File"
echo 4. A extensao detectara os erros automaticamente
echo 5. Foque na linha do erro e use @restricted no chat
echo.
echo OU teste a deteccao automatica:
echo 1. Execute um script Python com erro
echo 2. A extensao monitorara os logs automaticamente
echo 3. Quando detectar erro, focara na linha correspondente
echo.
echo ====================================
echo   COMANDOS DISPONIVEIS
echo ====================================
echo.
echo - Ctrl+Shift+P → "Restricted Copilot: Compile & Validate"
echo - Botao direito → "🔧 Compile & Validate Current File"
echo - Chat: @restricted [sua pergunta sobre o erro]
echo - Botao direito → "Analyze Current Function"
echo - Botao direito → "Analyze Selection"
echo.
echo Pressione qualquer tecla para continuar...
pause >nul
