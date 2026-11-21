# Estado del Proyecto - Lanzador Eidico

## Resumen de archivos principales

- **`main.py`**: Interfaz gráfica en PyQt6 (`GestorEidico` y `DialogoSoporte`), elevación automática de privilegios UAC al inicio, gestión de ícono en la bandeja del sistema (`QSystemTrayIcon`), menú desplegable "Opciones", panel de aviso "Sin conexión VPN" (`panel_sin_vpn`) y coordinación de hilos de trabajo.
- **`config.py`**: Configuración global (`CONFIG`), detección moderna de AWS VPN Client (`obtener_ruta_aws_vpn`, `esta_aws_vpn_instalado`, `NOMBRES_EXE_VPN`) priorizando `AWS VPN Client.exe` con fallback a `AWSVPNClient.exe`, decodificación de credenciales Base64 (`get_cred`), filtro sanitizador de credenciales en logs (`FiltroSanitizadorCredenciales`) y configuración de `RotatingFileHandler` con ruta de respaldo.
- **`workers.py`**: Hilos `QThread` en segundo plano (`WorkerVerificacionInicio`, `WorkerMonitor`, `WorkerCheckRed`, `WorkerTransferencia`, `WorkerAccionSistema`), lanzamiento de procesos desacoplados (`lanzar_proceso_desacoplado`), verificación de conectividad TCP/SMB (`is_server_reachable`), registro de credenciales con `cmdkey` (`inyectar_credencial_smb`), limpieza selectiva de sesiones SMB (`limpiar_sesiones_smb_eidico`) y extracción segura de archivos ZIP (`extraer_zip_seguro`).

## Funcionalidades implementadas

- Elevación UAC automática al ejecutar sin permisos de administrador.
- Registro de eventos (`gestor_eidico.log`) con rotación de archivos y sanitización de contraseñas, secretos Base64 y parámetros `/pass`.
- Detección moderna de **AWS VPN Client** en Windows 10/11 priorizando `AWS VPN Client.exe` (con `AWSVPNClient.exe` como fallback secundario) mediante rutas estándar, registro de servicios (`AWS.VPN.Client.Service` y `AWS VPN Client OpenVPN Service`), claves `Uninstall` (32/64 bits) y `App Paths`.
- Visibilidad exclusiva en menú "Opciones", bandeja del sistema y `panel_sin_vpn`: muestra **"Abrir AWS VPN Client"** (y **"Reinstalar AWS VPN Client"** / **"Reiniciar VPN"**) solo cuando `esta_aws_vpn_instalado()` es `True`, y **"Instalar VPN"** únicamente cuando es `False`.
- Flujo offline sin apertura automática de AWS VPN Client ni de `EidicoPrueba.exe`: muestra `panel_sin_vpn` con título y subtítulo centrados con `wordWrap` sin recortes dentro de la ventana (`360x355`).
- Detección de reconexión desde `WorkerMonitor` cuando el usuario está en `panel_sin_vpn`, actualizando el mensaje y habilitando **Abrir Eidico** en el mismo panel.
- Corrección de `WorkerCheckRed` para raíces UNC como `\\172.30.0.13`, autenticando y manteniendo activa la sesión `\\172.30.0.13\IPC$`; `fin_check_red` notifica el resultado sin abrir automáticamente el Explorador de Windows.
- Nombre interno de la aplicación (`QApplication.setApplicationName` / `setApplicationDisplayName`), tooltip de bandeja y notificaciones del sistema unificados como **Eidico**, manteniendo `"Gestor Eidico"` como título de la ventana principal.

## Pendientes / errores abiertos

- Validación visual en vivo del nuevo `panel_sin_vpn` y de la detección de `AWS VPN Client.exe`.
- Compilación final del nuevo `Eidico.exe` con PyInstaller usando `comando.txt` (pendiente de autorización explícita).
- En `main.py` (`fin_descarga_simple`, línea 709) persiste `"Gestor Eidico"` en una llamada a `emitir_notificacion` (reportado en auditoría).

## Última actualización

- Se corrigió el nombre real del ejecutable (`AWS VPN Client.exe` prioritario con fallback `AWSVPNClient.exe`) en `config.py` y `workers.py`.
- Se implementó visibilidad exclusiva de **Instalar VPN** vs. **Abrir AWS VPN Client** y se rediseñaron los textos y dimensiones de `panel_sin_vpn` en `main.py`.
- Validación sintáctica ejecutada con `ast.parse` en Python 3.12 (`OK`).
- Siguiente paso: aguardar revisión/aprobación del usuario sobre las sugerencias de auditoría o autorización para compilar `Eidico.exe`.
