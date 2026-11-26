# Reglas Globales — Monorepo

## Anti-alucinación y Alcance
- Leer `ESTADO.md` y los archivos objetivo en disco antes de proponer o aplicar cambios. Nunca asumir rutas, nombres de funciones ni dependencias no verificadas.
- Si falta un archivo o hay ambigüedad, detenerse y preguntar; no improvisar.
- Editar solo lo solicitado. Prohibido refactorizar o formatear código fuera de alcance.

## Estándares Técnicos
- **Idioma:** Respuestas, comentarios y docstrings en español técnico directo.
- **Codificación:** `.py` y `.md` = UTF-8 sin BOM | `.ps1` = UTF-8 con BOM | `.vbs` = Windows-1252 (ANSI).
- **Entorno:** Usar `.venv\Scripts\python.exe` si existe en el subproyecto. Prohibido comandos PowerShell multilínea en terminal.
- **Subprocesos Windows (Python):** Usar siempre `shell=False` y `CREATE_NO_WINDOW` (excepto si se requiere consola explícita). Validar códigos de retorno y entradas antes de invocar binarios del sistema.
- **Seguridad:** Prohibido hardcodear credenciales, contraseñas o rutas UNC en código (usar `config.json` o almacenes cifrados), salvo excepción explícita del subproyecto.

## Control de Ejecución y Estado
- Pedir autorización explícita antes de compilar (`build.ps1`, PyInstaller), correr pruebas o ejecutar comandos que alteren el sistema.
- Al finalizar cada tarea, actualizar el `ESTADO.md` del subproyecto de forma concisa (reemplazar estado obsoleto en vez de acumular bitácoras extensas).
