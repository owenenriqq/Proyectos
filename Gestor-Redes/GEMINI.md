# Reglas Obligatorias del Proyecto — Gestor-Redes

Este documento define las normas de arquitectura, seguridad y flujo de trabajo que deben respetarse en toda intervención sobre `Gestor-Redes\`.

## 1. Idioma y Comunicación
- Responder siempre en **español**, de forma directa y técnica.

## 2. Entorno de Desarrollo y Terminal
- Todo el desarrollo, pruebas y ejecución deben realizarse exclusivamente dentro de `Gestor-Redes\`.
- Ejecutar Python utilizando estrictamente el intérprete del entorno virtual del proyecto cuando exista: `.venv\Scripts\python.exe` (y `.venv\Scripts\pip.exe` / `.venv\Scripts\pyinstaller.exe` para dependencias y compilación).
- **PROHIBIDO ejecutar comandos PowerShell multilínea** en la terminal. Cuando se necesiten bloques complejos, escribir archivos físicos (`.ps1`, `.py`) o ejecutar comandos planos en una sola línea.

## 3. Independencia y Seguridad
- `Gestor-Redes\` es un proyecto **100% standalone**: sin dependencias externas de configuración JSON, sin referencias corporativas y sin gestión de redes privadas externas.
- Todas las ejecuciones de comandos del sistema (`netsh`, `ipconfig`, `ping`, `tracert`, `nslookup`, `route`, `arp`, `powershell`) deben usar estrictamente **`shell=False`** y **`CREATE_NO_WINDOW`**.
- Validar siempre direcciones IPv4, máscaras de subred, puertos TCP y nombres de host antes de invocar cualquier utilidad del sistema (`net_tasks.py`).
- Escapar correctamente todo parámetro dinámico pasado a PowerShell (`_ps_quote`) para evitar inyección de comandos.
- Mantener la elevación UAC nativa (`--uac-admin` en compilación y `ShellExecuteW(..., "runas", ...)` en `main.py`), permitiendo `--no-elevate` solo para pruebas de interfaz.

## 4. Diseño Visual
- Conservar la paleta oscura monocromática (`#0F1012`, `#17191D`, `#272A30`, `#24272E`, `#F4F4F5`, `#1F2228`) definida en `styles.py`, reservando verde/ámbar/rojo exclusivamente para badges semánticos de estado y acciones destructivas.
- Toda operación de red o diagnóstico debe correr de forma asíncrona mediante `QThread` (`workers.py`) para no bloquear la interfaz gráfica.

## 5. Bitácora y Control de Estado
- Antes de cerrar cualquier sesión o cambio relevante, actualizar `ESTADO.md` reflejando el avance real, los archivos modificados/creados, resultados de pruebas y próximos pasos.
