"""Carga y validación centralizada de config.json para EzSetup."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
from typing import Any


class ConfigError(Exception):
    """Error producido al cargar o validar config.json."""


REQUIRED_TOP_KEYS = (
    "app",
    "servers",
    "local_paths",
    "registry",
    "security",
    "urls",
    "unc_paths",
    "menus",
)

REQUIRED_APP_KEYS = (
    "name",
    "version",
    "title",
    "copy_chunk_size_bytes",
    "server_check_interval_ms",
)

REQUIRED_UNC_SECTIONS = ("eidico", "tecnica", "office", "adobe")

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


class AppConfig:
    """Contenedor validado e inmutable de la configuración de EzSetup."""

    def __init__(self, data: dict[str, Any], source_path: Path) -> None:
        self._data = data
        self.source_path = source_path

    @classmethod
    def load(cls, config_path: Path | None = None) -> "AppConfig":
        """Carga y valida config.json priorizando un archivo externo junto al ejecutable."""
        if config_path is None:
            external_cfg = resolve_app_root() / "config.json"
            bundled_cfg = resolve_bundle_root() / "config.json"
            if external_cfg.is_file():
                config_path = external_cfg
            elif bundled_cfg.is_file():
                config_path = bundled_cfg
            else:
                raise ConfigError(
                    f"No se encontró config.json en {external_cfg} ni en {bundled_cfg}."
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
        if not isinstance(unc_section, dict):
            raise ConfigError("La sección 'unc_paths' debe ser un objeto JSON.")
        missing_unc = [key for key in REQUIRED_UNC_SECTIONS if key not in unc_section]
        if missing_unc:
            raise ConfigError(
                f"Faltan subsecciones en 'unc_paths': {', '.join(missing_unc)}"
            )

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
        servers = self._data.get("servers", {})
        if not isinstance(servers, dict):
            raise ConfigError("La sección 'servers' debe ser un diccionario.")
        return servers

    def get_server(self, key: str) -> dict[str, Any]:
        servers = self.get_servers()
        if key not in servers:
            raise ConfigError(f"Servidor no configurado en config.json: '{key}'")
        return servers[key]

    def get_local_path_raw(self, key: str) -> str:
        local_paths = self._data.get("local_paths", {})
        if key not in local_paths:
            raise ConfigError(f"Ruta local no configurada en config.json: '{key}'")
        value = local_paths[key]
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"La ruta local '{key}' en config.json está vacía.")
        return value

    def get_local_path(self, key: str) -> Path:
        """Expande variables de entorno de Windows y retorna un Path."""
        raw_value = self.get_local_path_raw(key)
        expanded = os.path.expandvars(raw_value)
        return Path(expanded)

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

    def get_default_credentials_enc_path(self) -> Path:
        """Retorna la ruta local predeterminada para credentials.enc junto a la app."""
        filename = self.get_local_path_raw("credentials_enc_file")
        return resolve_app_root() / filename

    def resolve_credentials_enc_path(self) -> Path | None:
        """Busca credentials.enc en el directorio local, empaquetado o ruta UNC configurada."""
        filename = self.get_local_path_raw("credentials_enc_file")
        candidates: list[Path] = [
            resolve_app_root() / filename,
            resolve_bundle_root() / filename,
        ]
        try:
            unc_raw = str(self.get_unc("eidico", "credentials_enc_unc") or "").strip()
            if unc_raw:
                candidates.append(Path(unc_raw))
        except ConfigError:
            pass

        for candidate in candidates:
            try:
                if candidate.is_file():
                    return candidate
            except OSError:
                continue
        return None
