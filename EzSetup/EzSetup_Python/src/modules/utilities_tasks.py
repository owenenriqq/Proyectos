"""Adaptadores de las utilidades de Windows para ejecución asíncrona mediante TaskWorker."""

from __future__ import annotations

from typing import Any, Callable

from src.modules.utilities import shell_repair, system_repair, system_tweaks

LogCallback = Callable[[str], None]


def _noop_log(_: str) -> None:
    """Callback por defecto cuando no se provee logger."""


def _unwrap_result(ok: bool, msg: str, log: LogCallback) -> str:
    """Traduce el resultado (ok, msg) al contrato de TaskWorker (str o excepción)."""
    if not ok:
        raise RuntimeError(msg)
    for line in msg.splitlines():
        if line.strip():
            log(f"[OK] {line}")
    return msg


def task_dism_scan(_config: Any, log: LogCallback = _noop_log) -> str:
    """Ejecuta DISM /ScanHealth con salida en vivo."""
    ok, msg = system_repair.dism_scan_health(log)
    return _unwrap_result(ok, msg, log)


def task_dism_restore(_config: Any, log: LogCallback = _noop_log) -> str:
    """Ejecuta DISM /RestoreHealth /NoRestart con salida en vivo."""
    ok, msg = system_repair.dism_restore_health(log)
    return _unwrap_result(ok, msg, log)


def task_dism_cleanup(_config: Any, log: LogCallback = _noop_log) -> str:
    """Ejecuta DISM /StartComponentCleanup con salida en vivo."""
    ok, msg = system_repair.dism_component_cleanup(log)
    return _unwrap_result(ok, msg, log)


def task_sfc_scannow(_config: Any, log: LogCallback = _noop_log) -> str:
    """Ejecuta sfc /scannow con salida en vivo."""
    ok, msg = system_repair.sfc_scannow(log)
    return _unwrap_result(ok, msg, log)


def task_full_repair(_config: Any, log: LogCallback = _noop_log) -> str:
    """Ejecuta la secuencia completa DISM + SFC + ComponentCleanup."""
    ok, msg = system_repair.run_full_repair(log)
    return _unwrap_result(ok, msg, log)


def task_hibernation_status(_config: Any, log: LogCallback = _noop_log) -> str:
    """Consulta el estado actual de hibernación e Inicio Rápido."""
    _, msg = system_tweaks.get_hibernation_status()
    log(f"[INFO] {msg}")
    return msg


def task_hibernation_off(_config: Any, log: LogCallback = _noop_log) -> str:
    """Desactiva la hibernación y el Inicio Rápido."""
    ok, msg = system_tweaks.set_hibernation(False, include_fast_boot=False)
    return _unwrap_result(ok, msg, log)


def task_hibernation_on(_config: Any, log: LogCallback = _noop_log) -> str:
    """Activa la hibernación sin alterar el Inicio Rápido."""
    ok, msg = system_tweaks.set_hibernation(True, include_fast_boot=False)
    return _unwrap_result(ok, msg, log)


def task_hibernation_on_fastboot(_config: Any, log: LogCallback = _noop_log) -> str:
    """Activa la hibernación junto con el Inicio Rápido (HiberbootEnabled = 1)."""
    ok, msg = system_tweaks.set_hibernation(True, include_fast_boot=True)
    return _unwrap_result(ok, msg, log)


def task_create_local_user(
    _config: Any,
    username: str,
    password: str,
    full_name: str = "",
    add_to_admins: bool = False,
    log: LogCallback = _noop_log,
) -> str:
    """Crea una cuenta local en Windows mediante PowerShell."""
    log(f"[INFO] Creando usuario local '{username.strip()}'...")
    ok, msg = system_tweaks.create_local_user(
        username=username,
        password=password,
        full_name=full_name,
        add_to_admins=add_to_admins,
    )
    return _unwrap_result(ok, msg, log)


def task_get_max_icons(_config: Any, log: LogCallback = _noop_log) -> str:
    """Consulta el valor de Max Cached Icons en el Registro."""
    _, msg = shell_repair.get_max_cached_icons()
    log(f"[INFO] {msg}")
    return msg


def task_set_max_icons(_config: Any, log: LogCallback = _noop_log) -> str:
    """Establece Max Cached Icons en 4096 en HKLM."""
    ok, msg = shell_repair.set_max_cached_icons("4096")
    return _unwrap_result(ok, msg, log)


def task_rebuild_icon_cache(_config: Any, log: LogCallback = _noop_log) -> str:
    """Reconstruye la caché de iconos y reinicia explorer.exe."""
    log("[INFO] Reconstruyendo caché de iconos de Windows...")
    ok, msg = shell_repair.rebuild_icon_cache()
    return _unwrap_result(ok, msg, log)


def task_reregister_appx(_config: Any, log: LogCallback = _noop_log) -> str:
    """Verifica MpsSvc y re-registra paquetes AppX para todos los usuarios."""
    log("[INFO] Re-registrando paquetes AppX (verificando MpsSvc)...")
    ok, msg = shell_repair.reregister_appx_packages()
    return _unwrap_result(ok, msg, log)


def task_clean_temp(_config: Any, log: LogCallback = _noop_log) -> str:
    """Limpia carpetas temporales %TEMP% y C:\\Windows\\Temp."""
    log("[INFO] Limpiando archivos temporales del usuario y del sistema...")
    ok, msg = shell_repair.clean_temp_and_update_cache(clean_wu_cache=False)
    return _unwrap_result(ok, msg, log)


def task_clean_temp_wu(_config: Any, log: LogCallback = _noop_log) -> str:
    """Limpia temporales y la caché de descargas de Windows Update."""
    log("[INFO] Limpiando temporales y caché de Windows Update...")
    ok, msg = shell_repair.clean_temp_and_update_cache(clean_wu_cache=True)
    return _unwrap_result(ok, msg, log)


def task_restart_spooler(_config: Any, log: LogCallback = _noop_log) -> str:
    """Detiene Spooler, vacía trabajos atascados y reinicia el servicio."""
    log("[INFO] Reiniciando cola de impresión (Spooler)...")
    ok, msg = shell_repair.restart_print_spooler()
    return _unwrap_result(ok, msg, log)


UTILITIES_TASK_REGISTRY: dict[str, Callable[..., str]] = {
    "util_dism_scan": task_dism_scan,
    "util_dism_restore": task_dism_restore,
    "util_dism_cleanup": task_dism_cleanup,
    "util_sfc_scannow": task_sfc_scannow,
    "util_full_repair": task_full_repair,
    "util_hibernation_status": task_hibernation_status,
    "util_hibernation_off": task_hibernation_off,
    "util_hibernation_on": task_hibernation_on,
    "util_hibernation_on_fastboot": task_hibernation_on_fastboot,
    "util_get_max_icons": task_get_max_icons,
    "util_set_max_icons": task_set_max_icons,
    "util_rebuild_icon_cache": task_rebuild_icon_cache,
    "util_reregister_appx": task_reregister_appx,
    "util_clean_temp": task_clean_temp,
    "util_clean_temp_wu": task_clean_temp_wu,
    "util_restart_spooler": task_restart_spooler,
}
