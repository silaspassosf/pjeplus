@echo off
chcp 65001 >nul
title PJeTools - Compressor de PDF

echo.
echo ========================================
echo   PJeTools - Compressor de PDF v3.0
echo   Powered by PyMuPDF (offline/nativo)
echo ========================================
echo.

set MAX_MB=9.5
set SCRIPT=%~dp0comprimir_pdf.py

:: ── Drag-and-drop ou argumento direto ───────────────────────────
if not "%~1"=="" (
    echo Processando: %~1
    echo Limite: %MAX_MB% MB
    echo.
    py "%SCRIPT%" --max-mb %MAX_MB% -- %1
    goto fim
)

:: ── Sem argumento: pede o caminho manualmente ────────────────────
echo Arraste um PDF sobre este .bat, ou:
echo.
set /p "CAMINHO=Digite o caminho completo do PDF (sem aspas): "

if "%CAMINHO%"=="" (
    echo Nenhum arquivo informado.
    goto fim
)

echo.
echo Processando: %CAMINHO%
echo Limite: %MAX_MB% MB
echo.

py "%SCRIPT%" --max-mb %MAX_MB% -- "%CAMINHO%"

:fim
echo.
if %ERRORLEVEL% neq 0 (
    echo ERRO: o script terminou com codigo %ERRORLEVEL%
)
echo ----------------------------------------
echo Pressione qualquer tecla para fechar...
pause >nul
