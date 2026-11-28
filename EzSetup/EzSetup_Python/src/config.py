"""Carga y validación centralizada de config.json para EzSetup."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import ipaddress
import json
import os
from pathlib import Path
import sys
from typing import Any


class ConfigError(Exception):
    """Error producido al cargar o validar config.json."""


class UnauthorizedUNCHostError(PermissionError):
    """Error lanzado cuando una ruta UNC apunta a un host no autorizado en config.json."""


def validate_unc_host(path_str: str, allowed_hosts: set[str]) -> None:
    """Valida que toda ruta UNC pertenezca a un host autorizado en config.json."""
    normalized = path_str.strip()
    if not normalized.startswith("\\\\"):
        return
    remainder = normalized.lstrip("\\")
    host = remainder.split("\\", 1)[0].strip().lower()
    if not host or host not in allowed_hosts:
        raise UnauthorizedUNCHostError(
            f"Host UNC no autorizado por config.json: '{host or normalized}'"
        )


REQUIRED_TOP_KEYS = (
    "app",
    "local_paths",
    "registry",
    "security",
    "urls",
    "menus",
)

REQUIRED_APP_KEYS = (
    "name",
    "version",
    "title",
    "copy_chunk_size_bytes",
    "server_check_interval_ms",
)

RESOURCE_SUBDIRS = ("Office", "Nitro", "Tecnica", "KMS")

# GUIDs oficiales de carpetas conocidas de Windows (KnownFolders)
_FOLDERID_DOWNLOADS = "{374DE290-123F-4565-9164-39C4925E467B}"
_FOLDERID_PICTURES = "{33E28130-4E1E-4676-835A-98395C3BC3BB}"
_FOLDERID_DESKTOP = "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}"


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _parse_guid(guid_str: str) -> _GUID:
    import uuid

    parsed = uuid.UUID(guid_str)
    data4 = (ctypes.c_ubyte * 8)(*parsed.bytes[8:])
    return _GUID(parsed.time_low, parsed.time_mid, parsed.time_hi_version, data4)


def _get_known_folder_path(folder_guid: str, fallback: Path) -> Path:
    """Obtiene una carpeta conocida de Windows mediante SHGetKnownFolderPath."""
    if os.name != "nt":
        return fallback

    try:
        shell32 = ctypes.windll.shell32
        ole32 = ctypes.windll.ole32
        guid = _parse_guid(folder_guid)
        ppsz_path = ctypes.c_wchar_p()
        hr = shell32.SHGetKnownFolderPath(
            ctypes.byref(guid),
            0,
            None,
            ctypes.byref(ppsz_path),
        )
        if hr == 0 and ppsz_path.value:
            resolved = Path(ppsz_path.value)
            ole32.CoTaskMemFree(ppsz_path)
            return resolved
    except Exception:
        pass

    return fallback


def resolve_app_root() -> Path:
    """Devuelve el directorio base de la aplicación (script o ejecutable)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resolve_bundle_root() -> Path:
    """Devuelve el directorio de recursos empaquetados (PyInstaller _MEIPASS o raíz)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return resolve_app_root()


def ensure_resources_dirs(app_root: Path | None = None) -> Path:
    """Crea automáticamente Recursos\\ y sus subcarpetas relativas al directorio base."""
    base = app_root or resolve_app_root()
    resources_root = base / "Recursos"
    resources_root.mkdir(parents=True, exist_ok=True)
    for subdir in RESOURCE_SUBDIRS:
        (resources_root / subdir).mkdir(parents=True, exist_ok=True)
    return resources_root


class AppConfig:
    """Contenedor validado e inmutable de la configuración de EzSetup."""

    def __init__(self, data: dict[str, Any], source_path: Path) -> None:
        self._data = data
        self.source_path = source_path

    @classmethod
    def resolve_config_path(
        cls,
        profile: str | None = None,
        config_override: str | Path | None = None,
    ) -> Path:
        """Resuelve el archivo de configuración por ruta explícita, perfil (--profile) o config.json."""
        if config_override is not None and str(config_override).strip():
            raw_override = Path(os.path.expandvars(str(config_override).strip()))
            override_candidates = (
                [raw_override]
                if raw_override.is_absolute()
                else [resolve_app_root() / raw_override, raw_override]
            )
            for candidate in override_candidates:
                if candidate.is_file():
                    return candidate.resolve()
            searched = ", ".join(str(p) for p in override_candidates)
            raise ConfigError(f"No se encontró el archivo de configuración especificado: {searched}")

        clean_profile = str(profile or "").strip().lower()
        filename = f"config.{clean_profile}.json" if clean_profile else "config.json"

        candidates: list[Path] = []
        if getattr(sys, "frozen", False):
            candidates.append(resolve_app_root() / filename)
            if hasattr(sys, "_MEIPASS"):
                candidates.append(resolve_bundle_root() / filename)
        else:
            candidates.append(resolve_app_root() / filename)

        for candidate in candidates:
            if candidate.is_file():
                return candidate

        searched = ", ".join(str(p) for p in candidates)
        raise ConfigError(f"No se encontró {filename} en ninguna ruta esperada: {searched}")

    @classmethod
    def load(
        cls,
        config_path: Path | None = None,
        profile: str | None = None,
        config_override: str | Path | None = None,
    ) -> "AppConfig":
        """Carga y valida config.json (o perfil/ruta indicada) priorizando archivo junto al ejecutable."""
        if config_path is None:
            config_path = cls.resolve_config_path(
                profile=profile,
                config_override=config_override,
            )

        if not config_path.is_file():
            raise ConfigError(f"El archivo de configuración no existe: {config_path}")

        try:
            raw = config_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"JSON inválido en {config_path}: {exc}") from exc
        except OSError as exc:
            raise ConfigError(f"No se pudo leer {config_path}: {exc}") from exc

        cls._validate(data, config_path)
        ensure_resources_dirs()
        return cls(data=data, source_path=config_path)

    @staticmethod
    def _validate(data: Any, config_path: Path) -> None:
        if not isinstance(data, dict):
            raise ConfigError(f"La raíz de {config_path} debe ser un objeto JSON.")

        missing = [key for key in REQUIRED_TOP_KEYS if key not in data]
        if missing:
            raise ConfigError(
                f"Faltan claves obligatorias en {config_path}: {', '.join(missing)}"
            )

        app_section = data.get("app")
        if not isinstance(app_section, dict):
            raise ConfigError("La sección 'app' debe ser un objeto JSON.")
        missing_app = [key for key in REQUIRED_APP_KEYS if key not in app_section]
        if missing_app:
            raise ConfigError(
                f"Faltan claves en 'app' de {config_path}: {', '.join(missing_app)}"
            )

        unc_section = data.get("unc_paths")
        if unc_section is not None and not isinstance(unc_section, dict):
            raise ConfigError("La sección 'unc_paths' debe ser un objeto JSON.")

        menus = data.get("menus")
        if not isinstance(menus, list) or not menus:
            raise ConfigError("La sección 'menus' debe ser una lista no vacía.")
        for menu in menus:
            if not isinstance(menu, dict) or not menu.get("id") or not menu.get("title"):
                raise ConfigError("Cada entrada de 'menus' debe definir 'id' y 'title'.")
            subgroups = menu.get("subgroups")
            if not isinstance(subgroups, list):
                raise ConfigError(f"El menú '{menu.get('id')}' debe contener una lista 'subgroups'.")

    @property
    def app(self) -> dict[str, Any]:
        return self._data["app"]

    @property
    def menus(self) -> list[dict[str, Any]]:
        return self._data["menus"]

    @property
    def registry(self) -> dict[str, Any]:
        return self._data["registry"]

    @property
    def security(self) -> dict[str, Any]:
        return self._data["security"]

    def get_servers(self) -> dict[str, dict[str, Any]]:
        if "corporate_servers" in self._data:
            corp = self._data["corporate_servers"]
            if isinstance(corp, list):
                result: dict[str, dict[str, Any]] = {}
                for idx, entry in enumerate(corp):
                    if isinstance(entry, dict) and entry.get("host"):
                        srv_id = str(entry.get("id") or f"server_{idx}")
                        result[srv_id] = entry
                return result
            if isinstance(corp, dict):
                return corp
            raise ConfigError("La sección 'corporate_servers' debe ser una lista o un diccionario.")

        servers = self._data.get("servers", {})
        if not isinstance(servers, dict):
            raise ConfigError("La sección 'servers' debe ser un diccionario.")
        return servers

    def get_server(self, key: str) -> dict[str, Any]:
        servers = self.get_servers()
        if key not in servers:
            raise ConfigError(f"Servidor no configurado en config.json: '{key}'")
        return servers[key]

    def get_allowed_unc_hosts(self) -> set[str]:
        """Devuelve el conjunto de hosts autorizados (en minúsculas) configurados en servers y security."""
        hosts: set[str] = set()
        for info in self.get_servers().values():
            host = str(info.get("host", "")).strip().lower()
            if host:
                hosts.add(host)
        extra_hosts = self.security.get("extra_allowed_unc_hosts", [])
        if isinstance(extra_hosts, list):
            for extra in extra_hosts:
                clean = str(extra).strip().lower()
                if clean:
                    hosts.add(clean)
        return hosts

    def get_install_checks(self) -> dict[str, dict[str, Any]]:
        """Devuelve el diccionario de verificaciones de software instalado."""
        checks = self._data.get("install_checks", {})
        return checks if isinstance(checks, dict) else {}

    def get_local_path_raw(self, key: str) -> str:
        local_paths = self._data.get("local_paths", {})
        if key not in local_paths:
            raise ConfigError(f"Ruta local no configurada en config.json: '{key}'")
        value = local_paths[key]
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"La ruta local '{key}' en config.json está vacía.")
        return value

    def resolve_path(self, raw_path: str) -> Path:
        """Expande variables de entorno y resuelve rutas relativas respecto a resolve_app_root()."""
        expanded = os.path.expandvars(str(raw_path).strip())
        if not expanded:
            return resolve_app_root()
        candidate = Path(expanded)
        if not candidate.is_absolute():
            return resolve_app_root() / candidate
        return candidate

    def get_local_path(self, key: str) -> Path:
        """Expande variables de entorno de Windows y retorna un Path relativo al ejecutable si aplica."""
        raw_value = self.get_local_path_raw(key)
        return self.resolve_path(raw_value)

    def get_unc(self, section: str, key: str) -> Any:
        unc_paths = self._data.get("unc_paths", {})
        if section not in unc_paths:
            raise ConfigError(f"Sección UNC no configurada: '{section}'")
        section_data = unc_paths[section]
        if key not in section_data:
            raise ConfigError(f"Clave UNC no configurada: '{section}.{key}'")
        return section_data[key]

    def get_url_info(self, key: str) -> dict[str, Any]:
        urls = self._data.get("urls", {})
        if key not in urls:
            raise ConfigError(f"URL de descarga no configurada: '{key}'")
        info = urls[key]
        if not isinstance(info, dict) or not info.get("url") or not info.get("filename"):
            raise ConfigError(f"Entrada de URL inválida en config.json: '{key}'")
        return info

    @staticmethod
    def get_downloads_dir() -> Path:
        return _get_known_folder_path(_FOLDERID_DOWNLOADS, Path.home() / "Downloads")

    @staticmethod
    def get_pictures_dir() -> Path:
        return _get_known_folder_path(_FOLDERID_PICTURES, Path.home() / "Pictures")

    @staticmethod
    def get_desktop_dir() -> Path:
        return _get_known_folder_path(_FOLDERID_DESKTOP, Path.home() / "Desktop")

    @staticmethod
    def get_asset_path(filename: str) -> Path:
        external_asset = resolve_app_root() / "assets" / filename
        if external_asset.is_file():
            return external_asset
        return resolve_bundle_root() / "assets" / filename

    @staticmethod
    def get_asset_dir(dirname: str) -> Path:
        """Resuelve un directorio de recursos priorizando la carpeta externa junto al ejecutable."""
        external_dir = resolve_app_root() / "assets" / dirname
        if external_dir.is_dir():
            return external_dir
        return resolve_bundle_root() / "assets" / dirname

    def get_default_credentials_enc_path(self) -> Path:
        """Retorna la ruta local predeterminada para credentials.enc junto a la app."""
        filename = self.get_local_path_raw("credentials_enc_file")
        return resolve_app_root() / filename

    def resolve_credentials_enc_path(self) -> Path | None:
        """Busca credentials.enc por orden: externo junto al .exe (o padre de dist\\), empaquetado (_MEIPASS) o UNC."""
        filename = self.get_local_path_raw("credentials_enc_file")
        app_root = resolve_app_root()
        candidates: list[Path] = [app_root / filename]
        if app_root.name.lower() == "dist" and app_root.parent != app_root:
            candidates.append(app_root.parent / filename)
        candidates.append(resolve_bundle_root() / filename)

        try:
            unc_raw = str(self.get_unc("eidico", "credentials_enc_unc") or "").strip()
            if unc_raw:
                candidates.append(Path(unc_raw))
        except ConfigError:
            pass

        for candidate in candidates:
            try:
                if os.path.isfile(candidate):
                    return candidate
            except OSError:
                continue
        return None

    def get_printers_config(self) -> dict[str, Any]:
        """Retorna la sección de configuración de impresoras de red."""
        printers = self._data.get("printers", {})
        if not isinstance(printers, dict):
            raise ConfigError("La sección 'printers' en config.json debe ser un objeto.")
        return printers

    def get_inventory_config(self) -> dict[str, Any]:
        """Retorna y valida la sección de configuración del módulo de inventario."""
        inventory = self._data.get("inventory", {})
        if not isinstance(inventory, dict):
            raise ConfigError("La sección 'inventory' en config.json debe ser un objeto.")

        network_dir = str(inventory.get("network_dir", "")).strip()
        output_filename = str(inventory.get("output_filename", "")).strip()
        if not network_dir or not output_filename:
            raise ConfigError(
                "La sección 'inventory' debe definir 'network_dir' y 'output_filename' no vacíos."
            )

        raw_props = inventory.get("property_options", [])
        if isinstance(raw_props, list) and raw_props:
            property_options = [str(p).strip() for p in raw_props if str(p).strip()]
        else:
            property_options = ["EIDICO", "Urbis", "Órbita", "Personal", "Barrio"]

        return {
            "network_dir": network_dir,
            "output_filename": output_filename,
            "property_options": property_options,
        }

    def get_vpn_endpoints(self) -> dict[str, dict[str, Any]]:
        """Retorna y valida los enlaces VPN configurados en vpn_profiles o vpn_endpoints."""
        if "vpn_profiles" in self._data:
            raw_profiles = self._data["vpn_profiles"]
            if isinstance(raw_profiles, list):
                if not raw_profiles:
                    return {}
                raw: dict[str, Any] = {
                    str(entry.get("id") or entry.get("key") or f"vpn_{idx}"): entry
                    for idx, entry in enumerate(raw_profiles)
                    if isinstance(entry, dict)
                }
            elif isinstance(raw_profiles, dict):
                raw = raw_profiles
            else:
                raise ConfigError("La sección 'vpn_profiles' en config.json debe ser una lista o un objeto.")
        else:
            raw = self._data.get("vpn_endpoints", {})
            if not isinstance(raw, dict):
                raise ConfigError("La sección 'vpn_endpoints' en config.json debe ser un objeto.")

        validated: dict[str, dict[str, Any]] = {}
        for key, entry in raw.items():
            if not isinstance(entry, dict):
                raise ConfigError(f"El enlace VPN '{key}' debe ser un objeto JSON.")
            name = str(entry.get("name", "")).strip()
            host = str(entry.get("host", "")).strip()
            ip_str = str(entry.get("ip", "")).strip()
            if not name or not ip_str:
                raise ConfigError(f"El enlace VPN '{key}' debe definir 'name' e 'ip'.")
            try:
                ipaddress.ip_address(ip_str)
            except ValueError as exc:
                raise ConfigError(f"IP inválida en vpn_endpoints.{key}: '{ip_str}'") from exc
            try:
                port = int(entry.get("port", 0))
            except (TypeError, ValueError) as exc:
                raise ConfigError(f"Puerto inválido en vpn_endpoints.{key}") from exc
            if not (1 <= port <= 65535):
                raise ConfigError(f"Puerto fuera de rango (1-65535) en vpn_endpoints.{key}: {port}")
            protocol = str(entry.get("protocol", "tcp")).strip().lower() or "tcp"
            if protocol not in ("tcp", "udp"):
                raise ConfigError(
                    f"Protocolo inválido en vpn_endpoints.{key}: '{protocol}' (usar 'tcp' o 'udp')"
                )

            validated[str(key)] = {
                "key": str(key),
                "name": name,
                "host": host,
                "ip": ip_str,
                "port": port,
                "protocol": protocol,
            }
        return validated

    def get_vpn_endpoint(self, key: str) -> dict[str, Any]:
        """Retorna un enlace VPN validado por clave."""
        endpoints = self.get_vpn_endpoints()
        if key not in endpoints:
            raise ConfigError(f"Enlace VPN no configurado en config.json: '{key}'")
        return endpoints[key]
