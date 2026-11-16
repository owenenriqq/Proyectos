<#
.SYNOPSIS
    Script principal de la suite M365-Sanitizer.
.DESCRIPTION
    Proporciona un menú interactivo en consola para diagnosticar y reparar conflictos
    de activación y corrupción de licencias entre Microsoft 365 Apps y licencias
    por volumen (como Project/Visio 2021), así como errores de inicio de sesión WAM ("Try again").
    Requiere privilegios de Administrador y es compatible con PowerShell 5.1.
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param()

$ErrorActionPreference = 'Stop'

# Inicialización de rutas y archivo de registro
$ScriptRoot = $PSScriptRoot
$LogsDir = Join-Path -Path $ScriptRoot -ChildPath 'logs'
if (-not (Test-Path -LiteralPath $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

$LogTimestamp = (Get-Date).ToString('yyyyMMdd_HHmmss')
$LogFile = Join-Path -Path $LogsDir -ChildPath "sanitizer_$LogTimestamp.log"

function Write-SanitizerLog {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,

        [Parameter(Mandatory = $false)]
        [ValidateSet('INFO', 'WARN', 'ERROR')]
        [string]$Level = 'INFO'
    )

    $timestamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    $entry = "[$timestamp] [$Level] $Message"

    switch ($Level) {
        'INFO'  { Write-Host $entry -ForegroundColor Cyan }
        'WARN'  { Write-Host $entry -ForegroundColor Yellow }
        'ERROR' { Write-Host $entry -ForegroundColor Red }
    }

    $maxAttempts = 3
    $written = $false
    $lastError = $null

    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        $fileStream = $null
        $streamWriter = $null
        try {
            $fileStream = [System.IO.File]::Open(
                $LogFile,
                [System.IO.FileMode]::Append,
                [System.IO.FileAccess]::Write,
                [System.IO.FileShare]::ReadWrite
            )
            $streamWriter = New-Object System.IO.StreamWriter($fileStream, [System.Text.Encoding]::UTF8)
            $streamWriter.WriteLine($entry)
            $streamWriter.Flush()
            $written = $true
            break
        } catch [System.IO.IOException] {
            $lastError = $_
            if ($attempt -lt $maxAttempts) {
                Start-Sleep -Milliseconds 50
            }
        } catch {
            $lastError = $_
            break
        } finally {
            if ($streamWriter) {
                $streamWriter.Dispose()
            } elseif ($fileStream) {
                $fileStream.Dispose()
            }
        }
    }

    if (-not $written -and $lastError) {
        Write-Host "[WARN] No se pudo escribir en el archivo de registro tras $maxAttempts intentos: $($lastError.Exception.Message)" -ForegroundColor Yellow
    }
}

function Test-IsAdministrator {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Stop-OfficeProcesses {
    [CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
    param()

    $targetProcesses = @(
        'winword', 'excel', 'outlook', 'powerpnt',
        'msaccess', 'mspub', 'onenote', 'teams', 'ms-teams'
    )

    Write-SanitizerLog -Message 'Verificando procesos activos de Microsoft Office...' -Level 'INFO'

    foreach ($procName in $targetProcesses) {
        try {
            $running = Get-Process -Name $procName -ErrorAction SilentlyContinue
            if ($running) {
                if ($PSCmdlet.ShouldProcess($procName, 'Finalizar proceso de Office')) {
                    $running | Stop-Process -Force -ErrorAction Stop
                    Write-SanitizerLog -Message "Proceso finalizado forzadamente: $procName" -Level 'INFO'
                }
            }
        } catch {
            Write-SanitizerLog -Message "Error al finalizar el proceso '$procName': $($_.Exception.Message)" -Level 'ERROR'
        }
    }
}

function Show-PostSanitizationReminder {
    Write-Host ''
    Write-Host '======================================================================' -ForegroundColor Green
    Write-Host '                  RECORDATORIO OPERATIVO POSTERIOR                    ' -ForegroundColor Green
    Write-Host '======================================================================' -ForegroundColor Green
    Write-Host '1. Reinicie el equipo para aplicar la limpieza de WAM y licencias.' -ForegroundColor White
    Write-Host '2. Abra primero Microsoft Word e inicie sesión con su cuenta de' -ForegroundColor White
    Write-Host '   Microsoft 365 hasta confirmar que la suscripción quede activada.' -ForegroundColor White
    Write-Host '3. Una vez activada la suscripción de Microsoft 365, abra Project 2021' -ForegroundColor White
    Write-Host '   para verificar su coexistencia sin conflictos.' -ForegroundColor White
    Write-Host '======================================================================' -ForegroundColor Green
    Write-Host ''
}

# Validación de privilegios de Administrador
if (-not (Test-IsAdministrator)) {
    Write-Host '[ERROR] Este script requiere privilegios de Administrador. Ejecute PowerShell como Administrador.' -ForegroundColor Red
    exit 1
}

Write-SanitizerLog -Message "Iniciando M365-Sanitizer. Registro activo en: $LogFile" -Level 'INFO'

# Carga de módulos
$modulesDir = Join-Path -Path $ScriptRoot -ChildPath 'modules'
$requiredModules = @(
    'Get-OfficeDiagnostics.ps1',
    'Clear-IdentityCache.ps1',
    'Reset-OfficeLicenses.ps1'
)

foreach ($mod in $requiredModules) {
    $modPath = Join-Path -Path $modulesDir -ChildPath $mod
    if (-not (Test-Path -LiteralPath $modPath -PathType Leaf)) {
        Write-SanitizerLog -Message "Módulo requerido no encontrado: $modPath" -Level 'ERROR'
        exit 1
    }
    try {
        . $modPath
        Write-SanitizerLog -Message "Módulo cargado correctamente: $mod" -Level 'INFO'
    } catch {
        Write-SanitizerLog -Message "Error al cargar el módulo '$mod': $($_.Exception.Message)" -Level 'ERROR'
        exit 1
    }
}

$loggerCallback = {
    param([string]$Message, [string]$Level = 'INFO')
    Write-SanitizerLog -Message $Message -Level $Level
}

$backupDllDir = Join-Path -Path $LogsDir -ChildPath 'backup_dll'

function Show-Menu {
    Write-Host ''
    Write-Host '==================================================================' -ForegroundColor White
    Write-Host '                     M365-Sanitizer v1.1                          ' -ForegroundColor White
    Write-Host '        Saneamiento de Licencias e Identidad de Office            ' -ForegroundColor White
    Write-Host '==================================================================' -ForegroundColor White
    Write-Host '1. Ejecutar diagnóstico de entorno (solo lectura)'
    Write-Host '2. Cerrar procesos de Office'
    Write-Host '3. Limpiar caché de identidad y WAM (OneAuth/TokenBroker/cmdkey)'
    Write-Host '4. Restablecer licencias - Modo Selectivo (preserva Project/Visio)'
    Write-Host '5. Restablecer licencias - Modo Total (elimina todas las claves)'
    Write-Host '6. Saneamiento completo Selectivo (Pasos 2 -> 3 -> 4) [Recomendado]'
    Write-Host '7. Saneamiento completo Total (Pasos 2 -> 3 -> 5)'
    Write-Host '0. Salir'
    Write-Host '==================================================================' -ForegroundColor White
}

# Bucle principal del menú interactivo
do {
    Show-Menu
    $selection = Read-Host 'Seleccione una opción'

    switch ($selection) {
        '1' {
            Get-OfficeDiagnostics -Logger $loggerCallback | Out-Null
        }
        '2' {
            Stop-OfficeProcesses -Confirm:$false -WhatIf:$WhatIfPreference
        }
        '3' {
            $confirm = Read-Host 'Esta acción detendrá AAD.BrokerPlugin y eliminará la caché de identidad/WAM y credenciales. ¿Desea continuar? (S/N)'
            if ($confirm -match '^[Ss]$') {
                Clear-IdentityCache -Logger $loggerCallback -Confirm:$false -WhatIf:$WhatIfPreference
            } else {
                Write-SanitizerLog -Message 'Limpieza de identidad cancelada por el operador.' -Level 'WARN'
            }
        }
        '4' {
            $confirm = Read-Host 'Se eliminarán sppc.dll (con respaldo), claves de Office (conservando Project/Visio) y caché vNext. ¿Desea continuar? (S/N)'
            if ($confirm -match '^[Ss]$') {
                Reset-OfficeLicenses -Mode 'Selectivo' -BackupRoot $backupDllDir -Logger $loggerCallback -Confirm:$false -WhatIf:$WhatIfPreference
            } else {
                Write-SanitizerLog -Message 'Restablecimiento selectivo de licencias cancelado por el operador.' -Level 'WARN'
            }
        }
        '5' {
            $confirm = Read-Host 'ADVERTENCIA: Se eliminarán TODAS las claves de producto de Office sin excepción (incluyendo Project/Visio). ¿Desea continuar? (S/N)'
            if ($confirm -match '^[Ss]$') {
                Reset-OfficeLicenses -Mode 'Total' -BackupRoot $backupDllDir -Logger $loggerCallback -Confirm:$false -WhatIf:$WhatIfPreference
            } else {
                Write-SanitizerLog -Message 'Restablecimiento total de licencias cancelado por el operador.' -Level 'WARN'
            }
        }
        '6' {
            $confirm = Read-Host 'Se ejecutará el saneamiento completo Selectivo (cierre de procesos, identidad/WAM y licencias preservando Project/Visio). ¿Desea continuar? (S/N)'
            if ($confirm -match '^[Ss]$') {
                Stop-OfficeProcesses -Confirm:$false -WhatIf:$WhatIfPreference
                Clear-IdentityCache -Logger $loggerCallback -Confirm:$false -WhatIf:$WhatIfPreference
                Reset-OfficeLicenses -Mode 'Selectivo' -BackupRoot $backupDllDir -Logger $loggerCallback -Confirm:$false -WhatIf:$WhatIfPreference
                Write-SanitizerLog -Message 'Saneamiento completo Selectivo finalizado.' -Level 'INFO'
                Show-PostSanitizationReminder
            } else {
                Write-SanitizerLog -Message 'Saneamiento completo Selectivo cancelado por el operador.' -Level 'WARN'
            }
        }
        '7' {
            $confirm = Read-Host 'ADVERTENCIA: Se ejecutará el saneamiento completo Total (eliminará TODAS las licencias, incluyendo Project/Visio). ¿Desea continuar? (S/N)'
            if ($confirm -match '^[Ss]$') {
                Stop-OfficeProcesses -Confirm:$false -WhatIf:$WhatIfPreference
                Clear-IdentityCache -Logger $loggerCallback -Confirm:$false -WhatIf:$WhatIfPreference
                Reset-OfficeLicenses -Mode 'Total' -BackupRoot $backupDllDir -Logger $loggerCallback -Confirm:$false -WhatIf:$WhatIfPreference
                Write-SanitizerLog -Message 'Saneamiento completo Total finalizado.' -Level 'INFO'
                Show-PostSanitizationReminder
            } else {
                Write-SanitizerLog -Message 'Saneamiento completo Total cancelado por el operador.' -Level 'WARN'
            }
        }
        '0' {
            Write-SanitizerLog -Message 'Finalizando sesión de M365-Sanitizer.' -Level 'INFO'
        }
        default {
            Write-Host 'Opción no válida. Intente nuevamente.' -ForegroundColor Yellow
        }
    }
} while ($selection -ne '0')
