# Estado del Proyecto — EzSetup_Python

## 1. Resumen y Arquitectura

**EzSetup v3.0.0** es una aplicación de escritorio para Windows 10/11 (**Python 3.12 + PyQt6**) que unifica el aprovisionamiento corporativo, saneamiento M365, utilidades del sistema, inventario WMI y gestión/diagnóstico de redes, sin alojar activadores no oficiales ni credenciales en texto plano.

- **Stack**: `PyQt6` (tema oscuro QSS en `src/ui/styles.py`), `requests` (descargas por streaming `.tmp`), `cryptography` (`AES-256-GCM` + `PBKDF2HMAC-SHA256`), `pywin32`, `wmi` y `pyinstaller`.
- **Seguridad y portabilidad**: `shell=False` + `CREATE_NO_WINDOW` en subprocesos, validación UNC (`validate_unc_host`), `src/modules/utilities/` y `src/modules/network/` 100% libres de referencias a Eidico/`src.config`, y resolución prioritaria `resolve_config_path()` (externo junto al `.exe` > `_MEIPASS` > desarrollo).
- **Ejecución local**: `.venv\Scripts\python.exe main.py` (o `--no-elevate` para pruebas sin UAC).
- **Compilación**: `powershell -ExecutionPolicy Bypass -File build.ps1` (`dist\EzSetup\EzSetup.exe` `--onedir --windowed --uac-admin`, copiando `config.json` neutro y creando `dist\EzSetup\Recursos\`).

---

## 2. Árbol de Carpetas Vigente

```text
EzSetup_Python/
├── .venv/                              # Entorno virtual Python 3.12 (gitignored)
├── Recursos/                           # Carpeta portable creada en ejecución (gitignored)
│   ├── Office/                         # ProPlus2021Retail.img, ProjectPro2021Retail.img, VisioPro2021Retail.img
│   ├── Nitro/                          # Instalador/paquete de Nitro PDF Pro
│   ├── Tecnica/                        # Instaladores de AutoCAD 2021 y Revit LT 2020.1
│   └── KMS/                            # KMS.txt y script .bat de activación
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

### Estado Vigente (`v3.0.0` — Modo Portable / Neutro)
- **Portabilidad y Perfiles (`src/config.py`, `main.py`, `src/system_tasks.py`, `config.json`, `config.eidico.json`)**:
  - **Perfil Neutro por defecto (`config.json`)**: 100% libre de referencias corporativas (`corporate_servers: []`, `vpn_profiles: []`), con rutas relativas a `Recursos\Office\`, `Recursos\Nitro\`, `Recursos\Tecnica\` y `Recursos\KMS\` creadas automáticamente por `ensure_resources_dirs()`.
  - **Perfil Corporativo (`--profile eidico` o `--config <ruta>`)**: carga `config.eidico.json` (gitignored), habilitando la pestaña **`EIDICO`** al inicio, píldoras de servidores (`172.30.0.13` y `172.31.11.146`) en el header y fila **`Verificar VPN`** en `Diagnóstico de Red`.
- **UI/UX y Navegación (`src/ui/main_window.py`, `src/ui/styles.py`, `config.json`)**:
  - Barra lateral compacta (`245px`) con 3 categorías raíz: **`Instaladores`** (inicio por defecto), **`Reparaciones y Diagnóstico`** y **`Redes`** (desplegado por defecto con conectores en `L` dibujados con `QPainter` y margen izquierdo `34px` sin solapamiento en hover), más sección inferior **`ACCESOS RÁPIDOS`** de 7 botones (`Reparación Completa Automática`, `Reparar Explorer y Barra de Tareas`, `Caché de Iconos y Registro`, `Sanitizer O365`, `Activación KMS`, `Reparación Rápida (Sin reinicio)`, `Renovar IP y DNS (Completo)`). Categorías ausentes o con `"enabled": false` (como `EIDICO`) no se renderizan.
  - Header sin píldoras IP cuando `corporate_servers` está vacío (conserva indicador `Administrador`/`Sin UAC` y botón `Verificar Red`, que en modo neutro ejecuta verificación de salida a Internet y DNS actualizando la píldora de `Redes` y la barra inferior).
  - **Instaladores**: subgrupo **`OFIMÁTICA`** (Office 2021 ProPlus, Project Pro 2021 y Visio Pro 2021 desde `Recursos\Office\` con `Descargar IMG oficial` en `⋮` hacia `Recursos\Office\`, más Nitro PDF Pro desde `Recursos\Nitro\`) y subgrupo **`CAD Y BIM`** (AutoCAD 2021 y Revit LT 2020.1 desde `Recursos\Tecnica\`).
  - **Reparaciones y Diagnóstico**: incluye `Reparar Explorer y Barra de Tareas` (`repair_explorer_taskbar` en `src/system_tasks.py`: reinicio de procesos Shell/StartMenu/SearchHost, limpieza de `TempState`/`IrisService` y re-registro AppX); sin `.NET Framework 3.5`, `Gestor de Redes` ni `Hard Disk Sentinel Pro`; `Activación KMS` apuntando a `Recursos\KMS\`.
- **Vista Redes (`src/ui/network_view.py`)**:
  - `NetworkManagerView` montada directo en `MainWindow.stack` con 2 subvistas: **`Adaptadores y Caché`** (interfaces detectadas con `Solo conectados` activo por defecto + `ncpa.cpl` + secuencias automáticas, renovación IP/DNS y reparación TCP/IP) y **`Diagnóstico de Red`** (pruebas activas + tablas del sistema + salida amplia; barra `Verificar VPN` oculta cuando `vpn_profiles` está vacío). `src/modules/network/` libre de referencias corporativas.
- **Suite-M365-Saneamiento (`src/modules/m365_wrapper.py`, `src/ui/dialogs.py`)**:
  - `M365SanitizerDialog` (`580px`, sin scroll horizontal) con 6 opciones, `-WhatIf` por defecto y confirmación previa.

---

## 4. Próximos Pasos

1. Compilar `dist\EzSetup.exe` manualmente cuando se requiera con `powershell -ExecutionPolicy Bypass -File build.ps1`.
2. Probar `dist\EzSetup.exe` en un equipo Windows 10/11 limpio desde pendrive verificando la descarga de los `.img` de Office en `Recursos\Office\`.
