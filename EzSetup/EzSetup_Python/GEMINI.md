# Reglas Obligatorias del Proyecto — EzSetup_Python

Este documento define las normas de arquitectura, seguridad y flujo de trabajo que deben respetarse en toda intervención sobre `EzSetup_Python\`.

## 1. Idioma y Comunicación
- Responder siempre en **español**, de forma directa y técnica.

## 2. Entorno de Desarrollo y Terminal
- Todo el desarrollo, pruebas y ejecución deben realizarse exclusivamente dentro de `EzSetup_Python\`.
- Ejecutar Python utilizando estrictamente el intérprete del entorno virtual: `.venv\Scripts\python.exe` (y `.venv\Scripts\pip.exe` / `.venv\Scripts\pyinstaller.exe` para dependencias y compilación).
- **PROHIBIDO ejecutar comandos PowerShell multilínea** en la terminal. Cuando se necesiten bloques complejos, escribir archivos físicos (`.ps1`, `.py`) o ejecutar comandos planos en una sola línea.
- No modificar bajo ningún concepto los scripts de referencia ubicados en `..\EzSetup_CMD_PS\`.

## 3. Seguridad, Configuración y Cero Hardcoding
- **PROHIBIDO hardcodear** rutas UNC (`\\172.30.0.13\...`, `\\172.31.11.146\...`), URLs de descarga, rutas locales de Windows o credenciales en el código fuente `.py`.
- Toda ruta, URL, parámetro de comportamiento y estructura de menús debe centralizarse en `config.json` y consumirse mediante `src/config.py`.
- Las credenciales para el Administrador de Credenciales de Windows (`cmdkey`) deben solicitarse siempre al usuario en tiempo de ejecución mediante diálogo seguro en la UI (`src/ui/dialogs.py`). Nunca almacenar contraseñas en código, `config.json`, archivos temporales ni logs.
- **PROHIBIDO incluir o migrar** cracks, keygens, patchers o scripts de activación no oficial (`KMS.bat`, `Crack.zip`, `Patch.zip`, `fw_block_autocad2021.reg`).

## 4. Codificación de Scripts Auxiliares
- Si se generan, modifican o leen archivos `.vbs` de soporte para Windows Script Host, utilizar estrictamente codificación **`Windows-1252` (`cp1252` / ANSI)**.

## 5. Bitácora y Control de Estado
- Antes de cerrar cualquier sesión o cambio relevante, actualizar `ESTADO.md` reflejando el avance real, los archivos modificados/creados, resultados de pruebas y los próximos pasos.
