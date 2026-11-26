# Reglas — Gestor-Redes
- **100% Standalone:** Ejecutable independiente para soporte particular, sin JSON externo, sin referencias a Eidico ni gestión de VPN/redes corporativas. Su lógica base se sincroniza con `..\EzSetup\EzSetup_Python\src\modules\network\`.
- Validar IPv4, máscaras, puertos TCP y hostnames en `net_tasks.py` antes de invocar utilidades de red. Escapar todo parámetro dinámico de PowerShell con `_ps_quote`.
- Mantener elevación UAC nativa (`--uac-admin` y `ShellExecuteW(..., "runas", ...)` en `main.py`), conservando `--no-elevate` solo para pruebas de UI.
- Ejecutar toda operación de red/diagnóstico de forma asíncrona con `QThread` (`workers.py`).
- **UI:** Conservar paleta oscura monocromática en `styles.py` (`#0F1012`, `#17191D`, `#272A30`, `#24272E`, `#F4F4F5`, `#1F2228`); verde/ámbar/rojo solo para badges de estado y acciones destructivas.
