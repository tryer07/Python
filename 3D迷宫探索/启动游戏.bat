@echo off
title 3D Maze Launcher
cd /d "%~dp0"

set "PY=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo Starting 3D maze game window, please wait...
echo In game: click to lock mouse, WASD to move, Shift to run,
echo collect 5 keys, reach the green exit to win, press R for a new maze.
echo Press Esc to release mouse, then close the window to quit.
echo.

"%PY%" main.py

echo.
echo Game exited. Press any key to close this window.
pause >nul
