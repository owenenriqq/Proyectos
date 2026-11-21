[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "Lanzador Antigravity CLI"

# 1. Detectar automáticamente la raíz de Proyectos en Casa o Trabajo
$posiblesRaices = @(
    $PSScriptRoot,
    "D:\Proyectos",
    "D:\Carpetas de usuario\Proyectos"
)

$raizProyectos = $posiblesRaices | Where-Object {
    $_ -and (Test-Path (Join-Path $_ ".git"))
} | Select-Object -First 1

if (-not $raizProyectos) {
    $raizProyectos = $posiblesRaices | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}

# 2. Construir lista dinámica de carpetas según lo que exista en este equipo
$opciones = [System.Collections.Generic.List[PSCustomObject]]::new()

if ($raizProyectos) {
    $opciones.Add([PSCustomObject]@{
        Nombre = "Raíz de Proyectos ($raizProyectos)"
        Ruta   = $raizProyectos
    })

    # Carpetas habituales (solo agrega las que existan en la PC actual)
    $candidatas = @(
        "EidicoVBS",
        "EzSetup\EzSetup_Python",
        "Gestor-Redes",
        "Inventario Eidico",
        "Lanzador Eidico",
        "Suite-M365-Saneamiento"
    )

    foreach ($rel in $candidatas) {
        $full = Join-Path $raizProyectos $rel
        if (Test-Path $full) {
            $opciones.Add([PSCustomObject]@{ Nombre = $rel; Ruta = $full })
        }
    }

    # Sumar automáticamente cualquier otra subcarpeta nueva dentro de Proyectos
    Get-ChildItem -Path $raizProyectos -Directory | Where-Object {
        $_.Name -notmatch '^\.' -and ($opciones.Ruta -notcontains $_.FullName)
    } | ForEach-Object {
        $opciones.Add([PSCustomObject]@{ Nombre = $_.Name; Ruta = $_.FullName })
    }
}

# 3. Mostrar menú interactivo
Clear-Host
Write-Host "=== Antigravity CLI - Selector de Proyecto ===" -ForegroundColor Cyan
Write-Host "Equipo actual: $env:COMPUTERNAME | Base: $raizProyectos`n" -ForegroundColor DarkGray

for ($i = 0; $i -lt $opciones.Count; $i++) {
    Write-Host ("  [{0}] {1}" -f ($i + 1), $opciones[$i].Nombre)
}
Write-Host "  [O] Seleccionar otra carpeta del ordenador (Explorador)..." -ForegroundColor Yellow
Write-Host "  [R] Escribir o pegar una ruta manualmente..." -ForegroundColor Yellow
Write-Host "  [S] Salir`n" -ForegroundColor DarkGray

$eleccion = Read-Host "Elegí una opción"
$rutaDestino = $null

switch ($eleccion.Trim().ToUpper()) {
    "S" { exit 0 }
    "O" {
        Add-Type -AssemblyName System.Windows.Forms
        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
        $dialog.Description = "Seleccioná la carpeta donde abrir Antigravity CLI"
        $dialog.SelectedPath = if ($raizProyectos) { $raizProyectos } else { "D:\" }
        $dialog.ShowNewFolderButton = $true
        if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
            $rutaDestino = $dialog.SelectedPath
        } else {
            exit 0
        }
    }
    "R" {
        $manual = Read-Host "Pegá la ruta completa de la carpeta"
        $rutaDestino = $manual.Trim('"').Trim()
    }
    default {
        $indice = 0
        if ([int]::TryParse($eleccion, [ref]$indice) -and $indice -ge 1 -and $indice -le $opciones.Count) {
            $rutaDestino = $opciones[$indice - 1].Ruta
        }
    }
}

if (-not $rutaDestino -or -not (Test-Path $rutaDestino)) {
    Write-Host "`n[ERROR] Ruta inválida o inexistente: $rutaDestino" -ForegroundColor Red
    Pause
    exit 1
}

Set-Location -Path $rutaDestino
Write-Host "`nIniciando Antigravity CLI en: $rutaDestino`n" -ForegroundColor Green
agy