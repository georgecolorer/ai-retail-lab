@echo off
cd /d "%~dp0"
if not exist "..\.venv\Scripts\python.exe" (
    echo Aplikace jeste neni nainstalovana. Spustte nejprve instalace.bat.
    pause
    exit /b 1
)
"..\.venv\Scripts\python.exe" launcher.py
exit /b 0