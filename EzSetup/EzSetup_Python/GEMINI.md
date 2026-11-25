# Reglas del Proyecto — EzSetup_Python

- Todo el desarrollo, pruebas y ejecución deben realizarse exclusivamente dentro de `EzSetup_Python\`.
- No modificar bajo ningún concepto los scripts de referencia ubicados en `..\EzSetup_CMD_PS\`.
- **Arquitectura unificada (`v3.0.0`):** `EzSetup_Python` integra de forma nativa/wrapper los módulos de `Gestor-Redes`, `Utilidades`, `Inventario Eidico` y `Suite-M365-Saneamiento`. Los paquetes `src\modules\utilities\` y `src\modules\network\` deben mantenerse **100% libres de referencias corporativas a Eidico** (sin depender de `src.config` ni `credentials.enc`).
- Toda ruta, URL, parámetro de comportamiento y estructura de menús debe centralizarse en `config.json` y consumirse mediante `src/config.py`.
- Las credenciales para el Administrador de Credenciales de Windows (`cmdkey`) deben solicitarse siempre al usuario en tiempo de ejecución mediante diálogo seguro en la UI (`src/ui/dialogs.py`).
- **PROHIBIDO incluir o migrar** binarios o scripts de activación no oficial (`KMS.bat`, `Crack.zip`, `Patch.zip`, `.reg`) dentro del repositorio. `config.json` sí puede referenciar rutas externas de red ya existentes sin alojar archivos en Git.
