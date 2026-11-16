# Estado del Proyecto - Lanzador Eidico

## Resumen de archivos principales

- **`main.py`**: Interfaz gráfica en PyQt6 (`GestorEidico` y `DialogoSoporte`), elevación automática de privilegios UAC al inicio, gestión de ícono en la bandeja del sistema (`QSystemTrayIcon`), menú contextual y coordinación de hilos de trabajo.
- **`config.py`**: Configuración global (`CONFIG`), rutas de servidor/local/VPN/descargas, decodificación de credenciales Base64 (`get_cred`), filtro sanitizador de credenciales en logs (`FiltroSanitizadorCredenciales`) y configuración de `RotatingFileHandler` con ruta de respaldo.
- **`workers.py`**: Hilos `QThread` en segundo plano (`WorkerVerificacionInicio`, `WorkerMonitor`, `WorkerCheckRed`, `WorkerTransferencia`, `WorkerAccionSistema`), verificación de conectividad TCP/SMB (`is_server_reachable`), registro de credenciales con `cmdkey` (`inyectar_credencial_smb`), limpieza selectiva de sesiones SMB (`limpiar_sesiones_smb_eidico`) y extracción segura de archivos ZIP (`extraer_zip_seguro`).

## Funcionalidades implementadas

- Elevación UAC automática al ejecutar sin permisos de administrador.
- Registro de eventos (`gestor_eidico.log`) con rotación de archivos y sanitización de contraseñas, secretos Base64 y parámetros `/pass`.
- Verificación de red y conectividad hacia los servidores corporativos (`172.31.11.146` y `172.30.0.13`) y manejo de credenciales SMB.
- Descarga y extracción segura de paquetes corporativos (Sistema Fox Eidico, FortiClient, AWS VPN Client, TeamViewer).
- Diálogo de Soporte Técnico IT con accesos directos a WhatsApp (aplicación y web) y correo electrónico.

## Pendientes actuales

- Revisar y validar la detección del cliente **AWS VPN Client** (`VPN_EXE` en `config.py` y su flujo en los workers/interfaz).
- Verificar y completar las opciones del menú en la interfaz / bandeja del sistema según los requerimientos vigentes.
- Revisar posibles correcciones en el manejo e inyección de credenciales SMB.
- Confirmar la compilación final con PyInstaller (`Eidico.spec`, `Eidico.ico`, `InstructivoAWSVPN.pdf`) cuando se autorice.

## Última actualización

- Se agregó la regla permanente de actualización de `ESTADO.md` en `GEMINI.md`.
- Se creó `.gitignore` excluyendo `.venv/`, `build/`, `dist/`, `__pycache__/` y `*.log`, manteniendo visibles `Eidico.ico`, `InstructivoAWSVPN.pdf` y `comando.txt`.
- Se creó este archivo `ESTADO.md` en codificación UTF-8.
