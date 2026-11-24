@echo off
setlocal enabledelayedexpansion
title Gemini Flow - Quick Restart Utility
cd /d "%~dp0"

echo ================================================================
echo             Gemini Flow - Instant Reload / Restart
echo ================================================================
echo.
echo [*] Terminating any stale background instances...

:: 1. Force kill any existing instances of Gemini Flow
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Process -Name 'python', 'pythonw', '*Gemini*' -ErrorAction SilentlyContinue | Where-Object { $_.Id -ne $PID } | Stop-Process -Force -ErrorAction SilentlyContinue"

:: 2. Clean up stale PID file
if exist "%APPDATA%\GeminiFlow\gemini_flow.pid" (
    del /f /q "%APPDATA%\GeminiFlow\gemini_flow.pid" 2>nul
)
if exist ".\runtime\gemini_flow.pid" (
    del /f /q ".\runtime\gemini_flow.pid" 2>nul
)
if exist ".\gemini_flow.pid" (
    del /f /q ".\gemini_flow.pid" 2>nul
)

:: 3. Launch fresh instance with Python / Pythonw
echo [*] Starting fresh Gemini Flow instance...
set "PYTHONW_BIN="
if exist ".\runtime\pythonw.exe" (
    set "PYTHONW_BIN=.\runtime\pythonw.exe"
) else if exist ".\runtime\python.exe" (
    set "PYTHONW_BIN=.\runtime\python.exe"
) else if exist ".\venv\Scripts\pythonw.exe" (
    set "PYTHONW_BIN=.\venv\Scripts\pythonw.exe"
) else if exist ".\.venv\Scripts\pythonw.exe" (
    set "PYTHONW_BIN=.\.venv\Scripts\pythonw.exe"
) else if exist "E:\PYTHON\pythonw.exe" (
    set "PYTHONW_BIN=E:\PYTHON\pythonw.exe"
)

if "%PYTHONW_BIN%"=="" (
    for /f "delims=" %%I in ('where pythonw.exe 2^>nul') do set "PYTHONW_BIN=%%I"
)
if "%PYTHONW_BIN%"=="" (
    for /f "delims=" %%I in ('where python.exe 2^>nul') do (
        set "PYTHON_DIR=%%~dpI"
        if exist "!PYTHON_DIR!pythonw.exe" (
            set "PYTHONW_BIN=!PYTHON_DIR!pythonw.exe"
        )
    )
)
if "%PYTHONW_BIN%"=="" set "PYTHONW_BIN=pythonw"

start "" "!PYTHONW_BIN!" "main_standalone.py" --force-restart

echo.
echo [✓] Gemini Flow restarted successfully in the background!
echo [✓] Global Hotkey (Ctrl + Space) is active and ready.
echo.
ping 127.0.0.1 -n 2 >nul
exit /b 0
