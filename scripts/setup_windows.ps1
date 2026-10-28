# ==============================================================================
# Gemini Flow - Automated Windows Setup Script
# Configures Python 3.10+, Virtual Environment, Neural Weights, and Mic Check
# ==============================================================================
param (
    [switch]$SkipModelDownload = $false,
    [string]$WhisperModel = "small.en"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location -Path $ProjectRoot

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "                Gemini Flow - Windows Setup Pipeline                 " -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "Root Directory: $ProjectRoot" -ForegroundColor DarkGray
Write-Host ""

# -----------------------------------------------------------------------------
# 1. Verify Python 3.10+
# -----------------------------------------------------------------------------
Write-Host "[1/6] Checking Python installation..." -ForegroundColor Yellow

$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
}

if (-not $pythonCmd) {
    Write-Host "[ERROR] Python was not found on your system PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10 or newer from https://www.python.org/downloads/" -ForegroundColor White
    Write-Host "IMPORTANT: Check 'Add python.exe to PATH' during installation." -ForegroundColor Yellow
    exit 1
}

$pyVerStr = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$major = [int]($pyVerStr.Split('.')[0])
$minor = [int]($pyVerStr.Split('.')[1])

if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
    Write-Host "[ERROR] Python $pyVerStr detected. Gemini Flow requires Python 3.10 or newer." -ForegroundColor Red
    exit 1
}
Write-Host "Found Python $pyVerStr ($pythonCmd) - Supported!" -ForegroundColor Green

# -----------------------------------------------------------------------------
# 2. Virtual Environment Setup
# -----------------------------------------------------------------------------
Write-Host "`n[2/6] Configuring Virtual Environment (.venv)..." -ForegroundColor Yellow
$VenvDir = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating fresh virtual environment in .venv..." -ForegroundColor DarkGray
    & $pythonCmd -m venv "$VenvDir"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
}
Write-Host "Virtual environment ready at: $VenvDir" -ForegroundColor Green

# -----------------------------------------------------------------------------
# 3. Install Dependencies
# -----------------------------------------------------------------------------
Write-Host "`n[3/6] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARNING] pip install reported errors. Retrying with verbose output..." -ForegroundColor Yellow
    & $VenvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Dependency installation failed." -ForegroundColor Red
        exit 1
    }
}
Write-Host "All Python dependencies installed successfully!" -ForegroundColor Green

# -----------------------------------------------------------------------------
# 4. Download Faster-Whisper Offline Model Weights
# -----------------------------------------------------------------------------
Write-Host "`n[4/6] Verifying Faster-Whisper Neural Speech Model ($WhisperModel)..." -ForegroundColor Yellow
if (-not $SkipModelDownload) {
    $downloadScript = Join-Path $ProjectRoot "scripts\download_models.py"
    & $VenvPython "$downloadScript" --model "$WhisperModel"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARNING] Model download failed or was interrupted. You can re-run later with:" -ForegroundColor Yellow
        Write-Host "python scripts/download_models.py --model $WhisperModel" -ForegroundColor White
    }
} else {
    Write-Host "Skipping model download (-SkipModelDownload enabled)." -ForegroundColor DarkGray
}

# -----------------------------------------------------------------------------
# 5. Ollama Status Check (Offline Local Brain)
# -----------------------------------------------------------------------------
Write-Host "`n[5/6] Checking Ollama Local AI Brain status..." -ForegroundColor Yellow
$ollamaInstalled = $false
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    $ollamaInstalled = $true
}

$ollamaRunning = $false
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop
    $ollamaRunning = $true
    Write-Host "Ollama server is active on localhost:11434" -ForegroundColor Green
    $models = $res.models | ForEach-Object { $_.name }
    if ($models -contains "gemma:2b" -or ($models -like "*gemma*").Count -gt 0) {
        Write-Host "Gemma model detected in Ollama! Offline AI editing ready." -ForegroundColor Green
    } else {
        Write-Host "[INFO] Gemma model not yet pulled in Ollama. Run: 'ollama pull gemma:2b'" -ForegroundColor Cyan
    }
} catch {
    if ($ollamaInstalled) {
        Write-Host "[INFO] Ollama is installed but not running. Start it with: 'ollama serve'" -ForegroundColor Cyan
    } else {
        Write-Host "[INFO] Ollama is optional for 100% offline local AI polish." -ForegroundColor DarkGray
        Write-Host "To enable it: Download from https://ollama.ai/ and run: ollama pull gemma:2b" -ForegroundColor DarkGray
    }
}

# -----------------------------------------------------------------------------
# 6. Settings Configuration & Microphone Verification
# -----------------------------------------------------------------------------
Write-Host "`n[6/6] Initializing user configuration & verifying microphone..." -ForegroundColor Yellow

$appDataDir = Join-Path $env:APPDATA "GeminiFlow"
if (-not (Test-Path $appDataDir)) {
    New-Item -ItemType Directory -Path $appDataDir -Force | Out-Null
}

$userConfig = Join-Path $appDataDir "config.json"
$exampleConfig = Join-Path $ProjectRoot "settings.example.json"
if (-not (Test-Path $userConfig) -and (Test-Path $exampleConfig)) {
    Copy-Item -Path $exampleConfig -Destination $userConfig
    Write-Host "Initialized default user settings at: $userConfig" -ForegroundColor Green
}

# Check microphone devices
& $VenvPython -c "
import sounddevice as sd
try:
    devs = sd.query_devices()
    inputs = [d for d in devs if d.get('max_input_channels', 0) > 0]
    if inputs:
        default_in = sd.query_devices(kind='input')
        print(f'Detected {len(inputs)} recording device(s).')
        print(f'Default microphone: \"{default_in.get(\"name\", \"Unknown\")}\"')
    else:
        print('[WARNING] No microphone input devices detected!')
except Exception as e:
    print(f'[WARNING] Unable to probe audio devices: {e}')
"

Write-Host "`n=====================================================================" -ForegroundColor Green
Write-Host "             Gemini Flow Setup Completed Successfully!               " -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "To launch Gemini Flow, run either:" -ForegroundColor White
Write-Host "  1. .\run.bat        (Double-click or run from CMD)" -ForegroundColor Cyan
Write-Host "  2. .\run.ps1        (Run from PowerShell)" -ForegroundColor Cyan
Write-Host "Hotkey: Press Ctrl+Space to begin dictation anywhere on Windows!" -ForegroundColor Yellow
Write-Host ""
