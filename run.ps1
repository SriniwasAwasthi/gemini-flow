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
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $VenvPython = "python"
    } else {
        Write-Host "[ERROR] Python not found!" -ForegroundColor Red
        Write-Host "Please install Python 3.10+ or run scripts\setup_windows.ps1." -ForegroundColor Yellow
        Read-Host "Press Enter to exit..."
        exit 1
    }
}

Write-Host "[*] Launching Gemini Flow via virtual environment..." -ForegroundColor Green
Write-Host "[*] Global Hotkey: Press Ctrl+Space anywhere to dictate." -ForegroundColor White
Write-Host ""

& $VenvPython (Join-Path $ProjectRoot "main.py")
