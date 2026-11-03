@echo off
rem local-chat-search - Windows one-click start (double-click this file)
chcp 65001 >nul
title local-chat-search
cd /d "%~dp0"

set "PORT=%~1"
if "%PORT%"=="" set "PORT=%CHAT_SEARCH_PORT%"
if "%PORT%"=="" set "PORT=8777"

py -3 -c "import sys;sys.exit(0 if sys.version_info>=(3,8) else 1)" >nul 2>nul
if not errorlevel 1 goto use_py

python -c "import sys;sys.exit(0 if sys.version_info>=(3,8) else 1)" >nul 2>nul
if not errorlevel 1 goto use_python

python3 -c "import sys;sys.exit(0 if sys.version_info>=(3,8) else 1)" >nul 2>nul
if not errorlevel 1 goto use_python3

echo.
echo [X] Python 3.8+ not found.
echo     未检测到 Python 3.8 或更高版本。
echo     请到 https://www.python.org/downloads/ 下载安装，
echo     安装时务必勾选 "Add python.exe to PATH"。
echo.
pause
exit /b 1

:use_py
echo Using: py -3   Port: %PORT%
py -3 app\server.py --port %PORT%
goto done

:use_python
echo Using: python   Port: %PORT%
python app\server.py --port %PORT%
goto done

:use_python3
echo Using: python3   Port: %PORT%
python3 app\server.py --port %PORT%
goto done

:done
echo.
echo Service stopped. 服务已停止。
pause
