@echo off
cd /d %~dp0
call limpar_temp.bat
cls
python m1.py
pause
