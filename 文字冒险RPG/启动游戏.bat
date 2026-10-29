@echo off
title RPG Server Launcher
cd /d "%~dp0"

set "PY=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo Starting game server, please wait...
echo A browser window will open automatically at:  http://127.0.0.1:8001
echo Keep this window open while playing. Close it to stop the game.
echo.

"%PY%" main.py

echo.
echo Server exited. Press any key to close this window.
pause >nul
