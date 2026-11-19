# M365-Sanitizer

Suite modular en PowerShell diseñada para diagnosticar y reparar conflictos de activación y corrupción de licencias entre **Microsoft 365 Apps** (suscripción por cuenta) y licencias perpetuas o por volumen (como **Project 2021** o **Visio 2021**), además de corregir errores de inicio de sesión WAM (`Try again`) y el aviso *"Hemos detectado otra licencia"*.

## Requisitos

- **Sistema operativo:** Windows 10 o Windows 11.
- **Intérprete:** PowerShell 5.1 (nativo en Windows, sin dependencias de módulos externos).
- **Privilegios:** Ejecución obligatoria como **Administrador** (gestionada automáticamente por `Iniciar-M365Sanitizer.bat`).

## Despliegue Rápido en Múltiples Equipos

La suite es completamente portátil y no requiere instalación ni modificación manual de `ExecutionPolicy`:

1. Copie la carpeta completa del proyecto a una unidad USB o a una carpeta compartida en red (`\\servidor\carpeta`).
2. En el equipo destino, haga doble clic en **`Iniciar-M365Sanitizer.bat`**.
3. Acepte la solicitud de Control de Cuentas de Usuario (UAC) para elevar privilegios y continuar con el menú interactivo.

## Estructura del Proyecto

- `Invoke-M365Sanitizer.ps1`: Script principal con menú interactivo (v1.2), validación de privilegios de administrador, cierre forzado de procesos de Office (`winword`, `excel`, `outlook`, `powerpnt`, `msaccess`, `mspub`, `onenote`, `winproj`, `visio`, `teams`), selección entre saneamiento selectivo/total o desinstalación de productos (Opción 8), soporte para `-WhatIf` y registro detallado en `.\logs\sanitizer_YYYYMMDD_HHmmss.log`.
- `modules\Get-OfficeDiagnostics.ps1`: Módulo de diagnóstico de solo lectura que detecta:
  - Instalaciones Click-to-Run y MSI, junto con la arquitectura del sistema.
  - Archivos `sppc.dll` inyectados o modificados (indicador de parche Ohook) en `root\vfs\System` y `root\vfs\SystemX86`.
  - Estado de licencias mediante análisis bloque por bloque de `ospp.vbs /dstatus` presentado en tabla (`Category`, `LicenseName`, `ApplicationId`, `LicenseStatus`, `PartialKey`), diferenciando **Microsoft 365 / ProPlus** de **Project / Visio**.
  - Existencia de cachés de identidad en `OneAuth`, `IdentityCache`, `TokenBroker` y el paquete UWP `Microsoft.AAD.BrokerPlugin`, además del almacenamiento vNext.
- `modules\Clear-IdentityCache.ps1`: Módulo para resolver errores de autenticación (`Try again`) y limpiar:
  - Detención previa de procesos `Microsoft.AAD.BrokerPlugin`.
  - Cachés en `%LOCALAPPDATA%\Microsoft\OneAuth`, `%LOCALAPPDATA%\Microsoft\IdentityCache`, `%LOCALAPPDATA%\Microsoft\TokenBroker\Cache` y `%LOCALAPPDATA%\Packages\Microsoft.AAD.BrokerPlugin_cw5n1h2txyewy\AC\TokenBroker`.
  - Credenciales en el Administrador de Credenciales (`cmdkey`) asociadas a `MicrosoftOffice`, `ADAL` y `msteams`.
  - Valores residuales y subclaves de identidad en `HKCU:\Software\Microsoft\Office\16.0\Common\Identity`.
- `modules\Reset-OfficeLicenses.ps1`: Módulo que ejecuta el saneamiento de licencias en orden técnico:
  1. Verifica, respalda en `.\logs\backup_dll\` y elimina archivos `sppc.dll` presentes en `root\vfs\System` y `root\vfs\SystemX86` que bloqueen la autenticación en la nube.
  2. Procesa las claves obtenidas de `ospp.vbs /dstatus` en dos modos:
     - **Modo Selectivo (Recomendado para coexistencia):** Desinstala mediante `ospp.vbs /unpkey` las claves de Office (`O365`, `ProPlus`, `Mondo`, `Standard`) conservando intactas las claves cuyo `License Name` contenga `Project` o `Visio`.
     - **Modo Total:** Desinstala todas las claves de Office sin excepción.
  3. Limpia el almacenamiento de licencias vNext (`%LOCALAPPDATA%\Microsoft\Office\16.0\Licensing`).
  4. Elimina claves y valores residuales de activación en `HKCU:\Software\Microsoft\Office\16.0\Common\Licensing` y `HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration` sin comprometer la instalación Click-to-Run.
- `modules\Uninstall-OfficeProducts.ps1`: Módulo integrado como **Opción 8** del menú principal para inventariar y desinstalar productos de Office, Project y Visio con doble confirmación explícita:
  - **Inventario completo:** Detecta e identifica instalaciones Click-to-Run (`ProductReleaseIds` en `HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration` y `WOW6432Node`) y MSI (`Uninstall` y `WOW6432Node`), clasificándolas en **Suite Office**, **Project** y **Visio**.
  - **Modo Selectivo por producto:** Permite desinstalar únicamente los `ProductReleaseIds` o `ProductCodes` seleccionados (por ejemplo, quitar Microsoft 365/Office conservando Project o Visio, o viceversa) mediante `OfficeClickToRun.exe` (`productstoremove` con `DisplayLevel=False`) para Click-to-Run y `msiexec.exe /x /qn /norestart` para MSI.
  - **Modo Desinstalación Total + Limpieza profunda:** Desinstala todos los productos detectados, detiene y elimina el servicio `ClickToRunSvc` residual, borra carpetas huérfanas (`Program Files\Microsoft Office`, `Program Files (x86)\Microsoft Office`, `ProgramData\Microsoft\Office` y rutas C2R), elimina tareas programadas de Office y ejecuta automáticamente `Clear-IdentityCache` y `Reset-OfficeLicenses -Mode Total`.
- `logs\`: Directorio donde se almacenan los registros de ejecución y los respaldos de `sppc.dll` (`logs\backup_dll\`).

## Flujo de Uso Recomendado

1. Abrir una consola de PowerShell como **Administrador**.
2. Ejecutar el script principal (puede utilizar `-WhatIf` para simular acciones destructivas):
   ```powershell
   .\Invoke-M365Sanitizer.ps1
   ```
3. Seleccionar la opción **1** para obtener el diagnóstico inicial, verificar si existe `sppc.dll` y revisar la tabla de licencias detectadas.
4. Ejecutar la opción **6 (Saneamiento completo Selectivo)** si desea preservar Project/Visio 2021, o la opción **7 (Saneamiento completo Total)** si requiere eliminar todas las claves.
5. Si necesita retirar productos instalados (por ejemplo, desinstalar solo un producto conflictivo o realizar una erradicación completa previa a una reinstalación limpia), seleccione la opción **8 (Desinstalar productos de Office / Project / Visio)**.
6. **Al finalizar el saneamiento:**
   - **Reiniciar el equipo**.
   - Abrir primero **Microsoft Word** e iniciar sesión con la cuenta de Microsoft 365 hasta confirmar la activación de la suscripción.
   - Una vez activado Microsoft 365, abrir **Project 2021** para validar la coexistencia.

## Advertencias Operativas

- El cierre forzado de procesos finalizará las aplicaciones de Office abiertas sin guardar cambios pendientes.
- La limpieza de identidad y WAM cerrará la sesión de las cuentas de Microsoft 365 configuradas en el equipo.
- Cualquier archivo `sppc.dll` eliminado se respalda automáticamente en `.\logs\backup_dll\` antes de su borrado.
- La **Opción 8 (Desinstalación Selectiva o Total + Limpieza profunda)** requiere **doble confirmación explícita** (confirmación `S/N` y palabra clave exacta `DESINSTALAR` o `ELIMINAR TODO`); en modo Total desinstalará toda la paquetería detectada y eliminará configuraciones, servicio `ClickToRunSvc`, carpetas residuales, tareas programadas y licencias.
- Todas las operaciones destructivas solicitan confirmación previa y soportan el parámetro `-WhatIf`.
