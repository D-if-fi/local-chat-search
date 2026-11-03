@echo off
chcp 65001 >nul
title 聊天记录检索
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
    python app\server.py 8777
    goto :done
)

where py >nul 2>nul
if %errorlevel%==0 (
    py app\server.py 8777
    goto :done
)

echo 未检测到 Python。
echo 请先安装 Python 3.8 或更高版本：https://www.python.org/downloads/
echo 安装时请勾选 "Add Python to PATH"。
echo.

:done
pause
