# Estado del Proyecto — EzSetup_Python

## 1. Resumen y Arquitectura

**EzSetup v3.0.0** es la migración completa de los scripts heredados de aprovisionamiento (`EzSetup_CMD_PS\`, solo lectura) a una aplicación de escritorio moderna para Windows 10/11 desarrollada en **Python 3.12 + PyQt6**, con configuración centralizada, ejecución asíncrona no bloqueante, portabilidad total (`config.json` + `credentials.enc` embebidos) y exclusión total de software o activadores no oficiales.

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
- [x] `config.json` centralizado (versión `3.0.0`) con catálogo extensible en **4 categorías** + vista lateral **Redes**, subgrupos `IMPRESORAS` (HP-Todas.exe + 8 impresoras catálogo/driver) y `LICENCIAS Y OFFICE` (`Sanitizer O365` y referencias externas en red), `Gestor de Redes` (`"Ir a Redes"`), DISM (`RestoreHealth` primario) y accesos externos en red configurados para herramientas de diseño/utilidades (sin alojar binarios ni scripts de activación en el repositorio).
- [x] `src\config.py`: validación de esquema JSON, `get_printers_config()`, `get_allowed_unc_hosts()`, `get_install_checks()`, `KnownFolders`, resolución prioritaria `resolve_config_path()` (externo junto a `.exe` > `sys._MEIPASS` > desarrollo) y resolución portable de `credentials.enc` (externo junto al `.exe` / padre de `dist\`, `sys._MEIPASS`, UNC).
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
- [x] **v3.0.0 (Correcciones visuales/funcionales, M365 diagnostics y portabilidad total)**: colapso real del panel de log en `QSplitter` sin espacio vacío (`_apply_log_panel_state`, `40px` colapsado), streaming directo a `[Console]::Out` en `src\modules\m365_wrapper.py` (corrigiendo `run_office_diagnostics()` + `*>&1 | Out-String -Stream`), estilos `QCheckBox::indicator` (`assets\check_dark.png`), `QRadioButton::indicator:checked` con anillo contrastado y `QComboBox:disabled` legible en `src\ui\styles.py`, margen inferior `16px` en scroll, `config.json` v3.0.0 (`RestoreHealth` primario, `"Ir a Redes"`), `resolve_config_path()` en `src\config.py` y compilación portable `dist\EzSetup.exe` (**40.64 MB** / `42,613,126` bytes) con `config.json`, `credentials.enc`, `assets\m365_sanitizer`, `check_dark.png` y `wmi` embebidos.

### En Progreso
- Ninguno (integración del monorepo completada hasta Fase 5).

### Pendientes
- [ ] Completar en `config.json` las rutas UNC definitivas de `unc_paths.tecnica` actualmente vacías (`revit_2021_iso`, `dwg_trueview_2020_installer`, `sketchup_installer`).
- [ ] Ejecutar pruebas funcionales interactivas en red corporativa/VPN contra `172.30.0.13`, `172.31.11.146` y `fileserver2025` (descargas HTTP, montaje ISO/IMG, impresoras IP, `Suite-M365-Saneamiento`, `Utilidades`, `Inventario de Equipo` y `Gestor de Redes`).
- [ ] Validar la ejecución de `dist\EzSetup.exe` compilado en un equipo Windows 10/11 limpio desde pendrive (con `credentials.enc` externo o en UNC).

---

## 3. Historial de Cambios

- **2026-11-25 — v3.0.0 (Mejoras en `CredentialDialog` y actualización de `GEMINI.md` del monorepo)**:
  - **Selección individual de servidores en `CredentialDialog` (`src\ui\dialogs.py`)**: agregados checkboxes dinámicos generados desde `servers` en `config.json` (tildados por defecto), visibles tanto en modo **Archivo cifrado (`credentials.enc`)** como en **Ingreso manual**, con validación previa de al menos un servidor seleccionado; tanto `cmdkey` como `create_shortcut` en `register_server_credential` (`src\system_tasks.py`) se aplican únicamente a los servidores tildados.
  - **Prefijo fijo `eidico\` en modo manual (`src\ui\dialogs.py`)**: reemplazado el campo de usuario libre por `QLabel("eidico\\")` + `QLineEdit` (placeholder `"ej. oenrique o fexterno"`) y función `normalize_eidico_username()` para anteponer o normalizar `eidico\<usuario>` (case-insensitive, evitando `eidico\eidico\`).
  - **Gobernanza del monorepo (`GEMINI.md`)**: actualizados `EzSetup\EzSetup_Python\GEMINI.md` (arquitectura unificada v3.0.0 y desacoplamiento de `utilities/` y `network/`), `Gestor-Redes\GEMINI.md` y `Utilidades\GEMINI.md` (compilación standalone + lógica compartida), e `Inventario Eidico\GEMINI.md` y `Suite-M365-Saneamiento\GEMINI.md` (referencia histórica).
  - **Validación sin compilación**: aprobados `py_compile` (27 `.py`), codificación UTF-8 sin BOM y smoke test headless (`QT_QPA_PLATFORM=offscreen --no-elevate`) de `CredentialDialog` (modos cifrado/manual, selección parcial, `normalize_eidico_username`) y `register_server_credential` (mocked `subprocess.run`).
- **2026-11-25 — v3.0.0 (Correcciones visuales/funcionales, Diagnóstico M365 y Portabilidad Total)**:
  - **Colapso real del panel de log (`src\ui\main_window.py`)**: implementado `_apply_log_panel_state()` con `setFixedHeight(40)`, `QSizePolicy.Policy.Fixed`, deshabilitación de handle del `QSplitter` (`setHandleWidth(0)`) y ajuste explícito de `splitter.setSizes()`, permitiendo que al ocultar el log el área de contenido superior recupere el 100% del espacio vertical sin dejar espacio negro vacío debajo.
  - **Streaming de Diagnóstico M365 (`src\modules\m365_wrapper.py`)**: corregido `_build_logger_preamble()` para escribir directamente a `[Console]::Out.WriteLine` con `Flush()` (evitando que `$diag = Get-OfficeDiagnostics -Logger $ezLogger` capture la salida de `Write-Output`) y añadido `*>&1 | Out-String -Stream` en `Clear-IdentityCache`, `Reset-OfficeLicenses`, `Stop-OfficeUserApplications` e `Invoke-OfficeDeepCleanup`.
  - **Optimizaciones visuales (`src\ui\styles.py`, `src\ui\main_window.py`, `src\ui\network_view.py`, `assets\check_dark.png`)**: generado `assets\check_dark.png` (16x16), estilizado `QCheckBox::indicator` (16x16, borde `#52525B`, fondo `#17191D`, `border-radius: 4px`), `QRadioButton::indicator:checked` con anillo contrastado (`qradialgradient`), mejorado contraste de `QComboBox:disabled` (`#8E8E98`), y añadido margen inferior de `16px` en `_create_scroll_container()` y `_create_scroll_tab()`.
  - **Catálogo y versión (`config.json`, `main.py`)**: subida la versión a `EzSetup v3.0.0` (`app.version`, `app.title`, `app_user_model_id: Eidico.EzSetup.3.0`), establecido `RestoreHealth` como `PrimaryButton` en `Integridad de Imagen (DISM)` y renombrado `"Abrir"` a `"Ir a Redes"` en `Gestor de Redes`.
  - **Portabilidad total (`src\config.py`, `build.ps1`)**: añadido `AppConfig.resolve_config_path()` con prioridad `1) externo junto a EzSetup.exe > 2) sys._MEIPASS embebido > 3) desarrollo` (y recarga `F5` respetando dicha prioridad); compilado `dist\EzSetup.exe` (**40.64 MB** / `42,613,126` bytes) verificando en `build\EzSetup\Analysis-00.toc` la inclusión de `config.json`, `credentials.enc`, `assets\m365_sanitizer`, `check_dark.png` y `wmi`.
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
- **2026-11-17 a 2026-11-20 — v2.2.0 a v2.5.0 (Resumen consolidado)**:
  - **v2.2.0 – v2.3.1**: Reorganización en 4 categorías (`EIDICO`, `Ofimática y Diseño`, `Técnica`, `Reparaciones y Diagnóstico`), catálogo declarativo extensible en `config.json`, buscador en tiempo real (`Ctrl+F`), regla de hasta 3 botones visibles por fila con menú desplegable, detección de software instalado en segundo plano (incluyendo `AWS VPN Client`), purga SMB/Kerberos + `renew_ip_and_dns` y hardening con `shell=False` y validación UNC (`validate_unc_host`).
  - **v2.3.2**: Limpieza de header (`F5` recarga, botón cliqueable `Sin UAC`), estandarización de microcopy en filas y botones vectoriales de ojo en `CredentialDialog`, además de traducción amigable de `PermissionError` (`format_task_exception`).
  - **v2.4.0**: Adopción de la paleta monocromática oscura (`#0F1012` / `#17191D` / `#F4F4F5`), ícono vectorial `⋮` y búsqueda de `credentials.enc` en el directorio padre de `dist\`.
  - **v2.5.0**: Portabilidad en pendrive con empaquetado condicional de `credentials.enc` y separación `CredentialIntegrityError` / `CredentialIOError`, instalador de impresoras IP (`PrinterInstallDialog` + `pnputil.exe` / `PrintManagement`), botón `"Copiar"` en el panel de log y nuevos accesos en red (`IMPRESORAS`, `LICENCIAS Y OFFICE`, `Gestor de Redes`).
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

Checklist para finalizar y validar **EzSetup v3.0.0** (nota: `config.json` y `credentials.enc` ya van embebidos dentro de `dist\EzSetup.exe`, aunque pueden sobrescribirse externamente colocándolos junto al ejecutable):
1. Completar en `config.json` las rutas UNC faltantes en `unc_paths.tecnica` (`revit_2021_iso`, `dwg_trueview_2020_installer`, `sketchup_installer`).
2. Recompilar `dist\EzSetup.exe` con `powershell -ExecutionPolicy Bypass -File build.ps1` (incluyendo los últimos cambios de `CredentialDialog`: selección individual de servidores por checkbox y prefijo fijo `eidico\`).
3. Validar en vivo contra `172.30.0.13`, `172.31.11.146` y `fileserver2025` (impresoras IP, M365 Sanitizer real, Inventario de Equipo y Gestor de Redes).
4. Probar `dist\EzSetup.exe` de forma autónoma en un equipo Windows 10/11 limpio desde pendrive.
