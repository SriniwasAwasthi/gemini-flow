@echo off
setlocal enabledelayedexpansion
title Gemini Flow - AI Voice Dictation & Real-Time Assistant
cd /d "%~dp0"

echo ================================================================
echo             Gemini Flow - AI Voice Dictation Engine
echo          Zero-Truncation Hybrid Speech-to-Text System
echo ================================================================
echo.

:: 1. Check for Virtual Environment
set "PYTHON_EXE="
if exist ".\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=.\.venv\Scripts\python.exe"
) else if exist ".\venv\Scripts\python.exe" (
    set "PYTHON_EXE=.\venv\Scripts\python.exe"
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Virtual environment not found!
    echo.
    echo Please run scripts\setup_windows.ps1 first to set up Gemini Flow.
    echo In PowerShell, execute:
    echo     powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
    echo.
    pause
    exit /b 1
)

:: 2. Launch Application
echo [*] Launching Gemini Flow via virtual environment...
echo [*] Global Hotkey: Press Ctrl+Space anywhere to dictate.
echo.
%PYTHON_EXE% main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [INFO] Application session closed.
)
