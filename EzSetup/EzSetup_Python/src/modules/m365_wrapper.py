"""Wrapper no interactivo para ejecutar Suite-M365-Saneamiento desde EzSetup."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Callable

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
    """Construye el preámbulo PowerShell con codificación UTF-8 y logger estándar."""
    return (
        "$OutputEncoding = [System.Text.Encoding]::UTF8; "
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "$ErrorActionPreference = 'Stop'; "
        "$ezLogger = { param([string]$Message, [string]$Level = 'INFO') "
        "Write-Output \"[$Level] $Message\" }; "
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
        + "if ($diag.ParsedLicenses -and $diag.ParsedLicenses.Count -gt 0) { "
        + "Write-Output '[INFO] --- Resumen de licencias detectadas ---'; "
        + "foreach ($lic in $diag.ParsedLicenses) { "
        + "Write-Output \"[INFO] [$($lic.Category)] $($lic.LicenseName) | Estado: $($lic.LicenseStatus) | Clave: $($lic.PartialKey)\" "
        + "} }"
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
        + f"Clear-IdentityCache -Logger $ezLogger -Confirm:$false{whatif_flag}"
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
        + f"Reset-OfficeLicenses -Mode '{mode}' -BackupRoot '{backup_root}' -Logger $ezLogger -Confirm:$false{whatif_flag}"
    )
    _run_ps_command(ps_script, log)
    return f"Saneamiento de licencias finalizado ({mode} - {mode_label})."


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
        + "Stop-OfficeUserApplications -Logger $ezLogger -Confirm:$false -WhatIf:$sim; "
        + "if ($inventory.Count -gt 0) { "
        + "$c2rExe = Get-OfficeClickToRunExePath -InstallationPaths $installPaths; "
        + "foreach ($prod in $inventory) { "
        + "[void](Invoke-SingleProductUninstall -Product $prod -ClickToRunExePath $c2rExe -Logger $ezLogger -Confirm:$false -WhatIf:$sim) "
        + "} "
        + "} else { "
        + "Write-Output '[INFO] No se detectaron productos activos en registro; ejecutando limpieza de residuos.' "
        + "}; "
        + f"Invoke-OfficeDeepCleanup -DetectedInstallationPaths $installPaths -BackupRoot '{backup_root}' -Logger $ezLogger -Confirm:$false -WhatIf:$sim"
    )
    _run_ps_command(ps_script, log)
    return f"Desinstalación y limpieza profunda de Office finalizada ({mode_label})."
