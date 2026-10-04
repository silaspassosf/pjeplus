@echo off
title Capturador de Prints para PDF (Google Drive)
chcp 65001 > nul
cd /d "%~dp0"
py GASTOS\capturador_print.py
pause
