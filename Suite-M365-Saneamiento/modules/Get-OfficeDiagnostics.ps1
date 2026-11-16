<#
.SYNOPSIS
    Módulo de diagnóstico de solo lectura para Microsoft 365 Apps y Office.
.DESCRIPTION
    Detecta versiones instaladas (Click-to-Run y MSI), arquitectura del sistema,
    archivos sppc.dll inyectados o modificados (indicador de parche Ohook),
    ubicación de ospp.vbs, análisis bloque por bloque de ospp.vbs /dstatus en tabla,
    y existencia de cachés de identidad (OneAuth, IdentityCache, TokenBroker, AAD.BrokerPlugin)
    y almacenamiento de licenciamiento vNext.
#>

function Get-OsppPath {
    [CmdletBinding()]
    param()

    $candidatePaths = @(
        "${env:ProgramFiles}\Microsoft Office\Office16\ospp.vbs",
        "${env:ProgramFiles(x86)}\Microsoft Office\Office16\ospp.vbs",
        "${env:ProgramFiles}\Microsoft Office\Office15\ospp.vbs",
        "${env:ProgramFiles(x86)}\Microsoft Office\Office15\ospp.vbs"
    )

    foreach ($path in $candidatePaths) {
        if ($path -and (Test-Path -LiteralPath $path -PathType Leaf)) {
            return $path
        }
    }

    return $null
}

function Get-OsppLicenseBlocks {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$OsppPath
    )

    $rawOutput = & cscript.exe //nologo $OsppPath /dstatus 2>&1
    $licenses = @()

    $currentBlock = @{
        LicenseName    = $null
        ApplicationId  = $null
        LicenseStatus  = $null
        PartialKey     = $null
    }

    foreach ($line in $rawOutput) {
        $text = [string]$line

        if ($text -match '^-{3,}') {
            if ($currentBlock.LicenseName -or $currentBlock.PartialKey -or $currentBlock.ApplicationId) {
                $classification = 'Otro'
                if ($currentBlock.LicenseName -match 'Project|Visio') {
                    $classification = 'Project / Visio'
                } elseif ($currentBlock.LicenseName -match 'O365|365|ProPlus|Mondo|Office|Standard') {
                    $classification = 'Microsoft 365 / ProPlus'
                }

                $licenses += [PSCustomObject]@{
                    Category      = $classification
                    LicenseName   = $currentBlock.LicenseName
                    ApplicationId = $currentBlock.ApplicationId
                    LicenseStatus = $currentBlock.LicenseStatus
                    PartialKey    = $currentBlock.PartialKey
                }

                $currentBlock = @{
                    LicenseName    = $null
                    ApplicationId  = $null
                    LicenseStatus  = $null
                    PartialKey     = $null
                }
            }
            continue
        }

        if ($text -match 'LICENSE NAME:\s*(.+)$') {
            $currentBlock.LicenseName = $Matches[1].Trim()
        } elseif ($text -match 'APPLICATION ID:\s*(.+)$') {
            $currentBlock.ApplicationId = $Matches[1].Trim()
        } elseif ($text -match 'LICENSE STATUS:\s*(.+)$') {
            $currentBlock.LicenseStatus = $Matches[1].Trim()
        } elseif ($text -match 'Last 5 characters of installed product key:\s*([A-Z0-9]{5})') {
            $currentBlock.PartialKey = $Matches[1].Trim()
        }
    }

    if ($currentBlock.LicenseName -or $currentBlock.PartialKey -or $currentBlock.ApplicationId) {
        $classification = 'Otro'
        if ($currentBlock.LicenseName -match 'Project|Visio') {
            $classification = 'Project / Visio'
        } elseif ($currentBlock.LicenseName -match 'O365|365|ProPlus|Mondo|Office|Standard') {
            $classification = 'Microsoft 365 / ProPlus'
        }

        $licenses += [PSCustomObject]@{
            Category      = $classification
            LicenseName   = $currentBlock.LicenseName
            ApplicationId = $currentBlock.ApplicationId
            LicenseStatus = $currentBlock.LicenseStatus
            PartialKey    = $currentBlock.PartialKey
        }
    }

    return [PSCustomObject]@{
        RawText  = ($rawOutput -join "`r`n")
        Licenses = $licenses
    }
}

function Get-OfficeDiagnostics {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)]
        [scriptblock]$Logger
    )

    function Write-DiagLog {
        param([string]$Message, [string]$Level = 'INFO')
        if ($Logger) {
            & $Logger -Message $Message -Level $Level
        } else {
            Write-Host "[$Level] $Message"
        }
    }

    Write-DiagLog -Message 'Iniciando diagnóstico de entorno de Microsoft Office (solo lectura).' -Level 'INFO'

    $diagnostics = [PSCustomObject]@{
        Timestamp          = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
        OSArchitecture     = if ([Environment]::Is64BitOperatingSystem) { '64-bit' } else { '32-bit' }
        OsppPath           = $null
        ClickToRun         = $null
        MsiInstallations   = @()
        SppcHooks          = @()
        ParsedLicenses     = @()
        OsppStatusRaw      = $null
        IdentityCaches     = @()
        VNextLicensingPath = $null
        VNextFiles         = @()
    }

    # 1. Detección de Click-to-Run
    $c2rRegPath = 'HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration'
    try {
        if (Test-Path -LiteralPath $c2rRegPath) {
            $c2rProps = Get-ItemProperty -LiteralPath $c2rRegPath -ErrorAction Stop
            $diagnostics.ClickToRun = [PSCustomObject]@{
                Platform                = $c2rProps.Platform
                VersionToReport         = $c2rProps.VersionToReport
                ProductReleaseIds       = $c2rProps.ProductReleaseIds
                CDNBaseUrl              = $c2rProps.CDNBaseUrl
                ClientCulture           = $c2rProps.ClientCulture
                SharedComputerLicensing = $c2rProps.SharedComputerLicensing
            }
            Write-DiagLog -Message "Click-to-Run detectado. Plataforma: $($c2rProps.Platform) | Versión: $($c2rProps.VersionToReport) | Productos: $($c2rProps.ProductReleaseIds)" -Level 'INFO'
        } else {
            Write-DiagLog -Message 'No se detectó configuración de Office Click-to-Run en el registro.' -Level 'WARN'
        }
    } catch {
        Write-DiagLog -Message "Error al consultar configuración Click-to-Run: $($_.Exception.Message)" -Level 'ERROR'
    }

    # 2. Detección de instalaciones MSI tradicionales
    $uninstallPaths = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    try {
        $msiItems = Get-ItemProperty -Path $uninstallPaths -ErrorAction SilentlyContinue |
            Where-Object {
                $_.DisplayName -match 'Microsoft Office|Microsoft Project|Microsoft Visio' -and
                $_.WindowsInstaller -eq 1
            } |
            Select-Object DisplayName, DisplayVersion, Publisher

        if ($msiItems) {
            $diagnostics.MsiInstallations = @($msiItems)
            foreach ($item in $msiItems) {
                Write-DiagLog -Message "Instalación MSI detectada: $($item.DisplayName) ($($item.DisplayVersion))" -Level 'INFO'
            }
        } else {
            Write-DiagLog -Message 'No se detectaron instalaciones MSI de Office/Project/Visio.' -Level 'INFO'
        }
    } catch {
        Write-DiagLog -Message "Error al consultar instalaciones MSI: $($_.Exception.Message)" -Level 'ERROR'
    }

    # 3. Detección de archivos sppc.dll inyectados o modificados (indicador de parche Ohook)
    $sppcCandidateDirs = @(
        "${env:ProgramFiles}\Microsoft Office\root\vfs\System",
        "${env:ProgramFiles(x86)}\Microsoft Office\root\vfs\SystemX86",
        "${env:ProgramFiles(x86)}\Microsoft Office\root\vfs\System"
    )

    foreach ($dir in $sppcCandidateDirs) {
        if (-not $dir) { continue }
        $sppcFile = Join-Path -Path $dir -ChildPath 'sppc.dll'
        try {
            if (Test-Path -LiteralPath $sppcFile -PathType Leaf) {
                $fileInfo = Get-Item -LiteralPath $sppcFile -ErrorAction Stop
                $sig = Get-AuthenticodeSignature -LiteralPath $sppcFile -ErrorAction SilentlyContinue
                $sigStatus = if ($sig) { $sig.Status.ToString() } else { 'Desconocido' }

                $hookInfo = [PSCustomObject]@{
                    Path            = $sppcFile
                    LengthBytes     = $fileInfo.Length
                    LastWriteTime   = $fileInfo.LastWriteTime
                    SignatureStatus = $sigStatus
                }
                $diagnostics.SppcHooks += $hookInfo
                Write-DiagLog -Message "ALERTA: Archivo sppc.dll detectado (posible parche Ohook): $sppcFile | Tamaño: $($fileInfo.Length) bytes | Firma: $sigStatus" -Level 'WARN'
            }
        } catch {
            Write-DiagLog -Message "Error al inspeccionar '$sppcFile': $($_.Exception.Message)" -Level 'ERROR'
        }
    }

    if ($diagnostics.SppcHooks.Count -eq 0) {
        Write-DiagLog -Message 'No se detectaron archivos sppc.dll en rutas VFS de Office.' -Level 'INFO'
    }

    # 4. Ubicación de ospp.vbs y análisis bloque por bloque de /dstatus
    try {
        $osppPath = Get-OsppPath
        $diagnostics.OsppPath = $osppPath

        if ($osppPath) {
            Write-DiagLog -Message "Archivo ospp.vbs localizado en: $osppPath" -Level 'INFO'
            Write-DiagLog -Message 'Ejecutando y analizando ospp.vbs /dstatus...' -Level 'INFO'

            $parsed = Get-OsppLicenseBlocks -OsppPath $osppPath
            $diagnostics.OsppStatusRaw = $parsed.RawText
            $diagnostics.ParsedLicenses = @($parsed.Licenses)

            if ($diagnostics.ParsedLicenses.Count -gt 0) {
                $tableText = ($diagnostics.ParsedLicenses | Format-Table -Property Category, LicenseName, ApplicationId, LicenseStatus, PartialKey -AutoSize | Out-String).TrimEnd()
                Write-DiagLog -Message "Licencias detectadas por ospp.vbs /dstatus:`r`n$tableText" -Level 'INFO'
            } else {
                Write-DiagLog -Message 'No se identificaron bloques de licencia en la salida de ospp.vbs /dstatus.' -Level 'WARN'
            }
        } else {
            Write-DiagLog -Message 'No se encontró ospp.vbs en las rutas estándar de Office15/Office16.' -Level 'WARN'
        }
    } catch {
        Write-DiagLog -Message "Error al ejecutar ospp.vbs /dstatus: $($_.Exception.Message)" -Level 'ERROR'
    }

    # 5. Verificación de cachés de identidad (OneAuth, IdentityCache, TokenBroker, AAD.BrokerPlugin)
    $cacheLocations = @(
        @{ Name = 'OneAuth'; Path = (Join-Path -Path $env:LOCALAPPDATA -ChildPath 'Microsoft\OneAuth') },
        @{ Name = 'IdentityCache'; Path = (Join-Path -Path $env:LOCALAPPDATA -ChildPath 'Microsoft\IdentityCache') },
        @{ Name = 'TokenBroker'; Path = (Join-Path -Path $env:LOCALAPPDATA -ChildPath 'Microsoft\TokenBroker') }
    )

    $packagesRoot = Join-Path -Path $env:LOCALAPPDATA -ChildPath 'Packages'
    try {
        if (Test-Path -LiteralPath $packagesRoot) {
            $aadPackages = Get-ChildItem -LiteralPath $packagesRoot -Directory -Filter 'Microsoft.AAD.BrokerPlugin*' -ErrorAction SilentlyContinue
            if ($aadPackages) {
                foreach ($pkg in $aadPackages) {
                    $cacheLocations += @{ Name = "UWP:$($pkg.Name)"; Path = $pkg.FullName }
                }
            } else {
                $cacheLocations += @{ Name = 'UWP:Microsoft.AAD.BrokerPlugin'; Path = (Join-Path -Path $packagesRoot -ChildPath 'Microsoft.AAD.BrokerPlugin_cw5n1h2txyewy') }
            }
        }
    } catch {
        Write-DiagLog -Message "Error al buscar paquetes UWP de AAD.BrokerPlugin: $($_.Exception.Message)" -Level 'ERROR'
    }

    foreach ($loc in $cacheLocations) {
        try {
            $exists = Test-Path -LiteralPath $loc.Path
            $itemCount = 0
            if ($exists) {
                $itemCount = (Get-ChildItem -LiteralPath $loc.Path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
            }

            $cacheObj = [PSCustomObject]@{
                Component = $loc.Name
                Exists    = $exists
                FileCount = $itemCount
                Path      = $loc.Path
            }
            $diagnostics.IdentityCaches += $cacheObj

            if ($exists) {
                Write-DiagLog -Message "Caché de identidad [$($loc.Name)] presente ($itemCount archivos): $($loc.Path)" -Level 'INFO'
            } else {
                Write-DiagLog -Message "Caché de identidad [$($loc.Name)] no presente: $($loc.Path)" -Level 'INFO'
            }
        } catch {
            Write-DiagLog -Message "Error al verificar caché [$($loc.Name)]: $($_.Exception.Message)" -Level 'ERROR'
        }
    }

    # 6. Revisión de almacenamiento de licencias vNext
    $vNextPath = Join-Path -Path $env:LOCALAPPDATA -ChildPath 'Microsoft\Office\16.0\Licensing'
    $diagnostics.VNextLicensingPath = $vNextPath
    try {
        if (Test-Path -LiteralPath $vNextPath) {
            $files = Get-ChildItem -LiteralPath $vNextPath -File -Recurse -ErrorAction Stop
            $diagnostics.VNextFiles = @($files | Select-Object Name, FullName, LastWriteTime, Length)
            Write-DiagLog -Message "Almacenamiento vNext encontrado ($($files.Count) archivos) en: $vNextPath" -Level 'INFO'
        } else {
            Write-DiagLog -Message "No existe directorio de licenciamiento vNext en: $vNextPath" -Level 'INFO'
        }
    } catch {
        Write-DiagLog -Message "Error al inspeccionar directorio vNext: $($_.Exception.Message)" -Level 'ERROR'
    }

    Write-DiagLog -Message 'Diagnóstico completado.' -Level 'INFO'
    return $diagnostics
}
