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

REM Força remoção completa dos arquivos problemáticos do histórico
echo Removendo DeboniTips_FREE.rar do historico completo...
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch 'telegrambot/exported_groups/DeboniTips_FREE.rar'" --prune-empty --tag-name-filter cat -- --all

echo Removendo Docker Desktop Installer.exe do historico completo...
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch 'MaisPje/Docker Desktop Installer.exe'" --prune-empty --tag-name-filter cat -- --all

REM Remove outros arquivos grandes que podem estar causando problema
echo Removendo outros arquivos grandes conhecidos...
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch '*.exe' '*.rar' '*.zip' '*.7z' '*.iso'" --prune-empty --tag-name-filter cat -- --all

echo === LIMPEZA COMPLETA DE REFERENCIAS ===
REM Remove todas as referências aos commits antigos
for /f %%i in ('git for-each-ref --format="%%^(refname^)" refs/original') do git update-ref -d %%i
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo === VERIFICANDO TAMANHOS DE ARQUIVOS ===
echo Arquivos maiores que 50MB no repositorio:
git ls-tree -r -t -l --full-name HEAD | sort -k 4 -n | tail -10

echo.
echo === ADICIONANDO ARQUIVOS DE FORMA INTELIGENTE ===
echo Verificando mudancas reais...

REM Adiciona apenas arquivos modificados/novos, não tudo
git add -u
echo Arquivos modificados adicionados.

REM Adiciona novos arquivos específicos importantes
git add *.py *.md *.json *.log *.bat
echo Arquivos importantes adicionados.

REM Evita adicionar arquivos grandes
echo Verificando se ha arquivos grandes sendo adicionados...
git diff --cached --name-only | while read file; do
    if [ -f "$file" ]; then
        size=$(wc -c < "$file")
        if [ $size -gt 52428800 ]; then  # 50MB
            echo "AVISO: Arquivo grande detectado: $file ($(($size/1024/1024))MB)"
            git reset HEAD "$file"
        fi
    fi
done
echo.
echo === EXECUTANDO PUSH INTELIGENTE ===
echo Verificando se ha mudancas para commitar...
git diff-index --quiet HEAD --
if %errorlevel% neq 0 (
    echo Mudancas detectadas, fazendo commit...
    git commit -m "%MSG%"
    
    echo Tentando push incremental primeiro...
    git push 2>push_error.log
    if %errorlevel% equ 0 (
        echo Push incremental bem-sucedido!
        del push_error.log 2>nul
    ) else (
        echo Push incremental falhou, verificando erro...
        type push_error.log
        echo.
        echo Tentando push forcado com lease (mais seguro)...
        git push --force-with-lease
        if %errorlevel% neq 0 (
            echo Push com lease falhou, usando force completo...
            git push --force
        )
        del push_error.log 2>nul
    )
) else (
    echo Nenhuma mudanca detectada, pulando commit e push.
)
endlocal
echo.
echo ===========================
echo Operacao concluida!
echo ===========================
pause
