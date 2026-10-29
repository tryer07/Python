@echo off
chcp 65001 >nul
title 3D迷宫出逃
cd /d "%~dp0"

rem 优先使用项目自带的虚拟环境 Python；找不到则退回系统 python
set "PY=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo ==================================================
echo   3D迷宫出逃 正在启动游戏窗口...
echo   进入后：点鼠标左键锁定视角，WASD 移动，Shift 奔跑，
echo   收集 5 把【钥匙】，走到绿色出口即胜利；按 R 换一局。
echo   想退出游戏，按 Esc 释放鼠标后关闭窗口即可。
echo ==================================================
echo.

"%PY%" main.py

echo.
echo 游戏已退出。按任意键关闭本窗口。
pause >nul
