# ==============================================================================
# Gemini Flow - PowerShell Application Launcher
# ==============================================================================
$ProjectRoot = $PSScriptRoot
Set-Location -Path $ProjectRoot

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "             Gemini Flow - AI Voice Dictation Engine            " -ForegroundColor Yellow
Write-Host "          Zero-Truncation Hybrid Speech-to-Text System          " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$VenvPython = $null
if (Test-Path (Join-Path $ProjectRoot ".venv\Scripts\python.exe")) {
    $VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
} elseif (Test-Path (Join-Path $ProjectRoot "venv\Scripts\python.exe")) {
    $VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
}

if (-not $VenvPython) {
    Write-Host "[ERROR] Virtual environment not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run scripts\setup_windows.ps1 first to set up Gemini Flow." -ForegroundColor Yellow
    Write-Host "Command:" -ForegroundColor White
    Write-Host "    powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1" -ForegroundColor Cyan
    Write-Host ""
    Read-Host "Press Enter to exit..."
    exit 1
}

Write-Host "[*] Launching Gemini Flow via virtual environment..." -ForegroundColor Green
Write-Host "[*] Global Hotkey: Press Ctrl+Space anywhere to dictate." -ForegroundColor White
Write-Host ""

& $VenvPython (Join-Path $ProjectRoot "main.py")
