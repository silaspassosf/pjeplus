@echo off
echo ==========================================
echo Script para Push e Limpeza do GitHub
echo Repositorio: https://github.com/silaspassosf/pjeplus/
echo ==========================================
echo.

:: Verifica se estamos na pasta certa
if not exist ".git" (
    echo Inicializando repositorio Git...
    git init
    echo.
)

:: Remove origem remota existente (se houver) e adiciona a nova
echo Configurando origem remota...
git remote remove origin 2>nul
git remote add origin https://github.com/silaspassosf/pjeplus.git
echo.

:: Adiciona todos os arquivos
echo Adicionando arquivos ao controle de versao...
git add .
echo.

:: Faz o commit com timestamp
echo Fazendo commit...
for /f "tokens=2-4 delims=/ " %%i in ('date /t') do set mydate=%%k-%%i-%%j
for /f "tokens=1-2 delims=/:" %%i in ('time /t') do set mytime=%%i:%%j
git commit -m "Auto commit - %mydate% %mytime%"
echo.

:: Faz push forçado (substitui completamente o repositorio remoto)
echo Fazendo push forcado para substituir o repositorio...
echo AVISO: Isso substituira COMPLETAMENTE o conteudo do repositorio GitHub!
pause
git push -f origin main
echo.

if %errorlevel% neq 0 (
    echo Tentando com branch master...
    git push -f origin master
)

echo.
echo ==========================================
echo Push concluido!
echo O repositorio GitHub foi substituido pelo conteudo local.
echo ==========================================
pause