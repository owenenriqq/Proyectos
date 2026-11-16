# Estado del Proyecto - Suite-M365-Saneamiento

## Arquitectura Actual

Suite modular portátil en PowerShell 5.1 sin dependencias externas:

- `Iniciar-M365Sanitizer.bat`: Lanzador con verificación y elevación automática de privilegios UAC, ejecutando PowerShell con `-ExecutionPolicy Bypass`.
- `Invoke-M365Sanitizer.ps1`: Script principal con menú interactivo, validación de privilegios de administrador, cierre forzado de procesos de Office, soporte para `-WhatIf` y registro en `logs\sanitizer_YYYYMMDD_HHmmss.log`.
- `modules\Get-OfficeDiagnostics.ps1`: Módulo de diagnóstico de solo lectura (instalaciones Click-to-Run/MSI, detección de `sppc.dll` en rutas VFS, análisis de `ospp.vbs /dstatus`, cachés WAM/OneAuth/TokenBroker y almacenamiento vNext).
- `modules\Clear-IdentityCache.ps1`: Módulo de limpieza de caché de identidad (`OneAuth`, `IdentityCache`, `TokenBroker`, `Microsoft.AAD.BrokerPlugin`), credenciales en `cmdkey` y claves de identidad en `HKCU`.
- `modules\Reset-OfficeLicenses.ps1`: Módulo de saneamiento de licencias (respaldo y eliminación de `sppc.dll`, desinstalación selectiva o total vía `ospp.vbs /unpkey`, limpieza de vNext y registro de licencias).
- `logs\`: Directorio para registros de ejecución y respaldos de `sppc.dll` (`logs\backup_dll\`).

## Módulos y Scripts que Funcionan

- `Iniciar-M365Sanitizer.bat` e `Invoke-M365Sanitizer.ps1`: Carga de menú, validación de entorno y sistema de logging verificados en ejecuciones recientes.
- `modules\Get-OfficeDiagnostics.ps1`: Ejecutado correctamente en modo solo lectura; corregida la resolución dinámica de `InstallationPath` (Click-to-Run / WOW6432Node) para `ospp.vbs` y `sppc.dll`/`sppc64.dll`/`sppc32.dll`, además de añadir detección de redirecciones IFEO (`osppsvc.exe` y `sppsvc.exe`).
- `modules\Reset-OfficeLicenses.ps1`: Actualizada la resolución dinámica de `InstallationPath` para `ospp.vbs` y rutas VFS de `sppc.dll`/`sppc64.dll`/`sppc32.dll` con respaldo estándar en `Program Files` y `Program Files (x86)` (incluyendo rutas `\root\`). Validación sintáctica superada (0 errores).

## Pendiente de Depurar / Verificar

- Probar `Get-OfficeDiagnostics.ps1` en un equipo con Microsoft 365 / Office y Project/Visio instalados para validar el parseo bloque por bloque de `ospp.vbs /dstatus` y la detección de `sppc.dll`.
- Validar `Clear-IdentityCache.ps1` y `Reset-OfficeLicenses.ps1` en modo `-WhatIf` y posteriormente en ejecución controlada (modo Selectivo y modo Total).

## Siguiente Paso

- Ejecutar una prueba de diagnóstico (`Get-OfficeDiagnostics.ps1`) en un equipo destino con Office instalado y revisar el log generado.
