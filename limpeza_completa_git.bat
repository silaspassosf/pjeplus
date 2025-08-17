@echo off
REM Limpeza completa de arquivos grandes do histórico Git
REM Execute este script UMA VEZ para limpar o repositório permanentemente

set FILTER_BRANCH_SQUELCH_WARNING=1

echo ================================================
echo    LIMPEZA COMPLETA DE ARQUIVOS GRANDES
echo ================================================
echo.
echo ATENÇÃO: Este processo irá reescrever o histórico Git
echo Certifique-se de ter backup antes de continuar!
echo.
pause

echo === PASSO 1: REMOVENDO ARQUIVOS ESPECÍFICOS DO HISTÓRICO ===
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch \"telegrambot/exported_groups/DeboniTips_FREE.rar\"" --prune-empty --tag-name-filter cat -- --all
if errorlevel 1 echo Erro na primeira limpeza, continuando...

git filter-branch --force --index-filter "git rm --cached --ignore-unmatch \"MaisPje/Docker Desktop Installer.exe\"" --prune-empty --tag-name-filter cat -- --all
if errorlevel 1 echo Erro na segunda limpeza, continuando...

echo === PASSO 2: REMOVENDO ARQUIVOS COM PADRÕES ESPECÍFICOS ===
REM Remove arquivos .rar grandes
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch \"*.rar\"" --prune-empty --tag-name-filter cat -- --all
if errorlevel 1 echo Erro removendo .rar, continuando...

REM Remove executáveis grandes  
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch \"*.exe\"" --prune-empty --tag-name-filter cat -- --all
if errorlevel 1 echo Erro removendo .exe, continuando...

echo === PASSO 3: LIMPEZA COMPLETA ===
REM Remove referências antigas
git for-each-ref --format="delete %%(refname)" refs/original | git update-ref --stdin
if errorlevel 1 echo Erro removendo refs originais, continuando...

REM Limpa reflog
git reflog expire --expire=now --all
git reflog expire --expire-unreachable=now --all

REM Garbage collection OTIMIZADO (sem --aggressive para evitar lentidão)
echo AVISO: Usando GC otimizado sem --aggressive (evita compressão lenta)
git gc --prune=now
echo GC otimizado concluído em tempo muito menor!

echo === PASSO 4: CRIANDO .gitignore PARA ARQUIVOS GRANDES ===
if not exist .gitignore (
    echo # Arquivos grandes - evitar no futuro > .gitignore
) else (
    echo. >> .gitignore
    echo # Arquivos grandes - evitar no futuro >> .gitignore
)
echo *.exe >> .gitignore
echo *.rar >> .gitignore
echo *.zip >> .gitignore
echo *.7z >> .gitignore
echo *.iso >> .gitignore
echo *.msi >> .gitignore
echo *.dmg >> .gitignore
echo # Pastas específicas >> .gitignore
echo telegrambot/exported_groups/*.rar >> .gitignore
echo MaisPje/*.exe >> .gitignore

echo === PASSO 5: VERIFICAÇÃO FINAL ===
echo Tamanho do repositório após limpeza:
git count-objects -vH

echo Arquivos no último commit:
git ls-tree -r -l HEAD | findstr /v "^100644 blob 0"

echo.
echo === LIMPEZA CONCLUÍDA ===
echo Agora execute: git push --force origin main
echo ATENÇÃO: Este push irá sobrescrever o histórico remoto!
echo.
pause
