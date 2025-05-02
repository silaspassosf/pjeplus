@echo off
REM Auto commit script for PjePlus project
REM Executa backup rotativo antes do commit
call backup_rotativo_selenium_pje_trt2.bat
setlocal
set MSG=Backup automático: commit programado (%DATE% %TIME%)
git add -A
git commit -m "%MSG%"
git push
endlocal
