# Estado del Proyecto — EzSetup_Python

## 1. Resumen y Arquitectura

**EzSetup v2.0.0** es la migración completa de los scripts heredados de aprovisionamiento (`EzSetup_CMD_PS\`, solo lectura) a una aplicación de escritorio moderna para Windows 10/11 desarrollada en **Python 3.12 + PyQt6**, con configuración centralizada, ejecución asíncrona no bloqueante y exclusión total de software o activadores no oficiales.

### Stack Tecnológico
- **Lenguaje**: Python 3.12 (`C:\Users\oenrique\AppData\Local\Programs\Python\Python312\python.exe`, aislado en `.venv\`)
- **Interfaz Gráfica**: `PyQt6` (6.12.1) con diseño horizontal minimalista y tema oscuro QSS (`src/ui/styles.py`)
- **Red / Descargas**: `requests` (2.34.2) por streaming con archivo temporal `.tmp` y cancelación
- **Cifrado de Credenciales**: `cryptography` (50.0.2) — `AES-256-GCM` + `PBKDF2HMAC-SHA256` (600,000 iteraciones) en `src/crypto_creds.py`
- **Integración Windows (COM / ACL / Registro)**: `pywin32` (312), `winreg`, `ctypes`, `cmdkey`, `regedit.exe`, `powercfg`
- **Empaquetado**: `pyinstaller` (6.22.3)

### Árbol de Carpetas
```text
EzSetup_Python/
├── .venv/                      # Entorno virtual Python 3.12 (excluido en .gitignore)
├── assets/
│   └── EzSetup.ico             # Ícono oficial de la aplicación
├── src/
│   ├── __init__.py
│   ├── config.py               # Carga/validación de config.json, KnownFolders y resolución de credentials.enc
│   ├── crypto_creds.py         # Cifrado/descifrado AES-256-GCM + PBKDF2HMAC-SHA256 (600k iteraciones)
│   ├── workers.py              # QThreads: ServerCheckWorker, DownloadWorker, FileCopyWorker, IsoMountWorker, TaskWorker
│   ├── system_tasks.py         # Tareas administrativas Windows (cmdkey, COM .lnk, ACL S-1-5-32-545, RegAsm, Firewall, etc.)
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py      # UI minimalista de filas horizontales compactas, tooltips y log colapsado por defecto
│       ├── dialogs.py          # CredentialDialog (credentials.enc o manual) y ProgressDialog (con cancelación)
│       └── styles.py           # Hoja de estilos QSS minimalista (tema oscuro)
├── .gitignore                  # Excluye .venv/, build/, dist/, *.spec, *.enc, etc.
├── build.ps1                   # Script de compilación PyInstaller
├── config.json                 # Rutas UNC, URLs, rutas locales, servidores y menús centralizados
├── ESTADO.md                   # Bitácora viva del proyecto
├── GEMINI.md                   # Reglas obligatorias de desarrollo y seguridad
├── main.py                     # Entrypoint con elevación UAC automática y AppUserModelID
├── manage_creds.py             # CLI para generar/actualizar credentials.enc sin guardar texto plano
└── requirements.txt
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
- [x] `config.json` centralizado con catálogo extensible en **5 categorías** (`EIDICO`, `Ofimática y Diseño`, `Técnica`, `Reparaciones y Diagnóstico`, `Credenciales y Red`), acciones genéricas (`exe`, `msi`, `iso`, `ps1`, `copy`, `reg`, `url`, `task`), nuevas rutas (`Autodesk Revit LT 2020.1`, `uPanel Anura 4.4.2`, `Hard Disk Sentinel Pro 5.50`) y ocultamiento automático de ítems con ruta vacía (`dwg_trueview_2020`, `sketchup`).
- [x] `src\config.py`: validación de esquema JSON (incluyendo `menus[*].subgroups`), soporte dual script/PyInstaller, `KnownFolders` y resolución automática de `credentials.enc` (local, bundle o UNC).
- [x] `src\crypto_creds.py` y `manage_creds.py`: módulo AES-256-GCM + PBKDF2HMAC-SHA256 (600,000 iteraciones, salt 16 B, nonce 12 B) y CLI interactivo para generar/actualizar `credentials.enc`.
- [x] `src\workers.py`: workers `QThread` reutilizables (`ServerCheckWorker`, `DownloadWorker`, `FileCopyWorker`, `IsoMountWorker`, `TaskWorker`).
- [x] `src\system_tasks.py`: tareas administrativas (`cmdkey`, `create_network_shortcuts`, `Eidico.lnk`, ACL `FullControl` SID `S-1-5-32-545`, FortiClient ZIP, Firewall AutoCAD 2021, `RegAsm.exe`, OpenVPN, Fondos, EIDICO.vbs, `Produccion.zip`, `NitroPDF.zip`, `hdsentinel_replace_exe`, `powercfg /batteryreport`) y despacho genérico (`run_generic_exe`, `run_generic_msi`, `run_generic_reg`, `run_generic_ps1`, `copy_generic_item`, `TASK_REGISTRY`).
- [x] `src\ui\`: catálogo dinámico desde `config.json` con subgrupos, filas `ActionRow` con máximo 3 botones visibles + menú desplegable `▾` (`QMenu`), ocultamiento automático de ítems vacíos, buscador en tiempo real (`Ctrl+F`), recarga en caliente (`Recargar Config`) y panel de registro colapsado por defecto.
- [x] `main.py`: verificación y relanzamiento UAC (`ShellExecuteW "runas"`).
- [x] Verificación técnica aprobada: `py_compile` sobre los 11 `.py`, escaneo de cero hardcoding, prueba de cifrado/descifrado AES-256-GCM y prueba headless (`QT_QPA_PLATFORM=offscreen`) de `MainWindow` y `CredentialDialog`.

### En Progreso
- Ninguno en curso al cierre de esta sesión.

### Pendientes
- [ ] Completar en `config.json` las rutas UNC definitivas de `unc_paths.tecnica` actualmente vacías (`revit_2021_iso`, `dwg_trueview_2020_installer`, `sketchup_installer`).
- [ ] Ejecutar pruebas funcionales interactivas en red corporativa/VPN contra `172.30.0.13` y `172.31.11.146` (descargas HTTP, montaje ISO/IMG, copia de `EidicoPrueba.EXE`, permisos `Sol Sistemas`, `RegAsm` y `cmdkey`).
- [ ] Compilar `dist\EzSetup.exe` mediante `build.ps1` y validar la ejecución del binario empaquetado en un equipo Windows 10/11 limpio.

---

## 3. Historial de Cambios

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
