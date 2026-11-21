<#
.SYNOPSIS
    Script de mantenimiento preventivo corporativo avanzado con resolucion dinamica.
.DESCRIPTION
    Audita y repara la integridad logica (DISM/SFC). Extrae telemetria de hardware (S.M.A.R.T, Bateria)
    y metricas de SO. Requiere permisos administrativos.
#>
[CmdletBinding(SupportsShouldProcess=$true)]
param()

# -----------------------------------------------------------------------------
# INICIALIZACION Y VARIABLES DE ENTORNO
# -----------------------------------------------------------------------------
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$computerName = $env:COMPUTERNAME
# $PSScriptRoot resuelve automaticamente la ubicacion de este script
$targetFolder = $PSScriptRoot
$reportPath = Join-Path -Path $targetFolder -ChildPath "$computerName-Reporte.txt"

$reportContent = [System.Collections.Generic.List[string]]::new()
$reportContent.Add("======================================================")
$reportContent.Add("   INFORME DE MANTENIMIENTO PREVENTIVO - WINDOWS 11   ")
$reportContent.Add("======================================================")
$reportContent.Add("Equipo Evaluado : $computerName")
$reportContent.Add("Ruta de Trabajo : $targetFolder")
$reportContent.Add("Fecha y Hora    : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
$reportContent.Add("======================================================`n")

# Validacion de seguridad y privilegios
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "El script no cuenta con privilegios administrativos. Abortando."
    Exit 1
}

Try {
    # -------------------------------------------------------------------------
    # 1. EJECUCION Y ANALISIS DE DISM (ScanHealth / RestoreHealth)
    # -------------------------------------------------------------------------
    $reportContent.Add("[ETAPA 1] Diagnostico del Almacen de Componentes (DISM)")
    Write-Host "[1/5] Ejecutando DISM ScanHealth..." -ForegroundColor Cyan
    
    # Redireccion de streams para captura limpia en procesos nativos
    $dismScan = & DISM.exe /Online /Cleanup-Image /ScanHealth 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        $reportContent.Add("  - Estado: ERROR CRITICO (Codigo: $LASTEXITCODE)")
    } elseif ($dismScan -match "No se detectaron" -or $dismScan -match "No component store corruption") {
        $reportContent.Add("  - Estado: SALIO BIEN / SIN DANOS")
    } else {
        $reportContent.Add("  - Estado: DANOS DETECTADOS. Ejecutando RestoreHealth...")
        
        # Advertencia critica por modificacion de componentes base
        if ($PSCmdlet.ShouldProcess("Almacen de Componentes de Windows", "Restaurar Salud (RestoreHealth)")) {
            $dismRestore = & DISM.exe /Online /Cleanup-Image /RestoreHealth /NoRestart 2>&1
            if ($LASTEXITCODE -eq 0) {
                $reportContent.Add("  - Resultado: Reparacion exitosa mediante Windows Update/Local.")
            } else {
                $reportContent.Add("  - Resultado: FALLO en la reparacion (Codigo: $LASTEXITCODE).")
            }
        } else {
            $reportContent.Add("  - Resultado: Reparacion omitida por el operador (-WhatIf).")
        }
    }
    $reportContent.Add("")

    # -------------------------------------------------------------------------
    # 2. EJECUCION Y ANALISIS DE SFC (Scannow)
    # -------------------------------------------------------------------------
    $reportContent.Add("[ETAPA 2] Verificacion de Archivos de Sistema (SFC)")
    Write-Host "[2/5] Ejecutando SFC Scannow..." -ForegroundColor Cyan
    
    & sfc /scannow *>$null
    
    switch ($LASTEXITCODE) {
        0 { $reportContent.Add("  - Estado: SALIO BIEN. Sin violaciones de integridad.") }
        2 { $reportContent.Add("  - Estado: REPARACION EXITOSA. Archivos corruptos reemplazados.") }
        3 { $reportContent.Add("  - Estado: REPARACION FALLIDA. Bloqueo en uso exclusivo por el Kernel.") }
        default { $reportContent.Add("  - Estado: ERROR DE EJECUCION (Codigo: $LASTEXITCODE).") }
    }
    $reportContent.Add("")

    # -------------------------------------------------------------------------
    # 3. DIAGNOSTICO DE SALUD S.M.A.R.T.
    # -------------------------------------------------------------------------
    $reportContent.Add("[ETAPA 3] Estado de Salud del Almacenamiento (S.M.A.R.T.)")
    Write-Host "[3/5] Evaluando telemetria S.M.A.R.T..." -ForegroundColor Cyan
    
    $physicalDisks = Get-PhysicalDisk -ErrorAction SilentlyContinue
    foreach ($disk in $physicalDisks) {
        $reliability = $disk | Get-StorageReliabilityCounter -ErrorAction SilentlyContinue
        $lifeRemaining = if ($reliability.PercentLifeRemaining) { "$($reliability.PercentLifeRemaining)%" } else { "N/A" }
        $temperature = if ($reliability.Temperature) { "$($reliability.Temperature) C" } else { "N/A" }
        
        $reportContent.Add("  - Unidad ID [$($disk.DeviceId)]: $($disk.FriendlyName)")
        $reportContent.Add("    * Estado Operativo : $($disk.OperationalStatus)")
        $reportContent.Add("    * Salud General    : $($disk.HealthStatus)")
        $reportContent.Add("    * Vida Restante    : $lifeRemaining")
        $reportContent.Add("    * Temperatura      : $temperature")
        $reportContent.Add("    --------------------------------------------------")
    }
    $reportContent.Add("")

    # -------------------------------------------------------------------------
    # 4. TELEMETRIA DE BATERIA
    # -------------------------------------------------------------------------
    $reportContent.Add("[ETAPA 4] Reporte de Desgaste de Bateria")
    Write-Host "[4/5] Analizando subsistema de energia..." -ForegroundColor Cyan
    
    $batteryCheck = Get-CimInstance -ClassName Win32_Battery -ErrorAction SilentlyContinue
    
    if ($batteryCheck) {
        & powercfg /batteryreport /output "$env:TEMP\battery.html" *>$null
        $reportContent.Add("  - Estado: Bateria detectada. Reporte generado en $env:TEMP\battery.html")
    } else {
        $reportContent.Add("  - Estado: EXENTO. Hardware de escritorio/servidor.")
    }
    $reportContent.Add("")

    # -------------------------------------------------------------------------
    # 5. RENDIMIENTO Y ESTABILIDAD
    # -------------------------------------------------------------------------
    $reportContent.Add("[ETAPA 5] Rendimiento, Seguridad y Estabilidad")
    Write-Host "[5/5] Analizando variables del SO..." -ForegroundColor Cyan
    
    $osInstance = Get-CimInstance -ClassName Win32_OperatingSystem
    $uptimeSpan = (Get-Date) - $osInstance.LastBootUpTime
    $reportContent.Add("  - Uptime                : $($uptimeSpan.Days)d, $($uptimeSpan.Hours)h, $($uptimeSpan.Minutes)m")
    
    $totalRAM = [math]::Round($osInstance.TotalVisibleMemorySize / 1MB, 2)
    $freeRAM = [math]::Round($osInstance.FreePhysicalMemory / 1MB, 2)
    $usedRAM = $totalRAM - $freeRAM
    $ramUsagePct = [math]::Round(($usedRAM / $totalRAM) * 100, 2)
    $reportContent.Add("  - Memoria RAM           : Usado $usedRAM GB de $totalRAM GB ($ramUsagePct %)")
    
    $bsodLogs = Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-WER-SystemErrorReporting'; Id=1001} -ErrorAction SilentlyContinue
    $bsodCount = if ($bsodLogs) { $bsodLogs.Count } else { 0 }
    $reportContent.Add("  - Eventos Criticos BSOD : Detectados $bsodCount registros.")
    $reportContent.Add("")

} Catch {
    $reportContent.Add("`n[ERROR CRITICO NO CONTROLADO]")
    $reportContent.Add("Detalle: $($_.Exception.Message)")
    Write-Error "Fallo en linea de ejecucion: $($_.Exception.Message)"
} Finally {
    # -------------------------------------------------------------------------
    # 6. PERSISTENCIA DE DATOS
    # -------------------------------------------------------------------------
    Try {
        $reportContent | Out-File -FilePath $reportPath -Encoding utf8 -Force -ErrorAction Stop
        Write-Host "`n[EXITO] Reporte desplegado en: $reportPath" -ForegroundColor Green
    } Catch {
        Write-Error "Fallo de I/O al persistir el reporte en: $reportPath"
    }
}