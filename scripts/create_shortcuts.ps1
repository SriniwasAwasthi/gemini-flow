$WshShell = New-Object -ComObject WScript.Shell
$desktopPath = [Environment]::GetFolderPath('Desktop')
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$targetExe = Join-Path $ProjectRoot 'Gemini Flow.exe'
$iconPath = Join-Path $ProjectRoot 'app_icon.ico'
$workDir = $ProjectRoot

$shortcutPath1 = Join-Path $desktopPath 'Gemini Flow.lnk'
$shortcut1 = $WshShell.CreateShortcut($shortcutPath1)
$shortcut1.TargetPath = $targetExe
$shortcut1.WorkingDirectory = $workDir
$shortcut1.IconLocation = "$iconPath,0"
$shortcut1.Description = 'Gemini Flow — Voice AI Assistant'
$shortcut1.Save()
Write-Host "Created shortcut at: $shortcutPath1"
