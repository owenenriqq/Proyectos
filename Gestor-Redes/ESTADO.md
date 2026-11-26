# Estado del Proyecto — Gestor-Redes

## 1. Resumen y Arquitectura

**Gestor de Redes v1.0.0** es una aplicación de escritorio standalone para Windows 10/11 desarrollada en **Python 3.12 + PyQt6** para la administración de adaptadores de red, configuración IPv4/DHCP y DNS, renovación de concesiones/caché y diagnóstico integral de conectividad, manteniendo una interfaz oscura monocromática minimalista y elevación UAC integrada.

### Stack Tecnológico
- **Lenguaje**: Python 3.12 (sin dependencias externas fuera de `PyQt6` y `pyinstaller`)
- **Interfaz Gráfica**: `PyQt6` con paleta oscura monocromática QSS (`styles.py`), filas horizontales compactas (`ActionRow`) y panel de registro colapsable
- **Capa de Red Windows**: `subprocess` con `shell=False` + `CREATE_NO_WINDOW` sobre cmdlets nativos (`Get-NetAdapter`, `Enable/Disable/Restart-NetAdapter`), `netsh`, `ipconfig`, `ping`, `tracert`, `nslookup`, `route`, `arp` y `socket`
- **Empaquetado**: `PyInstaller` (`build.ps1`) con `--onefile --windowed --uac-admin`

### Estructura de Archivos
```text
Gestor-Redes/
├── main.py             # Entrypoint con elevación UAC, AppUserModelID y ventana principal (MainWindow)
├── net_tasks.py        # Inventario de adaptadores, IPv4/DHCP, DNS, habilitar/deshabilitar, renovación y diagnóstico
├── dialogs.py          # Modales: IPConfigDialog, DNSConfigDialog, AdapterDetailsDialog y DiagnosticResultDialog
├── workers.py          # QThreads: AdapterRefreshWorker, ConnectivityCheckWorker, TaskWorker y DiagnosticWorker
├── styles.py           # Hoja de estilos QSS oscura monocromática
├── requirements.txt    # Dependencias mínimas (PyQt6 y pyinstaller)
├── build.ps1           # Script de compilación standalone a dist\GestorRedes.exe
├── .gitignore          # Exclusiones de entorno virtual, compilación y temporales
├── GEMINI.md           # Reglas de arquitectura, seguridad y flujo de trabajo
└── ESTADO.md           # Bitácora viva del proyecto
```

### Comandos de Instalación, Ejecución y Compilación
- **Crear entorno virtual e instalar dependencias**:
  ```powershell
  python -m venv .venv
  .venv\Scripts\pip.exe install -r requirements.txt
  ```
- **Ejecución local**:
  - Normal (con elevación UAC): `.venv\Scripts\python.exe main.py`
  - Sin elevación (solo inspección/UI): `.venv\Scripts\python.exe main.py --no-elevate`
- **Compilación de `dist\GestorRedes.exe`**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File build.ps1
  ```

---

## 2. Estado Actual

### Módulos Completados
- [x] `net_tasks.py`: inventario completo de adaptadores (`list_network_adapters`), configuración IPv4 DHCP/estática (`set_adapter_dhcp`, `set_adapter_static_ip`), configuración DNS con perfiles rápidos (`set_adapter_dns`, `DNS_PRESETS`), habilitar/deshabilitar/reiniciar adaptadores (`set_adapter_enabled`, `restart_adapter`), renovación IP/DNS (`renew_ip_and_dns`, `flush_dns_cache`), purga de sesiones SMB/Kerberos (`purge_network_sessions`), secuencias automáticas (`run_quick_repair`, `run_deep_network_cleanup`), restablecimiento Winsock/TCP-IP (`reset_winsock_and_tcpip`), acceso a `ncpa.cpl` y suite de diagnóstico (`check_internet_connectivity`, `run_ping`, `run_traceroute`, `run_nslookup`, `run_tcp_port_check`, `get_ipconfig_all`, `get_routing_table`, `get_arp_table`, `run_full_network_diagnostic`, `generate_full_diagnostic_report`).
- [x] `styles.py`: tema oscuro monocromático (`#0F1012` / `#17191D` / `#272A30` / `#F4F4F5`) con badges semánticos de estado y controles estilizados.
- [x] `workers.py`: workers `QThread` asíncronos no bloqueantes con traducción amigable de errores UAC (`format_task_exception`).
- [x] `dialogs.py`: diálogos modales para configurar IPv4/DHCP (`IPConfigDialog`), DNS con presets (`DNSConfigDialog`), detalle de adaptador (`AdapterDetailsDialog`) y visor ampliado de diagnóstico (`DiagnosticResultDialog`).
- [x] `main.py`: elevación UAC automática + badge interactivo `"Elevar Admin"`, indicador de conectividad externa en header, 3 vistas laterales (`Adaptadores de Red` sin scroll horizontal innecesario, `Renovación y Caché` con sección `SECUENCIAS AUTOMÁTICAS` y sin `ncpa.cpl` duplicado, `Diagnóstico de Red` con `Generar Reporte Completo` y exportación `.txt`), filtro rápido (`Ctrl+F`), refresco (`F5`), botón vectorial `⋮` y panel inferior de registro colapsable.
- [x] `requirements.txt`, `build.ps1`, `.gitignore`, `GEMINI.md` y `ESTADO.md`.
- [x] Crear `.venv` local en `Gestor-Redes\` e instalar `requirements.txt`.
- [x] Compilar `dist\GestorRedes.exe` con `build.ps1` y validar el ejecutable standalone.

### En Progreso
- Ninguno.

### Pendientes
- [ ] Ejecutar prueba interactiva con privilegios UAC sobre un adaptador real (cambio DHCP/IP estática, DNS, habilitar/deshabilitar, Reparación Rápida y Limpieza Profunda).

---

## 3. Historial de Cambios

- **2026-11-19 — v1.0.5 (Decodificación UTF-8/OEM, tolerancia de retorno parcial NSI en `netsh int ip reset` y limpieza de mensaje UAC)**:
  - `net_tasks.py`:
    - Actualizados `_decode_console_output()` y `_run_cmd()` para intentar decodificación `utf-8` estricta primero y hacer fallback a `oem` / `cp850` / `cp1252` (`errors="replace"`), evitando caracteres acentuados corruptos (`restableció`, `acción`, `Dirección`, `Patrón`).
    - Agregado `is_user_admin()` (`ctypes.windll.shell32.IsUserAnAdmin() != 0`) y actualizado `UAC_PERMISSION_MSG` a `"Permisos insuficientes. Ejecutá Gestor de Redes como Administrador."`.
    - Ajustados `_check_access_denied()` y `format_task_exception()` para no reportar falta de elevación UAC cuando el proceso ya corre como Administrador.
    - Actualizados `_is_partial_ip_reset_success()` y `_log_partial_ip_reset_warning()` en `reset_winsock_and_tcpip` y `run_deep_network_cleanup` para detectar salidas reales en español e inglés (`"se restableci"`, `"restableciendo"`, `"reinicie el equipo"`, `"resetting"`, `"restart the computer"`, `"ok."`, `"ok\r"`, `"ok\n"`, `"ok!"`) con `returncode != 0`, registrando el detalle completo como `[ADVERTENCIA]` en el log sin lanzar error fatal.
  - `main.py`:
    - Eliminadas las referencias residuales a `'Sin UAC'` (`"Modo Estándar"` / `"Elevar Admin"`).
  - Verificación aprobada con mocks de `subprocess.run` en `cp850` y `utf-8` (`AST_OK`, `RESET_SPANISH_CP850_OK`, `DEEP_CLEANUP_SPANISH_CP850_OK`, `RESET_SPANISH_UTF-8_OK`, `DEEP_CLEANUP_SPANISH_UTF-8_OK`, `NON_ADMIN_OK`) y eliminación de scripts temporales de test.
  - Compilación completada: `dist\GestorRedes.exe` compilado con éxito mediante `build.ps1` (PyInstaller).

- **2026-11-19 — v1.0.4 (Pulido visual de tarjetas, purga SMB/Kerberos y recompilación)**:
  - `main.py` y `styles.py`:
    - `ActionRow`: eliminada la restricción de espacio cuando no hay badges en la línea superior (`title_label` con `Expanding` horizontal y `stretch=1` sin `addStretch` competidor), evitando saltos de línea innecesarios en *Renovación y Caché* y *Diagnóstico de Red*.
    - Adaptadores de Red (`badges_in_meta=True`, `compact_buttons=True`): movidos los badges de estado (`Conectado`/`Desconectado`) y modo (`DHCP`/`Estática`) a la fila inferior junto a `meta_label` (`setWordWrap(True)` + `Ignored` horizontal), dejando el nombre del adaptador solo en la línea superior; agregado estilo `QPushButton[compact="true"]` (`padding: 4px 8px`) en `styles.py` y compactado separador `" | "` en `NetworkAdapter.summary_line()` (`net_tasks.py`) para mostrar la MAC completa sin truncamiento en `1080x680`.
    - Vista *Diagnóstico de Red*: compactado el padding vertical (`compact_vertical=True`, márgenes y spacing reducidos) para que el encabezado y las primeras líneas de `SALIDA DE DIAGNÓSTICO` sean visibles sin scrollear en `1080x680` (`145 px` visibles en offscreen), más scroll automático hacia `diag_output` (`_scroll_diagnostics_to_output`) al iniciar o completar pruebas.
  - `net_tasks.py` y `main.py`:
    - Agregada función `purge_network_sessions` (`net use * /delete /y` y `klist purge` con `shell=False` y `CREATE_NO_WINDOW`, tolerando ausencia de sesiones SMB o tickets Kerberos) y su fila **"Purgar Sesiones de Red (SMB / Kerberos)"** en *Renovación y Caché*.
  - Validación y compilación:
    - Smoke test offscreen (`verify_ui.py`) aprobado (`AST_OK`, `PURGE_MOCK_OK`, `LAYOUT_OK_1040x620`, `LAYOUT_OK_1080x680`, `ALL_CHECKS_PASSED`).
    - Recompilado `dist\GestorRedes.exe` mediante `build.ps1` (34.273.261 bytes).

- **2026-11-18 — v1.0.3 (Corrección de recorte horizontal en QScrollArea y ActionRow)**:
  - `main.py`:
    - `_create_scroll_container()`: configurado `scroll.setWidgetResizable(True)`, `ScrollBarAlwaysOff` en horizontal, `QSizePolicy.Policy.Expanding` en el contenedor interno y margen derecho ajustado a `14 px` (`18, 10, 14, 14`) para alinear las tarjetas con el buscador superior.
    - `ActionRow` y `adapters_list_container`: `ActionRow` con `Expanding` horizontal, `title_lbl` con `setWordWrap(True)`, `meta_lbl` con `QSizePolicy.Policy.Ignored` horizontal, y botones derechos (`visible_actions` y `⋮`) con `QSizePolicy.Policy.Fixed`.
    - En la vista de Diagnóstico, `out_title` (`SALIDA DE DIAGNÓSTICO`) configurado con `QSizePolicy.Policy.Ignored` y `stretch=1` para no empujar la fila de botones de salida.
  - Verificación aprobada con smoke test offscreen (`verify_layout.py` a `1040x620`): `PAGE_0_OK`, `PAGE_1_OK`, `PAGE_2_OK`, `LAYOUT_CLIP_CHECK_OK` (todos los botones derechos dentro del ancho del viewport).
  - Nota de compilación: `build.ps1` falló al intentar eliminar `dist\GestorRedes.exe` por `Acceso denegado` (archivo en uso por una instancia abierta de `GestorRedes.exe`).

- **2026-11-18 — v1.0.2 (Ícono de aplicación, ajuste de ventana y compilación EXE)**:
  - Instalado `pillow` (13.0.0) en `.venv` y generado `assets\icon.ico` desde `assets\icon.svg` mediante `PyQt6.QtSvg.QSvgRenderer` + `QImage` + `Pillow` (resoluciones 16, 24, 32, 48, 64, 128 y 256 px).
  - `main.py`: ajustado tamaño inicial de `MainWindow` a `1080x680` y mínimo a `1040x620`; cargado `assets\icon.ico` en `QApplication` y `MainWindow` soportando ejecución normal y empaquetada (`sys._MEIPASS`).
  - `build.ps1`: configurado `--icon "assets\icon.ico"` y `--add-data "assets\icon.ico;assets"`.
  - Ejecutado `build.ps1` con éxito, generando `dist\GestorRedes.exe` (34.270.063 bytes) con ícono y manifiesto UAC embebidos.
  - Verificación aprobada: smoke test offscreen (`ICON_AND_SIZE_OK`) y compilación PyInstaller sin errores.

- **2026-11-18 — v1.0.1 (Secuencias automáticas, reporte completo y ajustes de UI)**:
  - `net_tasks.py`: agregadas `run_quick_repair` (flushdns -> release/renew -> reinicio de adaptador conectado -> verificación de conectividad), `run_deep_network_cleanup` (flushdns -> `arp -d *` -> `netsh winsock reset` -> `netsh int ip reset`) y `generate_full_diagnostic_report` (Diagnóstico Integral + `ipconfig /all` + `route print -4` + `arp -a` con separadores).
  - `main.py`:
    - En **Renovación y Caché**: eliminada la fila duplicada de `ncpa.cpl` y agregada la sección `SECUENCIAS AUTOMÁTICAS` con "Reparación Rápida (Sin reinicio)" y "Limpieza Profunda de Red" (badge `"Requiere reinicio"` y confirmación previa).
    - En **Diagnóstico de Red**: agregada la acción "Generar Reporte Completo" y el botón "Exportar Reporte (.txt)" junto a Ampliar/Copiar/Limpiar.
    - En **Adaptadores de Red**: deshabilitado el scroll horizontal (`Qt.ScrollBarPolicy.ScrollBarAlwaysOff`).
  - Verificación aprobada con `.venv\Scripts\python.exe`: análisis sintáctico AST de los 5 módulos `.py`, comprobación de importaciones y smoke test offscreen de `MainWindow` (`UI_SMOKE_OK`).

- **2026-11-18 — v1.0.0 (Creación inicial standalone)**:
  - Creado el proyecto independiente `Gestor-Redes\` con arquitectura plana modular (`main.py`, `net_tasks.py`, `dialogs.py`, `workers.py`, `styles.py`).
  - Implementadas todas las funciones de gestión de adaptadores (IPv4/DHCP, DNS, habilitar/deshabilitar, reinicio, renovación IP/DNS, restablecimiento Winsock/TCP-IP y diagnóstico completo de red), incluyendo fallback automático `.NET NetworkInterface` cuando el servicio CIM/WMI está restringido.
  - Verificación aprobada: análisis sintáctico AST de los 5 módulos `.py`, validación de direcciones IPv4/máscaras/hosts, decodificación correcta de salida Windows en español (`ipconfig /all`), enumeración real de adaptadores (5 interfaces detectadas) y auditoría de cero referencias externas.

---

## 4. Próximos Pasos
1. Ejecutar `dist\GestorRedes.exe` (con UAC) o `.venv\Scripts\python.exe main.py` para validar visualmente el ícono, la ventana (`1080x680`) y las operaciones reales de red sobre un adaptador.
