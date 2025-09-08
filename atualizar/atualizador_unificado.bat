@echo off
REM ========================================================
REM   ATUALIZADOR UNIFICADO PjePlus v2.0 - OTIMIZADO
REM ========================================================
REM Script completo para sincronização entre máquinas
REM Inclui resolução inteligente de conflitos integrada

setlocal enableextensions
color 0A

:inicio
cls
echo ========================================================
echo         ATUALIZADOR UNIFICADO PjePlus v2.0
echo ========================================================
echo.

REM === CONFIGURAÇÃO AUTOMÁTICA ===
set "REPO_URL=https://github.com/silaspassosf/pjeplus.git"
set "PASTA_DEFAULT=C:\PjePlus"
set "PASTA_PROJETO=%PASTA_DEFAULT%"

REM Detecta localização atual
if exist "%CD%\.git" (
    set "PASTA_PROJETO=%CD%"
    echo [✓] Diretório atual: %CD%
) else (
    echo [i] Pasta padrão: %PASTA_DEFAULT%
    set /p "CUSTOM=Usar pasta customizada? (S/enter=não): "
    if /i "%CUSTOM%"=="S" (
        set /p "PASTA_PROJETO=Caminho completo: "
    )
)

echo.
echo ========================================================
echo   MODOS DE SINCRONIZAÇÃO
echo ========================================================
echo.
echo [1] RÁPIDO     - Pull + backup (30s)
echo [2] AVANÇADO   - Commit + pull + conflitos (2-5min)  
echo [3] CONFLITOS  - Só resolução de conflitos
echo [4] SETUP      - Primeira instalação (5-10min)
echo [5] RESET      - Forçar versão remota (CUIDADO!)
echo [0] Sair
echo.

choice /c 123450 /m "Escolha o modo"
if errorlevel 6 goto :fim
if errorlevel 5 goto :reset_forcado
if errorlevel 4 goto :setup_inicial
if errorlevel 3 goto :resolver_conflitos
if errorlevel 2 goto :modo_avancado
if errorlevel 1 goto :modo_rapido

REM ========================================================
REM   MODO 1: RÁPIDO
REM ========================================================
:modo_rapido
echo.
echo === MODO RÁPIDO ===
call :verificar_repo || goto :fim
call :criar_backup "rapido"

echo [2/3] Baixando atualizações...
cd /d "%PASTA_PROJETO%"
git fetch origin main 2>nul
git merge --ff-only origin/main 2>nul
if errorlevel 1 (
    echo ⚠️ Merge fast-forward não possível. Use modo AVANÇADO.
    pause
    goto :inicio
)

echo [3/3] Verificando status...
git status --porcelain
echo ✅ ATUALIZAÇÃO RÁPIDA CONCLUÍDA!
goto :fim_sucesso

REM ========================================================
REM   MODO 2: AVANÇADO
REM ========================================================
:modo_avancado
echo.
echo === MODO AVANÇADO ===
call :verificar_repo || goto :fim
call :criar_backup "avancado"

echo [2/5] Salvando mudanças locais...
cd /d "%PASTA_PROJETO%"
git add -A 2>nul
git diff --cached --quiet || (
    git commit -m "Auto-save: %date% %time%" 2>nul
    echo Mudanças locais salvas
)

echo [3/5] Baixando atualizações...
git fetch origin main

echo [4/5] Aplicando merge...
git merge origin/main 2>nul
if errorlevel 1 (
    echo [CONFLITO] Resolvendo automaticamente...
    call :resolver_conflitos_auto
)

echo [5/5] Finalizando...
git gc --auto 2>nul
echo ✅ SINCRONIZAÇÃO AVANÇADA CONCLUÍDA!
goto :fim_sucesso

REM ========================================================
REM   MODO 3: CONFLITOS
REM ========================================================
:resolver_conflitos
echo.
echo === RESOLUÇÃO DE CONFLITOS ===
call :verificar_repo || goto :fim

cd /d "%PASTA_PROJETO%"
git diff --name-only --diff-filter=U >nul 2>&1
if errorlevel 1 (
    echo ✅ Nenhum conflito detectado!
    git status
    pause
    goto :inicio
)

echo Conflitos detectados:
git diff --name-only --diff-filter=U
echo.
call :resolver_conflitos_auto
echo ✅ CONFLITOS RESOLVIDOS!
goto :fim_sucesso

REM ========================================================
REM   MODO 4: SETUP
REM ========================================================
:setup_inicial
echo.
echo === CONFIGURAÇÃO INICIAL ===

if exist "%PASTA_PROJETO%\.git" (
    choice /c SN /m "Repositório existe. Recriar? (S/N)"
    if errorlevel 2 goto :inicio
    rmdir /S /Q "%PASTA_PROJETO%" 2>nul
)

echo [1/3] Clonando repositório...
git clone "%REPO_URL%" "%PASTA_PROJETO%"
if errorlevel 1 (
    echo ❌ Erro ao clonar! Verifique conexão.
    pause
    goto :inicio
)

echo [2/3] Configurando Git...
cd /d "%PASTA_PROJETO%"
git config --local user.name "PjePlus User"
git config --local user.email "user@pjeplus.local"
git config --local core.autocrlf true

echo [3/3] Criando estrutura...
mkdir "backups" 2>nul

echo ✅ SETUP CONCLUÍDO!
echo 📁 Projeto em: %PASTA_PROJETO%
goto :fim_sucesso

REM ========================================================
REM   MODO 5: RESET FORÇADO
REM ========================================================
:reset_forcado
echo.
echo === RESET FORÇADO ===
echo ⚠️ ATENÇÃO: Todas as mudanças locais serão perdidas!
choice /c SN /m "Continuar? (S/N)"
if errorlevel 2 goto :inicio

call :verificar_repo || goto :fim
call :criar_backup "reset"

cd /d "%PASTA_PROJETO%"
git fetch origin main
REM git reset --hard origin/main
REM git clean -fd

echo ✅ RESET DESABILITADO (protege alterações locais)!
goto :fim_sucesso

REM ========================================================
REM   FUNÇÕES AUXILIARES
REM ========================================================

:verificar_repo
if not exist "%PASTA_PROJETO%\.git" (
    echo ❌ Não é um repositório Git!
    echo Use modo SETUP para instalar.
    pause
    exit /b 1
)
exit /b 0

:criar_backup
set "BACKUP_DIR=backups\backup_%~1_%date:~6,4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "BACKUP_DIR=%BACKUP_DIR: =0%"
echo [1/X] Backup em: %BACKUP_DIR%
mkdir "%BACKUP_DIR%" 2>nul
if "%~1"=="rapido" (
    xcopy /E /Q /Y "*.py" "%BACKUP_DIR%\" 2>nul
    xcopy /E /Q /Y "*.json" "%BACKUP_DIR%\" 2>nul
) else (
    robocopy . "%BACKUP_DIR%" /E /XD .git backups /NFL /NDL /NJH /NJS
)
exit /b 0

:resolver_conflitos_auto
echo Resolvendo conflitos automaticamente...
for /f %%f in ('git diff --name-only --diff-filter=U') do (
    echo - Resolvendo: %%f
    if /i "%%~xf"==".py" (
        call :resolver_python "%%f"
    ) else if /i "%%~xf"==".json" (
        git checkout --theirs "%%f"
    ) else if /i "%%~xf"==".md" (
        git checkout --theirs "%%f"
    ) else if /i "%%~xf"==".bat" (
        git checkout --ours "%%f"
    ) else (
        git checkout --theirs "%%f"
    )
    git add "%%f" 2>nul
)

REM Verifica se ainda há conflitos
git diff --name-only --diff-filter=U >nul 2>&1
if not errorlevel 1 (
    echo ⚠️ Conflitos restantes - resolução manual necessária
    call :resolver_manual
) else (
    git commit --no-edit 2>nul
    echo ✅ Conflitos resolvidos automaticamente
)
exit /b 0

:resolver_python
set "arquivo=%~1"
echo %arquivo% | findstr /i "m1\.py\|main\.py\|config\.py" >nul
if not errorlevel 1 (
    echo   → Arquivo crítico, mantendo versão local
    git checkout --ours "%arquivo%"
) else (
    echo   → Preferindo versão remota
    git checkout --theirs "%arquivo%"
)
exit /b 0

:resolver_manual
echo.
echo RESOLUÇÃO MANUAL NECESSÁRIA:
git diff --name-only --diff-filter=U
echo.
echo [1] Preferir TODAS versões remotas
echo [2] Preferir TODAS versões locais  
echo [3] Editar manualmente
choice /c 123 /m "Escolha"

if errorlevel 3 (
    for /f %%f in ('git diff --name-only --diff-filter=U') do (
        start notepad "%%f"
        pause
        git add "%%f"
    )
    git commit --no-edit
) else if errorlevel 2 (
    git checkout --ours .
    git add .
    git commit --no-edit
) else (
    git checkout --theirs .
    git add .
    git commit --no-edit
)
exit /b 0

REM ========================================================
REM   FINALIZAÇÕES
REM ========================================================

:fim_sucesso
echo.
echo ========================================================
echo           ✅ OPERAÇÃO CONCLUÍDA!
echo ========================================================
echo 📁 Local: %PASTA_PROJETO%
echo ⏰ %date% %time%
echo.
choice /c SN /m "Executar novamente? (S/N)"
if errorlevel 2 goto :fim
goto :inicio

:fim
echo.
echo Até logo! 👋
endlocal
pause >nul
