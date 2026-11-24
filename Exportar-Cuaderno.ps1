#Requires -Version 5.1
<#
.SYNOPSIS
    Exporta los archivos GEMINI.md y ESTADO.md del monorepo a una carpeta temporal.
.DESCRIPTION
    Recopila el GEMINI.md global y los GEMINI.md / ESTADO.md de cada subproyecto,
    guardándolos en UTF-8 sin BOM dentro de $env:TEMP\Cuaderno_Proyectos.
#>

param(
    [string]$Destino = (Join-Path $env:TEMP "Cuaderno_Proyectos")
)

$ErrorActionPreference = "Stop"
$Raiz = $PSScriptRoot
$Utf8SinBom = New-Object System.Text.UTF8Encoding($false)

# 1. Preparar y vaciar la carpeta de destino si ya existe
if (Test-Path -LiteralPath $Destino) {
    Get-ChildItem -LiteralPath $Destino -Force | Remove-Item -Recurse -Force
} else {
    New-Item -ItemType Directory -Path $Destino -Force | Out-Null
}

$Generados = @()

# 2. Copiar el GEMINI.md de la raíz como 00_GLOBAL_GEMINI.md en UTF-8 sin BOM
$GeminiGlobal = Join-Path $Raiz "GEMINI.md"
if (Test-Path -LiteralPath $GeminiGlobal) {
    $DestinoGlobal = Join-Path $Destino "00_GLOBAL_GEMINI.md"
    $Contenido = [System.IO.File]::ReadAllText($GeminiGlobal)
    [System.IO.File]::WriteAllText($DestinoGlobal, $Contenido, $Utf8SinBom)
    $Generados += "00_GLOBAL_GEMINI.md"
}

# 3. Recorrer recursivamente las subcarpetas excluyendo directorios de sistema/compilación
$Excluidos = @(".git", ".venv", "build", "dist", "__pycache__", "legacy")

$Archivos = Get-ChildItem -LiteralPath $Raiz -Recurse -File | Where-Object {
    # Filtro estricto por nombre de archivo
    if ($_.Name -ne "GEMINI.md" -and $_.Name -ne "ESTADO.md") { return $false }

    # Excluir el GEMINI.md de la raíz (ya procesado)
    if ($_.DirectoryName -eq $Raiz) { return $false }

    # Verificar si alguna carpeta padre en la ruta relativa está excluida
    $Relativa = $_.FullName.Substring($Raiz.Length).TrimStart('\', '/')
    $Segmentos = $Relativa -split '[\\/]'
    foreach ($seg in $Segmentos) {
        if ($Excluidos -contains $seg) { return $false }
    }
    return $true
}

foreach ($Archivo in $Archivos) {
    $Relativa = $Archivo.FullName.Substring($Raiz.Length).TrimStart('\', '/')
    $NombreDestino = $Relativa -replace '[\\/]', '_'
    $RutaDestino = Join-Path $Destino $NombreDestino

    $Contenido = [System.IO.File]::ReadAllText($Archivo.FullName)
    [System.IO.File]::WriteAllText($RutaDestino, $Contenido, $Utf8SinBom)
    $Generados += $NombreDestino
}

# 4. Listar los archivos generados en consola
Write-Host "Archivos generados en ${Destino}:" -ForegroundColor Cyan
if ($Generados.Count -eq 0) {
    Write-Host "  (Ninguno)" -ForegroundColor Yellow
} else {
    foreach ($Item in ($Generados | Sort-Object)) {
        Write-Host "  - $Item"
    }
}

# 5. Abrir la carpeta de destino en el Explorador de Windows
Start-Process explorer.exe -ArgumentList "`"$Destino`""
