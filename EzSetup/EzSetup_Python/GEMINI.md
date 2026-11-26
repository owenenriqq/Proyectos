# Reglas — EzSetup_Python
- Desarrollar y probar exclusivamente en `EzSetup_Python\`. Prohibido modificar `..\EzSetup_CMD_PS\`.
- **Arquitectura v3.0.0:** Integra módulos de `Gestor-Redes`, `Utilidades`, `Inventario Eidico` y `Suite-M365-Saneamiento`. Mantener `src\modules\utilities\` y `src\modules\network\` 100% libres de referencias a Eidico (`src.config`, `credentials.enc`).
- Centralizar rutas, URLs, parámetros y menús en `config.json` vía `src/config.py`.
- Solicitar credenciales para `cmdkey` siempre en tiempo de ejecución desde `src/ui/dialogs.py`.
- **Prohibido en Git:** No incluir ni migrar activadores no oficiales (`KMS.bat`, `Crack.zip`, `Patch.zip`, `.reg`). `config.json` solo puede referenciar rutas de red externas existentes.
