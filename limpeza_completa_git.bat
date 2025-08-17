@echo off
REM Limpeza completa de arquivos grandes do histórico Git
REM Execute este script UMA VEZ para limpar o repositório permanentemente

echo ================================================
echo    LIMPEZA COMPLETA DE ARQUIVOS GRANDES
echo ================================================
echo.
echo ATENÇÃO: Este processo irá reescrever o histórico Git
echo Certifique-se de ter backup antes de continuar!
echo.
pause

echo === PASSO 1: REMOVENDO ARQUIVOS ESPECÍFICOS DO HISTÓRICO ===
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch 'telegrambot/exported_groups/DeboniTips_FREE.rar'" --prune-empty --tag-name-filter cat -- --all
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch 'MaisPje/Docker Desktop Installer.exe'" --prune-empty --tag-name-filter cat -- --all

echo === PASSO 2: REMOVENDO TODOS OS ARQUIVOS GRANDES (>50MB) ===
REM Lista e remove arquivos grandes
git rev-list --objects --all | git cat-file --batch-check="%(objecttype) %(objectname) %(objectsize) %(rest)" | sed -n "s/^blob //p" | sort --numeric-sort --key=2 | tail -20 > large_files.txt
echo Arquivos grandes encontrados:
type large_files.txt

REM Remove os maiores arquivos automaticamente
for /f "tokens=3*" %%a in ('type large_files.txt ^| findstr /r "[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]"') do (
    echo Removendo: %%b
    git filter-branch --force --index-filter "git rm --cached --ignore-unmatch '%%b'" --prune-empty --tag-name-filter cat -- --all
)

echo === PASSO 3: LIMPEZA COMPLETA ===
REM Remove referências antigas
for /f %%i in ('git for-each-ref --format="%%^(refname^)" refs/original') do git update-ref -d %%i

REM Limpa reflog
git reflog expire --expire=now --all

REM Garbage collection agressivo
git gc --prune=now --aggressive

echo === PASSO 4: CRIANDO .gitignore PARA ARQUIVOS GRANDES ===
echo # Arquivos grandes - evitar no futuro > .gitignore
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

echo Arquivos grandes restantes (se houver):
git ls-tree -r -t -l --full-name HEAD | sort -k 4 -n | tail -10

echo.
echo === LIMPEZA CONCLUÍDA ===
echo Agora execute: git push --force
echo ATENÇÃO: Este push irá sobrescrever o histórico remoto!
echo.
del large_files.txt 2>nul
pause
