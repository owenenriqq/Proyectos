"""Wrapper no interactivo para ejecutar Suite-M365-Saneamiento desde EzSetup."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any, Callable

from src.config import AppConfig

LogCallback = Callable[[str], None]

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

_REQUIRED_MODULES = (
    "Get-OfficeDiagnostics.ps1",
    "Clear-IdentityCache.ps1",
    "Reset-OfficeLicenses.ps1",
    "Uninstall-OfficeProducts.ps1",
)


def _noop_log(_: str) -> None:
    """Callback por defecto cuando no se provee logger."""


def _ps_quote(value: str) -> str:
    """Escapa comillas simples para interpolación segura en cadenas PowerShell."""
    return value.replace("'", "''")


def resolve_m365_sanitizer_dir() -> Path:
    """Resuelve y valida el directorio de scripts de Suite-M365-Saneamiento."""
    base_dir = AppConfig.get_asset_dir("m365_sanitizer")
    modules_dir = base_dir / "modules"
    if not modules_dir.is_dir():
        raise FileNotFoundError(
            f"No se encontró la carpeta de módulos M365 en: {modules_dir}"
        )

    for module_name in _REQUIRED_MODULES:
        module_path = modules_dir / module_name
        if not module_path.is_file():
            raise FileNotFoundError(
                f"Falta el módulo requerido de Suite-M365-Saneamiento: {module_path}"
            )
    return base_dir


def _get_backup_root() -> Path:
    """Obtiene una carpeta escribible en %TEMP% para respaldos de sppc.dll."""
    temp_base = Path(os.environ.get("TEMP") or os.environ.get("TMP") or Path.home())
    backup_dir = temp_base / "EzSetup_M365_Backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def _run_ps_command(ps_script: str, log: LogCallback) -> str:
    """Ejecuta un comando PowerShell sin ventana y transmite su salida al log."""
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        ps_script,
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        creationflags=_CREATE_NO_WINDOW,
    )

    lines: list[str] = []
    assert proc.stdout is not None
    for raw_line in proc.stdout:
        clean_line = raw_line.rstrip("\r\n")
        if clean_line:
            log(clean_line)
            lines.append(clean_line)

    returncode = proc.wait()
    output = "\n".join(lines)
    if returncode != 0:
        raise RuntimeError(
            f"PowerShell finalizó con código {returncode}. Revisá el registro de actividad."
        )
    return output


def _build_logger_preamble() -> str:
    """Construye el preámbulo PowerShell con codificación UTF-8 y logger directo a stdout."""
    return (
        "$OutputEncoding = [System.Text.Encoding]::UTF8; "
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "$ErrorActionPreference = 'Stop'; "
        "$ezLogger = { param([string]$Message, [string]$Level = 'INFO') "
        "[Console]::Out.WriteLine(\"[$Level] $Message\"); "
        "[Console]::Out.Flush() }; "
    )


def run_office_diagnostics(
    _config: AppConfig,
    log: LogCallback = _noop_log,
) -> str:
    """Ejecuta el diagnóstico de solo lectura de Office, sppc.dll y licencias."""
    base_dir = resolve_m365_sanitizer_dir()
    mod_path = _ps_quote(str(base_dir / "modules" / "Get-OfficeDiagnostics.ps1"))
    log("[INFO] Iniciando diagnóstico de Microsoft Office / 365 (solo lectura)...")

    ps_script = (
        _build_logger_preamble()
        + f". '{mod_path}'; "
        + "$diag = Get-OfficeDiagnostics -Logger $ezLogger; "
        + "if ($null -ne $diag -and $diag.PSObject.Properties['ParsedLicenses'] "
        + "-and $diag.ParsedLicenses -and $diag.ParsedLicenses.Count -gt 0) { "
        + "[Console]::Out.WriteLine('[INFO] --- Resumen de licencias detectadas ---'); "
        + "foreach ($lic in $diag.ParsedLicenses) { "
        + "[Console]::Out.WriteLine(\"[INFO] [$($lic.Category)] $($lic.LicenseName) | Estado: $($lic.LicenseStatus) | Clave: $($lic.PartialKey)\") "
        + "} "
        + "[Console]::Out.Flush() }"
    )
    _run_ps_command(ps_script, log)
    return "Diagnóstico de Office / Microsoft 365 completado."


def run_clear_identity_cache(
    _config: AppConfig,
    what_if: bool = True,
    log: LogCallback = _noop_log,
) -> str:
    """Ejecuta la limpieza de caché de identidad, WAM y credenciales cmdkey."""
    base_dir = resolve_m365_sanitizer_dir()
    mod_path = _ps_quote(str(base_dir / "modules" / "Clear-IdentityCache.ps1"))
    mode_label = "Simulación (-WhatIf)" if what_if else "Ejecución real"
    log(f"[INFO] Iniciando limpieza de caché de identidad M365 ({mode_label})...")

    whatif_flag = " -WhatIf" if what_if else ""
    ps_script = (
        _build_logger_preamble()
        + f". '{mod_path}'; "
        + f"Clear-IdentityCache -Logger $ezLogger -Confirm:$false{whatif_flag} *>&1 | Out-String -Stream"
    )
    _run_ps_command(ps_script, log)
    return f"Limpieza de caché de identidad finalizada ({mode_label})."


def run_reset_office_licenses(
    _config: AppConfig,
    mode: str = "Selectivo",
    what_if: bool = True,
    log: LogCallback = _noop_log,
) -> str:
    """Restablece licencias de Office en modo Selectivo o Total."""
    if mode not in ("Selectivo", "Total"):
        raise ValueError(f"Modo de restablecimiento inválido: '{mode}'")

    base_dir = resolve_m365_sanitizer_dir()
    mod_path = _ps_quote(str(base_dir / "modules" / "Reset-OfficeLicenses.ps1"))
    backup_root = _ps_quote(str(_get_backup_root()))
    mode_label = "Simulación (-WhatIf)" if what_if else "Ejecución real"
    log(f"[INFO] Iniciando saneamiento de licencias ({mode} - {mode_label})...")

    whatif_flag = " -WhatIf" if what_if else ""
    ps_script = (
        _build_logger_preamble()
        + f". '{mod_path}'; "
        + f"Reset-OfficeLicenses -Mode '{mode}' -BackupRoot '{backup_root}' -Logger $ezLogger -Confirm:$false{whatif_flag} *>&1 | Out-String -Stream"
    )
    _run_ps_command(ps_script, log)
    return f"Saneamiento de licencias finalizado ({mode} - {mode_label})."


def run_stop_office_processes(
    _config: AppConfig,
    what_if: bool = True,
    log: LogCallback = _noop_log,
) -> str:
    """Cierra procesos activos de Office / Project / Visio mediante Stop-OfficeUserApplications."""
    base_dir = resolve_m365_sanitizer_dir()
    mod_path = _ps_quote(str(base_dir / "modules" / "Uninstall-OfficeProducts.ps1"))
    mode_label = "Simulación (-WhatIf)" if what_if else "Ejecución real"
    log(f"[INFO] Cerrando aplicaciones activas de Office / Project / Visio ({mode_label})...")

    whatif_flag = " -WhatIf" if what_if else ""
    ps_script = (
        _build_logger_preamble()
        + f". '{mod_path}'; "
        + f"Stop-OfficeUserApplications -Logger $ezLogger -Confirm:$false{whatif_flag} *>&1 | Out-String -Stream"
    )
    _run_ps_command(ps_script, log)
    return f"Cierre de procesos Office finalizado ({mode_label})."


def list_installed_office_products(
    _config: AppConfig | None = None,
    log: LogCallback = _noop_log,
) -> list[dict[str, Any]]:
    """Lista productos Office / Project / Visio instalados (Click-to-Run y MSI)."""
    base_dir = resolve_m365_sanitizer_dir()
    mod_path = _ps_quote(str(base_dir / "modules" / "Uninstall-OfficeProducts.ps1"))
    marker = "__EZ_PRODUCTS_JSON__:"

    ps_script = (
        _build_logger_preamble()
        + f". '{mod_path}'; "
        + "$items = @(Get-InstalledOfficeProducts -Logger $ezLogger); "
        + "$payload = @(); "
        + "foreach ($it in $items) { "
        + "$payload += [PSCustomObject]@{ "
        + "DisplayName = [string]$it.DisplayName; "
        + "ProductId = [string]$it.ProductId; "
        + "Category = [string]$it.Category; "
        + "InstallType = [string]$it.InstallType; "
        + "Version = [string]$it.Version "
        + "} }; "
        + f"[Console]::Out.WriteLine('{marker}' + ($payload | ConvertTo-Json -Compress)); "
        + "[Console]::Out.Flush()"
    )
    captured_json = "[]"

    def _capture_log(line: str) -> None:
        nonlocal captured_json
        if line.startswith(marker):
            captured_json = line[len(marker):].strip() or "[]"
        else:
            log(line)

    _run_ps_command(ps_script, _capture_log)
    if not captured_json or captured_json == "null":
        return []
    parsed = json.loads(captured_json)
    if isinstance(parsed, dict):
        return [parsed]
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return []


def run_uninstall_selected_office_products(
    _config: AppConfig,
    product_ids: list[str],
    what_if: bool = True,
    log: LogCallback = _noop_log,
) -> str:
    """Desinstala selectivamente los ProductId seleccionados (C2R o MSI)."""
    clean_ids = [str(pid).strip() for pid in product_ids if str(pid).strip()]
    if not clean_ids:
        raise ValueError("Seleccioná al menos un producto de Office para desinstalar.")

    base_dir = resolve_m365_sanitizer_dir()
    mod_path = _ps_quote(str(base_dir / "modules" / "Uninstall-OfficeProducts.ps1"))
    mode_label = "Simulación (-WhatIf)" if what_if else "Ejecución real"
    whatif_bool = "$true" if what_if else "$false"
    ids_literal = ", ".join(f"'{_ps_quote(pid)}'" for pid in clean_ids)
    log(
        f"[INFO] Iniciando desinstalación selectiva de {len(clean_ids)} producto(s) ({mode_label})..."
    )

    ps_script = (
        _build_logger_preamble()
        + f". '{mod_path}'; "
        + f"$sim = {whatif_bool}; "
        + f"$targetIds = @({ids_literal}); "
        + "$inventory = @(Get-InstalledOfficeProducts -Logger $ezLogger); "
        + "$selected = @($inventory | Where-Object { $targetIds -contains [string]$_.ProductId }); "
        + "if ($selected.Count -eq 0) { "
        + "[Console]::Out.WriteLine('[WARN] Ninguno de los productos seleccionados sigue presente en el sistema.'); "
        + "[Console]::Out.Flush(); exit 0 }; "
        + "$installPaths = @(); "
        + "foreach ($item in $selected) { "
        + "if ($null -ne $item -and $item.PSObject.Properties['InstallationPath'] -and -not [string]::IsNullOrWhiteSpace([string]$item.InstallationPath)) { "
        + "$p = ([string]$item.InstallationPath).Trim().TrimEnd('\\'); "
        + "if ($p -and ($installPaths -notcontains $p)) { $installPaths += $p } } }; "
        + "Stop-OfficeUserApplications -Logger $ezLogger -Confirm:$false -WhatIf:$sim *>&1 | Out-String -Stream; "
        + "$c2rExe = Get-OfficeClickToRunExePath -InstallationPaths $installPaths; "
        + "foreach ($prod in $selected) { "
        + "[void](Invoke-SingleProductUninstall -Product $prod -ClickToRunExePath $c2rExe -Logger $ezLogger -Confirm:$false -WhatIf:$sim) "
        + "}"
    )
    _run_ps_command(ps_script, log)
    return f"Desinstalación selectiva finalizada ({len(clean_ids)} producto(s), {mode_label})."


def run_uninstall_office_products(
    _config: AppConfig,
    what_if: bool = True,
    log: LogCallback = _noop_log,
) -> str:
    """Ejecuta desinstalación total y limpieza profunda no interactiva de Office."""
    base_dir = resolve_m365_sanitizer_dir()
    mod_path = _ps_quote(str(base_dir / "modules" / "Uninstall-OfficeProducts.ps1"))
    backup_root = _ps_quote(str(_get_backup_root()))
    mode_label = "Simulación (-WhatIf)" if what_if else "Ejecución real"
    whatif_bool = "$true" if what_if else "$false"
    log(f"[INFO] Iniciando desinstalación y limpieza profunda de Office ({mode_label})...")

    ps_script = (
        _build_logger_preamble()
        + f". '{mod_path}'; "
        + f"$sim = {whatif_bool}; "
        + "$inventory = @(Get-InstalledOfficeProducts -Logger $ezLogger); "
        + "$installPaths = @(); "
        + "foreach ($item in $inventory) { "
        + "if ($null -ne $item -and $item.PSObject.Properties['InstallationPath'] -and -not [string]::IsNullOrWhiteSpace([string]$item.InstallationPath)) { "
        + "$p = ([string]$item.InstallationPath).Trim().TrimEnd('\\'); "
        + "if ($p -and ($installPaths -notcontains $p)) { $installPaths += $p } } }; "
        + "Stop-OfficeUserApplications -Logger $ezLogger -Confirm:$false -WhatIf:$sim *>&1 | Out-String -Stream; "
        + "if ($inventory.Count -gt 0) { "
        + "$c2rExe = Get-OfficeClickToRunExePath -InstallationPaths $installPaths; "
        + "foreach ($prod in $inventory) { "
        + "[void](Invoke-SingleProductUninstall -Product $prod -ClickToRunExePath $c2rExe -Logger $ezLogger -Confirm:$false -WhatIf:$sim) "
        + "} "
        + "} else { "
        + "[Console]::Out.WriteLine('[INFO] No se detectaron productos activos en registro; ejecutando limpieza de residuos.'); "
        + "[Console]::Out.Flush() "
        + "}; "
        + f"Invoke-OfficeDeepCleanup -DetectedInstallationPaths $installPaths -BackupRoot '{backup_root}' -Logger $ezLogger -Confirm:$false -WhatIf:$sim *>&1 | Out-String -Stream"
    )
    _run_ps_command(ps_script, log)
    return f"Desinstalación y limpieza profunda de Office finalizada ({mode_label})."
