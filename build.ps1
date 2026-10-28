# ==============================================================================
# Gemini Flow - Unified Build & Packaging Pipeline (Root Wrapper)
# Delegates to scripts/build.ps1
# ==============================================================================
param (
    [switch]$SkipTests = $false,
    [switch]$SkipZip = $false
)

$ScriptDir = $PSScriptRoot
$BuildScript = Join-Path $ScriptDir "scripts\build.ps1"

& $BuildScript -SkipTests:$SkipTests -SkipZip:$SkipZip
exit $LASTEXITCODE
