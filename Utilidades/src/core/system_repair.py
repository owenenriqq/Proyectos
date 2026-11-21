"""Módulo de reparación de integridad de Windows (DISM y SFC) con streaming en vivo."""

import re
import subprocess
from typing import Callable, Optional, Sequence

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
_PERCENT_RE = re.compile(r"(\d{1,3}(?:[.,]\d+)?)\s*%")


def _decode_console_bytes(raw: bytes) -> str:
    """Decodifica bytes de consola Windows soportando UTF-16LE (sfc), UTF-8 y OEM cp850."""
    if not raw:
        return ""
    if b"\x00" in raw:
        try:
            return raw.decode("utf-16le", errors="replace").replace("\x00", "")
        except UnicodeDecodeError:
            pass
    for enc in ("utf-8", "cp850", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("cp850", errors="replace")


def _run_streaming(
    command: Sequence[str],
    log_cb: Callable[[str], None],
    progress_cb: Optional[Callable[[int], None]] = None,
) -> tuple[int, str]:
    """Ejecuta un comando del sistema transmitiendo su salida línea a línea."""
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW,
    )
    lines: list[str] = []
    assert proc.stdout is not None

    for raw_line in iter(proc.stdout.readline, b""):
        text = _decode_console_bytes(raw_line).strip()
        if not text:
            continue
        lines.append(text)
        log_cb(text)
        if progress_cb is not None:
            match = _PERCENT_RE.search(text)
            if match:
                try:
                    pct = int(float(match.group(1).replace(",", ".")))
                    progress_cb(max(0, min(100, pct)))
                except ValueError:
                    pass

    proc.stdout.close()
    returncode = proc.wait()
    return returncode, "\n".join(lines)


def dism_scan_health(
    log_cb: Callable[[str], None],
    progress_cb: Optional[Callable[[int], None]] = None,
) -> tuple[bool, str]:
    """Ejecuta DISM /ScanHealth e interpreta si el almacén está sano o reparable."""
    if progress_cb:
        progress_cb(-1)
    log_cb("[DISM] Iniciando análisis de integridad (/ScanHealth)...")
    code, output = _run_streaming(
        ["DISM.exe", "/Online", "/Cleanup-Image", "/ScanHealth"],
        log_cb,
        progress_cb,
    )
    lower = output.lower()
    if code == 0:
        if "reparable" in lower or "repairable" in lower:
            return True, "DISM /ScanHealth: se detectó daño reparable en el almacén de componentes."
        return True, "DISM /ScanHealth: el almacén de componentes está íntegro."
    return False, f"DISM /ScanHealth finalizó con código {code}."


def dism_restore_health(
    log_cb: Callable[[str], None],
    progress_cb: Optional[Callable[[int], None]] = None,
) -> tuple[bool, str]:
    """Ejecuta DISM /RestoreHealth /NoRestart con reporte de porcentaje en vivo."""
    if progress_cb:
        progress_cb(0)
    log_cb("[DISM] Iniciando reparación del almacén (/RestoreHealth /NoRestart)...")
    code, _ = _run_streaming(
        ["DISM.exe", "/Online", "/Cleanup-Image", "/RestoreHealth", "/NoRestart"],
        log_cb,
        progress_cb,
    )
    if code == 0:
        return True, "DISM /RestoreHealth completado correctamente."
    return False, f"DISM /RestoreHealth finalizó con errores (código {code})."


def dism_component_cleanup(
    log_cb: Callable[[str], None],
    progress_cb: Optional[Callable[[int], None]] = None,
) -> tuple[bool, str]:
    """Ejecuta DISM /StartComponentCleanup para consolidar componentes obsoletos."""
    if progress_cb:
        progress_cb(0)
    log_cb("[DISM] Iniciando limpieza de componentes (/StartComponentCleanup)...")
    code, _ = _run_streaming(
        ["DISM.exe", "/Online", "/Cleanup-Image", "/StartComponentCleanup"],
        log_cb,
        progress_cb,
    )
    if code == 0:
        return True, "DISM /StartComponentCleanup completado correctamente."
    return False, f"DISM /StartComponentCleanup finalizó con código {code}."


def sfc_scannow(
    log_cb: Callable[[str], None],
    progress_cb: Optional[Callable[[int], None]] = None,
) -> tuple[bool, str]:
    """Ejecuta sfc /scannow y evalúa los códigos de retorno estándar (0, 1, 2, 3)."""
    if progress_cb:
        progress_cb(0)
    log_cb("[SFC] Iniciando verificación de archivos de sistema (sfc /scannow)...")
    code, _ = _run_streaming(["sfc.exe", "/scannow"], log_cb, progress_cb)
    if code == 0:
        return True, "SFC /scannow: no se encontraron infracciones de integridad (código 0)."
    if code == 1:
        return True, "SFC /scannow: se encontraron y repararon archivos dañados (código 1)."
    if code == 2:
        return False, "SFC /scannow: no pudo completar la operación solicitada (código 2)."
    if code == 3:
        return False, "SFC /scannow: encontró archivos dañados pero no pudo reparar algunos (código 3)."
    return False, f"SFC /scannow finalizó con código inesperado {code}."


def run_full_repair(
    log_cb: Callable[[str], None],
    progress_cb: Optional[Callable[[int], None]] = None,
) -> tuple[bool, str]:
    """Ejecuta la secuencia guiada: ScanHealth -> RestoreHealth (si aplica) -> SFC -> Cleanup."""
    log_cb("=== Iniciando Reparación Completa Automática ===")

    ok_scan, msg_scan = dism_scan_health(log_cb, progress_cb)
    if not ok_scan:
        return False, f"Secuencia detenida en ScanHealth: {msg_scan}"

    if "reparable" in msg_scan.lower():
        ok_restore, msg_restore = dism_restore_health(log_cb, progress_cb)
        if not ok_restore:
            return False, f"Secuencia detenida en RestoreHealth: {msg_restore}"
    else:
        log_cb("[DISM] Almacén sano; se omite /RestoreHealth.")

    ok_sfc, msg_sfc = sfc_scannow(log_cb, progress_cb)
    if not ok_sfc:
        return False, f"Secuencia detenida en SFC: {msg_sfc}"

    ok_clean, msg_clean = dism_component_cleanup(log_cb, progress_cb)
    if not ok_clean:
        return False, f"Secuencia detenida en StartComponentCleanup: {msg_clean}"

    return True, "Reparación Completa Automática finalizada con éxito."
