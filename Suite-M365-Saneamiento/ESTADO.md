# Estado del Proyecto - Suite-M365-Saneamiento

## Arquitectura Actual

Suite modular portátil en PowerShell 5.1 sin dependencias externas:

- `Iniciar-M365Sanitizer.bat`: Lanzador con verificación y elevación automática de privilegios UAC, ejecutando PowerShell con `-ExecutionPolicy Bypass`.
- `Invoke-M365Sanitizer.ps1`: Script principal (v1.2) con menú interactivo (Opciones 1 a 8), validación de privilegios de administrador, cierre forzado de procesos de Office/Project/Visio, soporte para `-WhatIf` y registro en `logs\sanitizer_YYYYMMDD_HHmmss.log`.
- `modules\Get-OfficeDiagnostics.ps1`: Módulo de diagnóstico de solo lectura (instalaciones Click-to-Run/MSI, detección de `sppc.dll` en rutas VFS, redirecciones IFEO, análisis de `ospp.vbs /dstatus`, cachés WAM/OneAuth/TokenBroker y almacenamiento vNext).
- `modules\Clear-IdentityCache.ps1`: Módulo de limpieza de caché de identidad (`OneAuth`, `IdentityCache`, `TokenBroker`, `Microsoft.AAD.BrokerPlugin`), credenciales en `cmdkey` y claves de identidad en `HKCU`.
- `modules\Reset-OfficeLicenses.ps1`: Módulo de saneamiento de licencias (respaldo y eliminación de `sppc.dll`, desinstalación selectiva o total vía `ospp.vbs /unpkey`, limpieza de vNext y registro de licencias).
- `modules\Uninstall-OfficeProducts.ps1`: Módulo integrado en la Opción 8 para inventario C2R/MSI (Suite Office, Project, Visio), desinstalación selectiva silenciosa (`OfficeClickToRun.exe` / `msiexec.exe`) y desinstalación total + limpieza profunda (`ClickToRunSvc`, carpetas huérfanas, tareas programadas, identidad y licencias) con doble confirmación explícita.
- `logs\`: Directorio para registros de ejecución y respaldos de `sppc.dll` (`logs\backup_dll\`).

## Módulos y Scripts que Funcionan

- `Iniciar-M365Sanitizer.bat` e `Invoke-M365Sanitizer.ps1`: Carga de menú (incluyendo Opción 8), validación de entorno y sistema de logging verificados. Validación sintáctica superada (0 errores).
- `modules\Get-OfficeDiagnostics.ps1`: Ejecutado correctamente en modo solo lectura; corregida la resolución dinámica de `InstallationPath` (Click-to-Run / WOW6432Node) para `ospp.vbs` y `sppc.dll`/`sppc64.dll`/`sppc32.dll`, además de añadir detección de redirecciones IFEO (`osppsvc.exe` y `sppsvc.exe`). Validación sintáctica superada (0 errores).
- `modules\Clear-IdentityCache.ps1`: Validación sintáctica superada (0 errores).
- `modules\Reset-OfficeLicenses.ps1`: Actualizada la resolución dinámica de `InstallationPath` para `ospp.vbs` y rutas VFS de `sppc.dll`/`sppc64.dll`/`sppc32.dll` con respaldo estándar en `Program Files` y `Program Files (x86)` (incluyendo rutas `\root\`). Validación sintáctica superada (0 errores).
- `modules\Uninstall-OfficeProducts.ps1`: Creado e integrado como Opción 8 en `Invoke-M365Sanitizer.ps1`. Corregido el retorno plano de `Get-InstalledOfficeProducts` (evitando arreglos anidados y aislando la salida visual con `Out-Host`) y la extracción defensiva de `InstallationPath` con respaldo directo desde el registro C2R. Validación sintáctica (`Parser::ParseFile`) y codificación UTF-8 con BOM verificadas (0 errores).

## Pendiente de Depurar / Verificar

- Validado en equipo real: limpieza de caché WAM/OneAuth (`Clear-IdentityCache.ps1`), reseteo de licencias (`Reset-OfficeLicenses.ps1`) y coexistencia de Microsoft 365 con Project 2021.
- Pendiente validar `Uninstall-OfficeProducts.ps1` (Opción 8) en ejecución controlada (Selectivo y Total) en equipo destino.

## Siguiente Paso

- Ejecutar una prueba `-WhatIf` y ejecución controlada de la Opción 8 (`Uninstall-OfficeProducts.ps1`) cuando se requiera desinstalación de productos Office/Project/Visio.
