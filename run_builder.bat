@echo off
REM === 设置窗口标题 ===
title CAE Knowledge Base Builder Launcher

REM === 切换到当前脚本所在的目录 (防止因为“以管理员身份运行”导致路径错误) ===
cd /d "%~dp0"

echo Starting Ansys Knowledge Base Builder...
echo.

REM === 运行 Python 入口脚本 ===
python main_gui.py

REM === 如果程序异常退出（返回码不为0），则暂停显示错误信息 ===
if %errorlevel% neq 0 (
    echo.
    echo [Error] The application crashed or closed unexpectedly.
    echo Please check the error message above.
    pause
)