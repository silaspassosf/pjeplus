@echo off
REM Script para integrar a pasta Agente ao projeto principal PjePlus
echo ========================================
echo INTEGRAÇÃO DA PASTA AGENTE AO PJEPLUS
echo ========================================
echo.

REM Verificar se estamos no diretório correto
if not exist "bacen.py" (
    echo ERRO: Execute este script na pasta raiz do PjePlus
    pause
    exit /b 1
)

REM Verificar se a pasta Agente existe
if not exist "Agente" (
    echo ERRO: Pasta Agente não encontrada
    pause
    exit /b 1
)

echo Opção 1: Integrar pasta Agente diretamente ao projeto PjePlus
echo Opção 2: Manter como repositório separado (não commitado automaticamente)
echo.
set /p "opcao=Escolha (1 ou 2): "

if "%opcao%"=="1" (
    echo.
    echo Passo 1: Fazendo backup da pasta Agente...
    if exist "Agente_backup" rmdir /s /q "Agente_backup"
    xcopy "Agente" "Agente_backup\" /E /I /Q
    
    echo.
    echo Passo 2: Removendo repositório Git independente da pasta Agente...
    if exist "Agente\.git" (
        rmdir /s /q "Agente\.git"
        echo ✅ Repositório Git removido da pasta Agente
    )
    
    echo.
    echo Passo 3: Adicionando pasta Agente ao projeto principal...
    git add Agente/
    git commit -m "Integrar pasta Agente ao projeto principal"
    
    echo.
    echo ✅ SUCESSO! Pasta Agente integrada ao projeto PjePlus
    echo A pasta Agente agora será commitada junto com o resto do projeto
    
) else if "%opcao%"=="2" (
    echo.
    echo Adicionando Agente ao .gitignore para ser ignorada nos commits...
    echo Agente/ >> .gitignore
    echo ✅ Pasta Agente adicionada ao .gitignore
    echo A pasta Agente será ignorada nos commits automáticos
    
) else (
    echo Opção inválida
    pause
    exit /b 1
)

echo.
echo Backup da pasta original salvo em: Agente_backup
echo.
pause
