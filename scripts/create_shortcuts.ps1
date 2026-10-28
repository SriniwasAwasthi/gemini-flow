$WshShell = New-Object -ComObject WScript.Shell
$desktopPath = [Environment]::GetFolderPath('Desktop')
$targetExe = 'E:\W c One Drive\Wisper\Gemini Flow.exe'
$iconPath = 'E:\W c One Drive\Wisper\app_icon.ico'
$workDir = 'E:\W c One Drive\Wisper'

$shortcutPath1 = Join-Path $desktopPath 'Gemini Flow.lnk'
$shortcut1 = $WshShell.CreateShortcut($shortcutPath1)
$shortcut1.TargetPath = $targetExe
$shortcut1.WorkingDirectory = $workDir
$shortcut1.IconLocation = "$iconPath,0"
$shortcut1.Description = 'Gemini Flow — Voice AI Assistant'
$shortcut1.Save()
Write-Host "Created shortcut at: $shortcutPath1"

$desktopFolder2 = 'E:\W c One Drive\1. Desktop'
if (Test-Path $desktopFolder2) {
    $shortcutPath2 = Join-Path $desktopFolder2 'Gemini Flow.lnk'
    $shortcut2 = $WshShell.CreateShortcut($shortcutPath2)
    $shortcut2.TargetPath = $targetExe
    $shortcut2.WorkingDirectory = $workDir
    $shortcut2.IconLocation = "$iconPath,0"
    $shortcut2.Description = 'Gemini Flow — Voice AI Assistant'
    $shortcut2.Save()
    Write-Host "Created shortcut at: $shortcutPath2"
}
