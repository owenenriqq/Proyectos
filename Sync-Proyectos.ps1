<#
.SYNOPSIS
    Sincroniza automáticamente el repositorio local de Proyectos con GitHub al finalizar la jornada.
#>

$ErrorActionPreference = "Stop"

# Detectar automáticamente la ruta del repositorio según la PC
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

# 1. Verificar identidad local para evitar avisos de Committer en PC corporativa
$currentEmail = git config user.email
if ($currentEmail -ne "owenntrip@gmail.com") {
    git config user.name "Owen Enrique"
    git config user.email "owenntrip@gmail.com"
}

# 2. Revisar estado actual
$status = git status --porcelain

if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Host "`nNo hay cambios locales pendientes de subir." -ForegroundColor Yellow
    Write-Host "Verificando si hay actualizaciones en GitHub..." -ForegroundColor Cyan
    git pull --rebase origin main
    Write-Host "`n[OK] Repositorio al día." -ForegroundColor Green
    Start-Sleep -Seconds 3
    exit 0
}

# 3. Mostrar archivos modificados
Write-Host "`nArchivos modificados o nuevos detectados:" -ForegroundColor Yellow
git status -s

# Recordatorio de ESTADO.md
$estadoModificado = $status | Select-String "ESTADO.md"
if (-not $estadoModificado) {
    Write-Host "`n[AVISO] Ningún archivo ESTADO.md fue modificado hoy." -ForegroundColor Magenta
}

# 4. Solicitar mensaje de commit (o usar uno por defecto con fecha/equipo)
$equipo = if ($repoPath -like "*Carpetas de usuario*") { "Trabajo" } else { "Casa" }
$fecha = Get-Date -Format "yyyy-MM-dd HH:mm"
$mensajeDefault = "Actualiza avances ($equipo - $fecha)"

Write-Host ""
$mensaje = Read-Host "Mensaje del commit [Enter para usar: '$mensajeDefault']"
if ([string]::IsNullOrWhiteSpace($mensaje)) {
    $mensaje = $mensajeDefault
}

# 5. Ejecutar flujo completo de sincronización
try {
    Write-Host "`n1. Preparando archivos (git add -A)..." -ForegroundColor Cyan
    git add -A

    Write-Host "2. Guardando commit local..." -ForegroundColor Cyan
    git commit -m $mensaje

    Write-Host "3. Integrando cambios remotos (git pull --rebase)..." -ForegroundColor Cyan
    git pull --rebase origin main

    Write-Host "4. Subiendo a GitHub (git push)..." -ForegroundColor Cyan
    git push origin main

    Write-Host "`n[ÉXITO] Todo sincronizado correctamente con GitHub." -ForegroundColor Green
}
catch {
    Write-Host "`n[ERROR] Ocurrió un problema durante la sincronización:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "Revisa el estado ejecutando 'git status' en la consola." -ForegroundColor Yellow
    Read-Host "Presiona Enter para cerrar"
    exit 1
}

Start-Sleep -Seconds 3