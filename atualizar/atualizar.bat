@echo off
REM Atualização segura do projeto PjePlus
call backup_rotativo_selenium_pje_trt2.bat
call auto_commit.bat
setlocal
REM Caminho onde deseja manter o projeto
SET PASTA_PROJETO=C:\Users\s164283\Desktop\pjeplus
REM URL do seu repositório
SET REPO_URL=https://github.com/silaspassosf/pjeplus.git

IF EXIST "%PASTA_PROJETO%\.git" (
    echo Atualizando projeto existente...
    cd "%PASTA_PROJETO%"
    git pull
) ELSE (
    echo Clonando projeto do GitHub...
    git clone "%REPO_URL%" "%PASTA_PROJETO%"
)
endlocal
pause