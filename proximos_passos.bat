@echo off
REM ========================================================
REM   EXECUÇÃO DOS PRÓXIMOS PASSOS - PjePlus
REM ========================================================
REM Resposta à solicitação: "execute os proximos passos!"
REM Continua processo de atualização após backup criado

echo ========================================================
echo     EXECUTANDO PRÓXIMOS PASSOS - PjePlus
echo ========================================================
echo.
echo [✓] Backup já foi criado
echo [→] Iniciando próximos passos da atualização...
echo.

REM Verifica se estamos no diretório correto
if not exist ".git" (
    echo ❌ Erro: Execute este script na pasta do projeto PjePlus
    pause
    exit /b 1
)

REM Verifica se o script de continuação existe
if not exist "atualizar\continuar_atualizacao.bat" (
    echo ❌ Erro: Script de continuação não encontrado
    echo Verifique se todos os arquivos estão presentes
    pause
    exit /b 1
)

echo [✓] Ambiente verificado
echo [→] Transferindo para script de continuação...
echo.

REM Executa o script de continuação
call "atualizar\continuar_atualizacao.bat"

REM Retorna o código de saída
exit /b %errorlevel%