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
rem ── /auto : roda em laco sem perguntar (para varios fluxos seguidos) ──
set "MODO_AUTO="
if /I "%~1"=="/auto" set "MODO_AUTO=1"

:loop
echo Iniciando pw.py em %date% %time%...
echo.

"%PY%" pw.py %*
set "COD=%errorlevel%"

echo.
echo Execucao encerrada (codigo de saida %COD%).
echo.

rem 88 = o usuario cancelou (X) no pw.py/x.py — encerra o laco sem perguntar.
rem O processo ja terminou e o browser ja foi fechado pelo finally do x.py;
rem a proxima execucao e um processo NOVO, portanto le o codigo atualizado.
if "%COD%"=="88" goto :cancelado

if defined MODO_AUTO goto :loop

choice /C SN /M "Executar novamente para escolher um novo fluxo (S=sim, N=nao)"
if errorlevel 2 goto :fim
if errorlevel 1 goto :loop

:cancelado
echo.
echo Fluxo cancelado pelo usuario — encerrando.
echo.

:fim
exit /b %COD%
