@echo off
REM teste_sisbajud_corrigido.bat
REM Executa o teste corrigido do SISBAJUD independente

echo ====================================
echo TESTE SISBAJUD CORRIGIDO
echo ====================================
echo.

cd /d "d:\PjePlus"

echo Executando teste do SISBAJUD corrigido...
python teste_sisbajud_corrigido.py

echo.
echo Pressione qualquer tecla para sair...
pause >nul
