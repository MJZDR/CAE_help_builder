@echo off
title CAE KB Builder - Auto Setup
cd /d "%~dp0"

echo ==================================================
echo      Checking Environment & Dependencies...
echo ==================================================

REM 1. 检查是否有 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Python not found! 
    echo Please install Python 3.x and add it to PATH.
    pause
    exit /b
)

REM 2. 自动安装/更新当前包 (静默模式，除非出错)
echo Installing package in editable mode...
pip install -e . 
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b
)

echo.
echoDependencies ready. Launching GUI...
echo ==================================================

REM 3. 启动 GUI
start /w python main_gui.py

REM 4. 只有在 Python 报错时才暂停，正常关闭则直接退出 cmd 窗口
if %errorlevel% neq 0 (
    pause
)