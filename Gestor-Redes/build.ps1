$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$PyInstaller = Join-Path $ProjectRoot ".venv\Scripts\pyinstaller.exe"
if (-not (Test-Path $PyInstaller)) {
    throw "No se encontró PyInstaller en .venv\Scripts\pyinstaller.exe"
}

if (Test-Path (Join-Path $ProjectRoot "build")) { Remove-Item (Join-Path $ProjectRoot "build") -Recurse -Force }
if (Test-Path (Join-Path $ProjectRoot "dist")) { Remove-Item (Join-Path $ProjectRoot "dist") -Recurse -Force }

$ArgsList = @(
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--uac-admin",
    "--name", "GestorRedes",
    "--exclude-module", "PyQt6.QtWebEngineCore",
    "--exclude-module", "PyQt6.QtWebEngineWidgets",
    "--exclude-module", "PyQt6.QtMultimedia",
    "--exclude-module", "PyQt6.Qt3DCore",
    "--exclude-module", "PyQt6.QtQml",
    "--exclude-module", "PyQt6.QtQuick"
)

$IconPath = Join-Path $ProjectRoot "assets\icon.ico"
if (Test-Path $IconPath) {
    $ArgsList += @("--icon", "assets\icon.ico", "--add-data", "assets\icon.ico;assets")
}

$ArgsList += "main.py"

& $PyInstaller @ArgsList
Write-Host "[OK] Compilación finalizada: dist\GestorRedes.exe" -ForegroundColor Green
