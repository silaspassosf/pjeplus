@echo off
chcp 65001 >nul
title PJeTools — Aud Standalone

:: ─── Configurações ───────────────────────────────────────────
set CDP_PORT=9222
set SERVER_PORT=7823
set SCRIPT=%~dp0aud_server.py

:: Caminhos comuns do Chrome
set CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe
if not exist "%CHROME%" set CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe
if not exist "%CHROME%" set CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe

:: ─── Verifica Chrome com CDP ──────────────────────────────────
echo.
echo =============================================
echo   PJeTools — Aud Standalone
echo   Playwright + Chrome CDP
echo =============================================
echo.

:: Testa se Chrome ja esta com CDP ativo
curl -s "http://localhost:%CDP_PORT%/json/version" >nul 2>&1
if %ERRORLEVEL%==0 (
    echo [OK] Chrome ja esta com remote-debugging-port=%CDP_PORT%
) else (
    echo [INFO] Iniciando Chrome com remote-debugging-port=%CDP_PORT%...
    if exist "%CHROME%" (
        start "" "%CHROME%" --remote-debugging-port=%CDP_PORT% --no-first-run --no-default-browser-check
        timeout /t 2 /nobreak >nul
    ) else (
        echo [AVISO] Chrome nao encontrado automaticamente.
        echo.
        echo Abra o Chrome manualmente com este comando:
        echo   chrome.exe --remote-debugging-port=%CDP_PORT%
        echo.
        echo Depois execute este .bat novamente.
        pause
        exit /b 1
    )
)

:: ─── Inicia servidor Python ───────────────────────────────────
echo.
echo [INFO] Iniciando servidor Aud...
echo [INFO] A interface abrira automaticamente no navegador.
echo.
echo Pressione Ctrl+C para encerrar.
echo.

py "%SCRIPT%"

echo.
echo [INFO] Servidor encerrado.
pause >nul
