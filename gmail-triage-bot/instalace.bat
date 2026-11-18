@echo off
chcp 65001 >nul
cd /d "%~dp0"
title InboxAI - Instalace a spusteni

echo ===================================================
echo   InboxAI - Priprava prostredi
echo ===================================================
echo.

set "PY_CMD="
py -3 --version >nul 2>&1 && set "PY_CMD=py -3"
if "%PY_CMD%"=="" (
    python --version >nul 2>&1 && set "PY_CMD=python"
)
if "%PY_CMD%"=="" if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PY_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
)

if "%PY_CMD%"=="" (
    echo [!] Instaluji Python 3.12 (vyckejte 1-2 minuty)...
    winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
    if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
        set "PY_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
    ) else (
        echo [CHYBA] Nainstalujte Python 3 z python.org a spuste instalaci znovu.
        pause
        exit /b 1
    )
)

if not exist "..\.venv\Scripts\python.exe" (
    echo [1/2] Vytvarim virtualni prostredi...
    %PY_CMD% -m venv "..\.venv"
)

echo [2/2] Instaluji potrebne knihovny...
"..\.venv\Scripts\python.exe" -m pip install -r requirements.txt

if not exist "..\.venv\Scripts\streamlit.exe" (
    echo [CHYBA] Instalace knihoven se nezdarila.
    pause
    exit /b 1
)

echo.
echo Hotovo! Spoustim aplikaci v prohlizeci...
"..\.venv\Scripts\streamlit.exe" run dashboard.py