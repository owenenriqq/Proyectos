# Estado del Proyecto — EzSetup_Python

## 1. Resumen y Arquitectura

**EzSetup v2.5.0** es la migración completa de los scripts heredados de aprovisionamiento (`EzSetup_CMD_PS\`, solo lectura) a una aplicación de escritorio moderna para Windows 10/11 desarrollada en **Python 3.12 + PyQt6**, con configuración centralizada, ejecución asíncrona no bloqueante y exclusión total de software o activadores no oficiales.

### Stack Tecnológico
- **Lenguaje**: Python 3.12 (`C:\Users\oenrique\AppData\Local\Programs\Python\Python312\python.exe`, aislado en `.venv\`)
- **Interfaz Gráfica**: `PyQt6` (6.12.1) con diseño horizontal minimalista y tema oscuro QSS (`src/ui/styles.py`)
- **Red / Descargas**: `requests` (2.34.2) por streaming con archivo temporal `.tmp` y cancelación
- **Cifrado de Credenciales**: `cryptography` (50.0.2) — `AES-256-GCM` + `PBKDF2HMAC-SHA256` (600,000 iteraciones) en `src/crypto_creds.py` y fachada `src/crypto_store.py`
- **Integración Windows (COM / ACL / Registro / Impresoras)**: `pywin32` (312), `winreg`, `ctypes`, `cmdkey`, `regedit.exe`, `powercfg`, `pnputil.exe`, `PrintManagement`
- **Empaquetado**: `pyinstaller` (6.22.3)

### Árbol de Carpetas
```text
EzSetup_Python/
├── .venv/                      # Entorno virtual Python 3.12 (excluido en .gitignore)
├── assets/
│   ├── EzSetup.ico             # Ícono oficial de la aplicación
│   └── m365_sanitizer/         # Suite-M365-Saneamiento (.ps1 UTF-8 con BOM)
├── src/
│   ├── __init__.py
│   ├── config.py               # Carga/validación de config.json, validate_unc_host, KnownFolders y credentials.enc
│   ├── crypto_creds.py         # Cifrado/descifrado AES-256-GCM + diferencia InvalidTag vs errores E/S
│   ├── crypto_store.py         # Fachada pública del almacén cifrado (CredentialIntegrityError / CredentialIOError)
│   ├── workers.py              # QThreads: ServerCheckWorker, DownloadWorker, FileCopyWorker, IsoMountWorker, TaskWorker
│   ├── system_tasks.py         # Tareas administrativas Windows (impresoras IP/pnputil, pushd .bat, explorer, cmdkey, etc.)
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── m365_wrapper.py     # Wrapper no interactivo (shell=False) para Suite-M365-Saneamiento
│   │   ├── utilities_tasks.py  # Adaptadores TaskWorker para Utilidades (UTILITIES_TASK_REGISTRY)
│   │   ├── utilities/          # Módulos desacoplados (diagnostics, shell_repair, system_repair, system_tweaks)
│   │   ├── inventory/          # Relevamiento WMI/PowerShell y guardado en Inventario.txt (inventory_tasks.py)
│   │   └── network/            # Gestión/diagnóstico de redes desacoplado (net_tasks, network_dialogs, network_workers)
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py      # UI minimalista (5 categorías + buscador), ActionRow con wordWrap y cierre seguro
│       ├── network_view.py     # Vista integrada de Redes (Adaptadores, Renovación y Caché, Diagnóstico)
│       ├── dialogs.py          # Modales: Credential, PrinterInstall, M365Sanitizer, CreateLocalUser, HardwareDiagnostics, Inventory
│       └── styles.py           # Hoja de estilos QSS minimalista (tema monocromático oscuro unificado)
├── .gitignore                  # Excluye .venv/, build/, dist/, *.spec, *.enc, etc.
├── build.ps1                   # Script PyInstaller (--onefile, --uac-admin, --hidden-import wmi, m365_sanitizer)
├── config.json                 # Rutas UNC, URLs, rutas locales, servidores, impresoras, inventario y menús
├── ESTADO.md                   # Bitácora viva del proyecto
├── GEMINI.md                   # Reglas obligatorias de desarrollo y seguridad
├── main.py                     # Entrypoint con elevación UAC automática y AppUserModelID
├── manage_creds.py             # CLI para generar/actualizar credentials.enc sin guardar texto plano
└── requirements.txt            # PyQt6, requests, pywin32, pyinstaller, cryptography, wmi
```

### Comando de Ejecución y Compilación
- **Ejecución local en desarrollo**:
  `.venv\Scripts\python.exe main.py` (o `.venv\Scripts\python.exe main.py --no-elevate` para abrir sin UAC durante pruebas de interfaz).
- **Compilación de `EzSetup.exe`**:
  `powershell -ExecutionPolicy Bypass -File build.ps1`
  *(Genera `dist\EzSetup.exe` con `--onefile --windowed --uac-admin --icon assets\EzSetup.ico` y copia `dist\config.json` junto al ejecutable).*

---

## 2. Estado Actual

### Módulos Completados
- [x] Entorno virtual `.venv` creado con Python 3.12 e instalación de `PyQt6`, `requests`, `pywin32`, `pyinstaller` y `cryptography`.
- [x] `GEMINI.md`, `.gitignore` (excluyendo `*.enc`), `requirements.txt`, `build.ps1` y copia de `assets\EzSetup.ico`.
- [x] `config.json` centralizado (versión `2.5.0`) con catálogo extensible en **4 categorías**, subgrupos `IMPRESORAS` (HP-Todas.exe + 8 impresoras catálogo/driver) y `LICENCIAS Y OFFICE` (`Sanitizer O365` y referencias externas en red), `Gestor de Redes`, y accesos externos en red configurados para herramientas de diseño/utilidades (sin alojar binarios ni scripts de activación en el repositorio).
- [x] `src\config.py`: validación de esquema JSON, `get_printers_config()`, `get_allowed_unc_hosts()`, `get_install_checks()`, `KnownFolders` y resolución portable de `credentials.enc` (externo junto al `.exe` / padre de `dist\`, `sys._MEIPASS`, UNC).
- [x] `src\crypto_creds.py`, `src\crypto_store.py` y `manage_creds.py`: AES-256-GCM + PBKDF2HMAC-SHA256 (600,000 iteraciones) con validación previa `os.path.isfile` y separación explícita entre `CredentialIntegrityError` (`InvalidTag`) y `CredentialIOError` (`OSError`/`FileNotFoundError`).
- [x] `src\workers.py`: workers `QThread` reutilizables (`ServerCheckWorker`, `InstalledSoftwareCheckWorker`, `DownloadWorker`, `FileCopyWorker`, `ZipExtractWorker`, `IsoMountWorker`, `TaskWorker`) con validación UNC, `shell=False` y traducción amigable de `PermissionError`.
- [x] `src\system_tasks.py`: tareas administrativas con `shell=False` estricto (`install_network_printers` con `pnputil.exe` + PowerShell `PrintManagement`, `run_generic_bat` con `pushd`/`call`/`popd`, `run_generic_explorer`, `run_generic_open`, detección universal AWS VPN + lectura de versión, purga SMB/Kerberos, `renew_ip_and_dns`, `apply_autocad_firewall_block`, etc.).
- [x] `src\ui\`: paleta monocromática limpia (`#0F1012` / `#17191D` / `#F4F4F5`), `windowTitle` `"EzSetup v2.5.0"`, botón `"Copiar"` en barra de log, tooltip del badge `"Almacén Cifrado"` con la ruta resuelta de `credentials.enc`, `PrinterInstallDialog` (catálogo + IP manual), logs técnicos en `CredentialDialog`, ícono `⋮` centrado sobre `QPixmap(16, 16)` y buscador con debounce de 150ms.
- [x] `main.py` y `build.ps1`: elevación UAC y compilación PyInstaller optimizada con exclusiones de módulos PyQt6 no utilizados (`QtWebEngine*`, `QtMultimedia`, `Qt3DCore`, `QtQml`, `QtQuick`).
- [x] Verificación técnica aprobada (`v2.5.0`): `py_compile` sobre los 12 `.py`, escaneo de cero hardcoding y cero `shell=True`, validación de `crypto_store` (`CredentialIOError` / `CredentialIntegrityError`), prueba headless (`QT_QPA_PLATFORM=offscreen`) de `MainWindow` (`EzSetup v2.5.0`, botón `"Copiar"` log, filas nuevas y menú `⋮` 16x16), `PrinterInstallDialog` (8 impresoras + IP manual) y compilación exitosa con `build.ps1` (`dist\EzSetup.exe`, `dist\config.json` y `dist\credentials.enc`).
- [x] **Fase 1 de integración (`Suite-M365-Saneamiento`)**: scripts `.ps1` embebidos en `assets\m365_sanitizer\` (UTF-8 con BOM), wrapper no interactivo `src\modules\m365_wrapper.py` (`shell=False` + `CREATE_NO_WINDOW`), diálogo `M365SanitizerDialog` con `-WhatIf` por defecto y confirmación previa, conectado en `config.json` (`open_m365_sanitizer_dialog`) y `build.ps1`.
- [x] **Fase 2 de integración (`Utilidades`)**: módulos desacoplados migrados a `src\modules\utilities\` (`diagnostics.py`, `system_repair.py`, `system_tweaks.py`, `shell_repair.py`) sin referencias de Eidico ni dependencia de `src.config`, adaptador `src\modules\utilities_tasks.py` para `TaskWorker`, diálogos `CreateLocalUserDialog` y `HardwareDiagnosticsDialog` (`src\ui\dialogs.py`) con estética `DARK_THEME_QSS`, y reorganización de `Reparaciones y Diagnóstico` en `config.json`.
- [x] **Fase 3 de integración (`Inventario Eidico`)**: migrada la lógica WMI/PowerShell a `src\modules\inventory\inventory_tasks.py` (con `pythoncom.CoInitialize`/`CoUninitialize`, `shell=False` y sin UAC en importación), centralizado `validate_unc_host` en `src\config.py`, configurada la sección `inventory` y `eidico_inventory` en `config.json`, agregado `wmi>=1.5.1` (`requirements.txt` / `.venv` / `--hidden-import wmi` en `build.ps1`) y creado `InventoryDialog` (`src\ui\dialogs.py`) con estilos oscuros para `QDateEdit` y `QCalendarWidget`.
- [x] **Fase 4 de integración (`Gestor-Redes`)**: migrada la lógica desacoplada a `src\modules\network\` (`net_tasks.py`, `network_dialogs.py`, `network_workers.py`) sin referencias de Eidico ni `src.config`, unificados los estilos en `src\ui\styles.py` (`QPushButton[compact="true"]`, `RowMeta`, `DiagnosticOutput`, `QTabWidget`), creada la vista integrada `src\ui\network_view.py` (`NetworkManagerView`) con las 3 pestañas (`Adaptadores de Red`, `Renovación y Caché`, `Diagnóstico de Red`) como categoría lateral **Redes** en `src\ui\main_window.py`, y redirigido el botón `Abrir` de `Gestor de Redes` en `config.json` (`open_network_manager_view`).
- [x] **Fase 5 (Auditoría integral y compilación final)**: `py_compile` aprobado sobre los 27 `.py`, codificación verificada (31 archivos sin BOM + 6 `.ps1` con BOM), cero `shell=True`/UNC hardcodeadas, 9 módulos puros desacoplados verificados, smoke test headless (`QT_QPA_PLATFORM=offscreen --no-elevate`) aprobado sobre las 5 categorías y 10 diálogos sin recortes (`0 clipping`), y compilación exitosa con `build.ps1` (`dist\EzSetup.exe` de **40.64 MB** / `42,610,181` bytes + `dist\config.json`, con `m365_sanitizer` y `wmi` verificados en `Analysis-00.toc`).

### En Progreso
- Ninguno (integración del monorepo completada hasta Fase 5).

### Pendientes
- [ ] Completar en `config.json` las rutas UNC definitivas de `unc_paths.tecnica` actualmente vacías (`revit_2021_iso`, `dwg_trueview_2020_installer`, `sketchup_installer`).
- [ ] Ejecutar pruebas funcionales interactivas en red corporativa/VPN contra `172.30.0.13`, `172.31.11.146` y `fileserver2025` (descargas HTTP, montaje ISO/IMG, impresoras IP, `Suite-M365-Saneamiento`, `Utilidades`, `Inventario de Equipo` y `Gestor de Redes`).
- [ ] Validar la ejecución de `dist\EzSetup.exe` compilado en un equipo Windows 10/11 limpio desde pendrive (con `credentials.enc` externo o en UNC).

---

## 3. Historial de Cambios

- **2026-11-24 — Fase 5 Auditoría Integral Final y Compilación (`dist\EzSetup.exe`)**:
  - Corregido en `src\ui\main_window.py` (`ActionRow` y `_create_scroll_container`) el ajuste de texto (`setWordWrap(True)`) y deshabilitación de scroll horizontal (`ScrollBarAlwaysOff`), eliminando todo recorte visual en ventanas desde `1080x650`.
  - Ejecutada auditoría integral con `.venv\Scripts\python.exe`: `py_compile` sobre 27 `.py`, verificación de codificación (31 archivos UTF-8 sin BOM + 6 `.ps1` UTF-8 con BOM), auditoría de cero `shell=True`, cero rutas UNC hardcodeadas y 9 módulos puros desacoplados en `utilities/` y `network/`.
  - Aprobado smoke test headless (`QT_QPA_PLATFORM=offscreen --no-elevate`) verificando las 5 categorías, buscador (`Ctrl+F`), redirección de `Gestor de Redes` a la vista `Redes`, `0` clipping y los 10 diálogos modales.
  - Compilado `dist\EzSetup.exe` con `build.ps1` (**40.64 MB** / `42,610,181` bytes) junto a `dist\config.json` (sin `credentials.enc` en raíz), verificando el empaquetado de `assets\m365_sanitizer` y `wmi` en `build\EzSetup\Analysis-00.toc`.
- **2026-11-24 — Fase 4 Integración Monorepo (`Gestor-Redes`)**:
  - Migrados `net_tasks.py`, `network_dialogs.py` (`IPConfigDialog`, `DNSConfigDialog`, `AdapterDetailsDialog`, `DiagnosticResultDialog`) y `network_workers.py` (`AdapterRefreshWorker`, `ConnectivityCheckWorker`, `NetworkTaskWorker`, `DiagnosticWorker`) a `src\modules\network\` 100% desacoplados de Eidico, `src.config` y `credentials.enc`, manteniendo `shell=False`, `CREATE_NO_WINDOW`, `_ps_quote`, validación IPv4/máscara/host y tolerancia NSI.
  - Unificados en `src\ui\styles.py` los estilos faltantes (`RowMeta`, `RowSubtitle`, `statusRole="netBadge"`, `QPushButton[compact="true"]`, `DiagnosticOutput`, `QSpinBox`, `:disabled` y `QTabWidget`/`QTabBar`).
  - Creada la vista `NetworkManagerView` en `src\ui\network_view.py` con las 3 pestañas (`Adaptadores de Red`, `Renovación y Caché` con confirmaciones previas y `Diagnóstico de Red` con exportación `.txt`), integrada como categoría lateral **Redes** en `src\ui\main_window.py` con carga perezosa (`ensure_initialized`) y cierre seguro (`shutdown`).
  - Redirigido el botón `Abrir` de `Gestor de Redes` en `config.json` hacia `open_network_manager_view` (sin depender de `GestorRedes.exe` externo).
  - Verificación aprobada con `.venv\Scripts\python.exe`: `py_compile`, auditoría de cero acoplamiento/hardcoding/BOM y prueba headless (`QT_QPA_PLATFORM=offscreen`) de `MainWindow`, `NetworkManagerView` y los 4 diálogos de red.
- **2026-11-24 — Fase 3 Integración Monorepo (`Inventario Eidico`)**:
  - Agregada dependencia `wmi>=1.5.1` en `requirements.txt`, instalada en `.venv` (`WMI-1.5.1`) y añadido `--hidden-import wmi` en `build.ps1` (preservando UTF-8 con BOM).
  - Centralizados `UnauthorizedUNCHostError` y `validate_unc_host()` en `src\config.py`, extendiendo `get_allowed_unc_hosts()` con `security.extra_allowed_unc_hosts` (`fileserver2025`) y agregando `get_inventory_config()`.
  - Creado `src\modules\inventory\inventory_tasks.py` con `collect_hardware_info` (`pythoncom.CoInitialize`/`CoUninitialize`), `analyze_ram`, `get_disks_powershell` (`shell=False` + `CREATE_NO_WINDOW`), `format_inventory_record`, `save_inventory_record` y `export_inventory_record_local`, eliminando todo UAC en importación y rutas UNC hardcodeadas.
  - Agregados estilos monocromáticos oscuros para `QDateEdit`, `QPlainTextEdit` y `QCalendarWidget` en `src\ui\styles.py`, implementado `InventoryDialog` en `src\ui\dialogs.py` (con relevamiento asíncrono, copia al portapapeles, exportación local y guardado en red) y conectado `open_inventory_dialog` en `config.json` (`EIDICO`) y `src\ui\main_window.py`.
  - Verificación aprobada con `.venv\Scripts\python.exe`: `py_compile`, auditoría de cero hardcoding/BOM, validación de `validate_unc_host` y prueba headless (`QT_QPA_PLATFORM=offscreen`) de `MainWindow` e `InventoryDialog`.
- **2026-11-24 — Fase 2 Integración Monorepo (`Utilidades`)**:
  - Migrados `diagnostics.py`, `system_repair.py`, `system_tweaks.py` y `shell_repair.py` a `src\modules\utilities\` 100% desacoplados de `src.config`, `credentials.enc` y referencias corporativas de Eidico, con `shell=False` + `CREATE_NO_WINDOW` y decodificación robusta (UTF-16LE / UTF-8 / `cp850` / `cp1252`).
  - Creado `src\modules\utilities_tasks.py` (`UTILITIES_TASK_REGISTRY`) para ejecutar todas las acciones de forma asíncrona vía `TaskWorker`.
  - Agregados `CreateLocalUserDialog` (creación de usuario local + SID `S-1-5-32-544`) y `HardwareDiagnosticsDialog` (S.M.A.R.T. sin USB, particiones fijas, batería HTML y estabilidad/BSOD + exportación `.txt`) en `src\ui\dialogs.py` usando `DARK_THEME_QSS`.
  - Reorganizada la categoría `Reparaciones y Diagnóstico` en `config.json` (subgrupos `REPARACIÓN DE SISTEMA`, `DIAGNÓSTICO Y HARDWARE`, `ENERGÍA Y CUENTAS`, `SHELL Y MANTENIMIENTO`, `SISTEMA Y RED`, `LICENCIAS Y OFFICE`) sin duplicados y respetando máximo 3 botones visibles por fila; conectado en `src\ui\main_window.py`.
  - Verificación aprobada con `.venv\Scripts\python.exe`: `py_compile`, auditoría de cero acoplamiento/hardcoding/BOM y prueba headless (`QT_QPA_PLATFORM=offscreen`) de `MainWindow`, `CreateLocalUserDialog` y `HardwareDiagnosticsDialog`.
- **2026-11-24 — Fase 1 Integración Monorepo (`Suite-M365-Saneamiento`)**:
  - Copiados `Invoke-M365Sanitizer.ps1` y `modules\*.ps1` a `assets\m365_sanitizer\` preservando codificación UTF-8 con BOM.
  - Agregado `AppConfig.get_asset_dir()` en `src\config.py` compatible con `sys._MEIPASS` y ejecución local.
  - Creado `src\modules\m365_wrapper.py` con ejecución no interactiva (`powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass`, `shell=False`, `CREATE_NO_WINDOW`) para diagnóstico (solo lectura), limpieza de identidad (`-WhatIf`/real), restablecimiento de licencias (`Selectivo`/`Total` + `-WhatIf`/real) y desinstalación/limpieza profunda sin `Read-Host`.
  - Agregado `M365SanitizerDialog` en `src\ui\dialogs.py` (priorizando `-WhatIf` y exigiendo `QMessageBox.question` antes de acciones reales) y conectado en `src\ui\main_window.py` y `config.json` (`open_m365_sanitizer_dialog`).
  - Actualizado `build.ps1` con `--add-data "assets\m365_sanitizer;assets\m365_sanitizer"`.
- **2026-11-20 — v2.5.0 (Portabilidad en Pendrive, Instalador de Impresoras IP, Botón Copiar Log y Nuevas Opciones)**:
  - Actualizado `build.ps1` para cerrar instancias previas de `EzSetup.exe`, empaquetar condicionalmente `credentials.enc` mediante `--add-data "credentials.enc;."` (si existe en la raíz del proyecto) y copiarlo junto a `dist\config.json`.
  - Reforzado `src\config.py` (`resolve_credentials_enc_path`), `src\crypto_creds.py`, `src\crypto_store.py` y `CredentialDialog` (`src\ui\dialogs.py`): verificación previa `os.path.isfile`, diferenciación explícita entre `CredentialIntegrityError` (`InvalidTag`) y `CredentialIOError` (`OSError`/`FileNotFoundError`), registro de detalle técnico en log y tooltip en `"Almacén Cifrado"` con la ruta resuelta.
  - Centrado el ícono vectorial `⋮` sobre `QPixmap(16, 16)` con `setIconSize(QSize(16, 16))` (`src\ui\main_window.py`) manteniendo `padding: 0px; min-width/max-width: 32px; min-height/max-height: 30px;` en `src\ui\styles.py`, y agregado botón `"Copiar"` en la barra inferior de log (`QApplication.clipboard()`).
  - Agregado subgrupo `IMPRESORAS` (`Impresoras de Oficina`: `"HP-Todas.exe"` y `"Instalar por IP"`), sección `printers` en `config.json` (drivers `HP-UPD`, `Ricoh 501`, `Ricoh 2554` y 8 impresoras), diálogo modal `PrinterInstallDialog` (selección múltiple + IP manual) e instalador `install_network_printers` en `src\system_tasks.py` (`pnputil.exe` + PowerShell `PrintManagement` con `shell=False`).
  - Incorporados nuevos accesos y renombrados en `config.json` y `src\system_tasks.py`: `"Patch"` en Nitro PDF Pro (`explorer` a `\\172.30.0.13\areas\0-IT\NitroPDF`), `"Crack"` (`explorer /select` sobre `crack.zip` con fallback a la carpeta contenedora) visible y `"Instructivo"` en menú `⋮` para AutoCAD 2021, `"Crack"` en Hard Disk Sentinel Pro, `"Gestor de Redes"` (`[Renovar IP/DNS]` + `[Abrir]`) y subgrupo `LICENCIAS Y OFFICE` (`Sanitizer O365` y `Activación KMS` con `"KMS.txt"` vía `os.startfile` y `"Ejecutar"` mediante `cmd.exe /c pushd ... && call ... & popd`).
- **2026-11-18 — v2.4.0 (Paleta Monocromática, Ícono `⋮` Vectorial, Microcopy y `credentials.enc` en `dist\`)**:
  - Renovada completamente la hoja de estilos QSS (`src\ui\styles.py`) a una paleta monocromática neutra (`#0F1012`, `#17191D`, `#272A30`, `#24272E`, `#F4F4F5`, `#2E323B`, `#1F2228`), reservando verde/ámbar/rojo únicamente para badges de estado.
  - Reemplazado el botón de texto `⋯` por un botón `32x30` con ícono vectorial de 3 puntos verticales (`_create_more_dots_icon` vía `QPainter`) en `src\ui\main_window.py`.
  - Actualizado `config.json`: versión `2.4.0`, subgrupos `"OFIMÁTICA"` y `"DISEÑO"`, títulos `"Nitro PDF Pro"` (sin badge `"MSI Oficial"`), `".NET Framework 3.5"`, `"Hard Disk Sentinel Pro"` y ejecución directa de `"Renovar"` sin diálogo `"confirm"`.
  - Actualizado `resolve_credentials_enc_path` (`src\config.py`) para buscar también en `resolve_app_root().parent` cuando `EzSetup.exe` corre desde `dist\`.
  - Validado con smoke test completo en `.venv\Scripts\python.exe`.
- **2026-11-18 — v2.3.2 (Detección Universal AWS VPN, Header Limpio, Microcopy + `⋯`, Ícono de Ojo y Botón `Sin UAC`)**:
  - Implementada detección universal de `AWS VPN Client` (`src\system_tasks.py` y `config.json`) revisando rutas v3.x/v5.x/v6.x+, clave de servicio `AWSVPNClientService` y subclaves `Uninstall` (`HKLM`/`HKCU` + `WOW6432Node`), extrayendo la versión para mostrarla en el tooltip del badge `"Instalado"`.
  - Limpiado el header (`src\ui\main_window.py` y `config.json`): `windowTitle` `"EzSetup v2.3.2"`, título interno `"EzSetup"` sin versión, eliminación del botón `"Recargar Config"` (mantenido mediante atajo `F5`) y conversión de `"Sin UAC"` en botón cliqueable que relanza con `ShellExecuteW "runas"`.
  - Estandarizado el orden y microcopy de botones (`[Secundarios] -> [Configurar Todo] -> [Primario] -> [⋯]`): Fox (`[Descargar] [Configurar Todo] [Instalar] [⋯]` con `"Producción"`, `"EIDICO.vbs"`, `"EidicoPrueba.exe"`, `"Permisos Sol Sistemas"`, `"Acceso Directo"`), WinSCP (`[Configurar Todo] [Instalar] [⋯]`), FortiClient (`[Descargar] [Configurar Todo] [Instalar] [⋯]`), Accesos Directos (`"Crear"`), Nitro (`"Limpiar"`) y Red (`"Renovar"`).
  - Reemplazados los botones de texto `"Mostrar"`/`"Ocultar"` en `CredentialDialog` (`src\ui\dialogs.py`) por botones cuadrados `32x30` con ícono vectorial de ojo (`QPainter`) abierto/tachado.
  - Agregado `format_task_exception` (`src\system_tasks.py` y `src\workers.py`) para mostrar `"Permisos insuficientes. Ejecutá EzSetup como Administrador (clic en 'Sin UAC')."` ante `PermissionError` de Windows.
- **2026-11-18 — v2.3.1 (4 Categorías, Nomenclatura de Servidores y Fix `'bool' object is not callable`)**:
  - Consolidada la barra lateral en **4 categorías** (`EIDICO`, `Ofimática y Diseño`, `Técnica`, `Reparaciones y Diagnóstico`), moviendo `Credenciales de Servidores` (badge `"Almacén Cifrado"` + botón `"Configurar"`) y `Accesos Directos de Red` (`"Crear en Escritorio"`) al subgrupo `CONECTIVIDAD Y ACCESOS` dentro de `EIDICO`.
  - Actualizada la nomenclatura de servidores en `config.json` (`Fileserver Benavidez` y `Fileserver AWS`), título del modal `"Configurar Credenciales de Red"` y formato `{label} ({host})` en `CredentialDialog` (`src\ui\dialogs.py`) sin duplicar la IP.
  - Corregido el bug `'bool' object is not callable` blindando la conexión de señales `clicked`/`triggered` en `ActionRow` y validando `callable(...)` en `_run_task` / `_start_copy_eidico_prueba` (`src\ui\main_window.py`).
  - Mejorado `src\ui\styles.py` con indicador circular visible en `QRadioButton::indicator` y `background-color: transparent` para `QDialog QLabel`.
  - Validado con smoke test headless en `.venv\Scripts\python.exe`.
- **2026-11-18 — v2.3.0 (Hardening, Fix Buscador, Botones en Línea, Detección y Build Optimizado)**:
  - Corregido el parpadeo y ventana emergente fantasma del buscador (`Ctrl+F`) pre-creando las filas de búsqueda con `parent` explícito, usando `QTimer` debounce de `150ms` y filtrando por `setVisible(True/False)` dentro de `setUpdatesEnabled(False/True)`.
  - Ajustada regla visual de botones: hasta **3 botones visibles en línea** (Nitro PDF `[Limpiar Temp] [Instalar]` y Hard Disk Sentinel `[Copiar EXE] [Importar Key] [Instalar]`) y botón desplegable `"Más ▾"` únicamente en filas con 4 o más acciones.
  - Hardening en `src\system_tasks.py` y `src\workers.py`: `shell=False` explícito en todas las invocaciones `subprocess`, reemplazo de `cmd /c start` por `os.startfile`, validación de hosts UNC autorizados contra `servers` (`validate_unc_host`) y registro/limpieza automática de carpetas temporales en `closeEvent`.
  - Agregada detección en segundo plano de software instalado (`InstalledSoftwareCheckWorker` + `install_checks` en `config.json` con badges `"Instalado"`), extracción asíncrona de `Produccion.zip` (`ZipExtractWorker`) y exclusiones de módulos PyQt6 no utilizados en `build.ps1`.
  - Validado con smoke test headless en `.venv\Scripts\python.exe`.
- **2026-11-17 — v2.2.1 (Red, Purga SMB y Prefijo de Dominio)**:
  - Agregada tarea asíncrona `renew_ip_and_dns` (`src\system_tasks.py`) y botón `"Renovar IP y DNS"` en `Reparaciones y Diagnóstico` (`config.json`), con confirmación previa `QMessageBox.question`, secuencia `ipconfig /flushdns`, `/release`, `/renew`, `/registerdns`, verificación contra `internet_probe_host` (`1.1.1.1`) y servidores configurados, y refresco automático de los badges de red del header.
  - Actualizado `register_server_credential` (`src\system_tasks.py`) para purgar sesiones previas (`net use \\<host> /delete /y`, `net use \\<host>\* /delete /y`, `klist purge`, `cmdkey /delete:<host>`) antes de `cmdkey /add`.
  - Actualizado el ingreso manual de `CredentialDialog` (`src\ui\dialogs.py`) para anteponer automáticamente el dominio de `default_user_hint` cuando el usuario no incluye `\`.
- **2026-11-17 — v2.2.0 (5 Categorías, Catálogo Extensible, Buscador y Nuevas Herramientas)**:
  - Reorganizado `config.json` en exactamente **5 categorías** (`EIDICO`, `Ofimática y Diseño`, `Técnica`, `Reparaciones y Diagnóstico`, `Credenciales y Red`) con subgrupos y catálogo declarativo extensible (`exe`, `msi`, `iso`, `ps1`, `copy`, `reg`, `url`, `task`).
  - Incorporadas nuevas herramientas: `Autodesk Revit LT 2020.1`, `uPanel Anura 4.4.2`, `Hard Disk Sentinel Pro 5.50` (instalador, `key.reg` y reemplazo seguro de `HDSentinel.exe` con cierre previo del proceso) y `Accesos Directos de Red` (`create_network_shortcuts`).
  - Refactorizado `src\ui\main_window.py` y `src\ui\styles.py`: renderizado 100% dinámico desde `config.json`, límite de 3 botones visibles por fila con menú desplegable `▾` (`QMenu`) para acciones secundarias, ocultamiento automático de ítems con ruta vacía (`dwg_trueview_2020`, `sketchup`), buscador rápido en tiempo real (`Ctrl+F`) y botón `Recargar Config` en el header superior.
  - Validado con smoke test headless en `.venv\Scripts\python.exe`.
- **2026-11-17 — v2.1.0 (UI Minimalista + Credenciales Cifradas)**:
  - Rediseñados `src\ui\main_window.py` y `src\ui\styles.py`: eliminados textos descriptivos largos, subtítulos de sección/header y rutas visibles; convertidas las tarjetas en filas horizontales compactas (`ActionRow`) con botones directos y tooltips con rutas UNC/URLs; panel de "Registro de actividad" colapsado por defecto mostrando el último evento y botón `Mostrar Log`.
  - Agregada dependencia `cryptography` (`50.0.2`), exclusión `*.enc` en `.gitignore` y claves `credentials_enc_file` / `credentials_enc_unc` en `config.json`.
  - Implementado `src\crypto_creds.py` (AES-256-GCM + PBKDF2HMAC-SHA256 con 600,000 iteraciones, salt 16 B, nonce 12 B) y CLI `manage_creds.py` para administrar `credentials.enc`.
  - Actualizado `CredentialDialog` (`src\ui\dialogs.py`) para descifrar `credentials.enc` mediante Contraseña Maestra de IT o permitir ingreso manual individual.
  - Ejecutado smoke test completo con `.venv\Scripts\python.exe`.
- **2026-11-17 — v2.0.1 (Pre-compilación)**:
  - Actualizado `config.json`, `src\system_tasks.py`, `src\workers.py` y `src\ui\main_window.py` para usar el paquete unificado de FortiClient en red (`\\172.30.0.13\areas\0-IT\FortiClientVPN_7.4.3.6002_EIDICO.zip`), extrayendo `FortiClientVPN_7.4.3.6002_Offline.msi` (`msiexec /i`) y/o `VPN Config.reg` (`regedit /s`) en una carpeta temporal con limpieza automática al finalizar (compatible también con el ZIP descargado por HTTP).
  - Actualizada la ruta UNC de fondos a `\\172.30.0.13\areas\0-IT\Fondos Eidico 4K`.
  - Agregada la configuración `unc_paths.tecnica.autocad_2021_firewall` en `config.json`, implementada `apply_autocad_firewall_block` en `src\system_tasks.py` mediante script `.ps1` físico temporal con `Get-NetFirewallRule` / `New-NetFirewallRule` (evitando duplicados por `DisplayName`) e integrado el botón `"Aplicar bloqueo en Firewall (AutoCAD 2021)"` en `src\ui\main_window.py`.
  - Re-validado con smoke test headless en `.venv\Scripts\python.exe`.
- **2026-11-17 — v2.0.0**:
  - Creación inicial desde cero de `EzSetup_Python\` tomando como referencia funcional `EzSetup_CMD_PS\`.
  - Implementación completa de la arquitectura modular (`config.json`, `src\config.py`, `src\workers.py`, `src\system_tasks.py`, `src\ui\*`, `main.py`, `build.ps1`).
  - Integración de flujos de FortiClient desde red (`FortiClientVPNInstaller.exe` + `\\172.30.0.13\it\SOFTWARE\VPN Config.reg`) y descarga ZIP con importación automática del `.reg` contenido.
  - Eliminación de todas las credenciales en texto plano (reemplazadas por `CredentialDialog`) y exclusión explícita de `KMS.bat`, `Crack.zip`, `fw_block_autocad2021.reg` y `Patch.zip`.
  - Verificación de compilación Python y renderizado offscreen de PyQt6.

---

## 4. Próximos Pasos

Checklist para retomar el proyecto desde otra PC tras `git pull`:
1. Abrir terminal en `EzSetup_Python\`, crear el entorno virtual si aún no existe (`python -m venv .venv`) e instalar dependencias: `.venv\Scripts\pip.exe install -r requirements.txt`.
2. Editar `config.json` si cambiaron rutas del fileserver y completar `revit_2021_iso`, `dwg_trueview_2020_installer` y `sketchup_installer` en `unc_paths.tecnica`.
3. Lanzar la aplicación en modo prueba sin elevación o con administrador: `.venv\Scripts\python.exe main.py`.
4. Probar en vivo cada categoría contra la red corporativa (`172.30.0.13` y `172.31.11.146`).
5. Compilar el ejecutable final ejecutando `powershell -ExecutionPolicy Bypass -File build.ps1` y verificar `dist\EzSetup.exe` junto a `dist\config.json`.
