<#
.SYNOPSIS
    Sincroniza automáticamente el repositorio local de Proyectos con GitHub al finalizar la jornada.
#>

$ErrorActionPreference = "Continue"

$posiblesRutas = @(
    "D:\Proyectos",
    "D:\Carpetas de usuario\Proyectos"
)

$repoPath = $posiblesRutas | Where-Object { Test-Path "$_\.git" } | Select-Object -First 1

if (-not $repoPath) {
    Write-Host "[ERROR] No se encontró el repositorio Git en las rutas configuradas." -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit 1
}

Set-Location $repoPath
Write-Host "=== Sincronizando repositorio en: $repoPath ===" -ForegroundColor Cyan

# 1. Asegurar identidad local compatible con privacidad de GitHub
$noreplyEmail = "280557745+owenenriqq@users.noreply.github.com"
if ((git config user.email) -ne $noreplyEmail) {
    git config user.name "Owen Enrique"
    git config user.email $noreplyEmail
}

# 2. Revisar cambios sin commitear
$status = git status --porcelain

if (-not [string]::IsNullOrWhiteSpace($status)) {
    Write-Host "`nArchivos modificados o nuevos detectados:" -ForegroundColor Yellow
    git status -s

    if (-not ($status | Select-String "ESTADO.md")) {
        Write-Host "`n[AVISO] Ningún archivo ESTADO.md fue modificado hoy." -ForegroundColor Magenta
    }

    $equipo = if ($repoPath -like "*Carpetas de usuario*") { "Trabajo" } else { "Casa" }
    $fecha = Get-Date -Format "yyyy-MM-dd HH:mm"
    $mensajeDefault = "Actualiza avances ($equipo - $fecha)"

    Write-Host ""
    $mensaje = Read-Host "Mensaje del commit [Enter para usar: '$mensajeDefault']"
    if ([string]::IsNullOrWhiteSpace($mensaje)) {
        $mensaje = $mensajeDefault
    }

    Write-Host "`n1. Preparando archivos (git add -A)..." -ForegroundColor Cyan
    git add -A

    Write-Host "2. Guardando commit local..." -ForegroundColor Cyan
    git commit -m $mensaje
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n[ERROR] Falló git commit. Revisa el mensaje arriba." -ForegroundColor Red
        Read-Host "Presiona Enter para cerrar"
        exit 1
    }
}
else {
    Write-Host "`nNo hay archivos nuevos sin guardar." -ForegroundColor Yellow
}

# 3. Integrar cambios remotos (siempre se ejecuta)
Write-Host "`n3. Integrando cambios remotos (git pull --rebase)..." -ForegroundColor Cyan
git pull --rebase origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Hubo un conflicto o error en git pull --rebase. Resuélvelo antes de subir." -ForegroundColor Red
    Read-Host "Presiona Enter para cerrar"
    exit 1
}

# 4. Verificar si hay commits locales pendientes de subir (incluso de ejecuciones anteriores)
$commitsPendientes = [int](git rev-list --count origin/main..HEAD)

if ($commitsPendientes -gt 0) {
    Write-Host "`n4. Subiendo $commitsPendientes commit(s) pendiente(s) a GitHub (git push)..." -ForegroundColor Cyan
    git push origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n[ERROR] Falló git push. Revisa tu conexión o credenciales arriba." -ForegroundColor Red
        Read-Host "Presiona Enter para cerrar"
        exit 1
    }
    Write-Host "`n[ÉXITO] Todo sincronizado correctamente con GitHub." -ForegroundColor Green
}
else {
    Write-Host "`n[OK] El repositorio ya estaba completamente sincronizado con GitHub." -ForegroundColor Green
}

# Esperar 30 segundos o permitir cierre inmediato con cualquier tecla
Write-Host "`nEsta ventana se cerrará automáticamente en 30 segundos (o presiona una tecla para cerrar ya)..." -ForegroundColor DarkGray
$timeout = 30
while ($timeout -gt 0 -and -not [Console]::KeyAvailable) {
    Start-Sleep -Seconds 1
    $timeout--
}
if ([Console]::KeyAvailable) { [Console]::ReadKey($true) | Out-Null }