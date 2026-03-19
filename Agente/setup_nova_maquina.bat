@echo off
echo ====================================
echo   RESTRICTED COPILOT - SETUP
echo   Configuracao para Nova Maquina
echo ====================================
echo.

echo 1. Verificando prerequisitos...

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js nao encontrado. Instale antes de continuar.
    echo Download: https://nodejs.org
    pause
    exit /b 1
)

where code >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ VS Code nao encontrado. Instale antes de continuar.
    echo Download: https://code.visualstudio.com
    pause
    exit /b 1
)

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Python nao encontrado. Compilacao .py nao funcionara.
    echo Download: https://python.org
)

echo ✅ Prerequisitos verificados

echo.
echo 2. Instalando extensao Restricted Copilot...

if exist "restricted-copilot-0.0.1.vsix" (
    code --install-extension restricted-copilot-0.0.1.vsix --force
    if %errorlevel% equ 0 (
        echo ✅ Extensao instalada com sucesso
    ) else (
        echo ❌ Erro na instalacao da extensao
        pause
        exit /b 1
    )
) else (
    echo ❌ Arquivo restricted-copilot-0.0.1.vsix nao encontrado
    echo Execute 'npx vsce package' primeiro
    pause
    exit /b 1
)

echo.
echo 3. Verificando instalacao...
code --list-extensions | findstr restricted-copilot >nul
if %errorlevel% equ 0 (
    echo ✅ Extensao confirmada na lista
) else (
    echo ❌ Extensao nao aparece na lista
    pause
    exit /b 1
)

echo.
echo 4. Abrindo VS Code no workspace PjePlus...
cd ..
start code .

echo.
echo ====================================
echo   SETUP CONCLUIDO COM SUCESSO!
echo ====================================
echo.
echo Agora voce pode:
echo.
echo 1. Abrir qualquer arquivo .py, .js, .ts
echo 2. Clicar direito → "🔧 Compile & Validate Current File"
echo 3. Usar @restricted no GitHub Copilot Chat
echo 4. Testar com o arquivo: teste_auto_compile.py
echo.
echo A extensao esta monitorando automaticamente:
echo - pje_automacao.log
echo - pje_automation.log  
echo - erro_fatal_selenium.log
echo.
echo Pressione qualquer tecla para finalizar...
pause >nul
