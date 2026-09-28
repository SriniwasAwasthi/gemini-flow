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
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe' -or $_.Name -like '*Gemini Flow*') -and ($_.CommandLine -like '*main_standalone.py*' -or $_.CommandLine -like '*main.py*' -or $_.CommandLine -like '*Wisper*') -and $_.ProcessId -ne $PID } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

:: 2. Clean up stale PID file
if exist "%APPDATA%\GeminiFlow\gemini_flow.pid" (
    del /f /q "%APPDATA%\GeminiFlow\gemini_flow.pid" 2>nul
)

:: 3. Launch fresh instance with Python / Pythonw
echo [*] Starting fresh Gemini Flow instance...
if exist ".\venv\Scripts\pythonw.exe" (
    start "" ".\venv\Scripts\pythonw.exe" "main_standalone.py" --force-restart
) else if exist ".\venv\Scripts\python.exe" (
    start "" ".\venv\Scripts\python.exe" "main_standalone.py" --force-restart
) else (
    start "" pythonw "main_standalone.py" --force-restart
)

echo.
echo [✓] Gemini Flow restarted successfully in the background!
echo [✓] Global Hotkey (Ctrl + Space) is active and ready.
echo.
timeout /t 2 >nul
exit /b 0
