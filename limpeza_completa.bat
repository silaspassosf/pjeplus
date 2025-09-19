@echo off
echo ========================================
echo LIMPEZA RAPIDA DE ARQUIVOS TEMPORARIOS
echo ========================================
echo.

REM Executar script Python de limpeza
python limpeza_temp.py

echo.
echo ========================================
echo LIMPEZA ADICIONAL (arquivos sistema)
echo ========================================

REM Limpar arquivos temporários do Windows na pasta do projeto
if exist "*.tmp" (
    echo Removendo arquivos .tmp...
    del /q "*.tmp" 2>nul
)

if exist "*.temp" (
    echo Removendo arquivos .temp...
    del /q "*.temp" 2>nul
)

REM Limpar logs específicos do geckodriver
if exist "geckodriver.log" (
    echo Removendo geckodriver.log...
    del /q "geckodriver.log" 2>nul
)

REM Limpar arquivos de backup do editor
if exist "*.bak" (
    echo Removendo arquivos .bak...
    del /q "*.bak" 2>nul
)

if exist "*~" (
    echo Removendo arquivos temporarios do editor...
    del /q "*~" 2>nul
)

REM Limpar pastas vazias
echo Verificando pastas vazias...
for /f "delims=" %%d in ('dir /ad /b 2^>nul') do (
    if exist "%%d" (
        rmdir "%%d" 2>nul && echo Pasta vazia removida: %%d
    )
)

echo.
echo ========================================
echo Limpeza completa finalizada!
echo ========================================
pause
