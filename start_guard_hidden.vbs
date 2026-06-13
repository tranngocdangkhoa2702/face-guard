' Chay canh gac + bot Telegram NGAM (khong hien cua so gi ca)
' Da chay san thi ban moi tu thoat (chong trung bang mutex)
Dim shell, scriptDir
Set shell = CreateObject("WScript.Shell")
scriptDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
shell.Run """" & scriptDir & ".venv\Scripts\pythonw.exe"" """ & scriptDir & "guard.py""", 0, False
shell.Run """" & scriptDir & ".venv\Scripts\pythonw.exe"" """ & scriptDir & "bot.py""", 0, False
