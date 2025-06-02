@echo off
REM Batch script para executar o script p2.py diretamente no PowerShell

REM Navegar para o diretório do script
cd /d "c:\Users\s164283\Desktop\Pjeplus\pjeplus"

REM Executar o script Python no PowerShell
powershell -Command "python p2.py"

REM Pausar para visualizar a saída
pause