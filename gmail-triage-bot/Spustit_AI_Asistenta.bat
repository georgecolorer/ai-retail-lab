@echo off
cd /d "%~dp0"
if not exist "..\.venv\Scripts\pythonw.exe" (
    echo Aplikace jeste neni nainstalovana. Spustte nejprve 2_Instalace_InboxAI.bat.
    pause
    exit /b 1
)
start "" "..\.venv\Scripts\pythonw.exe" launcher.py
exit