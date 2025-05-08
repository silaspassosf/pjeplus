@echo off
cd /d %~dp0
REM Remove arquivos temporários comuns do Windows e do Python
if exist __pycache__ rmdir /s /q __pycache__
del /q /f *.pyc
for %%f in (*.tmp *.log *.bak *.temp *.cache) do del /q /f "%%f"
REM Remove screenshots de erro
for %%f in (erro_ato_*.png) do del /q /f "%%f"
echo Temporários removidos.
pause
