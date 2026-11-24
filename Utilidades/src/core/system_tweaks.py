"""Módulo de ajustes del sistema: hibernación/inicio rápido y cuentas locales."""

import os
import subprocess
import winreg
from typing import Sequence

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
POWER_REG_PATH = r"SYSTEM\CurrentControlSet\Control\Session Manager\Power"
HIBERBOOT_KEY = "HiberbootEnabled"


def _run_silent(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Ejecuta un comando del sistema sin ventana de consola visible."""
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )


def _get_hiberboot_enabled() -> bool | None:
    """Lee el valor DWORD HiberbootEnabled del Registro (Inicio Rápido)."""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, POWER_REG_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, HIBERBOOT_KEY)
            return bool(int(value))
    except (FileNotFoundError, OSError, ValueError):
        return None


def _set_hiberboot_enabled(enabled: bool) -> tuple[bool, str]:
    """Establece HiberbootEnabled (1 o 0) en HKLM."""
    try:
        with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, POWER_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, HIBERBOOT_KEY, 0, winreg.REG_DWORD, 1 if enabled else 0)
        return True, ""
    except OSError as exc:
        return False, f"No se pudo actualizar {HIBERBOOT_KEY}: {exc}"


def get_hibernation_status() -> tuple[bool, str]:
    """Verifica por separado el estado de Hibernación (hiberfil.sys) e Inicio Rápido (HiberbootEnabled)."""
    hiber_exists = os.path.exists(r"C:\hiberfil.sys")
    fast_boot = _get_hiberboot_enabled()

    hiber_txt = "ACTIVA (hiberfil.sys presente)" if hiber_exists else "DESACTIVADA (hiberfil.sys ausente)"
    if fast_boot is True:
        fast_txt = "ACTIVO"
    elif fast_boot is False:
        fast_txt = "DESACTIVADO"
    else:
        fast_txt = "N/D"

    return (hiber_exists or bool(fast_boot)), f"Hibernación: {hiber_txt} | Inicio Rápido: {fast_txt}"


def set_hibernation(enabled: bool, include_fast_boot: bool = False) -> tuple[bool, str]:
    """Activa o desactiva la hibernación y opcionalmente el Inicio Rápido."""
    flag = "on" if enabled else "off"
    res = _run_silent(["powercfg", "-h", flag])

    if res.returncode != 0:
        err = res.stderr.strip() or res.stdout.strip() or f"Código de salida {res.returncode}"
        return False, f"No se pudo cambiar la hibernación ({flag}): {err}"

    if not enabled:
        ok_reg, reg_err = _set_hiberboot_enabled(False)
        if not ok_reg:
            return False, reg_err
    elif include_fast_boot:
        ok_reg, reg_err = _set_hiberboot_enabled(True)
        if not ok_reg:
            return False, reg_err

    _, status_msg = get_hibernation_status()
    return True, f"Operación completada (powercfg -h {flag}). {status_msg}"


def create_local_user(
    username: str,
    password: str,
    full_name: str = "",
    description: str = "Cuenta local creada con Utilidades",
    add_to_admins: bool = False,
) -> tuple[bool, str]:
    """Crea una cuenta de usuario local en Windows mediante PowerShell sin consola visible."""
    clean_user = username.strip()
    if not clean_user:
        return False, "El nombre de usuario no puede estar vacío."
    if any(ch in clean_user for ch in ['"', "'", "\\", "/", ":", ";", "|", "=", ",", "+", "*", "?", "<", ">"]):
        return False, "El nombre de usuario contiene caracteres no permitidos."
    if not password:
        return False, "La contraseña no puede estar vacía."

    safe_full = (full_name.strip() or clean_user).replace("'", "''")
    safe_desc = description.strip().replace("'", "''")
    safe_user = clean_user.replace("'", "''")
    safe_pass = password.replace("'", "''")

    ps_parts = [
        "$ErrorActionPreference = 'Stop'",
        f"$sec = ConvertTo-SecureString '{safe_pass}' -AsPlainText -Force",
        f"New-LocalUser -Name '{safe_user}' -Password $sec -FullName '{safe_full}' -Description '{safe_desc}' | Out-Null",
    ]
    if add_to_admins:
        ps_parts.append("$adminGroup = (Get-LocalGroup -SID 'S-1-5-32-544').Name")
        ps_parts.append(f"Add-LocalGroupMember -Group $adminGroup -Member '{safe_user}'")

    ps_script = "; ".join(ps_parts)

    res = _run_silent(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script])
    if res.returncode != 0:
        err = res.stderr.strip() or res.stdout.strip() or f"Código de salida {res.returncode}"
        return False, f"Error al crear el usuario '{clean_user}': {err}"

    if add_to_admins:
        return True, f"Usuario local '{clean_user}' creado y agregado al grupo Administradores (SID S-1-5-32-544)."
    return True, f"Usuario local '{clean_user}' creado correctamente."
