@echo off
chcp 65001 >nul
cd /d "%~dp0"
title InboxAI - Dashboard

if not exist "..\.venv\Scripts\streamlit.exe" (
    echo [CHYBA] Aplikace jeste neni nainstalovana. Spustte nejprve instalace.bat.
    pause
    exit /b 1
)

echo Spoustim InboxAI v prohlizeci...
"..\.venv\Scripts\streamlit.exe" run dashboard.py
if errorlevel 1 pause