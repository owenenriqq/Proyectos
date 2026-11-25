$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$PyInstaller = Join-Path $ProjectRoot ".venv\Scripts\pyinstaller.exe"
if (-not (Test-Path $PyInstaller)) {
    throw "No se encontró PyInstaller en .venv\Scripts\pyinstaller.exe"
}

$Running = Get-Process -Name "EzSetup" -ErrorAction SilentlyContinue
if ($Running) {
    Write-Host "[INFO] Cerrando instancias activas de EzSetup.exe..." -ForegroundColor Yellow
    Stop-Process -Name "EzSetup" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
}

if (Test-Path (Join-Path $ProjectRoot "build")) { Remove-Item (Join-Path $ProjectRoot "build") -Recurse -Force }
if (Test-Path (Join-Path $ProjectRoot "dist")) { Remove-Item (Join-Path $ProjectRoot "dist") -Recurse -Force }

$PyInstallerArgs = @(
    "--noconfirm"
    "--clean"
    "--onefile"
    "--windowed"
    "--uac-admin"
    "--name", "EzSetup"
    "--icon", "assets\EzSetup.ico"
    "--exclude-module", "PyQt6.QtWebEngineCore"
    "--exclude-module", "PyQt6.QtWebEngineWidgets"
    "--exclude-module", "PyQt6.QtMultimedia"
    "--exclude-module", "PyQt6.Qt3DCore"
    "--exclude-module", "PyQt6.QtQml"
    "--exclude-module", "PyQt6.QtQuick"
    "--hidden-import", "wmi"
    "--add-data", "config.json;."
    "--add-data", "assets;assets"
    "--add-data", "assets\m365_sanitizer;assets\m365_sanitizer"
)

$CredentialsEnc = Join-Path $ProjectRoot "credentials.enc"
if (Test-Path $CredentialsEnc -PathType Leaf) {
    Write-Host "[INFO] Incluyendo credentials.enc en el paquete portable..." -ForegroundColor Cyan
    $PyInstallerArgs += @("--add-data", "credentials.enc;.")
}

& $PyInstaller @PyInstallerArgs "main.py"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller finalizó con código de error $LASTEXITCODE"
}

Copy-Item -Path (Join-Path $ProjectRoot "config.json") -Destination (Join-Path $ProjectRoot "dist\config.json") -Force
if (Test-Path $CredentialsEnc -PathType Leaf) {
    Copy-Item -Path $CredentialsEnc -Destination (Join-Path $ProjectRoot "dist\credentials.enc") -Force
}
Write-Host "[OK] Compilación finalizada: dist\EzSetup.exe" -ForegroundColor Green
