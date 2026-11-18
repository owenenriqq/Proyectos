$RutaBase = "D:\Proyectos"
$Proyectos = Get-ChildItem -Path $RutaBase -Directory | Where-Object { $_.Name -notlike ".*" }

Write-Host "=== Selecciona un proyecto para iniciar Agy ===" -ForegroundColor Cyan
for ($i = 0; $i -lt $Proyectos.Count; $i++) {
    Write-Host "[$($i + 1)] $($Proyectos[$i].Name)"
}
Write-Host "[0] Abrir en la carpeta raiz ($RutaBase)"

$Seleccion = Read-Host "`nIngresa el numero"

if ($Seleccion -eq "0") {
    $Destino = $RutaBase
} elseif ($Seleccion -match "^\d+$" -and [int]$Seleccion -ge 1 -and [int]$Seleccion -le $Proyectos.Count) {
    $Destino = $Proyectos[[int]$Seleccion - 1].FullName
} else {
    Write-Host "Opcion no valida." -ForegroundColor Red
    Start-Sleep -Seconds 2
    exit
}

Set-Location -Path $Destino
Clear-Host
Write-Host "Iniciando agy en: $Destino`n" -ForegroundColor Green
agy
