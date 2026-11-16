<#
.SYNOPSIS
    Módulo para limpiar la caché de identidad, intermediario WAM, credenciales y tokens de Office.
.DESCRIPTION
    Detiene el proceso Microsoft.AAD.BrokerPlugin si está activo, elimina cachés de
    OneAuth, IdentityCache, TokenBroker\Cache y el paquete UWP Microsoft.AAD.BrokerPlugin
    (para corregir el error "Try again"), limpia credenciales en cmdkey (MicrosoftOffice,
    ADAL, msteams) y elimina valores y subclaves residuales bajo
    HKCU:\Software\Microsoft\Office\16.0\Common\Identity.
    Soporta -WhatIf y -Confirm.
#>

function Clear-IdentityCache {
    [CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
    param(
        [Parameter(Mandatory = $false)]
        [scriptblock]$Logger
    )

    function Write-IdLog {
        param([string]$Message, [string]$Level = 'INFO')
        if ($Logger) {
            & $Logger -Message $Message -Level $Level
        } else {
            Write-Host "[$Level] $Message"
        }
    }

    Write-IdLog -Message 'Iniciando limpieza de caché de identidad, WAM y credenciales de Office.' -Level 'INFO'

    # 1. Detener procesos Microsoft.AAD.BrokerPlugin si están activos
    try {
        $brokerProcs = Get-Process -Name 'Microsoft.AAD.BrokerPlugin' -ErrorAction SilentlyContinue
        if ($brokerProcs) {
            if ($PSCmdlet.ShouldProcess('Microsoft.AAD.BrokerPlugin', 'Finalizar proceso de intermediario WAM')) {
                $brokerProcs | Stop-Process -Force -ErrorAction Stop
                Write-IdLog -Message 'Proceso Microsoft.AAD.BrokerPlugin finalizado correctamente.' -Level 'INFO'
            }
        } else {
            Write-IdLog -Message 'El proceso Microsoft.AAD.BrokerPlugin no se encuentra en ejecución.' -Level 'INFO'
        }
    } catch {
        Write-IdLog -Message "Error al detener Microsoft.AAD.BrokerPlugin: $($_.Exception.Message)" -Level 'ERROR'
    }

    # 2. Limpieza de directorios de aplicación (OneAuth, IdentityCache) y contenido WAM/UWP (preservando ACLs)
    $appCacheFolders = @(
        (Join-Path -Path $env:LOCALAPPDATA -ChildPath 'Microsoft\OneAuth'),
        (Join-Path -Path $env:LOCALAPPDATA -ChildPath 'Microsoft\IdentityCache')
    )

    foreach ($folder in $appCacheFolders) {
        try {
            if (Test-Path -LiteralPath $folder) {
                if ($PSCmdlet.ShouldProcess($folder, 'Eliminar directorio de caché de identidad de aplicación')) {
                    Remove-Item -LiteralPath $folder -Recurse -Force -ErrorAction Stop
                    Write-IdLog -Message "Directorio eliminado: $folder" -Level 'INFO'
                }
            } else {
                Write-IdLog -Message "Directorio no encontrado (omitido): $folder" -Level 'INFO'
            }
        } catch {
            Write-IdLog -Message "Error al eliminar directorio '$folder': $($_.Exception.Message)" -Level 'ERROR'
        }
    }

    # Se vacía únicamente el contenido interno de los directorios WAM/UWP para mantener intactas las ACLs de AppContainer
    $wamCacheFolders = @(
        (Join-Path -Path $env:LOCALAPPDATA -ChildPath 'Microsoft\TokenBroker\Cache'),
        (Join-Path -Path $env:LOCALAPPDATA -ChildPath 'Packages\Microsoft.AAD.BrokerPlugin_cw5n1h2txyewy\AC\TokenBroker')
    )

    foreach ($folder in $wamCacheFolders) {
        try {
            if (Test-Path -LiteralPath $folder) {
                $childItems = @(Get-ChildItem -LiteralPath $folder -Force -ErrorAction SilentlyContinue)
                if ($childItems.Count -gt 0) {
                    if ($PSCmdlet.ShouldProcess($folder, 'Vaciar contenido de caché WAM/UWP preservando ACLs del contenedor')) {
                        $childItems | Remove-Item -Recurse -Force -ErrorAction Stop
                        Write-IdLog -Message "Contenido de caché WAM/UWP vaciado ($($childItems.Count) elementos): $folder" -Level 'INFO'
                    }
                } else {
                    Write-IdLog -Message "Directorio WAM/UWP ya se encuentra vacío (omitido): $folder" -Level 'INFO'
                }
            } else {
                Write-IdLog -Message "Directorio WAM/UWP no encontrado (omitido): $folder" -Level 'INFO'
            }
        } catch {
            Write-IdLog -Message "Error al vaciar contenido de caché WAM/UWP '$folder': $($_.Exception.Message)" -Level 'ERROR'
        }
    }

    # 3. Limpieza de credenciales en Windows Credential Manager (cmdkey)
    try {
        $cmdkeyOutput = & cmdkey.exe /list 2>&1
        $targetLines = $cmdkeyOutput | Select-String -Pattern 'Target:\s*(.+)$'
        $matchedTargets = @()

        foreach ($match in $targetLines) {
            $targetName = $match.Matches[0].Groups[1].Value.Trim()
            if ($targetName -match 'MicrosoftOffice|ADAL|msteams|OneAuth|MSAccount') {
                $matchedTargets += $targetName
            }
        }

        if ($matchedTargets.Count -eq 0) {
            Write-IdLog -Message 'No se encontraron credenciales de MicrosoftOffice/ADAL/msteams en cmdkey.' -Level 'INFO'
        } else {
            foreach ($target in $matchedTargets) {
                if ($PSCmdlet.ShouldProcess($target, 'Eliminar credencial en Administrador de Credenciales (cmdkey)')) {
                    $delResult = & cmdkey.exe /delete:$target 2>&1
                    Write-IdLog -Message "Credencial eliminada '$target': $($delResult -join ' ')" -Level 'INFO'
                }
            }
        }
    } catch {
        Write-IdLog -Message "Error al procesar credenciales en cmdkey: $($_.Exception.Message)" -Level 'ERROR'
    }

    # 4. Limpieza de valores residuales y subclaves en HKCU:\Software\Microsoft\Office\16.0\Common\Identity
    $identityRegPath = 'HKCU:\Software\Microsoft\Office\16.0\Common\Identity'
    $subKeysToClean = @(
        "$identityRegPath\Identities",
        "$identityRegPath\Profiles"
    )

    foreach ($regKey in $subKeysToClean) {
        try {
            if (Test-Path -LiteralPath $regKey) {
                if ($PSCmdlet.ShouldProcess($regKey, 'Eliminar subclave de registro de identidad de Office')) {
                    Remove-Item -LiteralPath $regKey -Recurse -Force -ErrorAction Stop
                    Write-IdLog -Message "Subclave de registro eliminada: $regKey" -Level 'INFO'
                }
            } else {
                Write-IdLog -Message "Subclave de registro no encontrada (omitida): $regKey" -Level 'INFO'
            }
        } catch {
            Write-IdLog -Message "Error al eliminar subclave de registro '$regKey': $($_.Exception.Message)" -Level 'ERROR'
        }
    }

    try {
        if (Test-Path -LiteralPath $identityRegPath) {
            $regItem = Get-Item -LiteralPath $identityRegPath -ErrorAction Stop
            $valueNames = $regItem.GetValueNames()
            if ($valueNames.Count -gt 0) {
                foreach ($valName in $valueNames) {
                    if ([string]::IsNullOrEmpty($valName)) { continue }
                    if ($PSCmdlet.ShouldProcess("$identityRegPath\$valName", 'Eliminar valor residual de identidad en registro')) {
                        Remove-ItemProperty -LiteralPath $identityRegPath -Name $valName -Force -ErrorAction Stop
                        Write-IdLog -Message "Valor residual eliminado en Identity: $valName" -Level 'INFO'
                    }
                }
            } else {
                Write-IdLog -Message "No hay valores residuales directos en $identityRegPath." -Level 'INFO'
            }
        }
    } catch {
        Write-IdLog -Message "Error al limpiar valores residuales en '$identityRegPath': $($_.Exception.Message)" -Level 'ERROR'
    }

    Write-IdLog -Message 'Limpieza de caché de identidad y WAM finalizada.' -Level 'INFO'
}
