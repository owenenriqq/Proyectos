# Reglas del Proyecto — Gestor-Redes

- `Gestor-Redes\` es un proyecto **100% standalone**: sigue compilándose como ejecutable independiente para soporte particular, sin dependencias externas de configuración JSON, sin referencias corporativas y sin gestión de redes privadas externas. Su lógica base se comparte y sincroniza con `..\EzSetup\EzSetup_Python\src\modules\network\`.
- Todas las ejecuciones de comandos del sistema (`netsh`, `ipconfig`, `ping`, `tracert`, `nslookup`, `route`, `arp`, `powershell`) deben usar estrictamente **`shell=False`** y **`CREATE_NO_WINDOW`**.
- Validar siempre direcciones IPv4, máscaras de subred, puertos TCP y nombres de host antes de invocar cualquier utilidad del sistema (`net_tasks.py`).
- Escapar correctamente todo parámetro dinámico pasado a PowerShell (`_ps_quote`) para evitar inyección de comandos.
- Mantener la elevación UAC nativa (`--uac-admin` en compilación y `ShellExecuteW(..., "runas", ...)` en `main.py`), permitiendo `--no-elevate` solo para pruebas de interfaz.
- Conservar la paleta oscura monocromática (`#0F1012`, `#17191D`, `#272A30`, `#24272E`, `#F4F4F5`, `#1F2228`) definida en `styles.py`, reservando verde/ámbar/rojo exclusivamente para badges semánticos de estado y acciones destructivas.
- Toda operación de red o diagnóstico debe correr de forma asíncrona mediante `QThread` (`workers.py`) para no bloquear la interfaz gráfica.
