@echo off
rem Dang ky / dang ky lai khuon mat chu may
rem (tu tat guard truoc khi chup, chup xong tu bat lai)

echo Tam tat canh gac de tranh tranh camera...
taskkill /im pythonw.exe /f >nul 2>&1

"%~dp0.venv\Scripts\python.exe" "%~dp0enroll.py"

echo Bat lai canh gac...
start "" wscript.exe "%~dp0start_guard_hidden.vbs"
echo Xong! Canh gac dang chay ngam voi khuon mat moi.
pause
