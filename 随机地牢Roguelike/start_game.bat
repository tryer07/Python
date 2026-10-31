@echo off
title Roguelike Dungeon Launcher
cd /d "%~dp0"

set "PY=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo Starting roguelike dungeon window, please wait...
echo In game: Arrow keys or WASD to move and bump-attack,
echo Space to wait one turn, walk onto the stairs to descend.
echo A bard (DeepSeek) writes your death report when you fall.
echo Press Esc to quit.
echo.

"%PY%" game.py

echo.
echo Game exited. Press any key to close this window.
pause >nul
