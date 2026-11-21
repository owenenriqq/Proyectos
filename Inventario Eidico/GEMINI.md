# Reglas del Proyecto - Inventario Eidico

Este proyecto hereda todas las reglas globales definidas en `../GEMINI.md`.

## Reglas Específicas

- **Stack tecnológico**: Python 3, PyQt6, `wmi`, `pythoncom`, `ctypes` y consultas de almacenamiento vía PowerShell (`Get-PhysicalDisk`).
- **Privilegios**: La aplicación solicita elevación UAC (`runas`) al iniciar para garantizar acceso completo a consultas WMI y de disco.
- **Configuración externa**: En futuras refactorizaciones, evitar hardcodear rutas UNC (como `CARPETA_RED`) en el código fuente y migrarlas a un archivo externo (`config.json`).
- **Versionado de scripts**: `Inventario3.py` es la versión de referencia actual. No eliminar `Inventario.py` ni `Inventario2.py` sin confirmación explícita.
