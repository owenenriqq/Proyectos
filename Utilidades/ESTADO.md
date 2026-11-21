# Estado del Proyecto: Utilidades

## Archivos Base Importados (Heredados en `legacy/`)
Se han importado 6 archivos heredados en la carpeta `legacy/` que conforman la base funcional del proyecto:

1. **`legacy/Crear usuario local por consola.txt`**: Snippet PowerShell (`New-LocalUser`) para crear una cuenta local con contraseña en texto plano convertida a `SecureString`.
2. **`legacy/Desactivar inicio rapido de Windows.txt`**: Comandos CMD (`powercfg -h off` y verificación de `C:\hiberfil.sys`) para desactivar la hibernación e inicio rápido de Windows.
3. **`legacy/Iconos.txt`**: Script PowerShell para reconstruir la caché de iconos de Windows (reinicio de `explorer.exe`, limpieza de `IconCache.db` e `iconcache*`), re-registrar paquetes AppX (`Add-AppxPackage`), ampliar `Max Cached Icons` a `4096` en el registro y limpiar caché DNS (`ipconfig /flushdns`).
4. **`legacy/repararwindows.bat`**: Lanzador CMD con resolución dinámica de ruta (`%~dp0`), validación de existencia de `RepararWindows.ps1` y elevación UAC mediante `Start-Process ... -Verb RunAs`.
5. **`legacy/repararwindows.ps1`**: Script PowerShell de mantenimiento preventivo y diagnóstico (convertido a UTF-8 con BOM). Ejecuta `DISM /ScanHealth` y `/RestoreHealth`, `sfc /scannow`, telemetría S.M.A.R.T. (`Get-PhysicalDisk` / `Get-StorageReliabilityCounter`), reporte de batería (`powercfg /batteryreport`), métricas de RAM/Uptime (`Win32_OperatingSystem`), conteo de BSOD (`EventLog` ID 1001) y genera un reporte `.txt` en la ruta del script.
6. **`legacy/Start.bat`**: Script CMD auto-elevable (`net session` + `runas`) con log en `%TEMP%\reparacion_windows.log` que ejecuta `DISM /RestoreHealth`, `sfc /scannow`, inicia `MpsSvc` si está detenido para re-registrar paquetes AppX y finaliza con `DISM /StartComponentCleanup`.

## Hoja de Ruta (Migración a App Standalone)
- [x] **Fase 1 - Estructura base**: Inicializar entorno virtual Python 3.12 (`.venv`), `requirements.txt` (PyQt6), `.gitignore` y estructura modular (`src/core/`, `src/ui/`, `assets/`).
- [x] **Fase 2 - Motor de ejecución**: Implementar `src/workers.py` y ejecución silenciosa (`CREATE_NO_WINDOW`), captura de salida, verificación UAC nativa (`src/main.py`) y manejo de errores.
- [x] **Fase 3 - Módulos funcionales**:
  - [x] `src/core/system_tweaks.py` (Hibernación / Inicio Rápido y creación de usuarios locales).
  - [x] `src/core/system_repair.py` (`DISM` y `SFC` con streaming en vivo).
  - [x] `src/core/diagnostics.py` (S.M.A.R.T., batería, RAM/Uptime, BSOD y exportación de reporte).
  - [x] `src/core/shell_repair.py` (Caché de iconos, `Max Cached Icons`, AppX con `MpsSvc`, `ipconfig /flushdns`).
- [x] **Fase 4 - Interfaz PyQt6**: Diseñar UI oscura monocromática por pestañas (`src/ui/main_window.py`) con visor de logs (completadas pestañas **Reparación de Sistema**, **Diagnóstico y Hardware**, **Energía y Cuentas** y **Shell, Iconos y Red**).
  - Controles compactos en **Registro de Actividad** (`Copiar`, `Limpiar`, `Guardar .log`).
  - Diálogos de confirmación (`QMessageBox.question`) para acciones críticas (`Reconstruir Caché de Iconos`, `Re-registrar Paquetes AppX`, `Reparación Completa Automática`) y protección de cierre (`closeEvent`) con tarea activa.
  - Botón `Exportar Reporte (.txt)` habilitado tras diagnóstico, botón `Abrir reporte HTML` para `%TEMP%\battery.html`, botón ver/ocultar contraseña y checkbox `Agregar al grupo Administradores` (SID `S-1-5-32-544`).
- [x] **Fase 5 - Empaquetado y portabilidad**: Ícono monocromático (`assets/icon.svg` / `assets/icon.ico`), resolución de recursos (`sys._MEIPASS`), dimensiones `1080x680` y compilación standalone `dist\Utilidades.exe` vía PyInstaller con manifiesto UAC (`--uac-admin`).
