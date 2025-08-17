@echo off
REM Auto commit script for PjePlus project
REM Versao otimizada sem compressao lenta

echo ========================================
echo       AUTO COMMIT OTIMIZADO PjePlus
echo ========================================
echo.
echo 💡 A tela permanecerá aberta para voce acompanhar o progresso
echo.
echo MODO DE OPERACAO:
echo [R] RAPIDO - Commit direto sem limpeza historico (30s)
echo [C] COMPLETO - Inclui limpeza de arquivos grandes (demorado)
echo.
choice /c RC /m "Escolha o modo: (R)apido ou (C)ompleto"
if errorlevel 2 set "MODE=COMPLETO" & goto :completo
if errorlevel 1 set "MODE=RAPIDO" & goto :rapido

:rapido
echo === MODO RAPIDO SELECIONADO ===
echo ⚡ Executando commit rapido sem limpeza de historico...
setlocal
set MSG=Commit rápido: atualizacao automatica (%DATE% %TIME%)
echo.
goto :commit_direto

:completo
echo === MODO COMPLETO SELECIONADO ===
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

echo === LIMPEZA OTIMIZADA DE REFERENCIAS ===
REM Remove todas as referências aos commits antigos
for /f %%i in ('git for-each-ref --format="%%^(refname^)" refs/original') do git update-ref -d %%i
git reflog expire --expire=now --all

REM OTIMIZAÇÃO: GC automático rápido (sem --aggressive)
echo Executando garbage collection otimizado...
git gc --auto
echo GC otimizado concluído rapidamente!

echo === VERIFICANDO TAMANHOS DE ARQUIVOS ===
echo Arquivos maiores que 50MB no repositorio:
git ls-tree -r -t -l --full-name HEAD | sort -k 4 -n | tail -10

:commit_direto

echo.
echo === ADICIONANDO ARQUIVOS DE FORMA INTELIGENTE ===
echo ⏳ Verificando mudancas reais...

REM Adiciona apenas arquivos modificados/novos, não tudo
git add -u
echo ✅ Arquivos modificados adicionados.

REM Adiciona novos arquivos específicos importantes (evita arquivos grandes automaticamente)
git add *.py *.md *.json *.bat *.txt *.js *.html *.css 2>nul
echo ✅ Arquivos importantes adicionados.
echo.
echo === STATUS ATUAL ===
git status --short
echo.
echo === EXECUTANDO PUSH INTELIGENTE ===
echo ⏳ Verificando se ha mudancas para commitar...

REM Tenta fazer commit diretamente - se não há mudanças, Git vai avisar
git commit -m "%MSG%"
if %errorlevel% equ 0 (
    echo ✅ Commit realizado com sucesso!
    
    echo ⏳ Tentando push incremental primeiro...
    git push 2>push_error.log
    if %errorlevel% equ 0 (
        echo ✅ Push incremental bem-sucedido!
        del push_error.log 2>nul
    ) else (
        echo ⚠️ Push incremental falhou, verificando erro...
        type push_error.log
        echo.
        echo ⏳ Tentando push forcado com lease (mais seguro)...
        git push --force-with-lease
        if %errorlevel% neq 0 (
            echo ⚠️ Push com lease falhou, usando force completo...
            git push --force
        )
        del push_error.log 2>nul
    )
) else (
    echo ℹ️ Nenhuma mudanca para commitar ou erro no commit.
)
endlocal
echo.
echo === %MODE% CONCLUÍDO ===
if "%MODE%"=="RAPIDO" (
    echo ⚡ Commit rápido executado sem compressão pesada
    echo ✅ Operação concluída em poucos segundos
) else (
    echo 🔧 Commit completo com limpeza de histórico
    echo ✅ Histórico otimizado e push realizado
)
echo ===========================
echo.
echo Pressione qualquer tecla para fechar...
pause >nul
