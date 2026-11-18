@echo off
cd /d "%~dp0"
start "" "..\.venv\Scripts\streamlit.exe" run dashboard.py --browser.gatherUsageStats false
