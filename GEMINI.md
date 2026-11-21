# Reglas Globales del Monorepo

Estas reglas aplican a todos los proyectos del repositorio (incluyendo `Inventario Eidico/` y cualquier nuevo subproyecto).

- **Idioma**: Responder siempre en español de forma directa y técnica. Redactar todos los comentarios y docstrings del código en español.
- **Codificación estricta**:
  - `.py` y `.md`: UTF-8 sin BOM.
  - `.ps1`: UTF-8 con BOM.
  - `.vbs`: Windows-1252 (ANSI).
- **Entorno y terminal**:
  - Usar siempre el entorno virtual local (`.venv\Scripts\python.exe`) cuando exista en el subproyecto.
  - Prohibido ejecutar comandos PowerShell multilínea en la terminal.
- **Seguridad**:
  - Prohibido hardcodear credenciales, contraseñas o rutas UNC en archivos de código fuente (`.py`, `.ps1`, `.vbs`, `.bat`).
  - Delegar la configuración a archivos externos (`config.json`) o almacenes cifrados.
- **Control de ejecución**:
  - Pedir autorización explícita antes de ejecutar compilaciones (`build.ps1`, `PyInstaller`), scripts de prueba o comandos que modifiquen el estado del sistema.
- **Mantenimiento**:
  - Actualizar el `ESTADO.md` del proyecto correspondiente al finalizar cada tarea.
