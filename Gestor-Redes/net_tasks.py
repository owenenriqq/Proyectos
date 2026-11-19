"""Tareas y utilidades de gestión y diagnóstico de redes para Windows 10/11."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass, field
from datetime import datetime
import ipaddress
import json
import os
import re
import socket
import subprocess
import time
from typing import Any, Callable

LogCallback = Callable[[str], None]

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

UAC_PERMISSION_MSG = "Permisos insuficientes. Ejecutá Gestor de Redes como Administrador."

DNS_PRESETS: dict[str, list[str]] = {
    "Automático (DHCP)": [],
    "Cloudflare (1.1.1.1 / 1.0.0.1)": ["1.1.1.1", "1.0.0.1"],
    "Google (8.8.8.8 / 8.8.4.4)": ["8.8.8.8", "8.8.4.4"],
    "Quad9 (9.9.9.9 / 149.112.112.112)": ["9.9.9.9", "149.112.112.112"],
    "OpenDNS (208.67.222.222 / 208.67.220.220)": ["208.67.222.222", "208.67.220.220"],
}

_HOST_PATTERN = re.compile(r"^[A-Za-z0-9.\-:]{1,253}$")

_ACCESS_DENIED_MARKERS = (
    "access is denied",
    "acceso denegado",
    "requires elevation",
    "requiere elevación",
    "requiere elevacion",
    "requested operation requires elevation",
    "la operación solicitada requiere elevación",
    "permissiondenied",
    "unauthorizedaccessexception",
    "0x80070005",
)


@dataclass
class NetworkAdapter:
    """Representa el estado y configuración IPv4/DNS de un adaptador de red."""

    name: str
    description: str = ""
    if_index: int = 0
    status: str = "Unknown"
    mac_address: str = ""
    link_speed: str = ""
    dhcp_enabled: bool = True
    ipv4_address: str = ""
    prefix_length: int | None = None
    subnet_mask: str = ""
    gateway: str = ""
    dns_servers: list[str] = field(default_factory=list)
    dns_dhcp: bool = True

    @property
    def is_up(self) -> bool:
        return self.status.lower() == "up"

    @property
    def is_disabled(self) -> bool:
        return self.status.lower() == "disabled"

    @property
    def status_label(self) -> str:
        low = self.status.lower()
        if low == "up":
            return "Conectado"
        if low == "disabled":
            return "Deshabilitado"
        if low in ("disconnected", "not present"):
            return "Desconectado"
        return self.status or "Desconocido"

    @property
    def status_badge_style(self) -> str:
        low = self.status.lower()
        if low == "up":
            return "RowBadgeOk"
        if low == "disabled":
            return "RowBadgeMuted"
        return "RowBadgeWarn"

    def summary_line(self) -> str:
        ip_part = (
            f"{self.ipv4_address}/{self.prefix_length}"
            if self.ipv4_address and self.prefix_length is not None
            else (self.ipv4_address or "Sin IPv4")
        )
        gw_part = self.gateway or "-"
        dns_part = ", ".join(self.dns_servers[:2]) if self.dns_servers else "Automático"
        mac_part = self.mac_address or "-"
        return f"IP: {ip_part} | GW: {gw_part} | DNS: {dns_part} | MAC: {mac_part}"


def _noop_log(_: str) -> None:
    """Callback por defecto cuando no se provee logger."""


def is_user_admin() -> bool:
    """Verifica si el proceso actual cuenta con privilegios reales de Administrador."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin() != 0)
    except Exception:
        return False


def format_task_exception(exc: Exception) -> str:
    """Traduce errores de permisos de Windows a un mensaje amigable UAC."""
    if isinstance(exc, PermissionError):
        return UAC_PERMISSION_MSG
    if not is_user_admin():
        if isinstance(exc, OSError) and (getattr(exc, "winerror", None) == 5 or exc.errno == 13):
            return UAC_PERMISSION_MSG
        text = str(exc)
        low = text.lower()
        if any(marker in low for marker in _ACCESS_DENIED_MARKERS):
            return UAC_PERMISSION_MSG
        return text
    return str(exc)


def _ps_quote(value: str) -> str:
    """Escapa un literal para cadena de comillas simples en PowerShell."""
    return "'" + value.replace("'", "''") + "'"


def _decode_console_output(raw: bytes | None) -> str:
    """Decodifica salida de utilidades nativas de Windows (UTF-8 estricto con fallback OEM)."""
    if not raw:
        return ""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass
    for encoding in ("oem", "cp850", "cp1252"):
        try:
            return raw.decode(encoding, errors="replace")
        except LookupError:
            continue
    return raw.decode("utf-8", errors="replace")


def _run_cmd(
    cmd: list[str],
    *,
    utf8: bool = False,
    timeout: float | None = 30.0,
) -> tuple[int, str, str]:
    """Ejecuta un comando del sistema con shell=False y sin ventana de consola."""
    proc = subprocess.run(
        cmd,
        capture_output=True,
        shell=False,
        timeout=timeout,
        creationflags=_CREATE_NO_WINDOW,
    )
    if utf8:
        try:
            stdout = (proc.stdout or b"").decode("utf-8")
            stderr = (proc.stderr or b"").decode("utf-8")
        except UnicodeDecodeError:
            stdout = _decode_console_output(proc.stdout)
            stderr = _decode_console_output(proc.stderr)
    else:
        stdout = _decode_console_output(proc.stdout)
        stderr = _decode_console_output(proc.stderr)
    return proc.returncode, stdout, stderr


def _run_powershell(script: str, timeout: float | None = 30.0) -> tuple[int, str, str]:
    """Ejecuta un bloque PowerShell forzando salida UTF-8 sin ventana visible."""
    wrapped = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "$OutputEncoding = [System.Text.Encoding]::UTF8; "
        + script
    )
    return _run_cmd(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            wrapped,
        ],
        utf8=True,
        timeout=timeout,
    )


def _check_access_denied(returncode: int, stdout: str, stderr: str) -> None:
    """Detecta respuestas de permiso denegado en salida de comandos Windows."""
    if returncode == 0 or is_user_admin():
        return
    combined = f"{stderr}\n{stdout}".lower()
    if any(marker in combined for marker in _ACCESS_DENIED_MARKERS):
        raise PermissionError(UAC_PERMISSION_MSG)


def _is_partial_ip_reset_success(
    cmd: list[str],
    returncode: int,
    stdout: str,
    stderr: str,
) -> bool:
    """Detecta si netsh int ip reset completó cambios pese a una subclave NSI protegida."""
    if returncode == 0 or cmd[:4] != ["netsh", "int", "ip", "reset"]:
        return False
    if not is_user_admin():
        return False
    combined = f"{stdout}\n{stderr}".lower()
    markers = (
        "se restableci",
        "restableciendo",
        "reinicie el equipo",
        "resetting",
        "restart the computer",
        "ok.",
        "ok\r",
        "ok\n",
        "ok!",
    )
    return any(marker in combined for marker in markers)


def _log_partial_ip_reset_warning(
    code: int,
    stdout: str,
    stderr: str,
    log: LogCallback,
) -> None:
    """Registra en el log el detalle completo de un retorno parcial de netsh int ip reset."""
    for line in stderr.splitlines():
        if line.strip():
            log(f"  {line.strip()}")
    detail = " | ".join(
        part.strip()
        for part in f"{stdout}\n{stderr}".splitlines()
        if part.strip()
    )
    log(
        f"[ADVERTENCIA] netsh int ip reset finalizó con código {code} por subclave protegida del sistema (NSI), "
        f"pero completó el restablecimiento TCP/IP. Detalle: {detail or 'sin detalle'}"
    )


# ---------------------------------------------------------------------------
# Validación de direcciones IPv4, máscaras y hosts
# ---------------------------------------------------------------------------

def prefix_length_to_mask(prefix: int) -> str:
    """Convierte longitud de prefijo CIDR (0-32) a máscara decimal punteada."""
    if not (0 <= prefix <= 32):
        raise ValueError(f"Prefijo CIDR inválido: {prefix}")
    net = ipaddress.IPv4Network(f"0.0.0.0/{prefix}", strict=False)
    return str(net.netmask)


def validate_ipv4(value: str, field_name: str, allow_empty: bool = False) -> str:
    """Valida una dirección IPv4 y devuelve su forma normalizada."""
    clean = value.strip()
    if not clean:
        if allow_empty:
            return ""
        raise ValueError(f"El campo '{field_name}' no puede estar vacío.")
    try:
        addr = ipaddress.IPv4Address(clean)
    except ValueError as exc:
        raise ValueError(f"'{clean}' no es una dirección IPv4 válida para {field_name}.") from exc
    return str(addr)


def validate_subnet_mask(mask: str) -> tuple[str, int]:
    """Valida una máscara de subred IPv4 contigua y retorna (máscara, prefijo)."""
    clean = mask.strip()
    if not clean:
        raise ValueError("La máscara de subred no puede estar vacía.")
    try:
        addr = ipaddress.IPv4Address(clean)
        net = ipaddress.IPv4Network(f"0.0.0.0/{addr}", strict=False)
    except ValueError as exc:
        raise ValueError(f"La máscara de subred '{clean}' no es válida (ej: 255.255.255.0).") from exc
    if str(net.netmask) != str(addr) or net.prefixlen == 0:
        raise ValueError(f"La máscara de subred '{clean}' no es contigua o es inválida.")
    return str(addr), int(net.prefixlen)


def validate_host_or_ip(target: str) -> str:
    """Valida que el destino de diagnóstico sea un hostname o IP seguro."""
    clean = target.strip()
    if not clean:
        raise ValueError("Ingresá un host o dirección IP válido.")
    if not _HOST_PATTERN.match(clean):
        raise ValueError(
            f"Destino inválido: '{clean}'. Usá solo letras, números, puntos, guiones o ':'."
        )
    return clean


def _validate_adapter_name(adapter_name: str) -> str:
    clean = adapter_name.strip()
    if not clean:
        raise ValueError("No se especificó el nombre del adaptador de red.")
    return clean


# ---------------------------------------------------------------------------
# Inventario e inspección de adaptadores de red
# ---------------------------------------------------------------------------

def _format_speed_bps(speed_bps: int) -> str:
    """Formatea velocidad en bps a cadena legible (Mbps / Gbps)."""
    if speed_bps <= 0:
        return ""
    if speed_bps >= 1_000_000_000:
        gbps = speed_bps / 1_000_000_000
        return f"{gbps:.1f} Gbps" if gbps % 1 else f"{int(gbps)} Gbps"
    if speed_bps >= 1_000_000:
        return f"{int(round(speed_bps / 1_000_000))} Mbps"
    return f"{int(round(speed_bps / 1_000))} Kbps"


def _list_adapters_dotnet_fallback() -> list[NetworkAdapter]:
    """Fallback sin CIM/WMI usando System.Net.NetworkInformation.NetworkInterface."""
    ps_script = """
$ErrorActionPreference = 'SilentlyContinue'
$ifaces = [System.Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces() |
    Where-Object { $_.NetworkInterfaceType -ne [System.Net.NetworkInformation.NetworkInterfaceType]::Loopback }
$result = @()
foreach ($ni in $ifaces) {
    $props = $ni.GetIPProperties()
    $v4Props = $null
    try { $v4Props = $props.GetIPv4Properties() } catch {}

    $ipv4 = ''
    $mask = ''
    foreach ($u in $props.UnicastAddresses) {
        if ($u.Address.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork) {
            $ipv4 = $u.Address.IPAddressToString
            if ($u.IPv4Mask) { $mask = $u.IPv4Mask.IPAddressToString }
            break
        }
    }

    $gw = ''
    foreach ($g in $props.GatewayAddresses) {
        if ($g.Address.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork) {
            $gw = $g.Address.IPAddressToString
            break
        }
    }

    $dnsList = @()
    foreach ($d in $props.DnsAddresses) {
        if ($d.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork) {
            $dnsList += $d.IPAddressToString
        }
    }

    $macRaw = $ni.GetPhysicalAddress().ToString()
    $macFmt = if ($macRaw.Length -eq 12) { ($macRaw -replace '(.{2})(?!$)', '$1-') } else { $macRaw }
    $opStatus = [string]$ni.OperationalStatus
    $status = if ($opStatus -eq 'Up') { 'Up' } else { 'Disconnected' }

    $dnsStatic = $false
    try {
        $regPath = "HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces\\$($ni.Id)"
        $nsVal = (Get-ItemProperty -Path $regPath -Name 'NameServer' -ErrorAction SilentlyContinue).NameServer
        if ($nsVal -and $nsVal.Trim().Length -gt 0) { $dnsStatic = $true }
    } catch {}

    $result += [PSCustomObject]@{
        name = [string]$ni.Name
        description = [string]$ni.Description
        if_index = if ($v4Props) { [int]$v4Props.Index } else { 0 }
        status = $status
        mac_address = $macFmt
        speed_bps = [int64]$ni.Speed
        dhcp_enabled = if ($v4Props) { [bool]$v4Props.IsDhcpEnabled } else { $true }
        ipv4_address = $ipv4
        subnet_mask = $mask
        gateway = $gw
        dns_servers = @($dnsList)
        dns_dhcp = (-not $dnsStatic)
    }
}
if ($result.Count -eq 0) {
    '[]'
} else {
    ConvertTo-Json -InputObject @($result) -Depth 4 -Compress
}
"""
    code, stdout, stderr = _run_powershell(ps_script, timeout=20.0)
    if code != 0 and not stdout.strip():
        _check_access_denied(code, stdout, stderr)
        raise RuntimeError(f"No se pudieron consultar los adaptadores de red: {(stderr or stdout).strip()}")

    raw_json = stdout.strip()
    if not raw_json:
        return []

    parsed = json.loads(raw_json)
    if isinstance(parsed, dict):
        parsed = [parsed]

    adapters: list[NetworkAdapter] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        mask = str(item.get("subnet_mask", "")).strip()
        prefix_val: int | None = None
        if mask:
            try:
                _, prefix_val = validate_subnet_mask(mask)
            except ValueError:
                prefix_val = None

        dns_raw = item.get("dns_servers")
        if isinstance(dns_raw, str):
            dns_list = [dns_raw] if dns_raw.strip() else []
        elif isinstance(dns_raw, list):
            dns_list = [str(d).strip() for d in dns_raw if str(d).strip()]
        else:
            dns_list = []

        adapters.append(
            NetworkAdapter(
                name=str(item.get("name", "")).strip(),
                description=str(item.get("description", "")).strip(),
                if_index=int(item.get("if_index", 0) or 0),
                status=str(item.get("status", "Unknown")).strip(),
                mac_address=str(item.get("mac_address", "")).strip(),
                link_speed=_format_speed_bps(int(item.get("speed_bps", 0) or 0)),
                dhcp_enabled=bool(item.get("dhcp_enabled", True)),
                ipv4_address=str(item.get("ipv4_address", "")).strip(),
                prefix_length=prefix_val,
                subnet_mask=mask,
                gateway=str(item.get("gateway", "")).strip(),
                dns_servers=dns_list,
                dns_dhcp=bool(item.get("dns_dhcp", True)),
            )
        )

    order = {"up": 0, "disconnected": 1, "disabled": 2}
    adapters.sort(key=lambda a: (order.get(a.status.lower(), 3), a.name.lower()))
    return adapters


def list_network_adapters() -> list[NetworkAdapter]:
    """Obtiene todos los adaptadores de red de Windows con su configuración IPv4/DNS."""
    ps_script = """
$ErrorActionPreference = 'SilentlyContinue'
$adapters = @(Get-NetAdapter | Sort-Object InterfaceIndex)
$result = @()
foreach ($a in $adapters) {
    $ifIndex = [int]$a.InterfaceIndex
    $ipIf = Get-NetIPInterface -InterfaceIndex $ifIndex -AddressFamily IPv4 | Select-Object -First 1
    $ipCfg = Get-NetIPConfiguration -InterfaceIndex $ifIndex | Select-Object -First 1
    $ipv4Obj = $null
    if ($ipCfg -and $ipCfg.IPv4Address) {
        $ipv4Obj = @($ipCfg.IPv4Address) | Select-Object -First 1
    }
    if (-not $ipv4Obj) {
        $ipv4Obj = Get-NetIPAddress -InterfaceIndex $ifIndex -AddressFamily IPv4 |
            Where-Object { $_.IPAddress -notlike '127.*' } |
            Select-Object -First 1
    }
    $gw = ''
    if ($ipCfg -and $ipCfg.IPv4DefaultGateway) {
        $gwObj = @($ipCfg.IPv4DefaultGateway) | Select-Object -First 1
        if ($gwObj) { $gw = [string]$gwObj.NextHop }
    }
    $dnsObj = Get-DnsClientServerAddress -InterfaceIndex $ifIndex -AddressFamily IPv4 | Select-Object -First 1
    $dnsList = @()
    if ($dnsObj -and $dnsObj.ServerAddresses) {
        $dnsList = @($dnsObj.ServerAddresses | Where-Object { $_ -and $_ -notmatch ':' })
    }
    $dnsStatic = $false
    try {
        $regPath = "HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces\\$($a.InterfaceGuid)"
        $nsVal = (Get-ItemProperty -Path $regPath -Name 'NameServer' -ErrorAction SilentlyContinue).NameServer
        if ($nsVal -and $nsVal.Trim().Length -gt 0) { $dnsStatic = $true }
    } catch {}

    $dhcpEnabled = $true
    if ($ipIf) {
        $dhcpEnabled = ([string]$ipIf.Dhcp -eq 'Enabled')
    }

    $result += [PSCustomObject]@{
        name = [string]$a.Name
        description = [string]$a.InterfaceDescription
        if_index = $ifIndex
        status = [string]$a.Status
        mac_address = [string]$a.MacAddress
        link_speed = [string]$a.LinkSpeed
        dhcp_enabled = $dhcpEnabled
        ipv4_address = if ($ipv4Obj) { [string]$ipv4Obj.IPAddress } else { '' }
        prefix_length = if ($ipv4Obj -and $null -ne $ipv4Obj.PrefixLength) { [int]$ipv4Obj.PrefixLength } else { $null }
        gateway = $gw
        dns_servers = @($dnsList)
        dns_dhcp = (-not $dnsStatic)
    }
}
if ($result.Count -eq 0) {
    '[]'
} else {
    ConvertTo-Json -InputObject @($result) -Depth 4 -Compress
}
"""
    code, stdout, stderr = _run_powershell(ps_script, timeout=25.0)
    raw_json = stdout.strip() if code == 0 else ""

    parsed: Any = []
    if raw_json:
        try:
            parsed = json.loads(raw_json)
            if isinstance(parsed, dict):
                parsed = [parsed]
        except json.JSONDecodeError:
            parsed = []

    if not parsed:
        return _list_adapters_dotnet_fallback()

    adapters: list[NetworkAdapter] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        prefix_raw = item.get("prefix_length")
        prefix_val = int(prefix_raw) if isinstance(prefix_raw, int) else None
        mask = ""
        if prefix_val is not None and 0 <= prefix_val <= 32:
            mask = prefix_length_to_mask(prefix_val)

        dns_raw = item.get("dns_servers")
        if isinstance(dns_raw, str):
            dns_list = [dns_raw] if dns_raw.strip() else []
        elif isinstance(dns_raw, list):
            dns_list = [str(d).strip() for d in dns_raw if str(d).strip()]
        else:
            dns_list = []

        adapters.append(
            NetworkAdapter(
                name=str(item.get("name", "")).strip(),
                description=str(item.get("description", "")).strip(),
                if_index=int(item.get("if_index", 0) or 0),
                status=str(item.get("status", "Unknown")).strip(),
                mac_address=str(item.get("mac_address", "")).strip(),
                link_speed=str(item.get("link_speed", "")).strip(),
                dhcp_enabled=bool(item.get("dhcp_enabled", True)),
                ipv4_address=str(item.get("ipv4_address", "")).strip(),
                prefix_length=prefix_val,
                subnet_mask=mask,
                gateway=str(item.get("gateway", "")).strip(),
                dns_servers=dns_list,
                dns_dhcp=bool(item.get("dns_dhcp", True)),
            )
        )

    order = {"up": 0, "disconnected": 1, "disabled": 2}
    adapters.sort(key=lambda a: (order.get(a.status.lower(), 3), a.name.lower()))
    return adapters


# ---------------------------------------------------------------------------
# Configuración de IPv4 (DHCP / Estática), DNS y estado del adaptador
# ---------------------------------------------------------------------------

def set_adapter_dhcp(
    adapter_name: str,
    also_reset_dns: bool = False,
    log: LogCallback = _noop_log,
) -> str:
    """Configura un adaptador de red para obtener IPv4 automáticamente por DHCP."""
    alias = _validate_adapter_name(adapter_name)
    log(f"[INFO] Configurando IPv4 por DHCP en '{alias}'...")

    cmd = ["netsh", "interface", "ipv4", "set", "address", f"name={alias}", "source=dhcp"]
    code, stdout, stderr = _run_cmd(cmd)
    _check_access_denied(code, stdout, stderr)

    if code != 0:
        detail = (stderr or stdout).strip()
        # Si ya estaba en DHCP, netsh devuelve un aviso no crítico en algunos equipos
        if "dhcp" not in detail.lower() or "already" not in detail.lower():
            # Intentar fallback directo con Set-NetIPInterface
            ps = (
                f"$ErrorActionPreference = 'Stop'; "
                f"Set-NetIPInterface -InterfaceAlias {_ps_quote(alias)} -AddressFamily IPv4 -Dhcp Enabled; "
                f"Remove-NetRoute -InterfaceAlias {_ps_quote(alias)} -DestinationPrefix '0.0.0.0/0' "
                f"-Confirm:$false -ErrorAction SilentlyContinue"
            )
            ps_code, ps_out, ps_err = _run_powershell(ps)
            _check_access_denied(ps_code, ps_out, ps_err)
            if ps_code != 0:
                raise RuntimeError(
                    f"No se pudo activar DHCP en '{alias}': {(ps_err or detail).strip()}"
                )

    log(f"[OK] IPv4 en modo DHCP aplicado a '{alias}'.")

    if also_reset_dns:
        set_adapter_dns(alias, dns_servers=[], use_dhcp=True, log=log)
        return f"Adaptador '{alias}' configurado en DHCP (IPv4 y DNS automáticos)."

    return f"Adaptador '{alias}' configurado para obtener IPv4 por DHCP."


def set_adapter_static_ip(
    adapter_name: str,
    ip_address: str,
    subnet_mask: str,
    gateway: str = "",
    dns_primary: str = "",
    dns_secondary: str = "",
    apply_dns: bool = False,
    log: LogCallback = _noop_log,
) -> str:
    """Configura dirección IPv4 estática, máscara, puerta de enlace y DNS opcionales."""
    alias = _validate_adapter_name(adapter_name)
    clean_ip = validate_ipv4(ip_address, "Dirección IP")
    clean_mask, prefix = validate_subnet_mask(subnet_mask)
    clean_gw = validate_ipv4(gateway, "Puerta de enlace", allow_empty=True)

    dns_list: list[str] = []
    if apply_dns:
        p_dns = validate_ipv4(dns_primary, "DNS Primario", allow_empty=True)
        s_dns = validate_ipv4(dns_secondary, "DNS Secundario", allow_empty=True)
        if p_dns:
            dns_list.append(p_dns)
        if s_dns and s_dns != p_dns:
            dns_list.append(s_dns)

    log(
        f"[INFO] Aplicando IPv4 estática en '{alias}': "
        f"{clean_ip}/{prefix} (GW: {clean_gw or 'ninguna'})..."
    )

    cmd = [
        "netsh",
        "interface",
        "ipv4",
        "set",
        "address",
        f"name={alias}",
        "source=static",
        f"address={clean_ip}",
        f"mask={clean_mask}",
    ]
    if clean_gw:
        cmd.extend([f"gateway={clean_gw}", "gwmetric=1"])
    else:
        cmd.append("gateway=none")

    code, stdout, stderr = _run_cmd(cmd)
    _check_access_denied(code, stdout, stderr)
    if code != 0:
        detail = (stderr or stdout).strip()
        raise RuntimeError(f"Error al aplicar IP estática en '{alias}': {detail}")

    log(f"[OK] IPv4 estática configurada en '{alias}': {clean_ip} ({clean_mask}).")

    if apply_dns:
        if dns_list:
            set_adapter_dns(alias, dns_servers=dns_list, use_dhcp=False, log=log)
        else:
            set_adapter_dns(alias, dns_servers=[], use_dhcp=True, log=log)

    return f"IPv4 estática {clean_ip}/{prefix} aplicada en '{alias}'."


def set_adapter_dns(
    adapter_name: str,
    dns_servers: list[str],
    use_dhcp: bool = False,
    log: LogCallback = _noop_log,
) -> str:
    """Configura servidores DNS estáticos o automáticos (DHCP) en un adaptador."""
    alias = _validate_adapter_name(adapter_name)

    if use_dhcp or not dns_servers:
        log(f"[INFO] Restableciendo DNS a automático (DHCP) en '{alias}'...")
        cmd = [
            "netsh",
            "interface",
            "ipv4",
            "set",
            "dnsservers",
            f"name={alias}",
            "source=dhcp",
        ]
        code, stdout, stderr = _run_cmd(cmd)
        _check_access_denied(code, stdout, stderr)
        if code != 0:
            ps = (
                f"$ErrorActionPreference = 'Stop'; "
                f"Set-DnsClientServerAddress -InterfaceAlias {_ps_quote(alias)} -ResetServerAddresses"
            )
            ps_code, ps_out, ps_err = _run_powershell(ps)
            _check_access_denied(ps_code, ps_out, ps_err)
            if ps_code != 0:
                raise RuntimeError(
                    f"No se pudo restablecer DNS en '{alias}': {(ps_err or stderr or stdout).strip()}"
                )
        _run_cmd(["ipconfig", "/flushdns"])
        log(f"[OK] DNS configurado en automático (DHCP) para '{alias}'.")
        return f"DNS automático (DHCP) aplicado en '{alias}'."

    validated: list[str] = []
    for idx, srv in enumerate(dns_servers):
        label = "DNS Primario" if idx == 0 else f"DNS #{idx + 1}"
        addr = validate_ipv4(srv, label)
        if addr not in validated:
            validated.append(addr)

    log(f"[INFO] Configurando DNS en '{alias}': {', '.join(validated)}...")
    primary_cmd = [
        "netsh",
        "interface",
        "ipv4",
        "set",
        "dnsservers",
        f"name={alias}",
        "source=static",
        f"address={validated[0]}",
        "validate=no",
    ]
    code, stdout, stderr = _run_cmd(primary_cmd)
    _check_access_denied(code, stdout, stderr)
    if code != 0:
        detail = (stderr or stdout).strip()
        raise RuntimeError(f"Error al configurar DNS primario en '{alias}': {detail}")

    for idx, secondary in enumerate(validated[1:], start=2):
        add_cmd = [
            "netsh",
            "interface",
            "ipv4",
            "add",
            "dnsservers",
            f"name={alias}",
            f"address={secondary}",
            f"index={idx}",
            "validate=no",
        ]
        code2, stdout2, stderr2 = _run_cmd(add_cmd)
        _check_access_denied(code2, stdout2, stderr2)
        if code2 != 0:
            detail2 = (stderr2 or stdout2).strip()
            raise RuntimeError(f"Error al agregar DNS secundario ({secondary}) en '{alias}': {detail2}")

    _run_cmd(["ipconfig", "/flushdns"])
    log(f"[OK] DNS aplicado en '{alias}': {', '.join(validated)} (caché DNS limpiada).")
    return f"DNS configurado en '{alias}': {', '.join(validated)}."


def set_adapter_enabled(
    adapter_name: str,
    enabled: bool,
    log: LogCallback = _noop_log,
) -> str:
    """Habilita o deshabilita un adaptador de red mediante PowerShell NetAdapter."""
    alias = _validate_adapter_name(adapter_name)
    verb = "Habilitando" if enabled else "Deshabilitando"
    cmdlet = "Enable-NetAdapter" if enabled else "Disable-NetAdapter"
    log(f"[INFO] {verb} adaptador '{alias}'...")

    ps = f"$ErrorActionPreference = 'Stop'; {cmdlet} -Name {_ps_quote(alias)} -Confirm:$false"
    code, stdout, stderr = _run_powershell(ps, timeout=25.0)
    _check_access_denied(code, stdout, stderr)
    if code != 0:
        detail = (stderr or stdout).strip()
        raise RuntimeError(f"No se pudo cambiar el estado de '{alias}': {detail}")

    estado = "habilitado" if enabled else "deshabilitado"
    log(f"[OK] Adaptador '{alias}' {estado} correctamente.")
    return f"Adaptador '{alias}' {estado}."


def restart_adapter(adapter_name: str, log: LogCallback = _noop_log) -> str:
    """Reinicia un adaptador de red con Restart-NetAdapter."""
    alias = _validate_adapter_name(adapter_name)
    log(f"[INFO] Reiniciando adaptador '{alias}'...")

    ps = f"$ErrorActionPreference = 'Stop'; Restart-NetAdapter -Name {_ps_quote(alias)} -Confirm:$false"
    code, stdout, stderr = _run_powershell(ps, timeout=30.0)
    _check_access_denied(code, stdout, stderr)
    if code != 0:
        detail = (stderr or stdout).strip()
        raise RuntimeError(f"No se pudo reiniciar el adaptador '{alias}': {detail}")

    log(f"[OK] Adaptador '{alias}' reiniciado correctamente.")
    return f"Adaptador '{alias}' reiniciado."


def open_network_connections(log: LogCallback = _noop_log) -> str:
    """Abre el panel clásico Conexiones de Red de Windows (ncpa.cpl)."""
    log("[INFO] Abriendo Conexiones de Red (ncpa.cpl)...")
    subprocess.Popen(
        ["control.exe", "ncpa.cpl"],
        shell=False,
        close_fds=True,
    )
    return "Panel de Conexiones de Red abierto."


# ---------------------------------------------------------------------------
# Renovación IP / DNS y restablecimiento de pila de red
# ---------------------------------------------------------------------------

def flush_dns_cache(log: LogCallback = _noop_log) -> str:
    """Ejecuta ipconfig /flushdns."""
    log("[INFO] Limpiando caché de resolución DNS (ipconfig /flushdns)...")
    code, stdout, stderr = _run_cmd(["ipconfig", "/flushdns"])
    _check_access_denied(code, stdout, stderr)
    for line in stdout.splitlines():
        if line.strip():
            log(f"  {line.strip()}")
    if code != 0:
        detail = (stderr or stdout).strip()
        raise RuntimeError(f"ipconfig /flushdns finalizó con código {code}: {detail}")
    log("[OK] Caché DNS limpiada correctamente.")
    return "Caché DNS limpiada correctamente."


def purge_network_sessions(log: LogCallback = _noop_log) -> str:
    """Purga conexiones SMB (net use * /delete /y) y tickets Kerberos (klist purge)."""
    log("[INFO] Purgando sesiones de red SMB (net use * /delete /y)...")
    try:
        net_code, net_out, net_err = _run_cmd(["net", "use", "*", "/delete", "/y"], timeout=20.0)
    except FileNotFoundError:
        net_code, net_out, net_err = -1, "", "Comando 'net' no encontrado."

    net_detail = (net_out or net_err).strip()
    for line in net_detail.splitlines():
        if line.strip():
            log(f"  {line.strip()}")

    if net_code == 0:
        log("[OK] Sesiones SMB / unidades de red purgadas.")
        smb_status = "OK"
    else:
        low_net = net_detail.lower()
        if "no hay entradas" in low_net or "no entries" in low_net or "no se encontr" in low_net:
            log("[INFO] Sin sesiones SMB activas para eliminar.")
            smb_status = "Sin sesiones activas"
        else:
            log(f"[ADVERTENCIA] net use finalizó con código {net_code}: {net_detail or 'sin detalle'}")
            smb_status = f"Aviso ({net_code})"

    log("[INFO] Purgando caché de tickets Kerberos (klist purge)...")
    try:
        k_code, k_out, k_err = _run_cmd(["klist", "purge"], timeout=20.0)
    except FileNotFoundError:
        k_code, k_out, k_err = -1, "", "Comando 'klist' no encontrado en este sistema."

    k_detail = (k_out or k_err).strip()
    for line in k_detail.splitlines():
        if line.strip():
            log(f"  {line.strip()}")

    if k_code == 0:
        log("[OK] Tickets Kerberos purgados correctamente.")
        krb_status = "OK"
    else:
        low_k = k_detail.lower()
        if "0x8009030e" in low_k or "no tickets" in low_k or "ningún" in low_k or "ningun" in low_k or "no hay" in low_k:
            log("[INFO] No había tickets Kerberos activos en caché.")
            krb_status = "Sin tickets activos"
        else:
            log(f"[ADVERTENCIA] klist purge finalizó con código {k_code}: {k_detail or 'sin detalle'}")
            krb_status = f"Aviso ({k_code})"

    return f"Sesiones de red purgadas (SMB: {smb_status} | Kerberos: {krb_status})."


def renew_ip_and_dns(
    adapter_name: str = "",
    probe_host: str = "1.1.1.1",
    log: LogCallback = _noop_log,
) -> str:
    """Ejecuta ipconfig /flushdns, /release, /renew, /registerdns y verifica conectividad."""
    alias = adapter_name.strip()
    release_cmd = ["ipconfig", "/release", alias] if alias else ["ipconfig", "/release"]
    renew_cmd = ["ipconfig", "/renew", alias] if alias else ["ipconfig", "/renew"]

    steps = [
        ("Limpiando caché DNS", ["ipconfig", "/flushdns"]),
        ("Liberando concesión IP", release_cmd),
        ("Renovando concesión IP", renew_cmd),
        ("Registrando DNS", ["ipconfig", "/registerdns"]),
    ]

    for title, cmd in steps:
        log(f"[INFO] {title} ({' '.join(cmd)})...")
        code, stdout, stderr = _run_cmd(cmd, timeout=45.0)
        if code != 0:
            detail = (stderr or stdout or "").strip()
            log(f"[ADVERTENCIA] {' '.join(cmd)} finalizó con código {code}: {detail}")
        else:
            log(f"[OK] {' '.join(cmd)} completado.")

    clean_probe = validate_host_or_ip(probe_host) if probe_host.strip() else ""
    internet_ok = False
    if clean_probe:
        p_code, _, _ = _run_cmd(["ping", "-n", "1", "-w", "2000", clean_probe], timeout=10.0)
        internet_ok = p_code == 0
        if internet_ok:
            log(f"[OK] Conectividad Internet ({clean_probe}): Online")
        else:
            log(f"[ADVERTENCIA] Conectividad Internet ({clean_probe}): Sin respuesta")

    dns_ok = False
    try:
        socket.getaddrinfo("www.google.com", 443)
        dns_ok = True
        log("[OK] Resolución DNS (www.google.com): Operativa")
    except OSError:
        log("[ADVERTENCIA] Resolución DNS (www.google.com): Sin respuesta")

    scope = f" en '{alias}'" if alias else ""
    return (
        f"IP/DNS renovados{scope}. Internet ({clean_probe or 'N/A'}): "
        f"{'OK' if internet_ok else 'Sin respuesta'} | DNS: {'OK' if dns_ok else 'Fallo'}"
    )


def reset_winsock_and_tcpip(log: LogCallback = _noop_log) -> str:
    """Restablece el catálogo Winsock y la pila TCP/IP (requiere privilegios UAC)."""
    steps = [
        ("Restableciendo catálogo Winsock", ["netsh", "winsock", "reset"]),
        ("Restableciendo pila TCP/IP", ["netsh", "int", "ip", "reset"]),
    ]
    for title, cmd in steps:
        log(f"[INFO] {title} ({' '.join(cmd)})...")
        code, stdout, stderr = _run_cmd(cmd, timeout=30.0)
        _check_access_denied(code, stdout, stderr)
        for line in stdout.splitlines():
            if line.strip():
                log(f"  {line.strip()}")
        if code != 0:
            if _is_partial_ip_reset_success(cmd, code, stdout, stderr):
                _log_partial_ip_reset_warning(code, stdout, stderr, log)
            else:
                detail = (stderr or stdout).strip()
                raise RuntimeError(f"Error al ejecutar {' '.join(cmd)}: {detail}")

    log("[OK] Winsock y TCP/IP restablecidos. Se recomienda reiniciar Windows.")
    return "Winsock y pila TCP/IP restablecidos. Reiniciá el equipo para aplicar los cambios."


def run_quick_repair(log: LogCallback = _noop_log) -> str:
    """Secuencia automática sin reinicio: flushdns -> release/renew -> reinicio de adaptador -> conectividad."""
    log("[PASO 1/4] Limpiando caché DNS (ipconfig /flushdns)...")
    flush_dns_cache(log=log)

    log("[PASO 2/4] Renovando concesiones DHCP (ipconfig /release y /renew)...")
    for cmd in (["ipconfig", "/release"], ["ipconfig", "/renew"]):
        log(f"[INFO] Ejecutando {' '.join(cmd)}...")
        code, stdout, stderr = _run_cmd(cmd, timeout=45.0)
        if code != 0:
            detail = (stderr or stdout or "").strip()
            log(f"[ADVERTENCIA] {' '.join(cmd)} finalizó con código {code}: {detail}")
        else:
            log(f"[OK] {' '.join(cmd)} completado.")

    log("[PASO 3/4] Detectando adaptador(es) conectado(s) para reiniciar...")
    adapters = list_network_adapters()
    connected = [a for a in adapters if a.is_up]
    if connected:
        for adp in connected:
            restart_adapter(adp.name, log=log)
        log("[INFO] Esperando estabilización de enlace tras reinicio de adaptador...")
        time.sleep(2.0)
        restarted_names = ", ".join(a.name for a in connected)
    else:
        log("[ADVERTENCIA] No se detectaron adaptadores conectados (Up); se omite el reinicio de interfaz.")
        restarted_names = "ninguno"

    log("[PASO 4/4] Verificando conectividad externa y resolución DNS...")
    conn = check_internet_connectivity(timeout=3.0)
    online = bool(conn.get("online", False))
    dns_ok = bool(conn.get("dns_ok", False))
    host = str(conn.get("host", ""))
    latency = conn.get("latency_ms")

    if online:
        ms_txt = f" ({latency:.0f} ms)" if isinstance(latency, (int, float)) else ""
        log(f"[OK] Conectividad Internet ({host}){ms_txt}: Online")
    else:
        log("[ADVERTENCIA] Conectividad Internet: Sin respuesta")

    if dns_ok:
        log("[OK] Resolución DNS: Operativa")
    else:
        log("[ADVERTENCIA] Resolución DNS: Sin respuesta")

    return (
        f"Reparación rápida completada (adaptador reiniciado: {restarted_names}). "
        f"Internet: {'OK' if online else 'Sin respuesta'} | DNS: {'OK' if dns_ok else 'Fallo'}."
    )


def run_deep_network_cleanup(log: LogCallback = _noop_log) -> str:
    """Secuencia profunda: flushdns -> arp -d * -> netsh winsock reset -> netsh int ip reset."""
    log("[PASO 1/4] Limpiando caché DNS (ipconfig /flushdns)...")
    flush_dns_cache(log=log)

    log("[PASO 2/4] Vaciando caché ARP local (arp -d *)...")
    code, stdout, stderr = _run_cmd(["arp", "-d", "*"], timeout=20.0)
    _check_access_denied(code, stdout, stderr)
    for line in stdout.splitlines():
        if line.strip():
            log(f"  {line.strip()}")
    if code != 0:
        detail = (stderr or stdout).strip()
        log(f"[ADVERTENCIA] arp -d * finalizó con código {code}: {detail}")
    else:
        log("[OK] Caché ARP eliminada.")

    reset_steps = [
        ("[PASO 3/4] Restableciendo catálogo Winsock", ["netsh", "winsock", "reset"]),
        ("[PASO 4/4] Restableciendo pila TCP/IP", ["netsh", "int", "ip", "reset"]),
    ]
    for title, cmd in reset_steps:
        log(f"{title} ({' '.join(cmd)})...")
        r_code, r_out, r_err = _run_cmd(cmd, timeout=30.0)
        _check_access_denied(r_code, r_out, r_err)
        for line in r_out.splitlines():
            if line.strip():
                log(f"  {line.strip()}")
        if r_code != 0:
            if _is_partial_ip_reset_success(cmd, r_code, r_out, r_err):
                _log_partial_ip_reset_warning(r_code, r_out, r_err, log)
            else:
                detail = (r_err or r_out).strip()
                raise RuntimeError(f"Error al ejecutar {' '.join(cmd)}: {detail}")
        else:
            log(f"[OK] {' '.join(cmd)} completado.")

    log("[OK] Limpieza profunda finalizada. Se requiere reiniciar Windows.")
    return "Limpieza profunda completada. Reiniciá el equipo para aplicar los cambios."


# ---------------------------------------------------------------------------
# Diagnóstico de red y verificación de conectividad
# ---------------------------------------------------------------------------

def check_internet_connectivity(
    probe_hosts: tuple[str, ...] = ("1.1.1.1", "8.8.8.8"),
    timeout: float = 2.0,
) -> dict[str, Any]:
    """Comprueba rápidamente conectividad TCP externa y resolución DNS."""
    online = False
    reachable_host = ""
    latency_ms: float | None = None

    for host in probe_hosts:
        start = time.perf_counter()
        try:
            with socket.create_connection((host, 53), timeout=timeout):
                latency_ms = round((time.perf_counter() - start) * 1000.0, 1)
                online = True
                reachable_host = host
                break
        except OSError:
            continue

    dns_ok = False
    if online:
        try:
            socket.getaddrinfo("www.google.com", 443)
            dns_ok = True
        except OSError:
            dns_ok = False

    return {
        "online": online,
        "host": reachable_host,
        "latency_ms": latency_ms,
        "dns_ok": dns_ok,
    }


def run_ping(target: str, count: int = 4, log: LogCallback = _noop_log) -> str:
    """Ejecuta ping ICMP hacia un host o IP y retorna la salida completa."""
    clean_target = validate_host_or_ip(target)
    safe_count = max(1, min(20, int(count)))
    log(f"[INFO] Ejecutando ping -n {safe_count} {clean_target}...")
    code, stdout, stderr = _run_cmd(
        ["ping", "-n", str(safe_count), "-w", "2000", clean_target],
        timeout=safe_count * 3.5 + 10.0,
    )
    output = (stdout or stderr).strip()
    if code == 0:
        log(f"[OK] Ping a {clean_target} completado con respuesta.")
    else:
        log(f"[ADVERTENCIA] Ping a {clean_target} finalizó sin respuesta completa (código {code}).")
    return output or "(Sin salida)"


def run_traceroute(
    target: str,
    max_hops: int = 20,
    resolve_names: bool = False,
    log: LogCallback = _noop_log,
) -> str:
    """Ejecuta tracert hacia un host o IP."""
    clean_target = validate_host_or_ip(target)
    safe_hops = max(1, min(30, int(max_hops)))
    cmd = ["tracert", "-h", str(safe_hops), "-w", "1500"]
    if not resolve_names:
        cmd.append("-d")
    cmd.append(clean_target)

    log(f"[INFO] Ejecutando {' '.join(cmd)}...")
    code, stdout, stderr = _run_cmd(cmd, timeout=90.0)
    output = (stdout or stderr).strip()
    if code == 0:
        log(f"[OK] Traceroute hacia {clean_target} finalizado.")
    else:
        log(f"[ADVERTENCIA] Traceroute hacia {clean_target} finalizó con código {code}.")
    return output or "(Sin salida)"


def run_nslookup(
    target: str,
    dns_server: str = "",
    log: LogCallback = _noop_log,
) -> str:
    """Ejecuta una consulta DNS con nslookup."""
    clean_target = validate_host_or_ip(target)
    cmd = ["nslookup", clean_target]
    if dns_server.strip():
        cmd.append(validate_host_or_ip(dns_server))

    log(f"[INFO] Ejecutando {' '.join(cmd)}...")
    code, stdout, stderr = _run_cmd(cmd, timeout=15.0)
    combined = "\n".join(part.strip() for part in (stdout, stderr) if part.strip())
    if code == 0:
        log(f"[OK] Consulta DNS completada para {clean_target}.")
    else:
        log(f"[ADVERTENCIA] nslookup finalizó con código {code}.")
    return combined or "(Sin salida)"


def run_tcp_port_check(
    host: str,
    port: int,
    timeout: float = 3.0,
    log: LogCallback = _noop_log,
) -> str:
    """Verifica apertura de un puerto TCP y mide la latencia de conexión."""
    clean_host = validate_host_or_ip(host)
    if not (1 <= int(port) <= 65535):
        raise ValueError("El puerto TCP debe estar entre 1 y 65535.")

    log(f"[INFO] Probando conexión TCP a {clean_host}:{port}...")
    start = time.perf_counter()
    try:
        resolved_ip = socket.gethostbyname(clean_host)
    except OSError as exc:
        msg = f"No se pudo resolver '{clean_host}': {exc}"
        log(f"[ADVERTENCIA] {msg}")
        return f"Destino: {clean_host}:{port}\nEstado: ERROR DE RESOLUCIÓN DNS\nDetalle: {exc}"

    try:
        with socket.create_connection((clean_host, int(port)), timeout=timeout):
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            log(f"[OK] Puerto {clean_host}:{port} ABIERTO ({elapsed_ms:.1f} ms).")
            return (
                f"Destino:   {clean_host}:{port}\n"
                f"IP:        {resolved_ip}\n"
                f"Estado:    ABIERTO / ACCESIBLE\n"
                f"Latencia:  {elapsed_ms:.1f} ms"
            )
    except OSError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        log(f"[ADVERTENCIA] Puerto {clean_host}:{port} sin respuesta ({exc}).")
        return (
            f"Destino:   {clean_host}:{port}\n"
            f"IP:        {resolved_ip}\n"
            f"Estado:    CERRADO / SIN RESPUESTA\n"
            f"Tiempo:    {elapsed_ms:.1f} ms\n"
            f"Detalle:   {exc}"
        )


def get_ipconfig_all(log: LogCallback = _noop_log) -> str:
    """Devuelve la salida completa de ipconfig /all."""
    log("[INFO] Consultando ipconfig /all...")
    _, stdout, stderr = _run_cmd(["ipconfig", "/all"], timeout=20.0)
    log("[OK] ipconfig /all obtenido.")
    return (stdout or stderr).strip() or "(Sin salida)"


def get_routing_table(log: LogCallback = _noop_log) -> str:
    """Devuelve la tabla de enrutamiento IPv4 (route print -4)."""
    log("[INFO] Consultando tabla de enrutamiento IPv4...")
    _, stdout, stderr = _run_cmd(["route", "print", "-4"], timeout=20.0)
    log("[OK] Tabla de rutas obtenida.")
    return (stdout or stderr).strip() or "(Sin salida)"


def get_arp_table(log: LogCallback = _noop_log) -> str:
    """Devuelve la tabla de caché ARP (arp -a)."""
    log("[INFO] Consultando caché ARP (arp -a)...")
    _, stdout, stderr = _run_cmd(["arp", "-a"], timeout=20.0)
    log("[OK] Tabla ARP obtenida.")
    return (stdout or stderr).strip() or "(Sin salida)"


def run_full_network_diagnostic(
    probe_ip: str = "1.1.1.1",
    dns_domain: str = "www.google.com",
    log: LogCallback = _noop_log,
) -> str:
    """Ejecuta un diagnóstico integral: adaptadores, gateway, ping externo, DNS y TCP 443."""
    clean_probe = validate_host_or_ip(probe_ip)
    clean_domain = validate_host_or_ip(dns_domain)

    lines: list[str] = []
    lines.append("=== DIAGNÓSTICO INTEGRAL DE RED ===")
    lines.append("")

    log("[INFO] Analizando adaptadores de red activos...")
    adapters = list_network_adapters()
    active = [a for a in adapters if a.is_up]
    lines.append(f"1. Adaptadores detectados: {len(adapters)} total | {len(active)} conectado(s)")

    gateways: list[str] = []
    for adp in active:
        mode = "DHCP" if adp.dhcp_enabled else "Estática"
        lines.append(f"   - {adp.name} ({adp.description})")
        lines.append(f"     {adp.summary_line()}  [{mode}]")
        if adp.gateway and adp.gateway not in gateways:
            gateways.append(adp.gateway)

    if not active:
        lines.append("   [ADVERTENCIA] No se detectaron adaptadores en estado Conectado (Up).")

    lines.append("")
    lines.append("2. Prueba de Puerta de Enlace (Gateway)")
    if not gateways:
        lines.append("   [ADVERTENCIA] No hay puerta de enlace predeterminada configurada.")
    else:
        for gw in gateways:
            log(f"[INFO] Probando gateway {gw}...")
            p_code, _, _ = _run_cmd(["ping", "-n", "2", "-w", "1500", gw], timeout=10.0)
            status = "OK (Responde)" if p_code == 0 else "FALLO (Sin respuesta)"
            lines.append(f"   - Gateway {gw}: {status}")

    lines.append("")
    lines.append(f"3. Conectividad Externa ICMP ({clean_probe})")
    log(f"[INFO] Probando conectividad ICMP hacia {clean_probe}...")
    ext_code, _, _ = _run_cmd(["ping", "-n", "2", "-w", "2000", clean_probe], timeout=12.0)
    lines.append(
        f"   - Ping {clean_probe}: {'OK (Conectividad IP operativa)' if ext_code == 0 else 'FALLO (Sin salida ICMP)'}"
    )

    lines.append("")
    lines.append(f"4. Resolución DNS ({clean_domain})")
    log(f"[INFO] Probando resolución DNS de {clean_domain}...")
    start = time.perf_counter()
    try:
        infos = socket.getaddrinfo(clean_domain, 443, family=socket.AF_INET)
        ips = sorted({info[4][0] for info in infos})
        elapsed = (time.perf_counter() - start) * 1000.0
        lines.append(f"   - Resolución DNS: OK ({', '.join(ips[:4])}) en {elapsed:.1f} ms")
        dns_ok = True
    except OSError as exc:
        lines.append(f"   - Resolución DNS: FALLO ({exc})")
        dns_ok = False

    lines.append("")
    lines.append(f"5. Conectividad HTTPS / TCP 443 ({clean_domain})")
    if dns_ok:
        log(f"[INFO] Probando conexión TCP 443 hacia {clean_domain}...")
        t0 = time.perf_counter()
        try:
            with socket.create_connection((clean_domain, 443), timeout=3.0):
                ms = (time.perf_counter() - t0) * 1000.0
                lines.append(f"   - TCP 443: OK (Conexión establecida en {ms:.1f} ms)")
        except OSError as exc:
            lines.append(f"   - TCP 443: FALLO ({exc})")
    else:
        lines.append("   - TCP 443: OMITIDO (falló la resolución DNS previa)")

    log("[OK] Diagnóstico integral de red completado.")
    return "\n".join(lines)


def generate_full_diagnostic_report(log: LogCallback = _noop_log) -> str:
    """Ejecuta diagnóstico integral + ipconfig /all + route print -4 + arp -a consolidados."""
    log("[PASO 1/4] Ejecutando Diagnóstico Integral de Conectividad...")
    diag_out = run_full_network_diagnostic(log=log)

    log("[PASO 2/4] Consultando ipconfig /all...")
    ipconfig_out = get_ipconfig_all(log=log)

    log("[PASO 3/4] Consultando tabla de enrutamiento IPv4 (route print -4)...")
    route_out = get_routing_table(log=log)

    log("[PASO 4/4] Consultando caché ARP local (arp -a)...")
    arp_out = get_arp_table(log=log)

    sep = "=" * 72
    sections = [
        f"REPORTE COMPLETO DE DIAGNÓSTICO DE RED\nGenerado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"{sep}\n1. DIAGNÓSTICO INTEGRAL DE CONECTIVIDAD\n{sep}\n{diag_out}",
        f"{sep}\n2. CONFIGURACIÓN IP DETALLADA (ipconfig /all)\n{sep}\n{ipconfig_out}",
        f"{sep}\n3. TABLA DE ENRUTAMIENTO IPv4 (route print -4)\n{sep}\n{route_out}",
        f"{sep}\n4. CACHÉ ARP LOCAL (arp -a)\n{sep}\n{arp_out}",
    ]
    log("[OK] Reporte completo de diagnóstico generado.")
    return "\n\n".join(sections)
