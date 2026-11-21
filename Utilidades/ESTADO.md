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
- [/] **Fase 3 - Módulos funcionales**:
  - [x] `src/core/system_tweaks.py` (Hibernación / Inicio Rápido y creación de usuarios locales).
  - [ ] `src/core/system_repair.py` (`DISM` y `SFC`).
  - [ ] `src/core/diagnostics.py` (S.M.A.R.T., batería, RAM/Uptime, BSOD y exportación de reporte).
  - [ ] `src/core/shell_repair.py` (Caché de iconos, AppX, `ipconfig /flushdns`).
- [/] **Fase 4 - Interfaz PyQt6**: Diseñar UI oscura monocromática por pestañas (`src/ui/main_window.py`) con visor de logs (completada pestaña **Energía y Cuentas**).
- [ ] **Fase 5 - Empaquetado y portabilidad**: Configurar compilación standalone (PyInstaller con manifiesto UAC) y evaluar portado puntual de utilidades hacia `EzSetup` manteniendo ambos proyectos desacoplados.
