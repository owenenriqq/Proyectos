# Estado del Proyecto - Inventario Eidico

## Propósito

Herramienta de escritorio en Python (PyQt6) para relevar automáticamente el hardware y sistema operativo de equipos Windows junto con datos administrativos ingresados por el operador (usuario AD, correo, puesto, antigüedad, área, propiedad, fecha de compra y observaciones), guardando cada registro en un archivo de texto centralizado en red (`Inventario.txt`).

## Arquitectura Actual (`Inventario3.py`)

- **Elevación de privilegios**: Verifica `es_admin()` mediante `ctypes.windll.shell32.IsUserAnAdmin()` y relanza el script con `ShellExecuteW(..., "runas", ...)` si no tiene permisos de administrador.
- **Captura de hardware (`WorkerInventario` en `QThread`)**:
  - **Equipo y SO**: `socket.gethostname()` y `Win32_OperatingSystem` vía `wmi`.
  - **CPU**: `Win32_Processor` vía `wmi`.
  - **RAM (`analizar_ram`)**: Suma `Capacity` de `Win32_PhysicalMemory`, redondea a GB con `math.ceil` y detecta factor de forma (`UDIMM`, `SODIMM`, `DIMM`, `Integrada`) y cantidad de ranuras usadas.
  - **Discos (`obtener_discos_powershell`)**: Ejecuta `Get-PhysicalDisk | Select-Object MediaType, BusType, Size | ConvertTo-Csv -NoTypeInformation` en PowerShell oculto (`creationflags=0x08000000`) para clasificar `HDD`, `SSD SATA` y `NVMe`.
- **Interfaz gráfica (PyQt6)**: Formulario compacto (`350x300`) con estilos QSS personalizados, iconos embebidos en Base64, `QComboBox` para propiedad, `QDateEdit` con `QCalendarWidget` popup y `QProgressBar` durante el relevamiento.
- **Persistencia**: Agrega una línea formateada separada por `|` al archivo `\\fileserver2025\IT\SOFT-INVENTARIO\Inventario.txt` en UTF-8.

## Qué quedó funcional

- Relevamiento asíncrono en `QThread` con inicialización/liberación COM (`pythoncom.CoInitialize` / `CoUninitialize`).
- Detección de CPU, RAM (capacidad, tipo y ranuras), discos físicos (NVMe/SSD/HDD) y versión de Windows.
- Corrección visual del popup `QCalendarWidget` (`min-width: 300px; min-height: 220px`) y botones desplegables azules en `Inventario3.py`.

## Pendientes por pulir

- **Configuración externa**: `CARPETA_RED` (`\\fileserver2025\IT\SOFT-INVENTARIO`) está hardcodeada en el código fuente; migrar a `config.json` para cumplir con las reglas globales de seguridad.
- **Recursos de empaquetado**: El código referencia `Inventario.ico` vía `resource_path("Inventario.ico")`, pero el archivo `.ico` no se encuentra actualmente en la carpeta.

## Última actualización

- Se eliminaron las versiones anteriores (`Inventario.py` e `Inventario2.py`), quedando `Inventario3.py` como única versión activa.
