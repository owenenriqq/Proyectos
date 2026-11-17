$source = "\\172.31.11.146\Fileserver\EidicoPrueba\EidicoPrueba.EXE"
$destination = "C:\Program Files (x86)\Sol Sistemas\EIDICO\EidicoPrueba.EXE"
$bufferSize = 4096

if (-Not (Test-Path $source)) {
    Write-Host "[ERROR] No se pudo copiar el archivo."
    exit 1
}

try {
    $sourceStream = [System.IO.File]::OpenRead($source)
    $destStream = [System.IO.File]::OpenWrite($destination)
} catch {
    Write-Host "[ERROR] No se pudo copiar el archivo.."
    exit 1
}

$totalBytes = $sourceStream.Length
$readBytes = 0
$buffer = New-Object byte[] $bufferSize

Write-Host "Copiando archivo EidicoPrueba.exe..."

while (($count = $sourceStream.Read($buffer, 0, $bufferSize)) -gt 0) {
    $destStream.Write($buffer, 0, $count)
    $readBytes += $count
    $mbCopied = [math]::Round($readBytes / 1MB, 2)
    $totalMB = [math]::Round($totalBytes / 1MB, 2)
    $percent = [math]::Round(($readBytes / $totalBytes) * 100, 0)
    Write-Host -NoNewline "`r[PROGRESO] Copiando... $mbCopied MB / $totalMB MB ($percent`%)"
}

$sourceStream.Close()
$destStream.Close()

Write-Host "`nArchivo copiado correctamente."

# Cuenta regresiva
for ($i = 5; $i -ge 1; $i--) {
    $dots = '.' * (11 - $i)
    Write-Host -NoNewline "`r[CERRANDO] Esperando $i segundos$dots"
    Start-Sleep -Seconds 1
}

# Cerrar completamente la ventana de PowerShell
Stop-Process -Id $PID