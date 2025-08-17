@echo off
REM ========================================================
REM   LIMPEZA COMPLETA UNIFICADA - GIT + TEMPORÁRIOS
REM ========================================================
REM Combina limpeza Git, VS Code e temporários do projeto
REM Execute para otimizar completamente o workspace

setlocal enableextensions
set FILTER_BRANCH_SQUELCH_WARNING=1

echo ========================================================
echo       LIMPEZA COMPLETA UNIFICADA PjePlus
echo ========================================================
echo.
echo Este script irá:
echo [1] Limpar temporários VS Code e Python
echo [2] Otimizar repositório Git (histórico)
echo [3] Remover arquivos grandes do Git
echo [4] Configurar .gitignore otimizado
echo.
echo MODOS DISPONÍVEIS:
echo [R] RÁPIDO - Só temporários + GC mínimo (30s)
echo [C] COMPLETO - Inclui limpeza histórico Git (pode demorar)
echo.
echo ATENÇÃO: Modo completo pode reescrever histórico Git!
echo Certifique-se de ter backup antes de continuar!
echo.
choice /c RCN /m "Escolha o modo: (R)ápido, (C)ompleto, (N)ão executar"
if errorlevel 3 goto :fim
if errorlevel 2 set "MODO=COMPLETO" & goto :inicio
if errorlevel 1 set "MODO=RAPIDO" & goto :inicio

:inicio
echo.
echo ========================================================
echo   MODO SELECIONADO: %MODO%
echo ========================================================
echo.
echo ========================================================
echo   FASE 1: LIMPEZA DE TEMPORÁRIOS E CACHE
echo ========================================================

REM === LIMPEZA VS CODE ===
echo [VS Code] Limpando cache e temporários...
set "VSCODE_BASE=%APPDATA%\Code"
for %%D in (Cache CachedData "Code Cache" "User\workspaceStorage") do (
    set "FOLDER=%VSCODE_BASE%\%%~D"
    if exist "!FOLDER!" (
        echo   - Limpando %%~D
        rd /s /q "!FOLDER!" 2>nul
        mkdir "!FOLDER!" 2>nul
    )
)

REM === LIMPEZA PYTHON ===
echo [Python] Removendo __pycache__ e .pyc...
cd /d "%~dp0"
for /r %%F in (__pycache__) do (
    if exist "%%F" (
        echo   - Removendo %%F
        rd /s /q "%%F" 2>nul
    )
)
for /r %%F in (*.pyc *.pyo) do del /q "%%F" 2>nul

REM === LIMPEZA LOGS E TEMPORÁRIOS DO PROJETO ===
echo [Projeto] Limpando logs e temporários...
for %%F in (*.log *.tmp temp.* ~*.* .DS_Store Thumbs.db) do del /q "%%F" 2>nul
if exist "node_modules" echo   - Encontrado node_modules (manter)
if exist "build\temp" rd /s /q "build\temp" 2>nul

echo Fase 1 concluída!
echo.

echo ========================================================
echo   FASE 2: OTIMIZAÇÃO GIT (LIMPEZA RÁPIDA)
echo ========================================================

REM === COMMIT PENDENTE ===
echo [Git] Verificando mudanças pendentes...
git add . >nul 2>&1
git diff --cached --quiet
if errorlevel 1 (
    echo   - Commitando mudanças pendentes...
    git commit -m "Auto-commit antes da limpeza [%date% %time%]" >nul
)

REM === LIMPEZA BÁSICA GIT ===
echo [Git] Limpeza básica e otimização...
if "%MODO%"=="RAPIDO" (
    echo   - Modo RÁPIDO: GC automático apenas
    git gc --auto --quiet
) else (
    echo   - Modo COMPLETO: Limpeza mais profunda
    git gc --auto --quiet
    git prune --expire=now
    git remote prune origin 2>nul
)

echo Fase 2 concluída!
echo.

echo ========================================================
echo   FASE 3: REMOÇÃO DE ARQUIVOS GRANDES (OPCIONAL)
echo ========================================================

if "%MODO%"=="RAPIDO" (
    echo MODO RÁPIDO: Pulando limpeza de histórico Git
    goto :gitignore
)

choice /c SN /m "Remover arquivos grandes do histórico Git? (S/N)"
if errorlevel 2 goto :gitignore

echo [Git] Removendo arquivos grandes específicos...
REM Remove arquivos conhecidamente grandes
for %%F in ("telegrambot/exported_groups/DeboniTips_FREE.rar" "MaisPje/Docker Desktop Installer.exe") do (
    echo   - Tentando remover %%F do histórico...
    git filter-branch --force --index-filter "git rm --cached --ignore-unmatch %%F" --prune-empty --tag-name-filter cat -- --all 2>nul
    if errorlevel 1 echo     Arquivo não encontrado no histórico
)

REM Remove padrões de arquivos grandes
echo [Git] Removendo padrões de arquivos grandes...
for %%E in (*.exe *.rar *.zip *.7z *.iso *.msi *.dmg) do (
    echo   - Removendo padrão %%E...
    git filter-branch --force --index-filter "git rm --cached --ignore-unmatch \"%%E\"" --prune-empty --tag-name-filter cat -- --all 2>nul
)

REM === LIMPEZA REFERÊNCIAS E GC OTIMIZADO ===
echo [Git] Limpeza de referências antigas...
git for-each-ref --format="delete %%(refname)" refs/original 2>nul | git update-ref --stdin 2>nul

echo [Git] Limpeza de reflog...
git reflog expire --expire=now --all 2>nul
git reflog expire --expire-unreachable=now --all 2>nul

echo [Git] Garbage collection ULTRA-RÁPIDO...
REM OTIMIZAÇÃO MÁXIMA: Só se necessário
if "%MODO%"=="RAPIDO" (
    echo   - Modo RÁPIDO: Sem GC adicional
) else (
    echo   - Modo COMPLETO: GC automático apenas
    git gc --auto
    echo   - GC automático concluído (ultra-rápido)
)

:gitignore
echo ========================================================
echo   FASE 4: CONFIGURAÇÃO .GITIGNORE OTIMIZADO
echo ========================================================

echo [Git] Criando .gitignore otimizado...
(
echo # ========================================
echo # .gitignore otimizado PjePlus
echo # ========================================
echo.
echo # Arquivos grandes ^(^>10MB^)
echo *.exe
echo *.rar
echo *.zip
echo *.7z
echo *.iso
echo *.msi
echo *.dmg
echo.
echo # Temporários Python
echo __pycache__/
echo *.py[cod]
echo *.pyo
echo *.egg-info/
echo .pytest_cache/
echo.
echo # Temporários VS Code
echo .vscode/settings.json
echo *.code-workspace
echo.
echo # Logs e temporários
echo *.log
echo *.tmp
echo temp.*
echo ~*.*
echo .DS_Store
echo Thumbs.db
echo.
echo # Diretórios específicos
echo telegrambot/exported_groups/*.rar
echo MaisPje/*.exe
echo node_modules/
echo build/temp/
echo.
echo # Arquivos de configuração sensíveis
echo *.env
echo cookies_*.json
echo dadosatuais.json
) > .gitignore

echo ========================================================
echo   FASE 5: VERIFICAÇÃO E RELATÓRIO FINAL
echo ========================================================

echo [Relatório] Tamanho do repositório:
git count-objects -vH

echo.
echo [Relatório] Arquivos grandes restantes ^(^>1MB^):
git ls-tree -r -l HEAD | findstr /r "[0-9][0-9][0-9][0-9][0-9][0-9][0-9]" | sort /r /+4

echo.
echo ========================================================
echo           LIMPEZA COMPLETA FINALIZADA!
echo ========================================================
echo.
echo STATUS:
echo ✓ Temporários VS Code limpos
echo ✓ Cache Python removido  
echo ✓ Repository Git otimizado (%MODO%)
echo ✓ .gitignore atualizado
echo.
echo PERFORMANCE:
if "%MODO%"=="RAPIDO" (
    echo ⚡ Modo RÁPIDO executado - sem operações pesadas
) else (
    echo 🔧 Modo COMPLETO executado - limpeza profunda
)
echo.
echo PRÓXIMOS PASSOS:
echo 1. git add .gitignore
echo 2. git commit -m "Gitignore otimizado"
echo 3. git push ^(ou git push --force se histórico alterado^)
echo.
echo NOTA: Modo RÁPIDO evita operações de compressão lentas
echo      Use COMPLETO apenas quando necessário limpar histórico
echo.

:fim
pause
