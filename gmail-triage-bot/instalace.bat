@echo off
chcp 65001 >nul
cd /d "%~dp0"
title InboxAI - Instalace a spusteni

echo ===================================================
echo   InboxAI - Priprava prostredi
echo ===================================================
echo.

:HLEDAT_PYTHON
set "PY_EXE="
set "PY_ARGS="

py -3 -c "import venv" >nul 2>&1
if %errorlevel%==0 (
    set "PY_EXE=py"
    set "PY_ARGS=-3"
    goto :PYTHON_NALEZEN
)

python -c "import venv" >nul 2>&1
if %errorlevel%==0 (
    set "PY_EXE=python"
    goto :PYTHON_NALEZEN
)

for /d %%D in ("%LocalAppData%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" set "PY_EXE=%%D\python.exe"
)
if not "%PY_EXE%"=="" goto :PYTHON_NALEZEN

for /d %%D in ("C:\Program Files\Python3*" "C:\Program Files (x86)\Python3*" "C:\Python3*") do (
    if exist "%%D\python.exe" set "PY_EXE=%%D\python.exe"
)
if not "%PY_EXE%"=="" goto :PYTHON_NALEZEN

if exist "%UserProfile%\anaconda3\python.exe" set "PY_EXE=%UserProfile%\anaconda3\python.exe"
if exist "%UserProfile%\miniconda3\python.exe" set "PY_EXE=%UserProfile%\miniconda3\python.exe"
if not "%PY_EXE%"=="" goto :PYTHON_NALEZEN

echo [!] V tomto pocitaci neni nainstalovany Python 3.
echo Spoustim automatickou instalaci Pythonu 3.12 (vyckejte, muze trvat 1-2 minuty)...
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
if %errorlevel%==0 (
    echo Python byl uspesne nainstalovan. Pokracuji...
    goto :HLEDAT_PYTHON
)

echo.
echo [CHYBA] Automaticka instalace Pythonu se nezdarila.
echo Nainstalujte Python rucne z https://www.python.org/downloads/ (zaskrtnete "Add Python to PATH") a spuste instalace.bat znovu.
pause
exit /b 1

:PYTHON_NALEZEN
if not exist "..\.venv\Scripts\python.exe" (
    echo [1/3] Vytvarim virtualni prostredi...
    "%PY_EXE%" %PY_ARGS% -m venv "..\.venv"
    if errorlevel 1 (
        echo [CHYBA] Nepodarilo se vytvorit virtualni prostredi.
        pause
        exit /b 1
    )
)

echo [2/3] Instaluji potrebne knihovny (muze trvat 1-2 minuty)...
"..\.venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
"..\.venv\Scripts\python.exe" -m pip install -r requirements.txt
if not exist "..\.venv\Scripts\streamlit.exe" (
    echo.
    echo [CHYBA] Instalace knihoven selhala. Zkontrolujte pripojeni k internetu a zkuste to znovu.
    pause
    exit /b 1
)

echo [3/3] Nastavuji automaticke trideni na pozadi...
schtasks /create /tn "InboxAI_Trideni" /tr "\"%~dp0..\.venv\Scripts\pythonw.exe\" \"%~dp0triage_bot.py\"" /sc minute /mo 30 /f >nul 2>&1

echo.
echo Hotovo! Spoustim aplikaci v prohlizeci...
start "" "..\.venv\Scripts\streamlit.exe" run dashboard.py