@echo off
setlocal enabledelayedexpansion
title Gemini Flow - AI Voice Dictation & Real-Time Assistant
cd /d "%~dp0"

echo ================================================================
echo             Gemini Flow - AI Voice Dictation Engine
echo          Zero-Truncation Hybrid Speech-to-Text System
echo ================================================================
echo.

:: 1. Check for Virtual Environment or Runtime
set "PYTHON_EXE="
if exist ".\runtime\python.exe" (
    set "PYTHON_EXE=.\runtime\python.exe"
) else if exist ".\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=.\.venv\Scripts\python.exe"
) else if exist ".\venv\Scripts\python.exe" (
    set "PYTHON_EXE=.\venv\Scripts\python.exe"
) else if exist "E:\PYTHON\python.exe" (
    set "PYTHON_EXE=E:\PYTHON\python.exe"
)

if "%PYTHON_EXE%"=="" (
    where python >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "PYTHON_EXE=python"
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python not found!
    echo Please install Python 3.10+ or run scripts\setup_windows.ps1.
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
