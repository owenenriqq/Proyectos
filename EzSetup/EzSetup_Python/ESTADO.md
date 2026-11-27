# Estado del Proyecto — EzSetup_Python

## 1. Resumen y Arquitectura

**EzSetup v3.0.0** es una aplicación de escritorio para Windows 10/11 (**Python 3.12 + PyQt6**) que unifica el aprovisionamiento corporativo, saneamiento M365, utilidades del sistema, inventario WMI y gestión/diagnóstico de redes, sin alojar activadores no oficiales ni credenciales en texto plano.

- **Stack**: `PyQt6` (tema oscuro QSS en `src/ui/styles.py`), `requests` (descargas por streaming `.tmp`), `cryptography` (`AES-256-GCM` + `PBKDF2HMAC-SHA256`), `pywin32`, `wmi` y `pyinstaller`.
- **Seguridad y portabilidad**: `shell=False` + `CREATE_NO_WINDOW` en subprocesos, validación UNC (`validate_unc_host`), `src/modules/utilities/` y `src/modules/network/` 100% libres de referencias a Eidico/`src.config`, y resolución prioritaria `resolve_config_path()` (externo junto al `.exe` > `_MEIPASS` > desarrollo).
- **Ejecución local**: `.venv\Scripts\python.exe main.py` (o `--no-elevate` para pruebas sin UAC).
- **Compilación**: `powershell -ExecutionPolicy Bypass -File build.ps1` (`dist\EzSetup.exe` `--onefile --windowed --uac-admin`).

---

## 2. Árbol de Carpetas Vigente

```text
EzSetup_Python/
├── .venv/                              # Entorno virtual Python 3.12 (gitignored)
├── assets/
│   ├── EzSetup.ico                     # Ícono oficial
│   ├── check_dark.png                  # Indicador QCheckBox
│   └── m365_sanitizer/
│       ├── Invoke-M365Sanitizer.ps1    # Referencia CLI original
│       └── modules/                    # Clear-IdentityCache, Get-OfficeDiagnostics, Reset-OfficeLicenses, Uninstall-OfficeProducts (.ps1)
├── src/
│   ├── __init__.py
│   ├── config.py                       # Carga/validación de config.json, vpn_endpoints, KnownFolders y credentials.enc
│   ├── crypto_creds.py                 # Cifrado/descifrado AES-256-GCM
│   ├── crypto_store.py                 # Fachada pública (CredentialIntegrityError / CredentialIOError)
│   ├── system_tasks.py                 # Tareas Windows, impresoras IP, diagnóstico VPN 4 capas y TASK_REGISTRY
│   ├── workers.py                      # QThreads reutilizables (red, descargas, copias, ISO, tareas)
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── m365_wrapper.py             # Wrapper no interactivo (shell=False) de Suite-M365-Saneamiento
│   │   ├── utilities_tasks.py          # Registro UTILITIES_TASK_REGISTRY
│   │   ├── inventory/                  # __init__.py, inventory_tasks.py (WMI/PowerShell -> Inventario.txt)
│   │   ├── network/                    # __init__.py, net_tasks.py, network_dialogs.py, network_workers.py
│   │   └── utilities/                  # __init__.py, diagnostics.py, shell_repair.py, system_repair.py, system_tweaks.py
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py              # Ventana principal, SidebarPanel desplegable, ActionRow y buscador Ctrl+F
│       ├── network_view.py             # Vista Redes (Adaptadores, Renovación y Caché, Diagnóstico)
│       ├── dialogs.py                  # Modales (Credential, PrinterInstall, M365Sanitizer, CreateLocalUser, HardwareDiagnostics, Inventory)
│       └── styles.py                   # Hoja QSS oscura unificada
├── .gitignore
├── build.ps1
├── config.json
├── ESTADO.md
├── GEMINI.md
├── main.py
├── manage_creds.py
└── requirements.txt
```

---

## 3. Estado Actual v3.0.0

### Resumen Consolidado (`v2.0.0` – `v2.5.0` y Fases 1–5)
- **`v2.0.0` – `v2.5.0`**: migración inicial desde `EzSetup_CMD_PS\`, catálogo declarativo en `config.json` (4 categorías + buscador `Ctrl+F`), almacén cifrado `credentials.enc` (`AES-256-GCM` + `CredentialDialog`), workers `QThread`, instalador de impresoras IP (`pnputil` + `PrintManagement`), detección de software instalado y exclusión de binarios/activadores no oficiales.
- **Fases 1–4 (Integración Monorepo)**: incorporadas en `src/modules/` las suites `Suite-M365-Saneamiento` (`m365_wrapper.py`), `Utilidades` (`utilities/` desacoplado + `CreateLocalUserDialog` / `HardwareDiagnosticsDialog`), `Inventario Eidico` (`inventory_tasks.py` + `InventoryDialog`) y `Gestor-Redes` (`network/` desacoplado + `NetworkManagerView`).
- **Fase 5 y Portabilidad**: auditoría de `shell=False` y codificación UTF-8, `resolve_config_path()`, streaming directo en M365, colapso real del panel de log en `QSplitter` (`40px`) y soporte de selección individual de servidores + prefijo fijo `eidico\` en `CredentialDialog`.

### Estado Vigente (`v3.0.0`)
- **UI/UX y Navegación (`src/ui/main_window.py`, `src/ui/styles.py`, `config.json`)**:
  - Barra lateral `SidebarPanel` con `NavButton` y submenú desplegable **`Redes ▸` / `Redes ▾`** (`SubNavButton`: `Adaptadores de Red`, `Renovación y Caché`, `Diagnóstico de Red`) con indicador lateral único (`submenuActive="true"`, fondo `#181B20` sin `border-left` en el padre cuando un subítem está activo) y `ContentToolbar` con `border-bottom: 1px solid #24272E`.
  - `ActionRow` con subtítulos descriptivos (`RowSubtitle` `#A8A8B3`, `12px`), `PrimaryButton` azul sobrio (`#2B5B9E`, borde `#366CB8`, texto `#F8FAFC`, hover `#356DB3`, pressed `#234B84`) de ancho fijo `140px` dentro de `ActionColumn` (`168px`), y botón `⋮` (`MoreButton` `22x22 px`, `border-radius: 5px`, ícono `12x12 px`) con `QMenu` oscuro alineado al borde derecho (o espaciador `22x22 px` en filas de 1 acción).
- **Vista Redes (`src/ui/network_view.py`)**:
  - `NetworkManagerView` montada directo en `MainWindow.stack` (sin `QTabBar` ni doble scroll) con `QStackedWidget` interno (`set_subpage`), barra `NetworkStatusBar` (`border-bottom: 1px solid #24272E`), precarga en segundo plano (`QTimer.singleShot(250, ...)`), `QSizePolicy` dinámico sin espacio vacío en `Adaptadores de Red`/`Renovación y Caché`, filtro **`Solo conectados`** activado por defecto, buscador contextual `Ctrl+F` y badges centrados (`AlignCenter` + `AlignVCenter`, `padding: 3px 10px`).
- **Diagnóstico VPN en 4 Capas (`config.json`, `src/config.py`, `src/system_tasks.py`)**:
  - `vpn_endpoints` validados (`forticlient_primary` `tcp:8443`, `forticlient_backup` `tcp:8443`, `aws_vpn` `udp:443`) y `diagnose_vpn_endpoint()` (Internet `1.1.1.1` → DNS → TCP `3s` o sonda UDP + alcance `tracert -d -h 15`), accesible desde `EIDICO` (`⋮`) y `Redes > Diagnóstico de Red`.
- **Suite-M365-Saneamiento (`src/modules/m365_wrapper.py`, `src/ui/dialogs.py`)**:
  - `M365SanitizerDialog` (`580px`, sin scroll horizontal) con 6 opciones: diagnóstico, cierre de procesos (`Stop-OfficeUserApplications`), limpieza de identidad, licencias (`Selectivo`/`Total`), desinstalación selectiva por producto (`Get-InstalledOfficeProducts`) y desinstalación total, con `-WhatIf` por defecto y confirmación previa.

---

## 4. Próximos Pasos

1. Completar en `config.json` las rutas UNC faltantes en `unc_paths.tecnica` (`revit_2021_iso`, `dwg_trueview_2020_installer`, `sketchup_installer`).
2. Compilar `dist\EzSetup.exe` manualmente con `powershell -ExecutionPolicy Bypass -File build.ps1`.
3. Validar en vivo contra `172.30.0.13`, `172.31.11.146` y `fileserver2025` (impresoras IP, M365 Sanitizer real, Inventario, Diagnóstico VPN y Gestor de Redes).
4. Probar `dist\EzSetup.exe` en un equipo Windows 10/11 limpio desde pendrive.
