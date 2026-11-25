"""Relevamiento de hardware/SO vía WMI y registro de inventario administrativo."""

from __future__ import annotations

import csv
import io
import math
from pathlib import Path
import socket
import subprocess
from typing import Any, Callable

from src.config import AppConfig, validate_unc_host

LogCallback = Callable[[str], None]

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def _noop_log(_: str) -> None:
    """Callback por defecto cuando no se provee logger."""


def _decode_console_bytes(raw: bytes) -> str:
    """Decodifica bytes de consola Windows soportando UTF-8, OEM cp850 y cp1252."""
    if not raw:
        return ""
    for enc in ("utf-8", "cp850", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("cp850", errors="replace")


def get_disks_powershell() -> str:
    """Consulta discos físicos vía PowerShell (Get-PhysicalDisk) sin ventana visible."""
    ps_cmd = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "Get-PhysicalDisk | Select-Object MediaType, BusType, Size | ConvertTo-Csv -NoTypeInformation"
    )
    try:
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True,
            text=False,
            shell=False,
            creationflags=_CREATE_NO_WINDOW,
            check=False,
        )
        if res.returncode != 0:
            return "Error discos"

        stdout = _decode_console_bytes(res.stdout or b"").strip()
        if not stdout:
            return "Sin discos detectados"

        reader = csv.reader(io.StringIO(stdout))
        rows = list(reader)
        discos_resumen: list[str] = []
        for parts in rows[1:]:
            if len(parts) < 3:
                continue
            media_type = parts[0].strip()
            bus_type = parts[1].strip()
            try:
                size_gb = int(int(parts[2].strip()) / (1024 ** 3))
            except ValueError:
                continue

            tipo_final = "HDD"
            if media_type == "SSD":
                tipo_final = "NVMe" if bus_type == "NVMe" else "SSD SATA"
            elif bus_type == "NVMe":
                tipo_final = "NVMe"

            discos_resumen.append(f"{size_gb}GB {tipo_final}")

        return " + ".join(discos_resumen) if discos_resumen else "Sin discos detectados"
    except Exception:
        return "Error discos"


def analyze_ram(wmi_client: Any) -> str:
    """Calcula la memoria RAM total en GB, su factor de forma y ranuras ocupadas."""
    ram_bytes = 0
    modulos = wmi_client.Win32_PhysicalMemory()
    slots_usados = len(modulos)
    tipos: set[str] = set()

    for modulo in modulos:
        ram_bytes += int(modulo.Capacity)
        ff = getattr(modulo, "FormFactor", 0)
        if ff == 8:
            tipos.add("UDIMM")
        elif ff == 12:
            tipos.add("SODIMM")
        elif ff == 0:
            tipos.add("Integrada")
        else:
            tipos.add("DIMM")

    ram_total_gb = math.ceil(ram_bytes / (1024 ** 3))
    tipo_str = "/".join(sorted(tipos)) if tipos else "Integrada"
    detalle = f"{tipo_str} - {slots_usados} ranuras" if slots_usados > 0 else "Integrada"
    return f"{ram_total_gb} GB ({detalle})"


def collect_hardware_info(log: LogCallback = _noop_log) -> dict[str, str]:
    """Releva equipo, CPU, RAM, discos y sistema operativo inicializando COM en el hilo."""
    import pythoncom
    import wmi

    log("[INFO] Iniciando relevamiento de hardware y sistema operativo (WMI)...")
    pythoncom.CoInitialize()
    try:
        client = wmi.WMI()
        hostname = socket.gethostname()

        procs = client.Win32_Processor()
        cpu = procs[0].Name.strip() if procs else "Desconocido"
        log(f"[INFO] Equipo: {hostname} | CPU: {cpu}")

        ram_info = analyze_ram(client)
        log(f"[INFO] RAM detectada: {ram_info}")

        discos_info = get_disks_powershell()
        log(f"[INFO] Discos detectados: {discos_info}")

        os_list = client.Win32_OperatingSystem()
        so = os_list[0].Caption.strip() if os_list else "Windows"
        log(f"[INFO] Sistema Operativo: {so}")

        return {
            "hostname": hostname,
            "cpu": cpu,
            "ram": ram_info,
            "disks": discos_info,
            "os": so,
        }
    finally:
        pythoncom.CoUninitialize()


def format_hardware_preview(hw: dict[str, str]) -> str:
    """Formatea un resumen legible del hardware relevado para la vista previa del diálogo."""
    return (
        f"Equipo: {hw.get('hostname', 'N/D')}\n"
        f"SO:     {hw.get('os', 'N/D')}\n"
        f"CPU:    {hw.get('cpu', 'N/D')}\n"
        f"RAM:    {hw.get('ram', 'N/D')}\n"
        f"Discos: {hw.get('disks', 'N/D')}"
    )


def format_inventory_record(admin_data: dict[str, str], hw: dict[str, str]) -> str:
    """Construye la línea formateada compatible con el archivo centralizado Inventario.txt."""
    obs_raw = str(admin_data.get("obs", ""))
    obs_clean = obs_raw.replace("\r\n", " | ").replace("\n", " | ").strip()

    return (
        f"AD: {admin_data.get('ad', '')} | "
        f"Correo: {admin_data.get('correo', '')} | "
        f"Equipo: {hw.get('hostname', '')} | "
        f"Puesto: {admin_data.get('puesto', '')} | "
        f"Antigüedad: {admin_data.get('antiguedad', '')} | "
        f"Depto: {admin_data.get('area', '')} | "
        f"Propiedad: {admin_data.get('propiedad', '')} | "
        f"Compra: {admin_data.get('compra', '')} | "
        f"CPU/GPU: {hw.get('cpu', '')} | "
        f"RAM: {hw.get('ram', '')} | "
        f"Discos: {hw.get('disks', '')} | "
        f"SO: {hw.get('os', '')} | "
        f"Obs: {obs_clean}\n"
        f"{'-' * 150}\n"
    )


def save_inventory_record(
    config: AppConfig,
    admin_data: dict[str, str],
    hw: dict[str, str] | None = None,
    log: LogCallback = _noop_log,
) -> str:
    """Releva hardware (si falta) y guarda el registro en la ruta UNC configurada."""
    inv_cfg = config.get_inventory_config()
    network_dir = str(inv_cfg["network_dir"])
    output_filename = str(inv_cfg["output_filename"])

    validate_unc_host(network_dir, config.get_allowed_unc_hosts())

    hw_data = hw if hw is not None else collect_hardware_info(log=log)
    dir_path = Path(network_dir)
    if not dir_path.is_dir():
        raise FileNotFoundError(
            f"No se pudo acceder a la ruta de inventario: {network_dir}"
        )

    dest_file = dir_path / output_filename
    record = format_inventory_record(admin_data, hw_data)

    try:
        with open(dest_file, mode="a", encoding="utf-8") as fh:
            fh.write(record)
    except PermissionError as exc:
        raise PermissionError(
            f"El archivo '{output_filename}' está abierto o sin permisos de escritura."
        ) from exc

    log(f"[OK] Registro de inventario guardado en: {dest_file}")
    return f"Guardado correctamente en {dest_file}"


def export_inventory_record_local(
    dest_path: Path,
    admin_data: dict[str, str],
    hw: dict[str, str],
) -> str:
    """Exporta o anexa el registro de inventario a un archivo local en UTF-8 sin BOM."""
    record = format_inventory_record(admin_data, hw)
    with open(dest_path, mode="a", encoding="utf-8") as fh:
        fh.write(record)
    return f"Registro exportado localmente en: {dest_path}"
