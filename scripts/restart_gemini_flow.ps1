# Gemini Flow - PowerShell Quick Restart Script
$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $currentDir

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "         Gemini Flow - Instant Reload / Restart" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# 1. Terminate any stale background instances
Write-Host "[*] Terminating any stale background instances..." -ForegroundColor Yellow
$currPid = $PID
Get-CimInstance Win32_Process | Where-Object { 
    ($_.Name -eq "python.exe" -or $_.Name -eq "pythonw.exe" -or $_.Name -like "*Gemini Flow*") -and 
    ($_.CommandLine -like "*main_standalone.py*" -or $_.CommandLine -like "*main.py*" -or $_.CommandLine -like "*Wisper*") -and 
    $_.ProcessId -ne $currPid 
} | ForEach-Object { 
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue 
}

# 2. Clean up stale PID file
$pidFile = "$env:APPDATA\GeminiFlow\gemini_flow.pid"
if (Test-Path $pidFile) {
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

# 3. Launch fresh instance
Write-Host "[*] Starting fresh Gemini Flow background instance..." -ForegroundColor Yellow
$pythonw = "E:\PYTHON\pythonw.exe"
if (-not (Test-Path $pythonw)) {
    $pythonw = "pythonw.exe"
}

$scriptPath = Join-Path $currentDir "main_standalone.py"
$cmdLine = "`"$pythonw`" `"$scriptPath`" --startup"
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmdLine; CurrentDirectory = $currentDir } | Out-Null

Write-Host "`n[✓] Gemini Flow restarted successfully in the background!" -ForegroundColor Green
Write-Host "[✓] Global Hotkey (Ctrl + Space) is active and ready.`n" -ForegroundColor Green
Start-Sleep -Seconds 1
