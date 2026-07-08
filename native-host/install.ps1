# install.ps1 — Registers the Zetamac native messaging host for Chrome
# Run this ONCE after loading the extension in Chrome.
#
# Usage:
#   .\install.ps1 -ExtensionId "YOUR_EXTENSION_ID_HERE"
#
# To find your extension ID:
#   1. Go to chrome://extensions/
#   2. Enable Developer Mode
#   3. Copy the ID shown under the extension name

param(
    [Parameter(Mandatory=$true)]
    [string]$ExtensionId
)

$ErrorActionPreference = "Stop"

$hostName = "com.zetamac.obsidian"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$batPath = Join-Path $scriptDir "write_file.bat"
$manifestPath = Join-Path $scriptDir "$hostName.json"

# Find the absolute path to Python to make the batch runner robust
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonExe) {
    # Fallback to search AppData for user installations
    $localAppPath = "$env:USERPROFILE\AppData\Local\Programs\Python"
    if (Test-Path $localAppPath) {
        $pythonExe = Get-ChildItem -Path $localAppPath -Filter "python.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
    }
}

if (-not $pythonExe) {
    Write-Error "Python was not found on your system! Please install Python before running this installer."
    exit 1
}

Write-Host "`n[+] Found Python at: $pythonExe" -ForegroundColor Green

# Create/Overwrite the batch file with the absolute Python path
$batContent = @"
@echo off
`"$pythonExe`" `"%~dp0write_file.py`" %*
"@
[System.IO.File]::WriteAllText($batPath, $batContent)
Write-Host "[+] Generated write_file.bat with absolute Python path" -ForegroundColor Green

# Build the native messaging manifest
$manifest = @{
    name = $hostName
    description = "Writes Zetamac session files to Obsidian vault"
    path = $batPath
    type = "stdio"
    allowed_origins = @("chrome-extension://$ExtensionId/")
}

# Write the manifest (Chrome requires no BOM)
$json = $manifest | ConvertTo-Json -Depth 3
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($manifestPath, $json, $utf8NoBom)

Write-Host "`n[+] Native messaging manifest written to:" -ForegroundColor Cyan
Write-Host "    $manifestPath" -ForegroundColor White

# Create the registry entry (HKCU — no admin needed)
$regPath = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$hostName"

if (-not (Test-Path $regPath)) {
    New-Item -Path $regPath -Force | Out-Null
}
Set-ItemProperty -Path $regPath -Name "(Default)" -Value $manifestPath

Write-Host "`n[+] Registry entry created at:" -ForegroundColor Cyan
Write-Host "    $regPath" -ForegroundColor White

Write-Host "`n[+] Default vault path:" -ForegroundColor Cyan
Write-Host "    C:\Users\varun\OneDrive\Documents\Obsidian Vault\Me\Daily logs\Zetamac" -ForegroundColor White

Write-Host "`n" -NoNewline
Write-Host "=== Installation complete! ===" -ForegroundColor Green
Write-Host "Restart Chrome for changes to take effect." -ForegroundColor Yellow
Write-Host ""
