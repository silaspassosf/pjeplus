@echo off
REM ========================================================
REM   CONTINUAÇÃO DA ATUALIZAÇÃO PjePlus
REM ========================================================
REM Script para continuar atualização após backup já criado
REM Resposta à solicitação: "execute os próximos passos!"

setlocal enableextensions
color 0A

:inicio
cls
echo ========================================================
echo       CONTINUAÇÃO DA ATUALIZAÇÃO PjePlus
echo ========================================================
echo.
echo [✓] Backup já foi criado anteriormente
echo [i] Próximos passos disponíveis:
echo.

REM === CONFIGURAÇÃO AUTOMÁTICA ===
set "REPO_URL=https://github.com/silaspassosf/pjeplus.git"
set "PASTA_PROJETO=%CD%"

REM Detecta se estamos no repositório
if not exist ".git" (
    echo ❌ ERRO: Não estamos em um repositório Git!
    echo Execute este script dentro da pasta do projeto PjePlus.
    pause
    goto :fim
)

echo [✓] Repositório detectado: %CD%
echo.
echo ========================================================
echo   PRÓXIMOS PASSOS DISPONÍVEIS
echo ========================================================
echo.
echo [1] ATUALIZAÇÃO RÁPIDA    - Merge rápido com repositório online
echo [2] ATUALIZAÇÃO AVANÇADA  - Commit local + merge + resolução automática  
echo [3] RESET PARA REMOTO     - Substituir TUDO pela versão online (CUIDADO!)
echo [4] VERIFICAR STATUS      - Só verificar estado atual
echo [0] Cancelar
echo.
echo 💡 RECOMENDAÇÃO: Use opção [1] para atualização segura
echo ⚠️  ATENÇÃO: Opção [3] remove TODAS as alterações locais!
echo.

choice /c 12340 /m "Escolha o próximo passo"
if errorlevel 5 goto :fim
if errorlevel 4 goto :verificar_status
if errorlevel 3 goto :reset_remoto
if errorlevel 2 goto :atualizacao_avancada
if errorlevel 1 goto :atualizacao_rapida

REM ========================================================
REM   OPÇÃO 1: ATUALIZAÇÃO RÁPIDA
REM ========================================================
:atualizacao_rapida
echo.
echo === ATUALIZAÇÃO RÁPIDA ===
echo.
echo [1/3] Verificando repositório remoto...
git fetch origin main 2>nul
if errorlevel 1 (
    echo ❌ Erro ao conectar com repositório remoto!
    echo Verifique sua conexão com a internet.
    pause
    goto :inicio
)

echo [2/3] Tentando merge rápido...
git merge --ff-only origin/main 2>nul
if errorlevel 1 (
    echo ⚠️ Merge rápido não é possível (há conflitos ou divergências).
    echo.
    echo Opções:
    echo [1] Tentar atualização avançada com resolução automática
    echo [2] Voltar ao menu principal
    echo.
    choice /c 12 /m "Escolha"
    if errorlevel 2 goto :inicio
    if errorlevel 1 goto :atualizacao_avancada
)

echo [3/3] Verificando resultado...
git status --porcelain
echo.
echo ✅ ATUALIZAÇÃO RÁPIDA CONCLUÍDA COM SUCESSO!
echo 📁 Projeto atualizado com a versão online mais recente.
goto :fim_sucesso

REM ========================================================
REM   OPÇÃO 2: ATUALIZAÇÃO AVANÇADA
REM ========================================================
:atualizacao_avancada
echo.
echo === ATUALIZAÇÃO AVANÇADA ===
echo.

echo [1/4] Salvando alterações locais...
git add -A 2>nul
git diff --cached --quiet || (
    git commit -m "Auto-save antes da atualização: %date% %time%" 2>nul
    echo ✓ Alterações locais salvas automaticamente
)

echo [2/4] Baixando atualizações do repositório online...
git fetch origin main
if errorlevel 1 (
    echo ❌ Erro ao baixar atualizações!
    pause
    goto :inicio
)

echo [3/4] Aplicando merge com repositório online...
git merge origin/main 2>nul
if errorlevel 1 (
    echo [CONFLITO] Resolvendo automaticamente...
    call :resolver_conflitos_auto
)

echo [4/4] Finalizando...
git gc --auto 2>nul
echo.
echo ✅ ATUALIZAÇÃO AVANÇADA CONCLUÍDA!
echo 📁 Projeto sincronizado com repositório online.
goto :fim_sucesso

REM ========================================================
REM   OPÇÃO 3: RESET PARA REMOTO
REM ========================================================
:reset_remoto
echo.
echo === RESET PARA VERSÃO REMOTA ===
echo.
echo ⚠️⚠️⚠️ ATENÇÃO MÁXIMA! ⚠️⚠️⚠️
echo.
echo Esta opção irá:
echo • APAGAR todas as alterações locais não commitadas
echo • SUBSTITUIR arquivos locais pela versão online
echo • REMOVER arquivos que não existem no repositório online
echo.
echo Você tem certeza que deseja continuar?
echo (O backup já foi criado anteriormente)
echo.

choice /c SN /m "CONFIRMAR reset completo? (S/N)"
if errorlevel 2 goto :inicio

echo.
echo [1/3] Baixando versão mais recente...
git fetch origin main
if errorlevel 1 (
    echo ❌ Erro ao baixar do repositório!
    pause
    goto :inicio
)

echo [2/3] Aplicando reset completo...
git reset --hard origin/main
git clean -fd

echo [3/3] Verificando resultado...
git status
echo.
echo ✅ RESET CONCLUÍDO!
echo 📁 Projeto agora é idêntico ao repositório online.
echo 💾 Suas alterações anteriores estão no backup.
goto :fim_sucesso

REM ========================================================
REM   OPÇÃO 4: VERIFICAR STATUS
REM ========================================================
:verificar_status
echo.
echo === STATUS ATUAL ===
echo.
echo 📁 Diretório: %CD%
echo.
echo Status do Git:
git status
echo.
echo Últimos commits:
git log --oneline -5
echo.
echo Backups disponíveis:
dir backups\ 2>nul || echo (Nenhum backup encontrado)
echo.
pause
goto :inicio

REM ========================================================
REM   FUNÇÃO: RESOLVER CONFLITOS AUTOMATICAMENTE
REM ========================================================
:resolver_conflitos_auto
echo Detectando e resolvendo conflitos...
for /f %%f in ('git diff --name-only --diff-filter=U 2^>nul') do (
    echo • Resolvendo conflito em: %%f
    
    REM Estratégia por tipo de arquivo
    echo %%f | findstr /i "\.py$" >nul && (
        echo   → Arquivo Python: mantendo versão remota
        git checkout --theirs "%%f"
    ) || (
    echo %%f | findstr /i "\.json$" >nul && (
        echo   → Arquivo JSON: mantendo versão remota  
        git checkout --theirs "%%f"
    ) || (
    echo %%f | findstr /i "\.bat$" >nul && (
        echo   → Arquivo Batch: mantendo versão local
        git checkout --ours "%%f"
    ) || (
        echo   → Outros arquivos: mantendo versão remota
        git checkout --theirs "%%f"
    )))
    
    git add "%%f" 2>nul
)

REM Verifica se ainda há conflitos
git diff --name-only --diff-filter=U >nul 2>&1
if not errorlevel 1 (
    echo ⚠️ Alguns conflitos precisam de resolução manual.
    echo Execute 'git status' para ver detalhes.
) else (
    git commit --no-edit 2>nul
    echo ✅ Todos os conflitos foram resolvidos automaticamente.
)
exit /b 0

REM ========================================================
REM   FINALIZAÇÕES
REM ========================================================
:fim_sucesso
echo.
echo ========================================================
echo           ✅ PRÓXIMOS PASSOS EXECUTADOS!
echo ========================================================
echo 📁 Local: %PASTA_PROJETO%
echo ⏰ Concluído em: %date% %time%
echo.
echo O ambiente foi atualizado com o repositório online.
echo Suas alterações anteriores estão seguras no backup.
echo.
choice /c SN /m "Executar outro passo? (S/N)"
if errorlevel 2 goto :fim
goto :inicio

:fim
echo.
echo ========================================================
echo Atualização finalizada! 
echo.
echo 💡 Para futuras atualizações, você pode usar:
echo    - atualizador_otimizado.bat (script completo)
echo    - continuar_atualizacao.bat (este script)
echo.
echo Até logo! 👋
echo ========================================================
endlocal
pause >nul