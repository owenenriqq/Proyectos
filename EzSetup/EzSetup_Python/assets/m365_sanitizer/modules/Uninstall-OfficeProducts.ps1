<#
.SYNOPSIS
    Módulo para inventariar y desinstalar productos de Microsoft Office, Project y Visio.
.DESCRIPTION
    Detecta instalaciones Click-to-Run (HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration)
    y MSI (HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall y WOW6432Node),
    clasificando cada producto en Suite Office, Project o Visio.
    Ofrece dos modos de desinstalación con doble confirmación explícita:
    1. Selectivo por producto: desinstala únicamente los ProductReleaseIds o ProductCodes
       seleccionados mediante OfficeClickToRun.exe (DisplayLevel=False) o msiexec.exe (/x /qn /norestart).
    2. Total + Limpieza profunda: desinstala todos los productos detectados, detiene y elimina
       el servicio ClickToRunSvc residual, elimina carpetas huérfanas de Office y tareas programadas,
       y ejecuta automáticamente Clear-IdentityCache y Reset-OfficeLicenses (-Mode Total).
    Soporta -WhatIf y -Confirm. Compatible estrictamente con PowerShell 5.1.
#>

function Write-UninstLog {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,

        [Parameter(Mandatory = $false)]
        [ValidateSet('INFO', 'WARN', 'ERROR')]
        [string]$Level = 'INFO',

        [Parameter(Mandatory = $false)]
        [scriptblock]$Logger
    )

    if ($Logger) {
        $null = & $Logger -Message $Message -Level $Level
    } else {
        switch ($Level) {
            'INFO'  { Write-Host "[INFO] $Message" -ForegroundColor Cyan }
            'WARN'  { Write-Host "[WARN] $Message" -ForegroundColor Yellow }
            'ERROR' { Write-Host "[ERROR] $Message" -ForegroundColor Red }
        }
    }
}

function Get-OfficeProductCategory {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)]
        [string]$Identifier = '',

        [Parameter(Mandatory = $false)]
        [string]$DisplayName = ''
    )

    $combined = "$Identifier $DisplayName"
    if ($combined -match 'Project') {
        return 'Project'
    }
    if ($combined -match 'Visio') {
        return 'Visio'
    }
    return 'Suite Office'
}

function Get-OfficeClickToRunExePath {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)]
        [string[]]$InstallationPaths = @()
    )

    $candidates = @()

    # 1. Consultar ImagePath del servicio ClickToRunSvc
    $svcRegPath = 'HKLM:\SYSTEM\CurrentControlSet\Services\ClickToRunSvc'
    try {
        if (Test-Path -LiteralPath $svcRegPath) {
            $svcProps = Get-ItemProperty -LiteralPath $svcRegPath -Name 'ImagePath' -ErrorAction SilentlyContinue
            if ($svcProps -and -not [string]::IsNullOrWhiteSpace($svcProps.ImagePath)) {
                $rawImg = [Environment]::ExpandEnvironmentVariables($svcProps.ImagePath.Trim())
                if ($rawImg -match '^"([^"]+)"') {
                    $candidates += $Matches[1]
                } elseif ($rawImg -match '^([^\s]+)') {
                    $candidates += $Matches[1]
                }
            }
        }
    } catch {
        # Ignorar errores puntuales de lectura del servicio
    }

    # 2. Rutas estándar de CommonProgramFiles
    if ($env:CommonProgramFiles) {
        $candidates += (Join-Path -Path $env:CommonProgramFiles -ChildPath 'Microsoft Shared\ClickToRun\OfficeClickToRun.exe')
    }
    if (${env:CommonProgramFiles(x86)}) {
        $candidates += (Join-Path -Path ${env:CommonProgramFiles(x86)} -ChildPath 'Microsoft Shared\ClickToRun\OfficeClickToRun.exe')
    }

    # 3. Rutas derivadas de InstallationPath detectados
    foreach ($instPath in $InstallationPaths) {
        if (-not [string]::IsNullOrWhiteSpace($instPath)) {
            $cleanPath = $instPath.Trim().TrimEnd('\')
            $candidates += (Join-Path -Path $cleanPath -ChildPath 'OfficeClickToRun.exe')
            $candidates += (Join-Path -Path $cleanPath -ChildPath 'root\Client\OfficeClickToRun.exe')
        }
    }

    $uniqueCandidates = @($candidates | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    foreach ($exePath in $uniqueCandidates) {
        if (Test-Path -LiteralPath $exePath -PathType Leaf) {
            return $exePath
        }
    }

    return $null
}

function Stop-OfficeUserApplications {
    [CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
    param(
        [Parameter(Mandatory = $false)]
        [scriptblock]$Logger
    )

    # No se detiene OfficeClickToRun aquí para no interrumpir el motor durante la desinstalación C2R
    $appProcesses = @(
        'winword', 'excel', 'outlook', 'powerpnt',
        'msaccess', 'mspub', 'onenote', 'onenotem',
        'winproj', 'visio', 'lync', 'teams', 'ms-teams', 'groove'
    )

    Write-UninstLog -Message 'Cerrando aplicaciones de Office en ejecución antes de desinstalar...' -Level 'INFO' -Logger $Logger

    foreach ($procName in $appProcesses) {
        try {
            $running = @(Get-Process -Name $procName -ErrorAction SilentlyContinue)
            if ($running.Count -gt 0) {
                if ($PSCmdlet.ShouldProcess($procName, 'Finalizar aplicación de Office antes de desinstalar')) {
                    $running | Stop-Process -Force -ErrorAction Stop
                    Write-UninstLog -Message "Proceso finalizado: $procName" -Level 'INFO' -Logger $Logger
                }
            }
        } catch {
            Write-UninstLog -Message "Error al finalizar '$procName': $($_.Exception.Message)" -Level 'WARN' -Logger $Logger
        }
    }
}

function Confirm-UninstallDoubleCheck {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$SummaryTitle,

        [Parameter(Mandatory = $true)]
        [string]$FirstPrompt,

        [Parameter(Mandatory = $true)]
        [string]$ConfirmKeyword,

        [Parameter(Mandatory = $false)]
        [scriptblock]$Logger
    )

    Write-Host ''
    Write-Host "=== $SummaryTitle ===" -ForegroundColor Yellow

    $firstAnswer = Read-Host $FirstPrompt
    if ($firstAnswer -notmatch '^[Ss]$') {
        Write-UninstLog -Message 'Operación cancelada por el operador en la primera confirmación.' -Level 'WARN' -Logger $Logger
        return $false
    }

    Write-Host "Segunda confirmación requerida: esta acción modificará o eliminará productos instalados." -ForegroundColor Red
    $secondAnswer = Read-Host "Escriba exactamente '$ConfirmKeyword' para confirmar (cualquier otro valor cancela)"
    if ($null -eq $secondAnswer -or ($secondAnswer.Trim() -cne $ConfirmKeyword)) {
        Write-UninstLog -Message 'Operación cancelada por el operador en la segunda confirmación.' -Level 'WARN' -Logger $Logger
        return $false
    }

    return $true
}

function Get-InstalledOfficeProducts {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)]
        [scriptblock]$Logger,

        [Parameter(Mandatory = $false)]
        [switch]$ShowTable
    )

    $inventory = @()
    $is64BitOS = [Environment]::Is64BitOperatingSystem

    # 1. Pre-lectura única de entradas ARP (Uninstall)
    $arpEntries = @()
    $uninstallRoots = @(
        @{ Path = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'; Arch = if ($is64BitOS) { 'x64' } else { 'x86' } },
        @{ Path = 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'; Arch = 'x86' }
    )

    foreach ($root in $uninstallRoots) {
        try {
            $items = @(Get-ItemProperty -Path $root.Path -ErrorAction SilentlyContinue)
            foreach ($item in $items) {
                if ($null -eq $item) { continue }
                $arpEntries += [PSCustomObject]@{
                    Item = $item
                    Arch = $root.Arch
                }
            }
        } catch {
            Write-UninstLog -Message "Error al leer entradas de desinstalación en '$($root.Path)': $($_.Exception.Message)" -Level 'WARN' -Logger $Logger
        }
    }

    # 2. Detección de productos Click-to-Run
    $c2rRegPaths = @(
        'HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Office\ClickToRun\Configuration'
    )
    $seenC2RIds = @()

    foreach ($c2rPath in $c2rRegPaths) {
        try {
            if (-not (Test-Path -LiteralPath $c2rPath)) {
                continue
            }

            $c2rProps = Get-ItemProperty -LiteralPath $c2rPath -ErrorAction Stop
            $rawIds = $null
            if ($c2rProps.PSObject.Properties['ProductReleaseIds']) {
                $rawIds = $c2rProps.ProductReleaseIds
            }
            if ([string]::IsNullOrWhiteSpace($rawIds)) {
                continue
            }

            $c2rPlatform = if ($c2rProps.PSObject.Properties['Platform'] -and $c2rProps.Platform) { [string]$c2rProps.Platform } else { 'Desconocida' }
            $c2rVersion = if ($c2rProps.PSObject.Properties['VersionToReport'] -and $c2rProps.VersionToReport) { [string]$c2rProps.VersionToReport } else { 'Desconocida' }
            $c2rCulture = if ($c2rProps.PSObject.Properties['ClientCulture'] -and -not [string]::IsNullOrWhiteSpace($c2rProps.ClientCulture)) {
                $c2rProps.ClientCulture.Trim().ToLower()
            } else {
                'es-es'
            }
            $c2rInstallPath = if ($c2rProps.PSObject.Properties['InstallationPath'] -and $c2rProps.InstallationPath) {
                [string]$c2rProps.InstallationPath.Trim().TrimEnd('\')
            } else {
                $null
            }

            $releaseIds = @($rawIds -split ',' | ForEach-Object { $_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })

            foreach ($releaseId in $releaseIds) {
                $releaseKey = $releaseId.ToLower()
                if ($seenC2RIds -contains $releaseKey) {
                    continue
                }
                $seenC2RIds += $releaseKey

                # Buscar entrada ARP asociada para obtener DisplayName y parámetros reales de OfficeClickToRun.exe
                $matchedArp = $null
                $escapedId = [regex]::Escape($releaseId)
                foreach ($entry in $arpEntries) {
                    $it = $entry.Item
                    $uninstStr = if ($it.PSObject.Properties['UninstallString'] -and $it.UninstallString) { [string]$it.UninstallString } else { '' }
                    $childName = if ($it.PSObject.Properties['PSChildName'] -and $it.PSChildName) { [string]$it.PSChildName } else { '' }

                    if (($uninstStr -match 'OfficeClickToRun\.exe' -and $uninstStr -match "productstoremove=$escapedId\.") -or
                        ($childName -match "^$escapedId\s+-")) {
                        $matchedArp = $it
                        break
                    }
                }

                $displayName = "$releaseId (Click-to-Run)"
                $removeToken = "$releaseId.16_${c2rCulture}_x-none"
                $culture = $c2rCulture
                $ver16 = '16.0'
                $prodVersion = $c2rVersion

                if ($matchedArp) {
                    if ($matchedArp.PSObject.Properties['DisplayName'] -and -not [string]::IsNullOrWhiteSpace($matchedArp.DisplayName)) {
                        $displayName = [string]$matchedArp.DisplayName
                    }
                    if ($matchedArp.PSObject.Properties['DisplayVersion'] -and -not [string]::IsNullOrWhiteSpace($matchedArp.DisplayVersion)) {
                        $prodVersion = [string]$matchedArp.DisplayVersion
                    }
                    $arpUninst = if ($matchedArp.PSObject.Properties['UninstallString'] -and $matchedArp.UninstallString) { [string]$matchedArp.UninstallString } else { '' }
                    if ($arpUninst -match 'productstoremove=([^\s]+)') {
                        $removeToken = $Matches[1].Trim('"')
                    }
                    if ($arpUninst -match 'culture=([^\s]+)') {
                        $culture = $Matches[1].Trim('"')
                    }
                    if ($arpUninst -match 'version\.16=([^\s]+)') {
                        $ver16 = $Matches[1].Trim('"')
                    }
                }

                $category = Get-OfficeProductCategory -Identifier $releaseId -DisplayName $displayName

                $inventory += [PSCustomObject]@{
                    Index              = 0
                    InstallType        = 'Click-to-Run'
                    Category           = $category
                    ProductId          = $releaseId
                    DisplayName        = $displayName
                    Version            = $prodVersion
                    Platform           = $c2rPlatform
                    Culture            = $culture
                    ProductRemoveToken = $removeToken
                    Version16          = $ver16
                    InstallationPath   = $c2rInstallPath
                }
            }
        } catch {
            Write-UninstLog -Message "Error al consultar configuración Click-to-Run en '$c2rPath': $($_.Exception.Message)" -Level 'ERROR' -Logger $Logger
        }
    }

    # 3. Detección de productos MSI
    $seenMsiCodes = @()
    $guidPattern = '\{[0-9A-Fa-f]{8}-([0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}\}'

    foreach ($entry in $arpEntries) {
        $item = $entry.Item

        $hasWinInst = $item.PSObject.Properties['WindowsInstaller'] -and ($item.WindowsInstaller -eq 1)
        if (-not $hasWinInst) { continue }

        $dispName = if ($item.PSObject.Properties['DisplayName'] -and $item.DisplayName) { [string]$item.DisplayName } else { '' }
        if ($dispName -notmatch 'Microsoft Office|Microsoft Project|Microsoft Visio') { continue }

        # Excluir actualizaciones, parches y entradas de Click-to-Run
        if ($item.PSObject.Properties['ParentKeyName'] -and -not [string]::IsNullOrWhiteSpace($item.ParentKeyName)) { continue }
        if ($item.PSObject.Properties['ReleaseType'] -and ($item.ReleaseType -match 'Update|Hotfix|Security Update')) { continue }

        $uninstStr = if ($item.PSObject.Properties['UninstallString'] -and $item.UninstallString) { [string]$item.UninstallString } else { '' }
        if ($uninstStr -match 'OfficeClickToRun\.exe') { continue }

        $childName = if ($item.PSObject.Properties['PSChildName'] -and $item.PSChildName) { [string]$item.PSChildName } else { '' }
        $productCode = $null
        if ($childName -match $guidPattern) {
            $productCode = $Matches[0].ToUpper()
        } elseif ($uninstStr -match $guidPattern) {
            $productCode = $Matches[0].ToUpper()
        }

        if (-not $productCode) { continue }
        if ($seenMsiCodes -contains $productCode) { continue }
        $seenMsiCodes += $productCode

        $dispVer = if ($item.PSObject.Properties['DisplayVersion'] -and $item.DisplayVersion) { [string]$item.DisplayVersion } else { 'Desconocida' }
        $category = Get-OfficeProductCategory -Identifier $productCode -DisplayName $dispName

        $inventory += [PSCustomObject]@{
            Index              = 0
            InstallType        = 'MSI'
            Category           = $category
            ProductId          = $productCode
            DisplayName        = $dispName
            Version            = $dispVer
            Platform           = $entry.Arch
            Culture            = $null
            ProductRemoveToken = $null
            Version16          = $null
            InstallationPath   = $null
        }
    }

    # 4. Ordenar y asignar índice secuencial
    $inventory = @($inventory | Sort-Object -Property InstallType, Category, ProductId)
    for ($i = 0; $i -lt $inventory.Count; $i++) {
        $inventory[$i].Index = $i + 1
    }

    if ($ShowTable) {
        if ($inventory.Count -eq 0) {
            Write-UninstLog -Message 'No se detectaron productos de Office, Project ni Visio instalados (ni Click-to-Run ni MSI).' -Level 'WARN' -Logger $Logger
        } else {
            '' | Out-Host
            $inventory | Format-Table -Property Index, InstallType, Category, ProductId, DisplayName, Version, Platform -AutoSize | Out-Host

            $suiteCount = @($inventory | Where-Object { $_.Category -eq 'Suite Office' }).Count
            $projectCount = @($inventory | Where-Object { $_.Category -eq 'Project' }).Count
            $visioCount = @($inventory | Where-Object { $_.Category -eq 'Visio' }).Count

            Write-UninstLog -Message "Inventario detectado ($($inventory.Count) producto(s)): Suite Office=$suiteCount | Project=$projectCount | Visio=$visioCount" -Level 'INFO' -Logger $Logger
        }
    }

    return @($inventory)
}

function Invoke-SingleProductUninstall {
    [CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$Product,

        [Parameter(Mandatory = $false)]
        [string]$ClickToRunExePath,

        [Parameter(Mandatory = $false)]
        [scriptblock]$Logger
    )

    if ($Product.InstallType -eq 'Click-to-Run') {
        if ([string]::IsNullOrWhiteSpace($ClickToRunExePath) -or -not (Test-Path -LiteralPath $ClickToRunExePath -PathType Leaf)) {
            Write-UninstLog -Message "No se encontró OfficeClickToRun.exe para desinstalar '$($Product.ProductId)'." -Level 'ERROR' -Logger $Logger
            return $false
        }

        $argString = "scenario=install scenariosubtype=ARP sourcetype=None productstoremove=$($Product.ProductRemoveToken) culture=$($Product.Culture) version.16=$($Product.Version16) DisplayLevel=False"
        $targetDesc = "$($Product.ProductId) ($($Product.DisplayName))"

        if ($PSCmdlet.ShouldProcess($targetDesc, "Desinstalar producto Click-to-Run en modo silencioso (DisplayLevel=False)")) {
            try {
                Write-UninstLog -Message "Ejecutando desinstalación silenciosa Click-to-Run para $($Product.ProductId)..." -Level 'INFO' -Logger $Logger
                $proc = Start-Process -FilePath $ClickToRunExePath -ArgumentList $argString -Wait -PassThru -NoNewWindow -ErrorAction Stop
                $exitCode = $proc.ExitCode
                if ($exitCode -eq 0) {
                    Write-UninstLog -Message "Producto Click-to-Run desinstalado correctamente: $($Product.ProductId)" -Level 'INFO' -Logger $Logger
                    return $true
                } elseif ($exitCode -eq 3010) {
                    Write-UninstLog -Message "Producto Click-to-Run desinstalado con reinicio pendiente (código 3010): $($Product.ProductId)" -Level 'WARN' -Logger $Logger
                    return $true
                } else {
                    Write-UninstLog -Message "La desinstalación de '$($Product.ProductId)' finalizó con código de salida $exitCode." -Level 'ERROR' -Logger $Logger
                    return $false
                }
            } catch {
                Write-UninstLog -Message "Error al ejecutar OfficeClickToRun.exe para '$($Product.ProductId)': $($_.Exception.Message)" -Level 'ERROR' -Logger $Logger
                return $false
            }
        }
        return $true
    } elseif ($Product.InstallType -eq 'MSI') {
        $guidPattern = '^\{[0-9A-Fa-f]{8}-([0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}\}$'
        if ($Product.ProductId -notmatch $guidPattern) {
            Write-UninstLog -Message "ProductCode MSI inválido para desinstalación: '$($Product.ProductId)'." -Level 'ERROR' -Logger $Logger
            return $false
        }

        $argString = "/x $($Product.ProductId) /qn /norestart"
        $targetDesc = "$($Product.ProductId) ($($Product.DisplayName))"

        if ($PSCmdlet.ShouldProcess($targetDesc, "Desinstalar producto MSI silenciosamente (msiexec.exe $argString)")) {
            try {
                Write-UninstLog -Message "Ejecutando desinstalación silenciosa MSI para $($Product.ProductId) ($($Product.DisplayName))..." -Level 'INFO' -Logger $Logger
                $proc = Start-Process -FilePath 'msiexec.exe' -ArgumentList $argString -Wait -PassThru -NoNewWindow -ErrorAction Stop
                $exitCode = $proc.ExitCode
                if ($exitCode -eq 0) {
                    Write-UninstLog -Message "Producto MSI desinstalado correctamente: $($Product.ProductId)" -Level 'INFO' -Logger $Logger
                    return $true
                } elseif ($exitCode -eq 3010) {
                    Write-UninstLog -Message "Producto MSI desinstalado con reinicio pendiente (código 3010): $($Product.ProductId)" -Level 'WARN' -Logger $Logger
                    return $true
                } elseif ($exitCode -eq 1605) {
                    Write-UninstLog -Message "El producto MSI ya no estaba instalado (código 1605): $($Product.ProductId)" -Level 'WARN' -Logger $Logger
                    return $true
                } else {
                    Write-UninstLog -Message "msiexec.exe finalizó con código de salida $exitCode para '$($Product.ProductId)'." -Level 'ERROR' -Logger $Logger
                    return $false
                }
            } catch {
                Write-UninstLog -Message "Error al ejecutar msiexec.exe para '$($Product.ProductId)': $($_.Exception.Message)" -Level 'ERROR' -Logger $Logger
                return $false
            }
        }
        return $true
    }

    Write-UninstLog -Message "Tipo de instalación desconocido para '$($Product.ProductId)': $($Product.InstallType)" -Level 'ERROR' -Logger $Logger
    return $false
}

function Invoke-OfficeDeepCleanup {
    [CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
    param(
        [Parameter(Mandatory = $false)]
        [string[]]$DetectedInstallationPaths = @(),

        [Parameter(Mandatory = $false)]
        [string]$BackupRoot,

        [Parameter(Mandatory = $false)]
        [scriptblock]$Logger
    )

    Write-UninstLog -Message 'Iniciando limpieza profunda posterior a la desinstalación total de Office...' -Level 'INFO' -Logger $Logger

    # 1. Detener procesos residuales de Click-to-Run
    $c2rResidualProcesses = @('OfficeClickToRun', 'OfficeC2RClient', 'AppVShNotify', 'Integrator', 'msoia', 'sdxhelper')
    foreach ($procName in $c2rResidualProcesses) {
        try {
            $procs = @(Get-Process -Name $procName -ErrorAction SilentlyContinue)
            if ($procs.Count -gt 0) {
                if ($PSCmdlet.ShouldProcess($procName, 'Finalizar proceso residual de Office Click-to-Run')) {
                    $procs | Stop-Process -Force -ErrorAction Stop
                    Write-UninstLog -Message "Proceso residual finalizado: $procName" -Level 'INFO' -Logger $Logger
                }
            }
        } catch {
            Write-UninstLog -Message "Error al finalizar proceso residual '$procName': $($_.Exception.Message)" -Level 'WARN' -Logger $Logger
        }
    }

    # 2. Detener y eliminar el servicio ClickToRunSvc si queda residual
    try {
        $c2rSvc = Get-Service -Name 'ClickToRunSvc' -ErrorAction SilentlyContinue
        if ($c2rSvc) {
            if ($c2rSvc.Status -ne 'Stopped') {
                if ($PSCmdlet.ShouldProcess('ClickToRunSvc', 'Detener servicio residual de Office Click-to-Run')) {
                    Stop-Service -Name 'ClickToRunSvc' -Force -ErrorAction Stop
                    Write-UninstLog -Message 'Servicio ClickToRunSvc detenido.' -Level 'INFO' -Logger $Logger
                }
            }

            if ($PSCmdlet.ShouldProcess('ClickToRunSvc', 'Eliminar servicio ClickToRunSvc mediante sc.exe delete')) {
                $scOut = & sc.exe delete ClickToRunSvc 2>&1
                $scExit = $LASTEXITCODE
                if ($scExit -eq 0) {
                    Write-UninstLog -Message 'Servicio ClickToRunSvc eliminado correctamente.' -Level 'INFO' -Logger $Logger
                } elseif ($scExit -eq 1072) {
                    Write-UninstLog -Message 'Servicio ClickToRunSvc marcado para eliminación tras reiniciar el equipo (código 1072).' -Level 'WARN' -Logger $Logger
                } elseif ($scExit -eq 1060) {
                    Write-UninstLog -Message 'El servicio ClickToRunSvc ya no existe (código 1060).' -Level 'INFO' -Logger $Logger
                } else {
                    Write-UninstLog -Message "Resultado de sc.exe delete ClickToRunSvc (código $scExit): $($scOut -join ' ')" -Level 'WARN' -Logger $Logger
                }
            }
        } else {
            Write-UninstLog -Message 'Servicio ClickToRunSvc no detectado (omitido).' -Level 'INFO' -Logger $Logger
        }
    } catch {
        Write-UninstLog -Message "Error al detener/eliminar servicio ClickToRunSvc: $($_.Exception.Message)" -Level 'ERROR' -Logger $Logger
    }

    # 3. Borrar carpetas huérfanas de Office
    $orphanFolders = @(
        "${env:ProgramFiles}\Microsoft Office",
        "${env:ProgramFiles(x86)}\Microsoft Office",
        "${env:ProgramData}\Microsoft\Office",
        "${env:CommonProgramFiles}\Microsoft Shared\ClickToRun",
        "${env:CommonProgramFiles(x86)}\Microsoft Shared\ClickToRun",
        "${env:ProgramData}\Microsoft\ClickToRun"
    )

    foreach ($extraPath in $DetectedInstallationPaths) {
        if (-not [string]::IsNullOrWhiteSpace($extraPath)) {
            $cleanExtra = $extraPath.Trim().TrimEnd('\')
            # Validación de seguridad para evitar borrar directorios raíz o del sistema
            if ($cleanExtra -match '\\Microsoft Office(\\|$)|\\Office\d*(\\|$)') {
                $orphanFolders += $cleanExtra
            }
        }
    }

    $orphanFolders = @($orphanFolders | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)

    foreach ($folder in $orphanFolders) {
        try {
            if (Test-Path -LiteralPath $folder) {
                if ($PSCmdlet.ShouldProcess($folder, 'Eliminar carpeta huérfana de Office')) {
                    Remove-Item -LiteralPath $folder -Recurse -Force -ErrorAction Stop
                    Write-UninstLog -Message "Carpeta huérfana eliminada: $folder" -Level 'INFO' -Logger $Logger
                }
            } else {
                Write-UninstLog -Message "Carpeta huérfana no encontrada (omitida): $folder" -Level 'INFO' -Logger $Logger
            }
        } catch {
            Write-UninstLog -Message "No se pudo eliminar completamente '$folder' (puede requerir reinicio): $($_.Exception.Message)" -Level 'WARN' -Logger $Logger
        }
    }

    # 4. Eliminar tareas programadas de Office
    try {
        if (Get-Command -Name 'Get-ScheduledTask' -ErrorAction SilentlyContinue) {
            $officeTasks = @(Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object {
                ($_.TaskPath -like '\Microsoft\Office\*') -or
                ($_.TaskName -match '^Office\b|ClickToRun|OfficeTelemetry|OfficeBackgroundTaskHandler|Office Automatic Updates|Office Feature Updates|Office Subscription')
            })

            if ($officeTasks.Count -eq 0) {
                Write-UninstLog -Message 'No se detectaron tareas programadas residuales de Office.' -Level 'INFO' -Logger $Logger
            } else {
                foreach ($task in $officeTasks) {
                    $taskFull = "$($task.TaskPath)$($task.TaskName)"
                    if ($PSCmdlet.ShouldProcess($taskFull, 'Eliminar tarea programada de Office')) {
                        try {
                            Unregister-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath -Confirm:$false -ErrorAction Stop
                            Write-UninstLog -Message "Tarea programada eliminada: $taskFull" -Level 'INFO' -Logger $Logger
                        } catch {
                            Write-UninstLog -Message "Error al eliminar tarea programada '$taskFull': $($_.Exception.Message)" -Level 'WARN' -Logger $Logger
                        }
                    }
                }
            }
        } else {
            Write-UninstLog -Message 'El cmdlet Get-ScheduledTask no está disponible en este entorno; se omite la limpieza de tareas programadas.' -Level 'WARN' -Logger $Logger
        }
    } catch {
        Write-UninstLog -Message "Error al consultar tareas programadas de Office: $($_.Exception.Message)" -Level 'WARN' -Logger $Logger
    }

    # 5. Ejecutar limpieza de identidad/WAM y restablecimiento total de licencias
    try {
        if (-not (Get-Command -Name 'Clear-IdentityCache' -ErrorAction SilentlyContinue)) {
            $idModPath = Join-Path -Path $PSScriptRoot -ChildPath 'Clear-IdentityCache.ps1'
            if (Test-Path -LiteralPath $idModPath -PathType Leaf) {
                . $idModPath
            }
        }
        if (Get-Command -Name 'Clear-IdentityCache' -ErrorAction SilentlyContinue) {
            Write-UninstLog -Message 'Ejecutando limpieza de caché de identidad y WAM (Clear-IdentityCache)...' -Level 'INFO' -Logger $Logger
            Clear-IdentityCache -Logger $Logger -Confirm:$false -WhatIf:$WhatIfPreference
        } else {
            Write-UninstLog -Message 'No se encontró la función Clear-IdentityCache para ejecutar la limpieza de identidad.' -Level 'WARN' -Logger $Logger
        }
    } catch {
        Write-UninstLog -Message "Error al ejecutar Clear-IdentityCache durante la limpieza profunda: $($_.Exception.Message)" -Level 'ERROR' -Logger $Logger
    }

    try {
        if (-not (Get-Command -Name 'Reset-OfficeLicenses' -ErrorAction SilentlyContinue)) {
            $licModPath = Join-Path -Path $PSScriptRoot -ChildPath 'Reset-OfficeLicenses.ps1'
            if (Test-Path -LiteralPath $licModPath -PathType Leaf) {
                . $licModPath
            }
        }
        if (Get-Command -Name 'Reset-OfficeLicenses' -ErrorAction SilentlyContinue) {
            Write-UninstLog -Message 'Ejecutando limpieza total de licencias y sppc.dll (Reset-OfficeLicenses -Mode Total)...' -Level 'INFO' -Logger $Logger
            Reset-OfficeLicenses -Mode 'Total' -BackupRoot $BackupRoot -Logger $Logger -Confirm:$false -WhatIf:$WhatIfPreference
        } else {
            Write-UninstLog -Message 'No se encontró la función Reset-OfficeLicenses para ejecutar la limpieza de licencias.' -Level 'WARN' -Logger $Logger
        }
    } catch {
        Write-UninstLog -Message "Error al ejecutar Reset-OfficeLicenses durante la limpieza profunda: $($_.Exception.Message)" -Level 'ERROR' -Logger $Logger
    }

    Write-UninstLog -Message 'Limpieza profunda de Office finalizada.' -Level 'INFO' -Logger $Logger
}

function Uninstall-OfficeProducts {
    [CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
    param(
        [Parameter(Mandatory = $false)]
        [ValidateSet('Interactivo', 'Selectivo', 'Total')]
        [string]$Mode = 'Interactivo',

        [Parameter(Mandatory = $false)]
        [string[]]$ProductIds = @(),

        [Parameter(Mandatory = $false)]
        [string]$BackupRoot,

        [Parameter(Mandatory = $false)]
        [scriptblock]$Logger
    )

    if (-not $BackupRoot) {
        $projectRoot = Split-Path -Parent $PSScriptRoot
        $BackupRoot = Join-Path -Path $projectRoot -ChildPath 'logs\backup_dll'
    }

    Write-UninstLog -Message 'Iniciando inventario de productos Microsoft Office / Project / Visio...' -Level 'INFO' -Logger $Logger
    $inventory = @(Get-InstalledOfficeProducts -Logger $Logger -ShowTable)

    # Extracción defensiva de InstallationPath desde el inventario y respaldo directo desde el registro C2R
    $detectedInstallPaths = @()
    foreach ($item in $inventory) {
        if ($null -ne $item -and $item.PSObject.Properties['InstallationPath']) {
            $instVal = [string]$item.InstallationPath
            if (-not [string]::IsNullOrWhiteSpace($instVal)) {
                $cleanInstVal = $instVal.Trim().TrimEnd('\')
                if ($cleanInstVal -and ($detectedInstallPaths -notcontains $cleanInstVal)) {
                    $detectedInstallPaths += $cleanInstVal
                }
            }
        }
    }

    foreach ($c2rRegKey in @('HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration', 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Office\ClickToRun\Configuration')) {
        try {
            if (Test-Path -LiteralPath $c2rRegKey) {
                $regProps = Get-ItemProperty -LiteralPath $c2rRegKey -Name 'InstallationPath' -ErrorAction SilentlyContinue
                if ($null -ne $regProps -and $regProps.PSObject.Properties['InstallationPath']) {
                    $regInstVal = [string]$regProps.InstallationPath
                    if (-not [string]::IsNullOrWhiteSpace($regInstVal)) {
                        $cleanRegInstVal = $regInstVal.Trim().TrimEnd('\')
                        if ($cleanRegInstVal -and ($detectedInstallPaths -notcontains $cleanRegInstVal)) {
                            $detectedInstallPaths += $cleanRegInstVal
                        }
                    }
                }
            }
        } catch {
            # Ignorar errores puntuales de lectura del registro
        }
    }

    $effectiveMode = $Mode
    if ($effectiveMode -eq 'Interactivo') {
        Write-Host ''
        Write-Host '------------------------------------------------------------------' -ForegroundColor White
        Write-Host '              Desinstalación de Productos de Office               ' -ForegroundColor White
        Write-Host '------------------------------------------------------------------' -ForegroundColor White
        Write-Host '1. Desinstalación Selectiva por producto (conservar los demás)'
        Write-Host '2. Desinstalación Total + Limpieza profunda (elimina todo)'
        Write-Host '0. Volver al menú principal'
        Write-Host '------------------------------------------------------------------' -ForegroundColor White

        $subChoice = Read-Host 'Seleccione el modo de desinstalación'
        switch ($subChoice) {
            '1' { $effectiveMode = 'Selectivo' }
            '2' { $effectiveMode = 'Total' }
            '0' {
                Write-UninstLog -Message 'Retornando al menú principal sin realizar desinstalaciones.' -Level 'INFO' -Logger $Logger
                return
            }
            default {
                Write-UninstLog -Message "Opción de desinstalación no válida: '$subChoice'." -Level 'WARN' -Logger $Logger
                return
            }
        }
    }

    if ($effectiveMode -eq 'Selectivo') {
        if ($inventory.Count -eq 0) {
            Write-UninstLog -Message 'No existen productos detectados para ejecutar una desinstalación selectiva.' -Level 'WARN' -Logger $Logger
            return
        }

        $tokensToResolve = @()
        if ($ProductIds.Count -gt 0) {
            $tokensToResolve = @($ProductIds | ForEach-Object { $_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        } else {
            Write-Host ''
            $rawSelection = Read-Host 'Ingrese los índices (ej. 1,2) o ProductId exactos separados por comas (0 o vacío para cancelar)'
            if ([string]::IsNullOrWhiteSpace($rawSelection) -or $rawSelection.Trim() -eq '0') {
                Write-UninstLog -Message 'Desinstalación selectiva cancelada por el operador.' -Level 'WARN' -Logger $Logger
                return
            }
            $tokensToResolve = @($rawSelection -split ',' | ForEach-Object { $_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        }

        $selectedProducts = @()
        $selectedKeys = @()
        $invalidTokens = @()

        foreach ($tok in $tokensToResolve) {
            $matchedItem = $null
            $parsedIdx = 0
            if ([int]::TryParse($tok, [ref]$parsedIdx)) {
                $matchedItem = $inventory | Where-Object { $_.Index -eq $parsedIdx } | Select-Object -First 1
            } else {
                $matchedItem = $inventory | Where-Object { $_.ProductId -ieq $tok } | Select-Object -First 1
            }

            if ($matchedItem) {
                $uniqueKey = "$($matchedItem.InstallType)::$($matchedItem.ProductId)".ToLower()
                if ($selectedKeys -notcontains $uniqueKey) {
                    $selectedKeys += $uniqueKey
                    $selectedProducts += $matchedItem
                }
            } else {
                $invalidTokens += $tok
            }
        }

        if ($invalidTokens.Count -gt 0) {
            Write-UninstLog -Message "Selección inválida. Los siguientes valores no corresponden a ningún producto listado: $($invalidTokens -join ', ')" -Level 'ERROR' -Logger $Logger
            return
        }

        if ($selectedProducts.Count -eq 0) {
            Write-UninstLog -Message 'No se seleccionó ningún producto válido para desinstalar.' -Level 'WARN' -Logger $Logger
            return
        }

        $keptProducts = @($inventory | Where-Object {
            $k = "$($_.InstallType)::$($_.ProductId)".ToLower()
            $selectedKeys -notcontains $k
        })

        Write-Host ''
        Write-Host 'Productos seleccionados PARA DESINSTALAR:' -ForegroundColor Red
        foreach ($p in $selectedProducts) {
            Write-Host "  - [$($p.Index)] [$($p.InstallType)] [$($p.Category)] $($p.ProductId) - $($p.DisplayName)" -ForegroundColor Red
        }

        Write-Host ''
        Write-Host 'Productos que SE CONSERVARÁN:' -ForegroundColor Green
        if ($keptProducts.Count -eq 0) {
            Write-Host '  (Ninguno: todos los productos listados fueron seleccionados)' -ForegroundColor Yellow
        } else {
            foreach ($p in $keptProducts) {
                Write-Host "  - [$($p.Index)] [$($p.InstallType)] [$($p.Category)] $($p.ProductId) - $($p.DisplayName)" -ForegroundColor Green
            }
        }

        $confirmed = Confirm-UninstallDoubleCheck `
            -SummaryTitle 'CONFIRMACIÓN DE DESINSTALACIÓN SELECTIVA' `
            -FirstPrompt "¿Desea desinstalar únicamente los $($selectedProducts.Count) producto(s) seleccionado(s)? (S/N)" `
            -ConfirmKeyword 'DESINSTALAR' `
            -Logger $Logger

        if (-not $confirmed) {
            return
        }

        Stop-OfficeUserApplications -Logger $Logger -Confirm:$false -WhatIf:$WhatIfPreference
        $c2rExe = Get-OfficeClickToRunExePath -InstallationPaths $detectedInstallPaths

        $okCount = 0
        $failCount = 0
        foreach ($prod in $selectedProducts) {
            $ok = Invoke-SingleProductUninstall -Product $prod -ClickToRunExePath $c2rExe -Logger $Logger -Confirm:$false -WhatIf:$WhatIfPreference
            if ($ok) { $okCount++ } else { $failCount++ }
        }

        Write-UninstLog -Message "Desinstalación selectiva finalizada. Exitosos: $okCount | Con errores: $failCount." -Level 'INFO' -Logger $Logger
        if ($okCount -gt 0 -and -not $WhatIfPreference) {
            Write-UninstLog -Message 'Se recomienda reiniciar el equipo para completar cualquier limpieza pendiente en el sistema.' -Level 'INFO' -Logger $Logger
        }
    } elseif ($effectiveMode -eq 'Total') {
        Write-Host ''
        Write-Host 'ADVERTENCIA CRÍTICA: La Desinstalación Total + Limpieza profunda eliminará:' -ForegroundColor Red
        Write-Host "  - Todos los productos de Office / Project / Visio detectados ($($inventory.Count) producto(s))." -ForegroundColor Red
        Write-Host '  - El servicio ClickToRunSvc residual, carpetas huérfanas y tareas programadas de Office.' -ForegroundColor Red
        Write-Host '  - Toda la caché de identidad/WAM, credenciales y licencias instaladas (Clear-IdentityCache + Reset-OfficeLicenses Total).' -ForegroundColor Red

        $confirmed = Confirm-UninstallDoubleCheck `
            -SummaryTitle 'CONFIRMACIÓN DE DESINSTALACIÓN TOTAL + LIMPIEZA PROFUNDA' `
            -FirstPrompt '¿Está seguro de que desea eliminar TODOS los productos de Office y limpiar por completo el equipo? (S/N)' `
            -ConfirmKeyword 'ELIMINAR TODO' `
            -Logger $Logger

        if (-not $confirmed) {
            return
        }

        Stop-OfficeUserApplications -Logger $Logger -Confirm:$false -WhatIf:$WhatIfPreference

        if ($inventory.Count -gt 0) {
            $c2rExe = Get-OfficeClickToRunExePath -InstallationPaths $detectedInstallPaths
            foreach ($prod in $inventory) {
                [void](Invoke-SingleProductUninstall -Product $prod -ClickToRunExePath $c2rExe -Logger $Logger -Confirm:$false -WhatIf:$WhatIfPreference)
            }
        } else {
            Write-UninstLog -Message 'No se detectaron productos activos en registro; se procederá directamente con la limpieza profunda de residuos.' -Level 'INFO' -Logger $Logger
        }

        Invoke-OfficeDeepCleanup -DetectedInstallationPaths $detectedInstallPaths -BackupRoot $BackupRoot -Logger $Logger -Confirm:$false -WhatIf:$WhatIfPreference
        Write-UninstLog -Message 'Desinstalación Total y Limpieza profunda completadas. Reinicie el equipo antes de realizar una nueva instalación.' -Level 'INFO' -Logger $Logger
    }
}
