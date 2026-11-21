# Reglas del Subproyecto: Utilidades

Este subproyecto hereda las reglas globales de `../GEMINI.md` y define las siguientes directrices específicas:

## Propósito y Alcance
- **Proyecto 100% standalone**: Orientado a soporte técnico particular y mantenimiento preventivo/correctivo de Windows 10/11.
- **Sin dependencias corporativas**: Prohibido incluir referencias, rutas UNC, dominios o configuraciones corporativas de Eidico.

## Ejecución de Comandos y Privilegios
- **Sin consola visible**: Todo comando de sistema o subproceso (`DISM`, `SFC`, `powercfg`, `PowerShell`, etc.) debe ejecutarse con `CREATE_NO_WINDOW` (o equivalente silencioso) cuando sea invocado desde Python.
- **Validación y manejo de errores**: Validar privilegios, existencia de recursos y códigos de retorno (`returncode` / `$LASTEXITCODE`) antes y después de cada operación, capturando `stdout`/`stderr` para diagnóstico.
- **Elevación UAC nativa**: La aplicación debe solicitar y verificar elevación de privilegios de Administrador de forma nativa (manifiesto UAC o `ShellExecuteW` con `runas`).

## Interfaz Gráfica y Arquitectura
- **Stack**: Python 3.12 + PyQt6.
- **Estética**: Mantener una interfaz oscura monocromática consistente con el resto del repositorio.
- **Desacoplamiento**: Cualquier funcionalidad que eventualmente se porte hacia `EzSetup` debe mantenerse desacoplada; `Utilidades` no debe depender de otros subproyectos.
