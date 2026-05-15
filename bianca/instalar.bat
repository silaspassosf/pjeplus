@echo off
title Instalar bianca
cd /d "%~dp0"

echo ========================================
echo  Instalacao - bianca
echo ========================================
echo.

REM ==========================================
REM 1. Verificar Python 3.10+
REM ==========================================
echo [1/6] Verificando Python...
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Python nao encontrado. Instale Python 3.10 ou superior.
    pause
    exit /b 1
)
py --version
echo Python OK.
echo.

REM ==========================================
REM 2. Criar ambiente virtual
REM ==========================================
echo [2/6] Criando ambiente virtual...
if exist venv\ (
    echo Ambiente virtual ja existe. Pulando...
) else (
    py -m venv venv
    if %errorlevel% neq 0 (
        echo ERRO: Falha ao criar ambiente virtual.
        pause
        exit /b 1
    )
    echo Ambiente virtual criado em venv\
)
echo.

REM ==========================================
REM 3. Instalar dependencias
REM ==========================================
echo [3/6] Instalando dependencias...
venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERRO: Falha ao instalar dependencias.
    pause
    exit /b 1
)
echo Dependencias instaladas.
echo.

REM ==========================================
REM 4. Verificar geckodriver
REM ==========================================
echo [4/6] Verificando geckodriver...
if exist drivers\geckodriver.exe (
    echo geckodriver.exe ja existe em drivers\
) else (
    echo Copiando geckodriver.exe de ..\Fix\...
    if exist ..\Fix\geckodriver.exe (
        if not exist drivers\ mkdir drivers
        copy ..\Fix\geckodriver.exe drivers\geckodriver.exe >nul
        if %errorlevel% equ 0 (
            echo geckodriver.exe copiado com sucesso.
        ) else (
            echo AVISO: Falha ao copiar geckodriver.exe.
        )
    ) else (
        echo AVISO: ..\Fix\geckodriver.exe nao encontrado.
        echo        Baixe o geckodriver manualmente e coloque em drivers\
    )
)
echo.

REM ==========================================
REM 5. Verificar Firefox Developer Edition
REM ==========================================
echo [5/6] Verificando Firefox Developer Edition...
if exist "C:\Program Files\Firefox Developer Edition\firefox.exe" (
    echo Firefox Developer Edition encontrado.
) else (
    echo AVISO: Firefox Developer Edition nao encontrado no caminho padrao.
    echo        Instale de: https://www.mozilla.org/pt-BR/firefox/developer/
)
echo.

REM ==========================================
REM 6. Criar diretorio de logs
REM ==========================================
echo [6/6] Criando diretorio de logs...
if not exist logs\ (
    mkdir logs
    echo Diretorio logs\ criado.
) else (
    echo Diretorio logs\ ja existe.
)
echo.

echo ========================================
echo  Instalacao concluida com sucesso!
echo ========================================
echo.
echo  Para ativar o ambiente:
echo      venv\Scripts\activate
echo.
pause
