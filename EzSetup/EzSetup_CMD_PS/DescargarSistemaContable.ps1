# Cargar función SHGetKnownFolderPath desde la API de Windows
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class KnownFolders {
    [DllImport("shell32.dll")]
    public static extern int SHGetKnownFolderPath(
        [MarshalAs(UnmanagedType.LPStruct)] Guid rfid,
        uint dwFlags,
        IntPtr hToken,
        out IntPtr ppszPath
    );
}
"@

# Obtener ruta de la carpeta de Descargas (universal)
$DownloadsGuid = [Guid]::Parse("374DE290-123F-4565-9164-39C4925E467B")
$ptr = [IntPtr]::Zero
$hr = [KnownFolders]::SHGetKnownFolderPath($DownloadsGuid, 0, [IntPtr]::Zero, [ref]$ptr)

if ($hr -eq 0 -and $ptr -ne [IntPtr]::Zero) {
    $downloads = [Runtime.InteropServices.Marshal]::PtrToStringUni($ptr)
    [Runtime.InteropServices.Marshal]::FreeCoTaskMem($ptr)
} else {
    Write-Host "`n[ERROR] No se pudo obtener la carpeta de Descargas."
    pause
    exit
}

if (-not (Test-Path $downloads)) {
    Write-Host "`n[ERROR] La ruta de Descargas no existe: $downloads"
    pause
    exit
}

# URL del nuevo archivo a descargar
$url = 'http://eidico.net/recursos/descargas/Instalar_Fox_EIDICO.zip'

# Ruta de destino
$dest = Join-Path $downloads 'Instalar_Fox_EIDICO.zip'
$tempFile = "$dest.tmp"

# Obtener tamaño total
try {
    $req = Invoke-WebRequest -Uri $url -Method Head -UseBasicParsing
    $total = [math]::Round($req.Headers['Content-Length'] / 1MB, 2)
} catch {
    Write-Host "`n[ERROR] No se pudo obtener el tamaño del archivo."
    pause
    exit
}

# Verificar si el archivo temporal ya existe
if (Test-Path $tempFile) {
    Remove-Item $tempFile -Force
}

# Crear cliente y flujo
try {
    $client = New-Object System.Net.WebClient
    $stream = $client.OpenRead($url)
    $file = [System.IO.File]::OpenWrite($tempFile)
} catch {
    Write-Host "`n[ERROR] No se pudo abrir la conexión o el archivo."
    pause
    exit
}

# Descargar con barra de progreso en una sola línea
$buffer = New-Object byte[] 4096
$read = 0
while (($count = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {
    $file.Write($buffer, 0, $count)
    $read += $count
    $mb = [math]::Round($read / 1MB, 2)
    $percent = [math]::Round(($read / ($total * 1MB)) * 100, 0)
    Write-Host -NoNewline "`r[PROGRESO] Descargando... $mb MB / $total MB ($percent`%)"
}

# Cerrar flujos
$file.Close()
$stream.Close()

# Renombrar archivo temporal
Move-Item -Path $tempFile -Destination $dest -Force

# Traer ventana al frente
Add-Type '[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);' -Name Win32 -Namespace Native
$hwnd = (Get-Process -Id $PID).MainWindowHandle
[Native.Win32]::SetForegroundWindow($hwnd) | Out-Null

Write-Host "`n[COMPLETADO] Archivo guardado en: $dest"

# Abrir el archivo ZIP automáticamente
Start-Process -FilePath $dest

# Cuenta regresiva
for ($i = 5; $i -ge 1; $i--) {
    $dots = '.' * (11 - $i)
    Write-Host -NoNewline "`r[CERRANDO] Esperando $i segundos$dots"
    Start-Sleep -Seconds 1
}

# Cerrar completamente la ventana de PowerShell
Stop-Process -Id $PID
