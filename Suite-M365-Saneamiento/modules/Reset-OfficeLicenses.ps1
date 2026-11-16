<#
.SYNOPSIS
    Módulo para restablecer licencias de Office respetando el orden técnico de saneamiento.
.DESCRIPTION
    1. Detecta y respalda en .\logs\backup_dll\ antes de eliminar cualquier archivo sppc.dll
       inyectado en root\vfs\System o root\vfs\SystemX86 que bloquee la autenticación en la nube.
    2. Consulta las claves de producto mediante ospp.vbs /dstatus y permite elegir entre:
       - Modo Selectivo: desinstala claves de Office (O365, ProPlus, Mondo, Standard) conservando
         intactas las claves cuyo License Name contenga Project o Visio.
       - Modo Total: desinstala todas las claves de Office sin excepción.
    3. Limpia el almacenamiento de licencias vNext (%LOCALAPPDATA%\Microsoft\Office\16.0\Licensing).
    4. Elimina claves y valores residuales de licenciamiento en HKCU y HKLM sin alterar
       la integridad de la instalación Click-to-Run.
    Soporta -WhatIf y -Confirm.
#>

function Get-InstalledLicenseKeys {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$OsppPath
    )

    $rawOutput = & cscript.exe //nologo $OsppPath /dstatus 2>&1
    $licenses = @()
    $currentName = $null
    $currentDesc = $null

    foreach ($line in $rawOutput) {
        $text = [string]$line
        if ($text -match '^-{3,}') {
            $currentName = $null
            $currentDesc = $null
            continue
        }
        if ($text -match 'LICENSE NAME:\s*(.+)$') {
            $currentName = $Matches[1].Trim()
        } elseif ($text -match 'LICENSE DESCRIPTION:\s*(.+)$') {
            $currentDesc = $Matches[1].Trim()
        } elseif ($text -match 'Last 5 characters of installed product key:\s*([A-Z0-9]{5})') {
            $licenses += [PSCustomObject]@{
                LicenseName        = $currentName
                LicenseDescription = $currentDesc
                PartialKey         = $Matches[1].Trim()
            }
        }
    }

    return $licenses
}

function Reset-OfficeLicenses {
    [CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
    param(
        [Parameter(Mandatory = $false)]
        [ValidateSet('Selectivo', 'Total')]
        [string]$Mode = 'Selectivo',

        [Parameter(Mandatory = $false)]
        [string[]]$ExcludePartialKeys = @(),

        [Parameter(Mandatory = $false)]
        [string]$BackupRoot,

        [Parameter(Mandatory = $false)]
        [scriptblock]$Logger
    )

    function Write-LicLog {
        param([string]$Message, [string]$Level = 'INFO')
        if ($Logger) {
            & $Logger -Message $Message -Level $Level
        } else {
            Write-Host "[$Level] $Message"
        }
    }

    if (-not $BackupRoot) {
        $projectRoot = Split-Path -Parent $PSScriptRoot
        $BackupRoot = Join-Path -Path $projectRoot -ChildPath 'logs\backup_dll'
    }

    Write-LicLog -Message "Iniciando restablecimiento de licencias de Office (Modo: $Mode)." -Level 'INFO'

    # Paso 1: Verificar, respaldar y eliminar archivos sppc.dll inyectados (Ohook)
    $nativeSppcPath = Join-Path -Path $env:SystemRoot -ChildPath 'System32\sppc.dll'
    if (-not (Test-Path -LiteralPath $nativeSppcPath -PathType Leaf)) {
        Write-LicLog -Message "No se encontró la biblioteca nativa del sistema '$nativeSppcPath'. Se omite la eliminación de sppc.dll en rutas VFS para evitar errores de biblioteca faltante." -Level 'WARN'
    } else {
        $sppcCandidateDirs = @(
            @{ Label = 'PF64_System'; Path = "${env:ProgramFiles}\Microsoft Office\root\vfs\System" },
            @{ Label = 'PF86_SystemX86'; Path = "${env:ProgramFiles(x86)}\Microsoft Office\root\vfs\SystemX86" },
            @{ Label = 'PF86_System'; Path = "${env:ProgramFiles(x86)}\Microsoft Office\root\vfs\System" }
        )

        foreach ($entry in $sppcCandidateDirs) {
            if (-not $entry.Path) { continue }
            $sppcFile = Join-Path -Path $entry.Path -ChildPath 'sppc.dll'
            try {
                if (Test-Path -LiteralPath $sppcFile -PathType Leaf) {
                    if ($PSCmdlet.ShouldProcess($sppcFile, "Respaldar en '$BackupRoot' y eliminar sppc.dll")) {
                        if (-not (Test-Path -LiteralPath $BackupRoot)) {
                            New-Item -ItemType Directory -Path $BackupRoot -Force -ErrorAction Stop | Out-Null
                        }
                        $stamp = (Get-Date).ToString('yyyyMMdd_HHmmss')
                        $backupName = "sppc_$($entry.Label)_$stamp.dll"
                        $backupDest = Join-Path -Path $BackupRoot -ChildPath $backupName

                        Copy-Item -LiteralPath $sppcFile -Destination $backupDest -Force -ErrorAction Stop
                        Write-LicLog -Message "Respaldo creado en: $backupDest" -Level 'INFO'

                        Remove-Item -LiteralPath $sppcFile -Force -ErrorAction Stop
                        Write-LicLog -Message "Archivo sppc.dll eliminado: $sppcFile" -Level 'INFO'
                    }
                }
            } catch {
                Write-LicLog -Message "Error al respaldar/eliminar '$sppcFile': $($_.Exception.Message)" -Level 'ERROR'
            }
        }
    }

    # Paso 2: Consultar y remover claves mediante ospp.vbs /unpkey según el modo seleccionado
    try {
        $osppPath = $null
        $candidatePaths = @(
            "${env:ProgramFiles}\Microsoft Office\Office16\ospp.vbs",
            "${env:ProgramFiles(x86)}\Microsoft Office\Office16\ospp.vbs",
            "${env:ProgramFiles}\Microsoft Office\Office15\ospp.vbs",
            "${env:ProgramFiles(x86)}\Microsoft Office\Office15\ospp.vbs"
        )
        foreach ($path in $candidatePaths) {
            if ($path -and (Test-Path -LiteralPath $path -PathType Leaf)) {
                $osppPath = $path
                break
            }
        }

        if (-not $osppPath) {
            Write-LicLog -Message 'No se encontró ospp.vbs. Se omite la desinstalación de claves por ospp.vbs.' -Level 'WARN'
        } else {
            $installedKeys = Get-InstalledLicenseKeys -OsppPath $osppPath
            if ($installedKeys.Count -eq 0) {
                Write-LicLog -Message 'No se detectaron claves de producto instaladas en ospp.vbs.' -Level 'INFO'
            } else {
                foreach ($lic in $installedKeys) {
                    $key5 = $lic.PartialKey
                    $licName = if ($lic.LicenseName) { $lic.LicenseName } else { 'Desconocida' }
                    $isExcluded = $ExcludePartialKeys -contains $key5
                    $isProjectOrVisio = ($licName -match 'Project|Visio')

                    if ($isExcluded) {
                        Write-LicLog -Message "Clave excluida explícitamente: $key5 ($licName)" -Level 'INFO'
                        continue
                    }

                    if ($Mode -eq 'Selectivo' -and $isProjectOrVisio) {
                        Write-LicLog -Message "Modo Selectivo: se conserva licencia perpetua/volumen de Project/Visio -> $key5 ($licName)" -Level 'INFO'
                        continue
                    }

                    if ($PSCmdlet.ShouldProcess("Clave $key5 ($licName)", 'Desinstalar clave de producto con ospp.vbs /unpkey')) {
                        $unpkeyOut = & cscript.exe //nologo $osppPath "/unpkey:$key5" 2>&1
                        Write-LicLog -Message "Resultado /unpkey:$key5 ($licName) -> $($unpkeyOut -join ' ')" -Level 'INFO'
                    }
                }
            }
        }
    } catch {
        Write-LicLog -Message "Error durante la consulta/remoción de claves con ospp.vbs: $($_.Exception.Message)" -Level 'ERROR'
    }

    # Paso 3: Limpiar almacenamiento de licencias vNext
    $vNextPath = Join-Path -Path $env:LOCALAPPDATA -ChildPath 'Microsoft\Office\16.0\Licensing'
    try {
        if (Test-Path -LiteralPath $vNextPath) {
            if ($PSCmdlet.ShouldProcess($vNextPath, 'Eliminar almacenamiento de licencias vNext')) {
                Remove-Item -LiteralPath $vNextPath -Recurse -Force -ErrorAction Stop
                Write-LicLog -Message "Almacenamiento vNext eliminado: $vNextPath" -Level 'INFO'
            }
        } else {
            Write-LicLog -Message "Directorio vNext no encontrado (omitido): $vNextPath" -Level 'INFO'
        }
    } catch {
        Write-LicLog -Message "Error al eliminar almacenamiento vNext '$vNextPath': $($_.Exception.Message)" -Level 'ERROR'
    }

    # Paso 4: Limpiar claves y valores residuales de licenciamiento en HKCU y HKLM (preservando instalación C2R)
    $hkcuLicensingPath = 'HKCU:\Software\Microsoft\Office\16.0\Common\Licensing'
    try {
        if (Test-Path -LiteralPath $hkcuLicensingPath) {
            if ($PSCmdlet.ShouldProcess($hkcuLicensingPath, 'Eliminar clave de registro residual de licenciamiento en HKCU')) {
                Remove-Item -LiteralPath $hkcuLicensingPath -Recurse -Force -ErrorAction Stop
                Write-LicLog -Message "Clave de registro eliminada: $hkcuLicensingPath" -Level 'INFO'
            }
        } else {
            Write-LicLog -Message "Clave de registro no encontrada (omitida): $hkcuLicensingPath" -Level 'INFO'
        }
    } catch {
        Write-LicLog -Message "Error al eliminar clave de registro '$hkcuLicensingPath': $($_.Exception.Message)" -Level 'ERROR'
    }

    $c2rConfigPath = 'HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration'
    $c2rLicensingSubKey = "$c2rConfigPath\Licensing"
    try {
        if (Test-Path -LiteralPath $c2rLicensingSubKey) {
            if ($PSCmdlet.ShouldProcess($c2rLicensingSubKey, 'Eliminar subclave Licensing residual en ClickToRun')) {
                Remove-Item -LiteralPath $c2rLicensingSubKey -Recurse -Force -ErrorAction Stop
                Write-LicLog -Message "Subclave residual eliminada: $c2rLicensingSubKey" -Level 'INFO'
            }
        }

        if (Test-Path -LiteralPath $c2rConfigPath) {
            $c2rItem = Get-Item -LiteralPath $c2rConfigPath -ErrorAction Stop

            # Lista explícita de valores estructurales de instalación C2R que nunca deben eliminarse
            $protectedC2RValues = @(
                'Platform',
                'VersionToReport',
                'ProductReleaseIds',
                'ClientCulture',
                'InstallationPath',
                'CDNBaseUrl',
                'ClientFolder',
                'ClientVersionToReport',
                'UpdateChannel',
                'UpdateUrl',
                'UpdatesEnabled',
                'PackageGUID',
                'SharedComputerLicensing'
            )

            $residualValuePatterns = '\.EmailAddress$|^SCLCacheOverride$|^DeviceBasedLicensing$'

            foreach ($valName in $c2rItem.GetValueNames()) {
                if ([string]::IsNullOrEmpty($valName) -or ($protectedC2RValues -contains $valName)) {
                    continue
                }

                $isOsppReady = ($valName -match '\.OSPPReady$')
                $isProjectOrVisioVal = ($valName -match 'Project|Visio')
                $shouldDelete = ($valName -match $residualValuePatterns) -or ($isOsppReady -and (($Mode -eq 'Total') -or (-not $isProjectOrVisioVal)))

                if ($shouldDelete) {
                    if ($PSCmdlet.ShouldProcess("$c2rConfigPath\$valName", 'Eliminar valor residual de activación/licencia en ClickToRun\Configuration')) {
                        Remove-ItemProperty -LiteralPath $c2rConfigPath -Name $valName -Force -ErrorAction Stop
                        Write-LicLog -Message "Valor residual de activación eliminado en ClickToRun\Configuration: $valName" -Level 'INFO'
                    }
                }
            }
        }
    } catch {
        Write-LicLog -Message "Error al limpiar valores residuales de activación en ClickToRun\Configuration: $($_.Exception.Message)" -Level 'ERROR'
    }

    Write-LicLog -Message 'Restablecimiento de licencias completado. El entorno está listo para reactivación.' -Level 'INFO'
}
