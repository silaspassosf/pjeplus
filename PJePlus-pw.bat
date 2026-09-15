@echo off
chcp 65001 >nul
title PJe Plus - pw.py

set "RAIZ=C:\Users\s164283\Desktop\Pje2"
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

choice /C SN /M "Executar novamente para escolher um novo fluxo (S=sim, N=nao)"
if errorlevel 2 goto :fim
if errorlevel 1 goto :loop

:fim
exit /b %COD%
