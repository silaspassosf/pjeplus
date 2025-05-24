@echo off
REM Limpa temporários do VS Code e do projeto PjePlus

REM Limpa cache e temporários do VS Code
setlocal enableextensions
set "VSCODE_CACHE=%APPDATA%\Code\Cache"
set "VSCODE_CACHEDDATA=%APPDATA%\Code\CachedData"
set "VSCODE_CODECACHE=%APPDATA%\Code\Code Cache"
set "VSCODE_WORKSPACESTORAGE=%APPDATA%\Code\User\workspaceStorage"

for %%A in ("%VSCODE_CACHE%" "%VSCODE_CACHEDDATA%" "%VSCODE_CODECACHE%" "%VSCODE_WORKSPACESTORAGE%") do (
    if exist %%A (
        echo Limpando %%A ...
        del /q /s %%A\* 2>nul
        for /d %%B in (%%A\*) do rd /s /q "%%B" 2>nul
    )
)

REM Limpa __pycache__ e arquivos .pyc do projeto atual
cd /d "%~dp0"
for /r %%F in (__pycache__) do rd /s /q "%%F"
for /r %%F in (*.pyc) do del /q "%%F"

echo Limpeza concluida!
pause
