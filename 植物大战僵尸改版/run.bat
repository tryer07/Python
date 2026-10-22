@echo off
rem PVZ fan remake - STEP1 launcher (pure ASCII, venv path relative to this folder)
cd /d %~dp0
"..\.venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo [run.bat] Python exited with error, check messages above.
    pause
)
