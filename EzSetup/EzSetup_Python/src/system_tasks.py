"""Tareas administrativas y de sistema para Windows 10/11 en EzSetup."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
from typing import Any, Callable
import winreg
import zipfile

import pythoncom
import pywintypes
import win32api
import win32com.client
import win32security
import ntsecuritycon

from src.config import AppConfig

LogCallback = Callable[[str], None]

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
_REGISTERED_TEMP_DIRS: set[Path] = set()
_TEMP_LOCK = threading.Lock()
UAC_PERMISSION_MSG = "Permisos insuficientes. Ejecutá EzSetup como Administrador (clic en 'Sin UAC')."


class UnauthorizedUNCHostError(PermissionError):
    """Error lanzado cuando una ruta UNC apunta a un host no autorizado en config.json."""


def format_task_exception(exc: Exception) -> str:
    """Traduce errores de permisos de Windows a un mensaje amigable UAC."""
    if isinstance(exc, UnauthorizedUNCHostError):
        return str(exc)
    if isinstance(exc, PermissionError):
        return UAC_PERMISSION_MSG
    if isinstance(exc, pywintypes.error) and getattr(exc, "winerror", None) == 5:
        return UAC_PERMISSION_MSG
    if isinstance(exc, OSError) and (getattr(exc, "winerror", None) == 5 or exc.errno == 13):
        return UAC_PERMISSION_MSG
    return str(exc)


def _noop_log(_: str) -> None:
    """Callback por defecto cuando no se provee logger."""


def register_temp_dir(path: Path) -> Path:
    """Registra una carpeta temporal para su limpieza automática al cerrar la app."""
    with _TEMP_LOCK:
        _REGISTERED_TEMP_DIRS.add(path)
    return path


def unregister_temp_dir(path: Path) -> None:
    """Elimina una carpeta temporal del registro tras ser limpiada."""
    with _TEMP_LOCK:
        _REGISTERED_TEMP_DIRS.discard(path)


def cleanup_registered_temp_dirs(log: LogCallback = _noop_log) -> int:
    """Limpia cualquier carpeta temporal registrada que permanezca en disco."""
    with _TEMP_LOCK:
        targets = list(_REGISTERED_TEMP_DIRS)
        _REGISTERED_TEMP_DIRS.clear()

    cleaned = 0
    for target in targets:
        try:
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
                cleaned += 1
                log(f"[INFO] Carpeta temporal limpiada al cerrar: {target}")
        except OSError:
            pass
    return cleaned


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


def _ensure_unc_exists(
    path_str: str,
    label: str,
    config: AppConfig | None = None,
) -> Path:
    if not path_str or not path_str.strip():
        raise ValueError(
            f"La ruta de '{label}' está vacía en config.json. "
            "Completala antes de ejecutar esta tarea."
        )
    if config is not None:
        validate_unc_host(path_str, config.get_allowed_unc_hosts())
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(
            f"No se pudo acceder a '{label}' en la ruta configurada: {path_str}"
        )
    return path


def _launch_detached(executable: Path | str, args: list[str] | None = None, cwd: Path | None = None) -> None:
    cmd = [str(executable)]
    if args:
        cmd.extend(args)
    subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        shell=False,
        close_fds=True,
    )


def write_vbs_file(target_path: Path, content: str) -> None:
    """Escribe un archivo .vbs usando estrictamente codificación Windows-1252 (cp1252)."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="cp1252")


# ---------------------------------------------------------------------------
# Credenciales de Windows (cmdkey) y Accesos Directos
# ---------------------------------------------------------------------------

def register_server_credential(
    config: AppConfig,
    server_key: str,
    username: str,
    password: str,
    create_shortcut: bool = True,
    log: LogCallback = _noop_log,
) -> str:
    """Registra credenciales en el Administrador de Credenciales de Windows (cmdkey)."""
    server = config.get_server(server_key)
    host = str(server["host"]).strip()
    label = str(server.get("label", host))

    clean_user = username.strip()
    if not clean_user or not password:
        raise ValueError("El usuario y la contraseña no pueden estar vacíos.")

    log(f"[INFO] Purgando sesiones SMB/Kerberos previas para {host}...")
    cleanup_commands = [
        ["net", "use", f"\\\\{host}", "/delete", "/y"],
        ["net", "use", f"\\\\{host}\\*", "/delete", "/y"],
        ["klist", "purge"],
        ["cmdkey", f"/delete:{host}"],
    ]
    for cmd in cleanup_commands:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,
            creationflags=_CREATE_NO_WINDOW,
        )

    log(f"[INFO] Registrando credenciales para {label} (usuario: {clean_user})...")
    result = subprocess.run(
        ["cmdkey", f"/add:{host}", f"/user:{clean_user}", f"/pass:{password}"],
        capture_output=True,
        text=True,
        shell=False,
        creationflags=_CREATE_NO_WINDOW,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"Error al registrar credencial en {host}: {detail}")

    log(f"[OK] Credencial registrada para {host}.")

    if create_shortcut and isinstance(server.get("desktop_shortcut"), dict):
        _create_desktop_shortcut(config, server["desktop_shortcut"], log)

    return f"Credenciales registradas correctamente para {label}."


def _create_desktop_shortcut(
    config: AppConfig,
    shortcut_cfg: dict[str, str],
    log: LogCallback = _noop_log,
) -> Path:
    desktop_dir = config.get_desktop_dir()
    desktop_dir.mkdir(parents=True, exist_ok=True)
    shortcut_path = desktop_dir / shortcut_cfg["name"]

    pythoncom.CoInitialize()
    shell = None
    shortcut = None
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(str(shortcut_path))
        shortcut.TargetPath = shortcut_cfg["target"]
        shortcut.Description = shortcut_cfg.get("description", "")
        icon = shortcut_cfg.get("icon", "")
        if icon:
            shortcut.IconLocation = icon
        shortcut.Save()
    finally:
        shortcut = None
        shell = None
        pythoncom.CoUninitialize()

    log(f"[OK] Acceso directo creado en Escritorio: {shortcut_path.name}")
    return shortcut_path


def open_credential_manager(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Abre el Administrador de Credenciales de Windows."""
    shell_uri = config.get_local_path_raw("credential_manager_shell")
    log("[INFO] Abriendo Administrador de Credenciales de Windows...")
    _launch_detached("explorer.exe", [shell_uri])
    return "Administrador de Credenciales abierto."


# ---------------------------------------------------------------------------
# Sistema Contable (Fox / EIDICO)
# ---------------------------------------------------------------------------

def run_fox_installer_lan(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Ejecuta el instalador de Fox EIDICO desde la red local."""
    installer = _ensure_unc_exists(
        config.get_unc("eidico", "fox_installer_exe"),
        "Instalador Sistema Contable Fox",
        config=config,
    )
    log(f"[INFO] Ejecutando instalador: {installer}")
    _launch_detached(installer, cwd=installer.parent)
    return "Instalador de Sistema Contable iniciado."


def fix_eidico_shortcut(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Corrige el campo 'Iniciar en' (WorkingDirectory) de Eidico.lnk en el Escritorio."""
    configured_lnk = config.get_local_path("eidico_desktop_lnk")
    if configured_lnk.is_file():
        lnk_path = configured_lnk
    else:
        fallback_lnk = config.get_desktop_dir() / configured_lnk.name
        if fallback_lnk.is_file():
            lnk_path = fallback_lnk
        else:
            raise FileNotFoundError(
                f"No se encontró el acceso directo {configured_lnk.name} en {configured_lnk.parent} "
                f"ni en {fallback_lnk.parent}."
            )

    workdir = str(config.get_local_path("eidico_dir"))
    if not workdir.endswith("\\"):
        workdir += "\\"

    log(f"[INFO] Actualizando 'Iniciar en' de {lnk_path} -> {workdir}")
    pythoncom.CoInitialize()
    shell = None
    shortcut = None
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(str(lnk_path))
        shortcut.WorkingDirectory = workdir
        shortcut.Save()
    finally:
        shortcut = None
        shell = None
        pythoncom.CoUninitialize()

    log("[OK] Campo 'Iniciar en' de Eidico.lnk actualizado correctamente.")
    return "Acceso directo Eidico.lnk actualizado."


def set_sol_sistemas_permissions(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Asigna permisos FullControl al grupo Users (SID S-1-5-32-545) en Sol Sistemas."""
    target_dir = config.get_local_path("sol_sistemas_dir")
    if not target_dir.exists():
        raise FileNotFoundError(f"La carpeta objetivo no existe: {target_dir}")

    sid_str = str(config.security["users_group_sid"])
    sid = win32security.ConvertStringSidToSid(sid_str)
    account_name, domain, _ = win32security.LookupAccountSid(None, sid)
    display_group = f"{domain}\\{account_name}" if domain else account_name

    log(f"[INFO] Aplicando permisos FullControl a '{display_group}' ({sid_str}) en {target_dir}...")

    sd = win32security.GetFileSecurity(
        str(target_dir),
        win32security.DACL_SECURITY_INFORMATION,
    )
    dacl = sd.GetSecurityDescriptorDacl()
    if dacl is None:
        dacl = win32security.ACL()

    # Eliminar ACEs previos del mismo SID antes de insertar la regla limpia
    for idx in range(dacl.GetAceCount() - 1, -1, -1):
        ace = dacl.GetAce(idx)
        if len(ace) >= 3 and ace[2] == sid:
            dacl.DeleteAce(idx)

    inheritance_flags = (
        win32security.CONTAINER_INHERIT_ACE | win32security.OBJECT_INHERIT_ACE
    )
    dacl.AddAccessAllowedAceEx(
        win32security.ACL_REVISION,
        inheritance_flags,
        ntsecuritycon.FILE_ALL_ACCESS,
        sid,
    )

    win32security.SetNamedSecurityInfo(
        str(target_dir),
        win32security.SE_FILE_OBJECT,
        win32security.DACL_SECURITY_INFORMATION,
        None,
        None,
        dacl,
        None,
    )

    log(f"[OK] Permisos FullControl aplicados correctamente a '{display_group}'.")
    return f"Permisos aplicados a '{display_group}' en {target_dir}."


def copy_eidico_vbs(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Copia EIDICO.vbs a la carpeta local de EIDICO."""
    source = _ensure_unc_exists(
        config.get_unc("eidico", "eidico_vbs"),
        "EIDICO.vbs",
        config=config,
    )
    dest_dir = config.get_local_path("eidico_dir")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / source.name

    log(f"[INFO] Copiando {source} -> {dest_file}")
    shutil.copy2(source, dest_file)
    log("[OK] EIDICO.vbs copiado correctamente.")
    return f"EIDICO.vbs copiado en {dest_dir}."


def extract_produccion_zip(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Extrae Produccion.zip desde la red en la carpeta local de EIDICO."""
    zip_path = _ensure_unc_exists(
        config.get_unc("eidico", "produccion_zip"),
        "Produccion.zip",
        config=config,
    )
    dest_dir = config.get_local_path("eidico_dir")
    dest_dir.mkdir(parents=True, exist_ok=True)

    log(f"[INFO] Extrayendo {zip_path} en {dest_dir}...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)
    log("[OK] Produccion.zip extraído correctamente.")
    return f"Produccion.zip extraído en {dest_dir}."


# ---------------------------------------------------------------------------
# FortiClient y AWS VPN Client
# ---------------------------------------------------------------------------

def _extract_zip_member(
    zf: zipfile.ZipFile,
    target_filename: str,
    dest_dir: Path,
) -> Path | None:
    """Busca y extrae un archivo específico (por nombre) desde un ZipFile."""
    matches = [
        member
        for member in zf.namelist()
        if Path(member).name.lower() == target_filename.lower() and not member.endswith("/")
    ]
    if not matches:
        return None
    return Path(zf.extract(matches[0], dest_dir))


def import_reg_file(reg_path: Path, log: LogCallback = _noop_log) -> None:
    """Importa silenciosamente un archivo .reg al Registro de Windows mediante regedit /s."""
    log(f"[INFO] Importando configuración de registro silenciosamente: {reg_path.name}")
    result = subprocess.run(
        ["regedit.exe", "/s", str(reg_path)],
        capture_output=True,
        text=True,
        shell=False,
        creationflags=_CREATE_NO_WINDOW,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"Error al importar {reg_path.name}: {detail}")
    log(f"[OK] Archivo {reg_path.name} importado silenciosamente al Registro de Windows.")


def process_forticlient_zip(
    zip_path: Path,
    msi_name: str | None = None,
    reg_name: str | None = None,
    install_msi: bool = False,
    import_reg: bool = False,
    log: LogCallback = _noop_log,
) -> tuple[bool, bool]:
    """Extrae un paquete ZIP de FortiClient a una carpeta temporal, ejecuta MSI / .reg y limpia."""
    msi_ran = False
    reg_imported = False

    if not zip_path.is_file():
        raise FileNotFoundError(f"No se encontró el paquete ZIP de FortiClient: {zip_path}")

    with tempfile.TemporaryDirectory(prefix="ezsetup_forti_") as tmp_dir:
        tmp_path = register_temp_dir(Path(tmp_dir))
        try:
            log("[INFO] Extrayendo paquete FortiClient en carpeta temporal...")
            with zipfile.ZipFile(zip_path, "r") as zf:
                if install_msi and msi_name:
                    extracted_msi = _extract_zip_member(zf, msi_name, tmp_path)
                    if extracted_msi and extracted_msi.is_file():
                        log(f"[INFO] Ejecutando instalador MSI: {extracted_msi.name}")
                        proc = subprocess.run(
                            ["msiexec.exe", "/i", str(extracted_msi)],
                            cwd=str(extracted_msi.parent),
                            shell=False,
                        )
                        if proc.returncode not in (0, 3010):
                            log(
                                f"[ADVERTENCIA] El instalador MSI finalizó con código {proc.returncode}."
                            )
                        else:
                            log("[OK] Instalador MSI de FortiClient finalizado.")
                        msi_ran = True
                    else:
                        log(f"[ADVERTENCIA] No se encontró '{msi_name}' dentro de {zip_path.name}.")

                if import_reg and reg_name:
                    extracted_reg = _extract_zip_member(zf, reg_name, tmp_path)
                    if extracted_reg and extracted_reg.is_file():
                        import_reg_file(extracted_reg, log)
                        reg_imported = True
                    else:
                        log(f"[ADVERTENCIA] No se encontró '{reg_name}' dentro de {zip_path.name}.")
        finally:
            unregister_temp_dir(tmp_path)

    log("[INFO] Archivos temporales de FortiClient eliminados.")
    return msi_ran, reg_imported


def install_forticlient_lan(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Extrae el MSI de FortiClient desde el paquete ZIP en red y lo ejecuta."""
    zip_path = _ensure_unc_exists(
        config.get_unc("eidico", "forticlient_zip"),
        "Paquete FortiClient ZIP",
        config=config,
    )
    msi_name = str(config.get_unc("eidico", "forticlient_msi_name"))
    msi_ran, _ = process_forticlient_zip(
        zip_path=zip_path,
        msi_name=msi_name,
        install_msi=True,
        import_reg=False,
        log=log,
    )
    if not msi_ran:
        raise FileNotFoundError(
            f"No se encontró el instalador '{msi_name}' dentro de {zip_path.name}."
        )
    return "Instalación de FortiClient completada."


def import_forticlient_reg_lan(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Extrae e importa silenciosamente VPN Config.reg desde el paquete ZIP en red."""
    zip_path = _ensure_unc_exists(
        config.get_unc("eidico", "forticlient_zip"),
        "Paquete FortiClient ZIP",
        config=config,
    )
    reg_name = str(config.get_unc("eidico", "forticlient_reg_name"))
    _, reg_imported = process_forticlient_zip(
        zip_path=zip_path,
        reg_name=reg_name,
        install_msi=False,
        import_reg=True,
        log=log,
    )
    if not reg_imported:
        raise FileNotFoundError(
            f"No se encontró '{reg_name}' dentro de {zip_path.name}."
        )
    return f"Configuración '{reg_name}' importada correctamente."


def install_and_configure_forticlient_lan(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Extrae el ZIP en red, ejecuta el MSI de FortiClient, importa VPN Config.reg y limpia temporales."""
    zip_path = _ensure_unc_exists(
        config.get_unc("eidico", "forticlient_zip"),
        "Paquete FortiClient ZIP",
        config=config,
    )
    msi_name = str(config.get_unc("eidico", "forticlient_msi_name"))
    reg_name = str(config.get_unc("eidico", "forticlient_reg_name"))
    msi_ran, reg_imported = process_forticlient_zip(
        zip_path=zip_path,
        msi_name=msi_name,
        reg_name=reg_name,
        install_msi=True,
        import_reg=True,
        log=log,
    )
    if not msi_ran or not reg_imported:
        raise FileNotFoundError(
            f"Faltan archivos requeridos ({msi_name} / {reg_name}) en {zip_path.name}."
        )
    return "FortiClient instalado y VPN Config.reg importado."


def import_reg_from_zip(zip_path: Path, reg_name: str, log: LogCallback = _noop_log) -> bool:
    """Busca e importa un archivo .reg contenido dentro de un .zip descargado."""
    _, reg_imported = process_forticlient_zip(
        zip_path=zip_path,
        reg_name=reg_name,
        install_msi=False,
        import_reg=True,
        log=log,
    )
    return reg_imported


def install_aws_vpn_lan(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Ejecuta el instalador MSI de AWS VPN Client desde la red."""
    msi_path = _ensure_unc_exists(
        config.get_unc("eidico", "aws_vpn_msi"),
        "AWS VPN Client MSI",
        config=config,
    )
    log(f"[INFO] Ejecutando msiexec /i {msi_path}")
    _launch_detached("msiexec.exe", ["/i", str(msi_path)])
    return "Instalador de AWS VPN Client iniciado."


# ---------------------------------------------------------------------------
# .NET Framework 3.5, detección de software instalado y WinSCP
# ---------------------------------------------------------------------------

def check_dotnet35_installed(config: AppConfig) -> bool:
    """Verifica en el Registro de Windows si .NET Framework 3.5 está instalado."""
    reg_key = str(config.registry["dotnet35_key"])
    value_name = str(config.registry["dotnet35_value"])
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_key, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, value_name)
            return int(val) == 1
    except OSError:
        return False


def _get_file_version(file_path: Path) -> str:
    """Lee la versión de un ejecutable/DLL de Windows mediante GetFileVersionInfo."""
    if os.name != "nt" or not file_path.is_file():
        return ""
    try:
        info = win32api.GetFileVersionInfo(str(file_path), "\\")
        ms = int(info["FileVersionMS"])
        ls = int(info["FileVersionLS"])
        parts = [ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF]
        return ".".join(str(p) for p in parts[:3]) if parts[3] == 0 else ".".join(str(p) for p in parts)
    except Exception:
        return ""


def _read_reg_str(key: Any, value_name: str) -> str:
    try:
        val, _ = winreg.QueryValueEx(key, value_name)
        return str(val).strip()
    except OSError:
        return ""


def check_software_installed(config: AppConfig) -> dict[str, dict[str, Any]]:
    """Verifica en disco, servicios y registro qué programas configurados están instalados."""
    results: dict[str, dict[str, Any]] = {}
    uninstall_roots: list[str] = list(config.registry.get("uninstall_roots", []))
    services_root = str(config.registry.get("services_root", "")).strip()

    for item_id, spec in config.get_install_checks().items():
        found = False
        version = ""

        for raw_path in spec.get("paths", []):
            expanded = os.path.expandvars(str(raw_path))
            if not expanded:
                continue
            candidate = Path(expanded)
            try:
                if candidate.exists():
                    found = True
                    version = _get_file_version(candidate)
                    break
            except OSError:
                continue

        if os.name == "nt" and services_root:
            for svc_name in spec.get("services", []):
                svc_key_path = f"{services_root}\\{svc_name}"
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, svc_key_path, 0, winreg.KEY_READ) as key:
                        found = True
                        if not version:
                            img_path = _read_reg_str(key, "ImagePath").strip('"')
                            if img_path:
                                exe_part = img_path.split(".exe", 1)[0] + ".exe" if ".exe" in img_path.lower() else img_path
                                version = _get_file_version(Path(os.path.expandvars(exe_part)))
                        break
                except OSError:
                    continue

        if os.name == "nt" and (not found or not version):
            for reg_subkey in spec.get("reg_keys", []):
                for view_flag in (0, winreg.KEY_WOW64_32KEY):
                    try:
                        with winreg.OpenKey(
                            winreg.HKEY_LOCAL_MACHINE,
                            str(reg_subkey),
                            0,
                            winreg.KEY_READ | view_flag,
                        ) as key:
                            found = True
                            if not version:
                                version = _read_reg_str(key, "DisplayVersion") or _read_reg_str(key, "Version")
                            break
                    except OSError:
                        continue
                if found and version:
                    break

        if os.name == "nt" and spec.get("uninstall_names") and (not found or not version):
            needles = [str(n).lower() for n in spec.get("uninstall_names", []) if str(n).strip()]
            for root_hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                for root_subkey in uninstall_roots:
                    try:
                        with winreg.OpenKey(root_hive, root_subkey, 0, winreg.KEY_READ) as root_key:
                            idx = 0
                            while True:
                                try:
                                    sub_name = winreg.EnumKey(root_key, idx)
                                    idx += 1
                                except OSError:
                                    break
                                try:
                                    with winreg.OpenKey(root_key, sub_name, 0, winreg.KEY_READ) as app_key:
                                        display_name = _read_reg_str(app_key, "DisplayName").lower()
                                        if display_name and any(n in display_name for n in needles):
                                            found = True
                                            if not version:
                                                version = _read_reg_str(app_key, "DisplayVersion")
                                            break
                                except OSError:
                                    continue
                    except OSError:
                        continue
                    if found and version:
                        break
                if found and version:
                    break

        results[str(item_id)] = {"installed": found, "version": version}
    return results


def open_optional_features(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Abre Características de Windows (optionalfeatures.exe) verificando estado de .NET 3.5."""
    installed = check_dotnet35_installed(config)
    if installed:
        log("[INFO] .NET Framework 3.5 ya se encuentra instalado en el equipo.")
    else:
        log("[ADVERTENCIA] .NET Framework 3.5 NO está instalado. Habilítelo en la ventana.")

    exe_name = config.get_local_path_raw("optional_features_exe")
    log(f"[INFO] Abriendo {exe_name}...")
    _launch_detached(exe_name)
    return "Características de Windows abiertas."


def install_winscp_lan(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Ejecuta el instalador de WinSCP desde la red."""
    installer = _ensure_unc_exists(
        config.get_unc("eidico", "winscp_installer_exe"),
        "Instalador WinSCP",
        config=config,
    )
    log(f"[INFO] Ejecutando instalador de WinSCP: {installer}")
    _launch_detached(installer, cwd=installer.parent)
    return "Instalador de WinSCP iniciado."


def copy_winscp_to_dotnet(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Copia WinSCPnet.dll y WINSCP.exe a la carpeta .NET Framework v4.0.30319."""
    source_dir = _ensure_unc_exists(
        config.get_unc("eidico", "winscp_dir"),
        "Carpeta WinSCP",
        config=config,
    )
    target_dir = config.get_local_path("dotnet_framework_dir")
    if not target_dir.is_dir():
        raise FileNotFoundError(f"No se encontró el directorio .NET: {target_dir}")

    files: list[str] = list(config.get_unc("eidico", "winscp_files"))
    for filename in files:
        src = source_dir / filename
        if not src.is_file():
            raise FileNotFoundError(f"No se encontró el archivo requerido: {src}")
        dst = target_dir / filename
        log(f"[INFO] Copiando {src} -> {dst}")
        shutil.copy2(src, dst)

    log("[OK] Archivos de WinSCP copiados a .NET v4.0.30319.")
    return "Archivos de WinSCP copiados correctamente."


def register_winscp_regasm(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Verifica .NET 3.5 y registra WinSCPnet.dll con RegAsm.exe /codebase /tlb."""
    if check_dotnet35_installed(config):
        log("[INFO] .NET Framework 3.5 se encuentra instalado correctamente.")
    else:
        log("[ADVERTENCIA] .NET Framework 3.5 NO se encuentra instalado.")

    framework_dir = config.get_local_path("dotnet_framework_dir")
    regasm_exe = config.get_local_path("regasm_exe")
    if not regasm_exe.is_file():
        raise FileNotFoundError(f"No se encontró RegAsm.exe en {regasm_exe}")

    dll_path = framework_dir / "WinSCPnet.dll"
    if not dll_path.is_file():
        raise FileNotFoundError(
            f"WinSCPnet.dll no está presente en {framework_dir}. Copiá los archivos primero."
        )

    log(f"[INFO] Ejecutando: {regasm_exe} WinSCPnet.dll /codebase /tlb")
    result = subprocess.run(
        [str(regasm_exe), "WinSCPnet.dll", "/codebase", "/tlb"],
        cwd=str(framework_dir),
        capture_output=True,
        text=True,
        shell=False,
        creationflags=_CREATE_NO_WINDOW,
    )
    for line in (result.stdout or "").splitlines():
        if line.strip():
            log(f"  {line}")
    for line in (result.stderr or "").splitlines():
        if line.strip():
            log(f"  [STDERR] {line}")

    if result.returncode != 0:
        raise RuntimeError(f"RegAsm.exe finalizó con código de error {result.returncode}.")

    log("[OK] WinSCPnet.dll registrada correctamente con RegAsm.")
    return "WinSCPnet.dll registrada correctamente."


def copy_and_register_winscp(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Copia los binarios de WinSCP a .NET y ejecuta RegAsm en secuencia."""
    copy_winscp_to_dotnet(config, log)
    register_winscp_regasm(config, log)
    return "WinSCP copiado y registrado correctamente."


# ---------------------------------------------------------------------------
# OpenVPN, Nitro PDF (sin patch) y Fondos Eidico
# ---------------------------------------------------------------------------

def install_openvpn_lan(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Ejecuta el instalador de OpenVPN desde la red."""
    installer = _ensure_unc_exists(
        config.get_unc("eidico", "openvpn_installer_exe"),
        "Instalador OpenVPN",
        config=config,
    )
    log(f"[INFO] Ejecutando instalador de OpenVPN: {installer}")
    _launch_detached(installer, cwd=installer.parent)
    return "Instalador de OpenVPN iniciado."


def copy_openvpn_configs(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Copia los certificados y perfiles de configuración a la carpeta config de OpenVPN."""
    source_dir = _ensure_unc_exists(
        config.get_unc("eidico", "openvpn_dir"),
        "Carpeta OpenVPN",
        config=config,
    )
    dest_dir = config.get_local_path("openvpn_config_dir")
    dest_dir.mkdir(parents=True, exist_ok=True)

    config_files: list[str] = list(config.get_unc("eidico", "openvpn_config_files"))
    for filename in config_files:
        src = source_dir / filename
        if not src.is_file():
            raise FileNotFoundError(f"Archivo de configuración OpenVPN faltante: {src}")
        dst = dest_dir / filename
        log(f"[INFO] Copiando {filename} -> {dst}")
        shutil.copy2(src, dst)

    log("[OK] Archivos de configuración de OpenVPN copiados correctamente.")
    return f"Archivos OpenVPN copiados en {dest_dir}."


def install_nitropdf_lan(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Extrae NitroPDF.zip (omitiendo cualquier patch) y lanza el instalador MSI oficial."""
    zip_path = _ensure_unc_exists(
        config.get_unc("eidico", "nitropdf_zip"),
        "NitroPDF.zip",
        config=config,
    )
    msi_name = str(config.get_unc("eidico", "nitropdf_msi_name"))
    extract_dir = config.get_local_path("nitro_temp_extract_dir")
    extract_dir.mkdir(parents=True, exist_ok=True)
    register_temp_dir(extract_dir)

    log(f"[INFO] Extrayendo instalador de {zip_path} en {extract_dir}...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            member_name_lower = Path(member.filename).name.lower()
            # Seguridad: omitir cualquier paquete de patch/crack al descomprimir
            if "patch" in member_name_lower or "crack" in member_name_lower:
                continue
            zf.extract(member, extract_dir)

    msi_path = extract_dir / msi_name
    if not msi_path.is_file():
        matches = list(extract_dir.rglob(msi_name))
        if not matches:
            raise FileNotFoundError(f"No se encontró {msi_name} dentro de {zip_path}")
        msi_path = matches[0]

    log(f"[INFO] Ejecutando instalador MSI: {msi_path}")
    _launch_detached("msiexec.exe", ["/i", str(msi_path)])
    return "Instalador de Nitro PDF iniciado."


def cleanup_nitropdf_temp(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Elimina la carpeta temporal NitroPDF extraída en el Escritorio."""
    extract_dir = config.get_local_path("nitro_temp_extract_dir")
    unregister_temp_dir(extract_dir)
    if not extract_dir.exists():
        log(f"[INFO] La carpeta temporal {extract_dir} no existe.")
        return "La carpeta NitroPDF no estaba presente."

    shutil.rmtree(extract_dir)
    log(f"[OK] Carpeta temporal eliminada: {extract_dir}")
    return "Carpeta NitroPDF eliminada correctamente."


def copy_fondos_eidico(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Copia la carpeta Fondos Eidico a Mis Imágenes."""
    source_dir = _ensure_unc_exists(
        config.get_unc("eidico", "fondos_eidico_dir"),
        "Fondos Eidico",
        config=config,
    )
    subdir = config.get_local_path_raw("fondos_eidico_dest_subdir")
    dest_dir = config.get_pictures_dir() / subdir

    log(f"[INFO] Copiando fondos desde {source_dir} -> {dest_dir}")
    shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)
    log("[OK] Fondos Eidico copiados en Imágenes correctamente.")
    return f"Fondos Eidico copiados en {dest_dir}."


# ---------------------------------------------------------------------------
# Técnica e IT (Instructivos, instaladores directos y Battery Report)
# ---------------------------------------------------------------------------

def open_autocad_instructions(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Abre el instructivo de instalación de AutoCAD 2021."""
    txt_path = _ensure_unc_exists(
        config.get_unc("tecnica", "autocad_2021_instructions"),
        "Instructivo AutoCAD 2021",
        config=config,
    )
    log(f"[INFO] Abriendo instructivo: {txt_path}")
    _launch_detached("notepad.exe", [str(txt_path)])
    return "Instructivo de AutoCAD abierto."


def _ps_quote(value: str) -> str:
    """Escapa un literal para cadena de comillas simples en PowerShell."""
    return "'" + value.replace("'", "''") + "'"


def apply_autocad_firewall_block(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Aplica reglas de bloqueo Inbound/Outbound en Firewall para Autodesk AutoCAD 2021 sin duplicados."""
    fw_cfg = config.get_unc("tecnica", "autocad_2021_firewall")
    in_out_raw: list[str] = list(fw_cfg.get("in_out_dirs", []))
    rec_out_raw: list[str] = list(fw_cfg.get("recursive_out_dirs", []))
    in_out_prefix = str(fw_cfg["in_out_rule_prefix"])
    rec_out_prefix = str(fw_cfg["recursive_out_rule_prefix"])

    in_out_dirs: list[str] = []
    for raw_dir in in_out_raw:
        expanded = os.path.expandvars(raw_dir)
        if Path(expanded).is_dir():
            in_out_dirs.append(expanded)
        else:
            log(f"[ADVERTENCIA] Carpeta no encontrada (se omite): {expanded}")

    rec_out_dirs: list[str] = []
    for raw_dir in rec_out_raw:
        expanded = os.path.expandvars(raw_dir)
        if Path(expanded).is_dir():
            rec_out_dirs.append(expanded)
        else:
            log(f"[ADVERTENCIA] Carpeta recursiva no encontrada (se omite): {expanded}")

    if not in_out_dirs and not rec_out_dirs:
        raise FileNotFoundError(
            "No se encontró ninguna de las carpetas de AutoCAD 2021 configuradas en config.json."
        )

    in_out_ps_array = "@(" + ", ".join(_ps_quote(d) for d in in_out_dirs) + ")" if in_out_dirs else "@()"
    rec_out_ps_array = "@(" + ", ".join(_ps_quote(d) for d in rec_out_dirs) + ")" if rec_out_dirs else "@()"

    ps_script = "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            f"$inOutDirs = {in_out_ps_array}",
            f"$recOutDirs = {rec_out_ps_array}",
            f"$inOutPrefix = {_ps_quote(in_out_prefix)}",
            f"$recOutPrefix = {_ps_quote(rec_out_prefix)}",
            "",
            "$existingNames = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)",
            "Get-NetFirewallRule -ErrorAction SilentlyContinue | ForEach-Object {",
            "    if ($_.DisplayName) { [void]$existingNames.Add($_.DisplayName) }",
            "}",
            "",
            "$processedExes = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)",
            "$createdCount = 0",
            "$skippedCount = 0",
            "",
            "function Ensure-FirewallBlockRule {",
            "    param(",
            "        [string]$DisplayName,",
            "        [string]$Direction,",
            "        [string]$ProgramPath",
            "    )",
            "    if ($existingNames.Contains($DisplayName) -or (Get-NetFirewallRule -DisplayName $DisplayName -ErrorAction SilentlyContinue)) {",
            "        [void]$existingNames.Add($DisplayName)",
            "        $script:skippedCount++",
            "        return",
            "    }",
            "    New-NetFirewallRule -DisplayName $DisplayName -Direction $Direction -Program $ProgramPath -Action Block -Profile Any -Enabled True | Out-Null",
            "    [void]$existingNames.Add($DisplayName)",
            "    $script:createdCount++",
            "}",
            "",
            "foreach ($dir in $inOutDirs) {",
            "    if (-not (Test-Path -LiteralPath $dir)) { continue }",
            "    Write-Output \"[INFO] Escaneando (In/Out): $dir\"",
            "    $exes = Get-ChildItem -LiteralPath $dir -Filter '*.exe' -Recurse -File -ErrorAction SilentlyContinue",
            "    foreach ($exe in $exes) {",
            "        [void]$processedExes.Add($exe.FullName)",
            "        $ruleOut = \"$inOutPrefix$($exe.BaseName) - Out\"",
            "        $ruleIn = \"$inOutPrefix$($exe.BaseName) - In\"",
            "        Ensure-FirewallBlockRule -DisplayName $ruleOut -Direction 'Outbound' -ProgramPath $exe.FullName",
            "        Ensure-FirewallBlockRule -DisplayName $ruleIn -Direction 'Inbound' -ProgramPath $exe.FullName",
            "    }",
            "}",
            "",
            "foreach ($dir in $recOutDirs) {",
            "    if (-not (Test-Path -LiteralPath $dir)) { continue }",
            "    Write-Output \"[INFO] Escaneando bloqueo recursivo (Out): $dir\"",
            "    $exes = Get-ChildItem -LiteralPath $dir -Filter '*.exe' -Recurse -File -ErrorAction SilentlyContinue",
            "    foreach ($exe in $exes) {",
            "        [void]$processedExes.Add($exe.FullName)",
            "        $ruleRec = \"$recOutPrefix$($exe.BaseName)\"",
            "        Ensure-FirewallBlockRule -DisplayName $ruleRec -Direction 'Outbound' -ProgramPath $exe.FullName",
            "    }",
            "}",
            "",
            "Write-Output \"[OK] Ejecutables bloqueados: $($processedExes.Count) | Reglas nuevas: $createdCount | Reglas existentes omitidas: $skippedCount\"",
        ]
    )

    log("[INFO] Aplicando reglas de bloqueo en Firewall de Windows para AutoCAD 2021...")
    with tempfile.TemporaryDirectory(prefix="ezsetup_fw_") as tmp_dir:
        tmp_path = register_temp_dir(Path(tmp_dir))
        try:
            ps1_path = tmp_path / "autocad_fw_block.ps1"
            ps1_path.write_text(ps_script, encoding="utf-8-sig")

            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1_path)],
                capture_output=True,
                text=True,
                shell=False,
                creationflags=_CREATE_NO_WINDOW,
            )
        finally:
            unregister_temp_dir(tmp_path)

    summary_line = ""
    for line in (result.stdout or "").splitlines():
        clean = line.strip()
        if clean:
            log(clean)
            if clean.startswith("[OK]"):
                summary_line = clean
    for line in (result.stderr or "").splitlines():
        clean = line.strip()
        if clean:
            log(f"[STDERR] {clean}")

    if result.returncode != 0:
        raise RuntimeError(
            f"Error al aplicar reglas de Firewall para AutoCAD 2021 (código {result.returncode})."
        )

    return summary_line or "Bloqueo de Firewall para AutoCAD 2021 aplicado."


def run_direct_installer(
    installer_path: str,
    label: str,
    log: LogCallback = _noop_log,
    config: AppConfig | None = None,
) -> str:
    """Ejecuta un instalador directo (.exe o .msi) configurado en config.json."""
    installer = _ensure_unc_exists(installer_path, label, config=config)
    log(f"[INFO] Ejecutando {label}: {installer}")
    if installer.suffix.lower() == ".msi":
        _launch_detached("msiexec.exe", ["/i", str(installer)])
    else:
        _launch_detached(installer, cwd=installer.parent)
    return f"Instalador de {label} iniciado."


def generate_battery_report(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Genera el reporte de batería de Windows con powercfg y lo abre en el navegador."""
    report_path = config.get_local_path("battery_report_path")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    log(f"[INFO] Generando reporte de batería en {report_path}...")
    result = subprocess.run(
        ["powercfg", "/batteryreport", "/output", str(report_path)],
        capture_output=True,
        text=True,
        shell=False,
        creationflags=_CREATE_NO_WINDOW,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            f"No se pudo generar el reporte de batería (¿equipo sin batería?): {detail}"
        )

    log(f"[OK] Reporte generado: {report_path}")
    if os.name == "nt":
        os.startfile(str(report_path))
    return f"Reporte de batería abierto: {report_path}"


def renew_ip_and_dns(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Ejecuta ipconfig /flushdns, /release, /renew, /registerdns y verifica conectividad."""
    steps = [
        ("Limpiando caché DNS", ["ipconfig", "/flushdns"]),
        ("Liberando concesión IP", ["ipconfig", "/release"]),
        ("Renovando concesión IP", ["ipconfig", "/renew"]),
        ("Registrando DNS", ["ipconfig", "/registerdns"]),
    ]

    for title, cmd in steps:
        log(f"[INFO] {title} ({' '.join(cmd)})...")
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,
            creationflags=_CREATE_NO_WINDOW,
        )
        if res.returncode != 0:
            detail = (res.stderr or res.stdout or "").strip()
            log(f"[ADVERTENCIA] {' '.join(cmd)} finalizó con código {res.returncode}: {detail}")
        else:
            log(f"[OK] {' '.join(cmd)} completado.")

    probe_host = str(config.app.get("internet_probe_host", "")).strip()
    internet_ok = False
    if probe_host:
        ping_res = subprocess.run(
            ["ping", "-n", "1", "-w", "2000", probe_host],
            capture_output=True,
            text=True,
            shell=False,
            creationflags=_CREATE_NO_WINDOW,
        )
        internet_ok = ping_res.returncode == 0
        if internet_ok:
            log(f"[OK] Conectividad Internet ({probe_host}): Online")
        else:
            log(f"[ADVERTENCIA] Conectividad Internet ({probe_host}): Sin respuesta")

    online_servers: list[str] = []
    for server_id, info in config.get_servers().items():
        host = str(info.get("host", "")).strip()
        port = int(info.get("port", 445))
        if not host:
            continue
        try:
            with socket.create_connection((host, port), timeout=2.0):
                online_servers.append(host)
                log(f"[OK] Servidor {host} ({server_id}): Accesible")
        except OSError:
            log(f"[ADVERTENCIA] Servidor {host} ({server_id}): Sin acceso")

    return (
        f"IP/DNS renovados. Internet ({probe_host or 'N/A'}): "
        f"{'OK' if internet_ok else 'Sin respuesta'} | Servidores accesibles: {len(online_servers)}"
    )


# ---------------------------------------------------------------------------
# Accesos directos de red, Hard Disk Sentinel y catálogo extensible
# ---------------------------------------------------------------------------

def create_network_shortcuts(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Crea en el Escritorio los accesos directos de red de los servidores sin pedir contraseñas."""
    created = 0
    for server_key, server_info in config.get_servers().items():
        shortcut_cfg = server_info.get("desktop_shortcut")
        if not isinstance(shortcut_cfg, dict) or not shortcut_cfg.get("name"):
            log(f"[ADVERTENCIA] Servidor '{server_key}' sin desktop_shortcut configurado.")
            continue
        _create_desktop_shortcut(config, shortcut_cfg, log)
        created += 1

    if created == 0:
        raise ValueError("No hay accesos directos de servidor configurados en config.json.")
    return f"Se crearon {created} acceso(s) directo(s) de red en el Escritorio."


def hdsentinel_replace_exe(config: AppConfig, log: LogCallback = _noop_log) -> str:
    """Extrae HDSentinel.exe a temporal, cierra el proceso si está abierto y sobrescribe el destino."""
    zip_path = _ensure_unc_exists(
        str(config.get_unc("diagnostics", "hdsentinel_crack_zip")),
        "Paquete Hard Disk Sentinel",
        config=config,
    )
    exe_name = str(config.get_unc("diagnostics", "hdsentinel_exe_name"))
    dest_exe = config.get_local_path("hdsentinel_exe_dest")

    with tempfile.TemporaryDirectory(prefix="ezsetup_hds_") as tmp_dir:
        tmp_path = register_temp_dir(Path(tmp_dir))
        try:
            log(f"[INFO] Extrayendo {exe_name} desde {zip_path}...")
            with zipfile.ZipFile(zip_path, "r") as zf:
                extracted = _extract_zip_member(zf, exe_name, tmp_path)
                if not extracted or not extracted.is_file():
                    raise FileNotFoundError(
                        f"No se encontró '{exe_name}' dentro de {zip_path.name}."
                    )

            log(f"[INFO] Verificando cierre de proceso {exe_name}...")
            subprocess.run(
                ["taskkill", "/F", "/IM", exe_name],
                capture_output=True,
                text=True,
                shell=False,
                creationflags=_CREATE_NO_WINDOW,
            )

            dest_exe.parent.mkdir(parents=True, exist_ok=True)
            log(f"[INFO] Copiando {extracted.name} -> {dest_exe}")
            shutil.copy2(extracted, dest_exe)
        finally:
            unregister_temp_dir(tmp_path)

    log(f"[OK] {exe_name} actualizado correctamente en {dest_exe}.")
    return f"{exe_name} copiado en {dest_exe}."


def run_generic_exe(
    path_str: str,
    label: str,
    args: list[str] | None = None,
    log: LogCallback = _noop_log,
    config: AppConfig | None = None,
) -> str:
    """Ejecuta un binario .exe configurado en config.json."""
    exe_path = _ensure_unc_exists(path_str, label, config=config)
    log(f"[INFO] Ejecutando {label}: {exe_path}")
    _launch_detached(exe_path, args=args, cwd=exe_path.parent)
    return f"{label} iniciado."


def run_generic_msi(
    path_str: str,
    label: str,
    args: list[str] | None = None,
    log: LogCallback = _noop_log,
    config: AppConfig | None = None,
) -> str:
    """Ejecuta un instalador .msi configurado en config.json mediante msiexec."""
    msi_path = _ensure_unc_exists(path_str, label, config=config)
    cmd_args = ["/i", str(msi_path), *(args or [])]
    log(f"[INFO] Ejecutando MSI {label}: {msi_path}")
    _launch_detached("msiexec.exe", cmd_args)
    return f"Instalador MSI de {label} iniciado."


def run_generic_reg(
    path_str: str,
    label: str,
    log: LogCallback = _noop_log,
    config: AppConfig | None = None,
) -> str:
    """Importa silenciosamente un archivo .reg configurado en config.json."""
    reg_path = _ensure_unc_exists(path_str, label, config=config)
    import_reg_file(reg_path, log)
    return f"Registro '{reg_path.name}' importado correctamente."


def run_generic_ps1(
    path_str: str,
    label: str,
    args: list[str] | None = None,
    log: LogCallback = _noop_log,
    config: AppConfig | None = None,
) -> str:
    """Ejecuta un script .ps1 físico configurado en config.json y registra su salida."""
    ps1_path = _ensure_unc_exists(path_str, label, config=config)
    log(f"[INFO] Ejecutando script PowerShell {label}: {ps1_path}")
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(ps1_path),
        *(args or []),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        shell=False,
        creationflags=_CREATE_NO_WINDOW,
    )
    for line in (result.stdout or "").splitlines():
        if line.strip():
            log(line.strip())
    for line in (result.stderr or "").splitlines():
        if line.strip():
            log(f"[STDERR] {line.strip()}")
    if result.returncode != 0:
        raise RuntimeError(f"El script {ps1_path.name} finalizó con código {result.returncode}.")
    return f"Script {label} ejecutado correctamente."


def copy_generic_item(
    config: AppConfig,
    source_str: str,
    dest_str: str,
    label: str,
    log: LogCallback = _noop_log,
) -> str:
    """Copia un archivo o carpeta configurado en config.json expandiendo variables."""
    src_expanded = os.path.expandvars(source_str)
    src_path = _ensure_unc_exists(src_expanded, label, config=config)

    resolved_dest = dest_str
    resolved_dest = resolved_dest.replace("{pictures}", str(config.get_pictures_dir()))
    resolved_dest = resolved_dest.replace("{desktop}", str(config.get_desktop_dir()))
    resolved_dest = resolved_dest.replace("{downloads}", str(config.get_downloads_dir()))
    dest_path = Path(os.path.expandvars(resolved_dest))

    log(f"[INFO] Copiando {label}: {src_path} -> {dest_path}")
    if src_path.is_dir():
        shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
    else:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest_path)

    log(f"[OK] {label} copiado correctamente.")
    return f"{label} copiado en {dest_path}."


TASK_REGISTRY: dict[str, Callable[[AppConfig, LogCallback], str]] = {
    "fix_eidico_shortcut": fix_eidico_shortcut,
    "set_sol_sistemas_permissions": set_sol_sistemas_permissions,
    "copy_eidico_vbs": copy_eidico_vbs,
    "extract_produccion_zip": extract_produccion_zip,
    "copy_and_register_winscp": copy_and_register_winscp,
    "copy_winscp_to_dotnet": copy_winscp_to_dotnet,
    "register_winscp_regasm": register_winscp_regasm,
    "copy_fondos_eidico": copy_fondos_eidico,
    "install_forticlient_lan": install_forticlient_lan,
    "import_forticlient_reg_lan": import_forticlient_reg_lan,
    "install_and_configure_forticlient_lan": install_and_configure_forticlient_lan,
    "copy_openvpn_configs": copy_openvpn_configs,
    "install_nitropdf_lan": install_nitropdf_lan,
    "cleanup_nitropdf_temp": cleanup_nitropdf_temp,
    "open_autocad_instructions": open_autocad_instructions,
    "apply_autocad_firewall_block": apply_autocad_firewall_block,
    "open_optional_features": open_optional_features,
    "hdsentinel_replace_exe": hdsentinel_replace_exe,
    "generate_battery_report": generate_battery_report,
    "renew_ip_dns": renew_ip_and_dns,
    "open_credential_manager": open_credential_manager,
    "create_network_shortcuts": create_network_shortcuts,
}
