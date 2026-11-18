@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONHOME="
set "PYTHONPATH="
title InboxAI - Instalace

echo ===================================================
echo   InboxAI - Priprava prostredi
echo ===================================================
echo.

:NAJIT_PYTHON
set "PY_EXE="
set "PY_ARGS="

py -3 -c "import encodings, venv" >nul 2>&1
if %errorlevel%==0 (
    set "PY_EXE=py"
    set "PY_ARGS=-3"
    goto :PYTHON_OK
)

python -c "import encodings, venv" >nul 2>&1
if %errorlevel%==0 (
    set "PY_EXE=python"
    goto :PYTHON_OK
)

for /d %%D in ("%LocalAppData%\Programs\Python\Python3*") do (
    "%%D\python.exe" -c "import encodings, venv" >nul 2>&1
    if not errorlevel 1 set "PY_EXE=%%D\python.exe"
)
if not "%PY_EXE%"=="" goto :PYTHON_OK

for /d %%D in ("C:\Program Files\Python3*" "C:\Python3*") do (
    "%%D\python.exe" -c "import encodings, venv" >nul 2>&1
    if not errorlevel 1 set "PY_EXE=%%D\python.exe"
)
if not "%PY_EXE%"=="" goto :PYTHON_OK

echo [!] V pocitaci chybi Python 3. Instaluji Python 3.12 - vyckejte 1 az 2 minuty...
winget install -e --id Python.Python.3.12 --scope user --force --accept-package-agreements --accept-source-agreements
for /d %%D in ("%LocalAppData%\Programs\Python\Python3*") do (
    "%%D\python.exe" -c "import encodings, venv" >nul 2>&1
    if not errorlevel 1 set "PY_EXE=%%D\python.exe"
)
if not "%PY_EXE%"=="" goto :PYTHON_OK

echo.
echo [CHYBA] Nepodarilo se najit ani nainstalovat Python 3.
echo Nainstalujte Python rucne z https://www.python.org/downloads/ a spuste instalace.bat znovu.
pause
exit /b 1

:PYTHON_OK
if not exist "..\.venv\Scripts\python.exe" (
    echo [1/2] Vytvarim virtualni prostredi...
    "%PY_EXE%" %PY_ARGS% -m venv "..\.venv"
    if errorlevel 1 (
        echo [CHYBA] Nepodarilo se vytvorit virtualni prostredi.
        pause
        exit /b 1
    )
)

echo [2/2] Instaluji potrebne knihovny - muze trvat 1 az 2 minuty...
"..\.venv\Scripts\python.exe" -m pip install -r requirements.txt
"..\.venv\Scripts\python.exe" -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [CHYBA] Instalace knihoven selhala. Zkontrolujte pripojeni k internetu.
    pause
    exit /b 1
)

if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit" >nul 2>&1
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    echo [general]> "%USERPROFILE%\.streamlit\credentials.toml"
    echo email = "">> "%USERPROFILE%\.streamlit\credentials.toml"
)

start "" "..\.venv\Scripts\pythonw.exe" launcher.py
exit /b 0