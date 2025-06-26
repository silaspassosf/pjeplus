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
echo === EXECUTANDO PUSH ===
git push
endlocal
echo.
echo ===========================
echo Operacao concluida!
echo ===========================
pause
