@echo off
chcp 65001 > nul
title PJePlus - Capturador de Holerites com Tarja de Privacidade
cls
echo ======================================================================
echo    PJePlus - Capturador de Holerites (Tarja e Sequencia Mensal)
echo ======================================================================
echo.
py GASTOS\capturador_holerite.py %*
pause

