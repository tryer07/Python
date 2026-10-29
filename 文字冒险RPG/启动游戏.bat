@echo off
chcp 65001 >nul
title 废土余生 - 文字冒险RPG
cd /d "%~dp0"

rem 优先使用项目自带的虚拟环境 Python；找不到则退回系统 python
set "PY=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo ==================================================
echo   废土余生 · AI 文字冒险RPG 正在启动...
echo   启动成功后会自动打开浏览器；若没有，请手动访问：
echo       http://127.0.0.1:8001
echo   想停止游戏，直接关闭本窗口即可。
echo ==================================================
echo.

"%PY%" main.py

echo.
echo 服务已退出。按任意键关闭本窗口。
pause >nul
