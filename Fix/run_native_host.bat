@echo off
echo %DATE% %TIME% > "%TEMP%\infojud_bridge_host_started.txt"
"C:\Python313\python.exe" -u "d:\PjePlus\___001\xx\Fix\native_host.py" 1>>"%TEMP%\infojud_bridge_stdout.log" 2>>"%TEMP%\infojud_bridge_stderr.log"