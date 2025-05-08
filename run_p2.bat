@echo off
cd /d %~dp0
call limpar_temp.bat
cls
python p2.py
pause
