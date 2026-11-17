$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$PyInstaller = Join-Path $ProjectRoot ".venv\Scripts\pyinstaller.exe"
if (-not (Test-Path $PyInstaller)) {
    throw "No se encontró PyInstaller en .venv\Scripts\pyinstaller.exe"
}

if (Test-Path (Join-Path $ProjectRoot "build")) { Remove-Item (Join-Path $ProjectRoot "build") -Recurse -Force }
if (Test-Path (Join-Path $ProjectRoot "dist")) { Remove-Item (Join-Path $ProjectRoot "dist") -Recurse -Force }

& $PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --uac-admin `
    --name "EzSetup" `
    --icon "assets\EzSetup.ico" `
    --add-data "config.json;." `
    --add-data "assets;assets" `
    "main.py"

Copy-Item -Path (Join-Path $ProjectRoot "config.json") -Destination (Join-Path $ProjectRoot "dist\config.json") -Force
Write-Host "[OK] Compilación finalizada: dist\EzSetup.exe" -ForegroundColor Green
