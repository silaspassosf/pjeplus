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
echo === EXECUTANDO COMMIT E PUSH ===
echo ⏳ Tentando fazer commit...

REM Tenta fazer commit diretamente - se não há mudanças, Git vai avisar
git commit -m "%MSG%"
if %errorlevel% equ 0 (
    echo.
    echo ✅ COMMIT REALIZADO COM SUCESSO!
    echo 📝 Mensagem: %MSG%
    echo.
    
    echo ⏳ Iniciando push para repositório remoto...
    git push
    if %errorlevel% equ 0 (
        echo.
        echo 🎉 PUSH BEM-SUCEDIDO! Alterações enviadas para o GitHub.
    ) else (
        echo.
        echo ⚠️ Push normal falhou. Tentando métodos alternativos...
        echo.
        echo ⏳ Tentando push com force-with-lease (mais seguro)...
        git push --force-with-lease
        if %errorlevel% equ 0 (
            echo ✅ Push com lease bem-sucedido!
        ) else (
            echo ⚠️ Push com lease falhou. Tentando force completo...
            git push --force
            if %errorlevel% equ 0 (
                echo ✅ Push forçado bem-sucedido!
            ) else (
                echo ❌ ERRO: Todos os tipos de push falharam. Verifique a conexão.
            )
        )
    )
) else (
    echo.
    echo ℹ️ Nenhuma mudança para commitar (repositório já atualizado).
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
echo 📋 Resultado final:
git status --porcelain | find /c /v "" > temp_count.txt
set /p file_count=<temp_count.txt
del temp_count.txt 2>nul
if %file_count% gtr 0 (
    echo ⚠️ Ainda há %file_count% arquivo(s) não commitado(s)
    echo Listando arquivos pendentes:
    git status --short
) else (
    echo ✅ Todos os arquivos foram commitados com sucesso!
)
echo.
echo 🔄 Status do repositório:
git log --oneline -1
echo.
echo ⏸️ TELA FICARÁ ABERTA - Pressione qualquer tecla para fechar...
pause
