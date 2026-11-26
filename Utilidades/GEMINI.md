# Reglas — Utilidades
- **100% Standalone:** Soporte técnico particular Windows 10/11 (Python 3.12 + PyQt6). Prohibido incluir referencias, rutas UNC, dominios o dependencias de Eidico ni de otros subproyectos. Su lógica base se sincroniza con `..\EzSetup\EzSetup_Python\src\modules\utilities\`.
- Mantener elevación UAC nativa (manifiesto o `ShellExecuteW` con `runas`).
- Validar privilegios, recursos y códigos de retorno (`returncode` / `$LASTEXITCODE`) capturando `stdout`/`stderr`.
- **UI:** Mantener estética oscura monocromática consistente con el monorepo.
