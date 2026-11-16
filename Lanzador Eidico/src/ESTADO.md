# Estado del Proyecto - Lanzador Eidico

## Resumen de archivos principales

- **`main.py`**: Interfaz gráfica en PyQt6 (`GestorEidico` y `DialogoSoporte`), elevación automática de privilegios UAC al inicio, gestión de ícono en la bandeja del sistema (`QSystemTrayIcon`), menú desplegable "Opciones", panel de aviso "Sin conexión VPN" y coordinación de hilos de trabajo.
- **`config.py`**: Configuración global (`CONFIG`), detección moderna de AWS VPN Client (`obtener_ruta_aws_vpn`, `esta_aws_vpn_instalado`), decodificación de credenciales Base64 (`get_cred`), filtro sanitizador de credenciales en logs (`FiltroSanitizadorCredenciales`) y configuración de `RotatingFileHandler` con ruta de respaldo.
- **`workers.py`**: Hilos `QThread` en segundo plano (`WorkerVerificacionInicio`, `WorkerMonitor`, `WorkerCheckRed`, `WorkerTransferencia`, `WorkerAccionSistema`), lanzamiento de procesos desacoplados (`lanzar_proceso_desacoplado`), verificación de conectividad TCP/SMB (`is_server_reachable`), registro de credenciales con `cmdkey` (`inyectar_credencial_smb`), limpieza selectiva de sesiones SMB (`limpiar_sesiones_smb_eidico`) y extracción segura de archivos ZIP (`extraer_zip_seguro`).

## Funcionalidades implementadas

- Elevación UAC automática al ejecutar sin permisos de administrador.
- Registro de eventos (`gestor_eidico.log`) con rotación de archivos y sanitización de contraseñas, secretos Base64 y parámetros `/pass`.
- Detección moderna de **AWS VPN Client** en Windows 10/11 mediante rutas estándar, registro de servicios (`AWS.VPN.Client.Service` y `AWS VPN Client OpenVPN Service`), claves `Uninstall` (32/64 bits) y `App Paths`.
- Flujo offline sin apertura automática de AWS VPN Client ni de `EidicoPrueba.exe`: muestra un panel claro sugiriendo abrir AWS VPN Client si está instalado, o consultar el instructivo PDF / instalarlo si no lo está.
- Detección de reconexión desde `WorkerMonitor` cuando el usuario está en el panel "Sin conexión VPN", actualizando el mensaje y habilitando el botón **Abrir Eidico** en el mismo panel.
- Opción **Abrir AWS VPN Client** agregada al menú desplegable **Opciones** (y sincronizada en bandeja), visible/habilitada solo si está instalado y lanzada de forma desacoplada sin bloquear la UI.
- Corrección de `WorkerCheckRed` para raíces UNC como `\\172.30.0.13`, autenticando y manteniendo activa la sesión `\\172.30.0.13\IPC$`; `fin_check_red` notifica el resultado sin abrir automáticamente el Explorador de Windows.
- Nombre interno de la aplicación (`QApplication.setApplicationName` / `setApplicationDisplayName`), tooltip de bandeja y notificaciones del sistema unificados como **Eidico**, manteniendo `"Gestor Eidico"` como título de la ventana principal.
- Reintento con limpieza de sesión SMB en `WorkerVerificacionInicio`, ejecución en segundo plano para `forzar_cierre_eidico` y `crear_accesos_directos`, bloqueo del menú "Opciones" durante tareas activas y límite de ciclos en la verificación de instalación de AWS VPN Client.

## Pendientes / errores abiertos

- Validación en vivo de las pruebas funcionales de UI, detección de AWS VPN Client, reconexión y acceso a `\\172.30.0.13`.
- Compilación final del nuevo `Eidico.exe` con PyInstaller usando `comando.txt` (pendiente de autorización explícita).

## Última actualización

- Se implementaron todos los cambios solicitados en `config.py`, `workers.py` y `main.py`, validando la sintaxis con `ast.parse` en Python 3.12 (`OK`).
- Siguiente paso: aguardar confirmación del usuario para ejecutar pruebas o compilar el nuevo `Eidico.exe`.
