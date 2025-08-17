@echo off
REM Auto commit script for PjePlus project
REM Executa backup rotativo antes do commit
call backup_rotativo_selenium_pje_trt2.bat
setlocal
set MSG=Backup automático: commit programado (%DATE% %TIME%)
echo.
echo === STATUS ANTES DO COMMIT ===
git status
echo.
echo === VERIFICANDO PASTA AGENTE ===
if exist "Agente\.git" (
    echo Pasta Agente é um repositório Git independente
    echo Ignorando pasta Agente no commit automático...
    echo Para adicionar como submódulo, execute manualmente:
    echo   cd Agente
    echo   git add .
    echo   git commit -m "Commit inicial Agente"
    echo   cd ..
    echo   git submodule add ./Agente Agente
) else if exist "Agente" (
    echo Pasta Agente será incluída normalmente no commit
)
echo.
echo === REMOVENDO ARQUIVOS GRANDES DO HISTÓRICO ===
echo Verificando se arquivos grandes ainda estao no historico...
git log --all --full-history -- "telegrambot/exported_groups/DeboniTips_FREE.rar" "MaisPje/Docker Desktop Installer.exe" >nul 2>&1
if %errorlevel% equ 0 (
    echo Arquivos grandes encontrados no historico, removendo...
    git filter-branch --force --index-filter "git rm --cached --ignore-unmatch 'telegrambot/exported_groups/DeboniTips_FREE.rar' 'MaisPje/Docker Desktop Installer.exe'" --prune-empty --tag-name-filter cat -- --all
    echo === LIMPANDO REFERENCIAS ANTIGAS ===
    git for-each-ref --format="delete %(refname)" refs/original | git update-ref --stdin
    git reflog expire --expire=now --all
    echo Executando limpeza rapida...
    git gc --prune=now
) else (
    echo Arquivos grandes nao encontrados no historico, pulando limpeza...
)
echo.
echo === ADICIONANDO ARQUIVOS (FORÇADO) ===
git add --all --force
echo.
echo === ADICIONANDO ARQUIVOS ESPECIFICOS ===
git add Fix.py atos.py bacen.py dadosatuais.json log.py loop.py m1.py p2.py auto_commit.bat
git add *.md *.py *.log *.json
echo.
echo === STATUS APOS ADD ===
git status
echo.
echo === EXECUTANDO COMMIT ===
git commit -m "%MSG%"
echo.
echo === EXECUTANDO PUSH OTIMIZADO ===
echo Tentando push normal primeiro...
git push >nul 2>&1
if %errorlevel% equ 0 (
    echo Push normal bem-sucedido!
) else (
    echo Push normal falhou, tentando push forcado...
    echo ATENÇÃO: Fazendo push forçado para sobrescrever histórico remoto...
    git push --force-with-lease
)
endlocal
echo.
echo ===========================
echo Operacao concluida!
echo ===========================
pause
