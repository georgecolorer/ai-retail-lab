@echo off
chcp 65001 >nul
color 0B
echo.
echo ===================================================
echo     InboxAI - Automaticka instalace pro klienta
echo ===================================================
echo.
echo [1/4] Pripravuji virtualni prostredi pro bezpecny beh...
cd /d "%~dp0"
if not exist "..\.venv" (
    python -m venv ..\.venv
)

echo [2/4] Instaluji potrebne moduly (toto muze chvili trvat)...
..\.venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
..\.venv\Scripts\pip.exe install -r requirements.txt >nul 2>&1

:: Vytvori globalni nastaveni Streamlitu, aby se nikdy neptal na e-mail
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
(
echo [general]
echo email = ""
) > "%USERPROFILE%\.streamlit\credentials.toml"

echo [3/4] Registruji automaticke trideni na pozadi do Windows...
schtasks /delete /tn "InboxAI_Trideni" /f >nul 2>&1
schtasks /create /tn "InboxAI_Trideni" /tr "\"%~dp0..\.venv\Scripts\pythonw.exe\" \"%~dp0triage_bot.py\"" /sc minute /mo 30 /np /ru SYSTEM /f >nul 2>&1
echo   - Automaticke trideni nastaveno na kazdych 30 minut.

echo [4/4] Spoustim ridici centrum (Dashboard)...
echo.
echo Hotovo! Oteviram prohlizec. Pro ukonceni tohoto okna stisknete libovolnou klavesu.
start "" "..\.venv\Scripts\streamlit.exe" run dashboard.py --browser.gatherUsageStats false
pause >nul