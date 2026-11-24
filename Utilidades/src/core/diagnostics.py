"""Módulo de diagnóstico de hardware y estabilidad de Windows (S.M.A.R.T., Batería, RAM y BSOD)."""

import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def _run_ps_json(ps_one_liner: str) -> tuple[bool, Any, str]:
    """Ejecuta un comando PowerShell de una sola línea y parsea su salida JSON."""
    res = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_one_liner],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )
    if res.returncode != 0:
        err = res.stderr.strip() or res.stdout.strip() or f"Código {res.returncode}"
        return False, None, err
    raw = res.stdout.strip()
    if not raw:
        return True, [], ""
    try:
        return True, json.loads(raw), ""
    except json.JSONDecodeError as exc:
        return False, None, f"Error al parsear JSON de PowerShell: {exc}"


def _format_capacity(size_bytes: Any) -> str:
    """Formatea una capacidad en bytes a GB o TB legibles."""
    try:
        size = int(size_bytes)
    except (TypeError, ValueError):
        return "N/D"
    if size <= 0:
        return "N/D"
    tb = 1024 ** 4
    gb = 1024 ** 3
    if size >= tb:
        return f"{size / tb:.2f} TB"
    return f"{size / gb:.1f} GB"


def get_smart_health() -> tuple[bool, str]:
    """Consulta discos físicos internos y contadores S.M.A.R.T. vía PowerShell."""
    ps_cmd = (
        "Get-PhysicalDisk | Where-Object { $_.BusType -ne 'USB' } | ForEach-Object { "
        "$rel = $_ | Get-StorageReliabilityCounter -ErrorAction SilentlyContinue; "
        "[PSCustomObject]@{ "
        "Model=$_.FriendlyName; MediaType=$_.MediaType.ToString(); "
        "Bus=$_.BusType.ToString(); Size=$_.Size; "
        "OpStatus=$_.OperationalStatus.ToString(); Health=$_.HealthStatus.ToString(); "
        "Temp=$rel.Temperature; ReadErrors=$rel.ReadErrorsTotal; WriteErrors=$rel.WriteErrorsTotal } "
        "} | ConvertTo-Json -Compress"
    )
    ok, data, err = _run_ps_json(ps_cmd)
    if not ok:
        return False, f"Error al consultar discos S.M.A.R.T.: {err}"

    disks = [data] if isinstance(data, dict) else (data or [])
    if not disks:
        return True, "No se detectaron discos físicos internos."

    lines: list[str] = []
    for d in disks:
        model = d.get("Model") or "Desconocido"
        media = d.get("MediaType") or ""
        bus = d.get("Bus") or "-"
        kind = f"{media}/{bus}" if media and media != "Unspecified" else bus
        cap = _format_capacity(d.get("Size"))
        op = d.get("OpStatus") or "-"
        health = d.get("Health") or "-"
        raw_temp = d.get("Temp")
        temp = f"{raw_temp} °C" if raw_temp not in (None, 0) else "N/D"

        read_err = int(d.get("ReadErrors") or 0)
        write_err = int(d.get("WriteErrors") or 0)
        err_part = f" | Errores R/W: {read_err}/{write_err}" if (read_err > 0 or write_err > 0) else ""

        lines.append(f"• {model} ({kind}, {cap}) | Estado: {health} ({op}) | Temp: {temp}{err_part}")

    return True, "\n".join(lines)


def get_fixed_partitions() -> tuple[bool, str]:
    """Consulta el espacio libre y total de las particiones fijas (DriveType = 3)."""
    ps_cmd = (
        "Get-CimInstance -ClassName Win32_LogicalDisk -Filter 'DriveType=3' | "
        "Select-Object DeviceID, VolumeName, Size, FreeSpace | ConvertTo-Json -Compress"
    )
    ok, data, err = _run_ps_json(ps_cmd)
    if not ok:
        return False, f"Error al consultar particiones: {err}"

    volumes = [data] if isinstance(data, dict) else (data or [])
    if not volumes:
        return True, "No se detectaron particiones fijas."

    lines: list[str] = []
    for v in volumes:
        drive = v.get("DeviceID") or "?"
        label = (v.get("VolumeName") or "").strip()
        name = f"{drive} ({label})" if label else drive
        size = int(v.get("Size") or 0)
        free = int(v.get("FreeSpace") or 0)
        pct_free = f"{(free / size) * 100:.1f}%" if size > 0 else "N/D"
        lines.append(f"• {name}: {_format_capacity(free)} libre / {_format_capacity(size)} total ({pct_free} libre)")

    return True, "\n".join(lines)


def get_battery_health() -> tuple[bool, str]:
    """Detecta batería vía Win32_Battery y extrae métricas de powercfg /batteryreport."""
    ok, data, err = _run_ps_json(
        "Get-CimInstance -ClassName Win32_Battery -ErrorAction SilentlyContinue | "
        "Select-Object Name, EstimatedChargeRemaining | ConvertTo-Json -Compress"
    )
    if not ok:
        return False, f"Error al consultar Win32_Battery: {err}"

    batteries = [data] if isinstance(data, dict) else (data or [])
    if not batteries:
        return True, "Equipo de escritorio o sin batería detectada."

    report_path = Path(tempfile.gettempdir()) / "battery.html"
    res = subprocess.run(
        ["powercfg", "/batteryreport", "/output", str(report_path)],
        capture_output=True,
        text=True,
        encoding="cp850",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )
    if res.returncode != 0 or not report_path.exists():
        charge = batteries[0].get("EstimatedChargeRemaining", "N/D")
        return True, f"Batería detectada (Carga: {charge}%). No se pudo generar batteryreport."

    html = report_path.read_text(encoding="utf-8", errors="replace")
    design_m = re.search(r"DESIGN CAPACITY.*?<td>([\d.,]+\s*mWh)</td>", html, re.IGNORECASE | re.DOTALL)
    full_m = re.search(r"FULL CHARGE CAPACITY.*?<td>([\d.,]+\s*mWh)</td>", html, re.IGNORECASE | re.DOTALL)
    cycles_m = re.search(r"CYCLE COUNT.*?<td>(\d+|-)</td>", html, re.IGNORECASE | re.DOTALL)

    design = design_m.group(1) if design_m else "N/D"
    full = full_m.group(1) if full_m else "N/D"
    cycles = cycles_m.group(1) if cycles_m else "N/D"
    return True, f"Diseño: {design} | Carga completa: {full} | Ciclos: {cycles} (Reporte: {report_path})"


def get_system_stability() -> tuple[bool, str]:
    """Obtiene equipo, versión de Windows, Uptime, RAM y eventos críticos BSOD/Kernel-Power (30 días)."""
    ps_cmd = (
        "$os = Get-CimInstance Win32_OperatingSystem; "
        "$up = (Get-Date) - $os.LastBootUpTime; "
        "$since = (Get-Date).AddDays(-30); "
        "$bsod = @(Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-WER-SystemErrorReporting'; Id=1001; StartTime=$since} -ErrorAction SilentlyContinue).Count; "
        "$kp = @(Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Kernel-Power'; Id=41; StartTime=$since} -ErrorAction SilentlyContinue).Count; "
        "[PSCustomObject]@{ "
        "Host=$env:COMPUTERNAME; Caption=$os.Caption; Version=$os.Version; "
        "UptimeDays=[math]::Round($up.TotalDays,1); "
        "TotalRAM_GB=[math]::Round($os.TotalVisibleMemorySize/1MB,2); "
        "FreeRAM_GB=[math]::Round($os.FreePhysicalMemory/1MB,2); "
        "BSOD=$bsod; KernelPower=$kp "
        "} | ConvertTo-Json -Compress"
    )
    ok, data, err = _run_ps_json(ps_cmd)
    if not ok or not isinstance(data, dict):
        return False, f"Error al consultar estabilidad del sistema: {err}"

    total_ram = float(data.get("TotalRAM_GB", 0))
    free_ram = float(data.get("FreeRAM_GB", 0))
    used_ram = round(max(0.0, total_ram - free_ram), 2)

    lines = [
        f"Equipo: {data.get('Host', os.environ.get('COMPUTERNAME', 'N/D'))}",
        f"Sistema: {data.get('Caption', 'Windows')} (v{data.get('Version', 'N/D')})",
        f"Uptime: {data.get('UptimeDays', 0)} días",
        f"RAM: {used_ram} GB usada / {total_ram} GB total ({free_ram} GB libre)",
        f"Eventos críticos (30 días): BSOD (ID 1001) = {data.get('BSOD', 0)} | Kernel-Power (ID 41) = {data.get('KernelPower', 0)}",
    ]
    return True, "\n".join(lines)


def export_diagnostic_report(path: str, results: dict[str, str]) -> tuple[bool, str]:
    """Exporta un reporte de diagnóstico legible en formato .txt."""
    try:
        computer = os.environ.get("COMPUTERNAME", "EQUIPO")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = [
            f"=== REPORTE DE DIAGNÓSTICO DE HARDWARE Y SISTEMA ===",
            f"Equipo: {computer}",
            f"Fecha:  {now}",
            "",
            "--- 1. DISCOS FÍSICOS (S.M.A.R.T.) ---",
            results.get("smart", "Sin datos."),
            "",
            "--- 1b. PARTICIONES FIJAS ---",
            results.get("partitions", "Sin datos."),
            "",
            "--- 2. SALUD DE BATERÍA ---",
            results.get("battery", "Sin datos."),
            "",
            "--- 3. ESTABILIDAD, RAM Y EVENTOS CRÍTICOS ---",
            results.get("stability", "Sin datos."),
            "",
        ]
        Path(path).write_text("\n".join(content), encoding="utf-8")
        return True, f"Reporte exportado correctamente en: {path}"
    except OSError as exc:
        return False, f"Error al exportar reporte: {exc}"
