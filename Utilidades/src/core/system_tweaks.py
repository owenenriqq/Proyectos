"""Módulo de ajustes del sistema: hibernación/inicio rápido y cuentas locales."""

import os
import subprocess
from typing import Sequence

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


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


def get_hibernation_status() -> tuple[bool, str]:
    """Verifica si el archivo de hibernación (C:\\hiberfil.sys) existe actualmente."""
    hiber_exists = os.path.exists(r"C:\hiberfil.sys")
    if hiber_exists:
        return True, "Hibernación / Inicio Rápido: ACTIVO (C:\\hiberfil.sys presente)."
    return False, "Hibernación / Inicio Rápido: DESACTIVADO (C:\\hiberfil.sys ausente)."


def set_hibernation(enabled: bool) -> tuple[bool, str]:
    """Activa o desactiva la hibernación e inicio rápido mediante powercfg."""
    flag = "on" if enabled else "off"
    res = _run_silent(["powercfg", "-h", flag])

    if res.returncode != 0:
        err = res.stderr.strip() or res.stdout.strip() or f"Código de salida {res.returncode}"
        return False, f"No se pudo cambiar la hibernación ({flag}): {err}"

    _, status_msg = get_hibernation_status()
    return True, f"Operación completada (powercfg -h {flag}). {status_msg}"


def create_local_user(
    username: str,
    password: str,
    full_name: str = "",
    description: str = "Cuenta local creada con Utilidades",
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

    ps_script = (
        "$ErrorActionPreference = 'Stop'; "
        f"$sec = ConvertTo-SecureString '{safe_pass}' -AsPlainText -Force; "
        f"New-LocalUser -Name '{safe_user}' -Password $sec -FullName '{safe_full}' -Description '{safe_desc}' | Out-Null"
    )

    res = _run_silent(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script])
    if res.returncode != 0:
        err = res.stderr.strip() or res.stdout.strip() or f"Código de salida {res.returncode}"
        return False, f"Error al crear el usuario '{clean_user}': {err}"

    return True, f"Usuario local '{clean_user}' creado correctamente."
