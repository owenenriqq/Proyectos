"""Módulo de reparación de Shell, caché de iconos, paquetes AppX y mantenimiento rápido."""

import os
import shutil
import subprocess
import time
import winreg
from pathlib import Path
from typing import Sequence

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
EXPLORER_REG_PATH = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer"
MAX_CACHED_ICONS_KEY = "Max Cached Icons"


def _run_silent(command: Sequence[str], encoding: str = "utf-8") -> subprocess.CompletedProcess[str]:
    """Ejecuta un comando del sistema sin ventana de consola visible."""
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding=encoding,
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )


def rebuild_icon_cache() -> tuple[bool, str]:
    """Detiene explorer.exe, limpia la caché de iconos y reinicia explorer.exe."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return False, "No se pudo resolver la variable de entorno %LOCALAPPDATA%."

    # 1. Detener explorer.exe de forma silenciosa
    kill_res = _run_silent(["taskkill", "/F", "/IM", "explorer.exe"], encoding="cp850")
    if kill_res.returncode not in (0, 128):
        err = kill_res.stderr.strip() or kill_res.stdout.strip()
        return False, f"No se pudo detener explorer.exe: {err}"

    time.sleep(0.6)

    # 2. Eliminar archivos de caché de iconos
    removed_count = 0
    errors: list[str] = []

    icon_db = Path(local_app_data) / "IconCache.db"
    if icon_db.exists():
        try:
            icon_db.unlink()
            removed_count += 1
        except OSError as exc:
            errors.append(f"{icon_db.name}: {exc}")

    explorer_cache_dir = Path(local_app_data) / "Microsoft" / "Windows" / "Explorer"
    if explorer_cache_dir.exists():
        for cache_file in explorer_cache_dir.glob("iconcache*"):
            try:
                cache_file.unlink()
                removed_count += 1
            except OSError as exc:
                errors.append(f"{cache_file.name}: {exc}")

    # 3. Reiniciar explorer.exe siempre para no dejar al usuario sin shell
    try:
        subprocess.Popen(["explorer.exe"], creationflags=CREATE_NO_WINDOW)
    except OSError as exc:
        return False, f"Caché limpiada ({removed_count} archivos), pero falló al reiniciar explorer.exe: {exc}"

    if errors:
        return True, f"Explorer reiniciado. {removed_count} archivos eliminados; omitidos: {'; '.join(errors)}"
    return True, f"Caché de iconos reconstruida ({removed_count} archivos eliminados) y explorer.exe reiniciado."


def get_max_cached_icons() -> tuple[bool, str]:
    """Lee el valor actual de Max Cached Icons en el Registro."""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, EXPLORER_REG_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, MAX_CACHED_ICONS_KEY)
            return True, f"Valor actual en Registro: {value}"
    except FileNotFoundError:
        return False, "Valor actual en Registro: No definido (predeterminado de Windows)."
    except OSError as exc:
        return False, f"Error al leer Registro: {exc}"


def set_max_cached_icons(value: str = "4096") -> tuple[bool, str]:
    """Establece Max Cached Icons en HKLM como REG_SZ previa lectura del valor actual."""
    _, current_msg = get_max_cached_icons()
    try:
        with winreg.CreateKeyEx(
            winreg.HKEY_LOCAL_MACHINE,
            EXPLORER_REG_PATH,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, MAX_CACHED_ICONS_KEY, 0, winreg.REG_SZ, value)
        return True, f"{current_msg} -> Actualizado a '{value}' (REG_SZ)."
    except OSError as exc:
        return False, f"No se pudo escribir '{MAX_CACHED_ICONS_KEY}' en el Registro: {exc}"


def reregister_appx_packages() -> tuple[bool, str]:
    """Verifica/inicia el servicio MpsSvc y re-registra los paquetes AppX para todos los usuarios."""
    sc_res = _run_silent(["sc", "query", "MpsSvc"], encoding="cp850")
    if "RUNNING" not in sc_res.stdout.upper():
        start_res = _run_silent(["net", "start", "MpsSvc"], encoding="cp850")
        if start_res.returncode != 0:
            err = start_res.stderr.strip() or start_res.stdout.strip()
            return False, f"El servicio MpsSvc (Firewall) está detenido y no pudo iniciarse: {err}"

    ps_cmd = (
        "$ErrorActionPreference = 'SilentlyContinue'; "
        "Get-AppxPackage -AllUsers | ForEach-Object { "
        "Add-AppxPackage -DisableDevelopmentMode -Register \"$($_.InstallLocation)\\AppXManifest.xml\" "
        "}"
    )
    res = _run_silent(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd], encoding="utf-8")
    if res.returncode != 0:
        err = res.stderr.strip() or res.stdout.strip() or f"Código {res.returncode}"
        return False, f"Error al re-registrar paquetes AppX: {err}"

    return True, "Paquetes AppX re-registrados correctamente (servicio MpsSvc verificado)."


def _clear_directory_contents(directory: Path) -> tuple[int, int]:
    """Elimina archivos y subcarpetas dentro de un directorio ignorando elementos en uso."""
    removed = 0
    skipped = 0
    if not directory.exists():
        return 0, 0
    for item in directory.iterdir():
        try:
            if item.is_dir() and not item.is_symlink():
                shutil.rmtree(item, ignore_errors=False)
            else:
                item.unlink()
            removed += 1
        except OSError:
            skipped += 1
    return removed, skipped


def clean_temp_and_update_cache(clean_wu_cache: bool = False) -> tuple[bool, str]:
    """Limpia %TEMP%, C:\\Windows\\Temp y opcionalmente la caché de Windows Update."""
    total_removed = 0
    total_skipped = 0

    user_temp = os.environ.get("TEMP") or os.environ.get("TMP")
    win_root = os.environ.get("SystemRoot", r"C:\Windows")
    targets = [Path(win_root) / "Temp"]
    if user_temp:
        targets.insert(0, Path(user_temp))

    for target in targets:
        rem, skip = _clear_directory_contents(target)
        total_removed += rem
        total_skipped += skip

    if not clean_wu_cache:
        return True, (
            f"Temporales limpiados ({total_removed} elementos eliminados, "
            f"{total_skipped} en uso omitidos)."
        )

    # Detener servicios de Windows Update antes de vaciar SoftwareDistribution\Download
    for svc in ("wuauserv", "bits"):
        _run_silent(["net", "stop", svc], encoding="cp850")

    wu_download = Path(win_root) / "SoftwareDistribution" / "Download"
    wu_rem, wu_skip = _clear_directory_contents(wu_download)
    total_removed += wu_rem
    total_skipped += wu_skip

    start_errors: list[str] = []
    for svc in ("bits", "wuauserv"):
        res = _run_silent(["net", "start", svc], encoding="cp850")
        if res.returncode != 0:
            out = (res.stdout or res.stderr or "").strip()
            # Código 2 o texto "ya se ha iniciado" no es fallo real
            if "ya se ha iniciado" not in out.lower() and "already been started" not in out.lower():
                start_errors.append(f"{svc}: {out}")

    if start_errors:
        return False, (
            f"Temporales y caché de Windows Update limpiados ({total_removed} eliminados, "
            f"{total_skipped} omitidos), pero hubo errores al reiniciar servicios: {'; '.join(start_errors)}"
        )

    return True, (
        f"Temporales y caché de Windows Update limpiados ({total_removed} elementos eliminados, "
        f"{total_skipped} en uso omitidos; servicios reiniciados)."
    )


def restart_print_spooler() -> tuple[bool, str]:
    """Detiene Spooler, vacía la cola de impresión (PRINTERS) y reinicia el servicio."""
    win_root = os.environ.get("SystemRoot", r"C:\Windows")
    printers_dir = Path(win_root) / "System32" / "spool" / "PRINTERS"

    stop_res = _run_silent(["net", "stop", "Spooler"], encoding="cp850")
    if stop_res.returncode != 0:
        sc_res = _run_silent(["sc", "query", "Spooler"], encoding="cp850")
        if "STOPPED" not in sc_res.stdout.upper():
            err = stop_res.stderr.strip() or stop_res.stdout.strip()
            return False, f"No se pudo detener la cola de impresión (Spooler): {err}"

    removed, skipped = _clear_directory_contents(printers_dir)

    start_res = _run_silent(["net", "start", "Spooler"], encoding="cp850")
    if start_res.returncode != 0:
        err = start_res.stderr.strip() or start_res.stdout.strip()
        return False, f"Cola vaciada ({removed} eliminados), pero falló al iniciar Spooler: {err}"

    return True, f"Cola de impresión reiniciada ({removed} archivos eliminados, {skipped} omitidos)."
