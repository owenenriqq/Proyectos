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
- [ ] **Fase 1 - Estructura base**: Inicializar entorno virtual Python 3.12 (`.venv`), `pyproject.toml`/`requirements.txt` (PyQt6) y estructura modular (`core/`, `ui/`, `utils/`).
- [ ] **Fase 2 - Motor de ejecución**: Implementar runner de comandos con `CREATE_NO_WINDOW`, captura de salida en tiempo real, verificación UAC nativa y manejo de errores.
- [ ] **Fase 3 - Módulos funcionales**: Migrar la lógica de los 6 scripts a módulos Python desacoplados (Integridad de Sistema, Telemetría y Hardware, Shell e Iconos, Energía y Usuarios).
- [ ] **Fase 4 - Interfaz PyQt6**: Diseñar UI oscura monocromática por pestañas con barra de progreso, visor de logs y exportación de reportes.
- [ ] **Fase 5 - Empaquetado y portabilidad**: Configurar compilación standalone (PyInstaller con manifiesto UAC) y evaluar portado puntual de utilidades hacia `EzSetup` manteniendo ambos proyectos desacoplados.
