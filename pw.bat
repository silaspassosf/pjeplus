@echo off
chcp 65001 >nul
title PJe Plus - pw.py

set "RAIZ=D:\PjePlus"
set "PY=%RAIZ%\.venv\Scripts\python.exe"

cd /d "%RAIZ%"

if exist "%PY%" goto :ok_python
echo.
echo  ERRO: Python do venv nao encontrado em:
echo    %PY%
echo  Crie o venv e instale as dependencias antes.
echo.
pause
exit /b 1

:ok_python
if exist "%RAIZ%\pw.py" goto :ok_pw
echo.
echo  ERRO: pw.py nao encontrado em %RAIZ%
echo.
pause
exit /b 1

:ok_pw
:loop
echo Iniciando pw.py em %date% %time%...
echo.

"%PY%" pw.py %*
set "COD=%errorlevel%"

echo.
echo Execucao encerrada (codigo de saida %COD%).
echo.

rem Laco automatico: ao final de um fluxo, ja volta ao menu de escolha,
rem sem perguntar "sim/nao". "X - Cancelar" no menu (pw.py sai com codigo 88)
rem encerra o laco.
if "%COD%"=="88" goto :fim
goto :loop

:fim
exit /b %COD%
