@echo off
setlocal enabledelayedexpansion
title Gemini Flow - AI Voice Dictation & Real-Time Assistant
cd /d "%~dp0"

echo ================================================================
echo             Starting Gemini Flow Setup & Launcher
echo       AI Voice Dictation & Context-Aware Assistant
echo ================================================================
echo.

:: 1. Check for Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found on your system!
    echo Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Auto-create Virtual Environment and install packages if needed
if not exist ".\venv\Scripts\python.exe" (
    echo [*] Setting up virtual environment (venv)...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [*] Installing dependencies from requirements.txt...
    .\venv\Scripts\pip.exe install -r requirements.txt
)

:: 3. Launch Application
echo [*] Launching Gemini Flow...
echo.
if exist ".\venv\Scripts\python.exe" (
    .\venv\Scripts\python.exe main.py
) else (
    python main.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [INFO] Application session closed.
)

