@echo off
rem Dung canh gac (vi du: cho ban muon may choi game)
rem Chi tat guard.py - bot Telegram van song de con bat lai tu xa (/start_guard)
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'guard\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo.
echo  ============================================
echo   DA DUNG CANH GAC - may khong duoc bao ve!
echo  ============================================
echo.
echo  Bat lai: nhay dup shortcut "Bat canh gac"
echo  (hoac nhan /start_guard cho bot Telegram,
echo   hoac khoi dong lai may - guard tu bat)
echo.
pause
