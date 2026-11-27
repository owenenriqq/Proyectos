<#
.SYNOPSIS
    Sincroniza de forma segura el repositorio local de Proyectos con GitHub al finalizar la jornada.
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

# 1. Validar rama activa
$ramaActual = (git rev-parse --abbrev-ref HEAD).Trim()
if ($ramaActual -ne "main") {
    Write-Host "[ERROR] Estás en la rama '$ramaActual' en lugar de 'main'. Cambia a 'main' antes de sincronizar." -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit 1
}

# 2. Asegurar identidad local compatible con privacidad de GitHub
$noreplyEmail = "280557745+owenenriqq@users.noreply.github.com"
if ((git config user.email) -ne $noreplyEmail) {
    git config user.name "Owen Enrique"
    git config user.email $noreplyEmail
}

# 3. Revisar cambios sin commitear
$status = git status --porcelain
$huboCambiosDocs = $false

if (-not [string]::IsNullOrWhiteSpace($status)) {
    Write-Host "`nArchivos modificados o nuevos detectados:" -ForegroundColor Yellow
    git status -s

    # Bloqueo preventivo de archivos sensibles no ignorados
    $sensibles = $status | Select-String -Pattern "\.(enc|pfx|p12|key|pem)$"
    if ($sensibles) {
        Write-Host "`n[BLOQUEADO] Se detectaron archivos sensibles sin ignorar:" -ForegroundColor Red
        $sensibles | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
        Read-Host "Eliminalos o agregalos a .gitignore antes de continuar. Presiona Enter para salir"
        exit 1
    }

    if ($status | Select-String -Pattern "(ESTADO|GEMINI)\.md") {
        $huboCambiosDocs = $true
    } else {
        Write-Host "`n[AVISO] Ningún archivo ESTADO.md fue modificado hoy." -ForegroundColor Magenta
    }

    $confirmar = Read-Host "`n¿Incluir todos estos archivos en el commit? [S/n]"
    if ($confirmar -match "^[nN]$") {
        Write-Host "Operación cancelada por el usuario." -ForegroundColor Yellow
        exit 0
    }

    $equipo = if ($repoPath -like "*Carpetas de usuario*") { "Trabajo" } else { "Casa" }
    $fecha = Get-Date -Format "yyyy-MM-dd HH:mm"
    $mensajeDefault = "Actualiza avances ($equipo - $fecha)"

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

# 4. Integrar cambios remotos
Write-Host "`n3. Integrando cambios remotos (git pull --rebase origin main)..." -ForegroundColor Cyan
git pull --rebase origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Hubo un conflicto en git pull --rebase." -ForegroundColor Red
    Write-Host "Puedes cancelar el rebase ejecutando: git rebase --abort" -ForegroundColor Yellow
    Read-Host "Presiona Enter para cerrar"
    exit 1
}

# 5. Subir commits pendientes
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

# 6. Exportación rápida al cuaderno si hubo cambios en .md
$exportScript = Join-Path $repoPath "Exportar-Cuaderno.ps1"
if ($huboCambiosDocs -and (Test-Path $exportScript)) {
    Write-Host "`nSe detectaron cambios en archivos .md. Ejecutando Exportar-Cuaderno.ps1..." -ForegroundColor Cyan
    & $exportScript
}

# Esperar 30 segundos o permitir cierre inmediato con cualquier tecla
Write-Host "`nEsta ventana se cerrará automáticamente en 30 segundos (o presiona una tecla para cerrar ya)..." -ForegroundColor DarkGray
$timeout = 30
while ($timeout -gt 0 -and -not [Console]::KeyAvailable) {
    Start-Sleep -Seconds 1
    $timeout--
}
if ([Console]::KeyAvailable) { [Console]::ReadKey($true) | Out-Null }
