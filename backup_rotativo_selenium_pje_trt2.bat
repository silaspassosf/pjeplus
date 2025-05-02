@echo off
REM Script de backup rotativo para Mandado.py e Prazo.py
REM Mantém sempre as 5 versões mais recentes de cada

setlocal
set "DIR=%~dp0"

for %%F in (Mandado.py Prazo.py) do (
    if exist "%DIR%%%F.bak5" del "%DIR%%%F.bak5"
    if exist "%DIR%%%F.bak4" ren "%DIR%%%F.bak4" "%%F.bak5"
    if exist "%DIR%%%F.bak3" ren "%DIR%%%F.bak3" "%%F.bak4"
    if exist "%DIR%%%F.bak2" ren "%DIR%%%F.bak2" "%%F.bak3"
    if exist "%DIR%%%F.bak1" ren "%DIR%%%F.bak1" "%%F.bak2"
    if exist "%DIR%%%F" copy /Y "%DIR%%%F" "%DIR%%%F.bak1" >nul
)
endlocal
