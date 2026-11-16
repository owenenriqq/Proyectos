# config.py
"""Configuración global, rutas, registro de eventos y utilidades de entorno."""

import base64
import ctypes
import logging
import os
import re
import sys
import winreg
from logging.handlers import RotatingFileHandler

CONFIG = {
    "APP_NAME": "Eidico",
    "IP_SERVER_1": "172.31.11.146",
    "IP_SERVER_2": "172.30.0.13",
    "USER_1": "foxeidico",
    "USER_2": r"eidico\fexterno",
    "PASS_1_B64": "NzZFZ3pnUVJDbUlaQld5",
    "PASS_2_B64": "Y2xEQkVQSkBqVDJhYmFs",
    "SERVER_FOLDER": r"\\172.31.11.146\Fileserver\EidicoPrueba",
    "LOCAL_FOLDER": r"C:\Program Files (x86)\Sol Sistemas\EIDICO",
    "BASE_FOLDER": r"C:\Program Files (x86)\Sol Sistemas",
    "EXE_NAME": "EidicoPrueba.exe",
    "VPN_EXE": r"C:\Program Files\Amazon\AWS VPN Client\AWS VPN Client.exe",
    "URL_TEAMVIEWER": "https://dl.teamviewer.com/download/TeamViewerQS.exe",
    "URL_EIDICO_ZIP": "http://eidico.net/recursos/descargas/Instalar_Fox_EIDICO.zip",
    "URL_FORTICLIENT": "http://eidico.net/recursos/descargas/FortiClient_x64.zip",
    "URL_AWS_VPN": "https://d20adtppz83p9s.cloudfront.net/WPF/latest/AWS_VPN_Client.msi",
    "WHATSAPP_NUM": "5491135812978",
    "EMAIL_SOPORTE": "it@eidico.com.ar",
}

TIEMPO_VERIFICACION = 20

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))


def get_cred(b64_str):
    """Decodifica una credencial almacenada en Base64."""
    return base64.b64decode(b64_str).decode("utf-8")


class FiltroSanitizadorCredenciales(logging.Filter):
    """Filtro de logging que oculta contraseñas, secretos Base64 y parámetros /pass."""

    _PATRON_PASS = re.compile(r'(/pass\s*:\s*)("[^"]*"|\S+)', re.IGNORECASE)

    def __init__(self):
        super().__init__()
        self._secretos = self._recopilar_secretos()

    @staticmethod
    def _recopilar_secretos():
        secretos = []
        for clave in ("PASS_1_B64", "PASS_2_B64"):
            valor_b64 = CONFIG.get(clave, "")
            if valor_b64:
                secretos.append(valor_b64)
                try:
                    decodificado = get_cred(valor_b64)
                    if decodificado:
                        secretos.append(decodificado)
                except (ValueError, UnicodeDecodeError):
                    pass
        # Ordenar de mayor a menor longitud para evitar reemplazos parciales
        return sorted(set(secretos), key=len, reverse=True)

    def sanitizar_texto(self, texto):
        """Reemplaza credenciales conocidas y parámetros /pass por ***."""
        if not isinstance(texto, str):
            return texto
        resultado = self._PATRON_PASS.sub(r"\1***", texto)
        for secreto in self._secretos:
            if secreto in resultado:
                resultado = resultado.replace(secreto, "***")
        return resultado

    def filter(self, record):
        """Sanitiza el mensaje del registro antes de escribirlo en el archivo."""
        try:
            mensaje_formateado = record.getMessage()
            record.msg = self.sanitizar_texto(mensaje_formateado)
            record.args = ()
        except Exception:
            record.msg = self.sanitizar_texto(str(record.msg))
            record.args = ()
        return True


def _configurar_logger():
    """Configura el logger con rotación y ruta de respaldo si APP_DIR no es escribible."""
    log_inst = logging.getLogger("GestorEidico")
    log_inst.setLevel(logging.INFO)
    log_inst.propagate = False

    if log_inst.handlers:
        return log_inst, LOG_PATH if "LOG_PATH" in globals() else os.path.join(APP_DIR, "gestor_eidico.log")

    ruta_primaria = os.path.join(APP_DIR, "gestor_eidico.log")
    local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    ruta_respaldo = os.path.join(local_app_data, "GestorEidico", "gestor_eidico.log")

    ruta_final = ruta_primaria
    handler = None
    try:
        handler = RotatingFileHandler(
            ruta_primaria, maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8"
        )
    except OSError:
        try:
            os.makedirs(os.path.dirname(ruta_respaldo), exist_ok=True)
            ruta_final = ruta_respaldo
            handler = RotatingFileHandler(
                ruta_respaldo, maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8"
            )
        except OSError:
            handler = logging.NullHandler()

    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    handler.addFilter(FiltroSanitizadorCredenciales())
    log_inst.addHandler(handler)
    return log_inst, ruta_final


logger, LOG_PATH = _configurar_logger()

ESTILO_GLOBAL = """
    QWidget { background-color: #f5f6fa; font-family: 'Segoe UI', sans-serif; color: #2d3436; }
    QLabel { background: transparent; }
    QPushButton { background-color: #ffffff; border: 1px solid #dcdde1; border-radius: 6px; padding: 6px 12px; font-weight: bold; font-size: 11px; color: #2d3436; }
    QPushButton:hover { background-color: #f1f2f6; border-color: #3498db; }
    QPushButton#BtnPrincipal { background-color: #2c3e50; color: white; border: none; }
    QProgressBar { border: 1px solid #dcdde1; background-color: #ffffff; height: 16px; border-radius: 8px; text-align: center; font-weight: bold; color: black; font-size: 10px; }
    QProgressBar::chunk { background-color: #3498db; border-radius: 8px; }

    QMenu { background-color: white; border: 1px solid #dcdde1; border-radius: 5px; padding: 5px; font-size: 11px; }
    QMenu#MenuOpciones { min-width: 320px; }
    QMenu#MenuBandeja { min-width: 150px; }
    QMenu::item { padding: 8px 12px; border-radius: 4px; color: #2d3436; }
    QMenu::item:selected { background-color: #3498db; color: white; }

    QFrame#FrameProgreso { background-color: #ffffff; border: 1px solid #dcdde1; border-radius: 8px; }
"""


def resource_path(relative_path):
    """Resuelve la ruta de recursos empaquetados con PyInstaller o locales en APP_DIR."""
    base_path = getattr(sys, "_MEIPASS", APP_DIR)
    return os.path.join(base_path, relative_path)


def obtener_carpeta_descargas():
    """Obtiene la carpeta Descargas del usuario desde el Registro de Windows."""
    try:
        ruta_reg = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ruta_reg) as key:
            return winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")[0]
    except OSError as exc:
        logger.warning("No se pudo leer la carpeta Descargas del registro: %s", exc)
        return os.path.join(os.path.expanduser("~"), "Downloads")


def obtener_carpeta_escritorio():
    """Obtiene la carpeta Escritorio del usuario desde el Registro de Windows."""
    try:
        ruta_reg = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ruta_reg) as key:
            return winreg.QueryValueEx(key, "Desktop")[0]
    except OSError as exc:
        logger.warning("No se pudo leer la carpeta Escritorio del registro: %s", exc)
        return os.path.join(os.path.expanduser("~"), "Desktop")


def es_admin():
    """Indica si el proceso actual se ejecuta con privilegios de administrador."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (OSError, AttributeError) as exc:
        logger.warning("No se pudo determinar si el usuario es administrador: %s", exc)
        return False


def _limpiar_ruta_ejecutable_registro(valor_raw):
    """Extrae una ruta de ejecutable limpia desde un valor del Registro de Windows."""
    if not valor_raw or not isinstance(valor_raw, str):
        return ""
    texto = os.path.expandvars(valor_raw.strip())
    if texto.startswith('"'):
        fin_comilla = texto.find('"', 1)
        if fin_comilla != -1:
            return texto[1:fin_comilla]
    match_exe = re.match(r"^(.*?\.exe)\b", texto, re.IGNORECASE)
    if match_exe:
        return match_exe.group(1)
    return texto.split(",")[0].strip().strip('"')


NOMBRES_EXE_VPN = ("AWS VPN Client.exe", "AWSVPNClient.exe")


def obtener_ruta_aws_vpn():
    """Detecta la ruta de AWS VPN Client priorizando 'AWS VPN Client.exe' en Windows 10/11."""
    candidatos = [CONFIG["VPN_EXE"]]
    for nombre_exe in NOMBRES_EXE_VPN:
        candidatos.append(
            os.path.join(r"C:\Program Files\Amazon\AWS VPN Client", nombre_exe)
        )
        for var_entorno in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
            base = os.environ.get(var_entorno)
            if base:
                candidatos.append(os.path.join(base, "Amazon", "AWS VPN Client", nombre_exe))

    vistos = set()
    for ruta in candidatos:
        if not ruta:
            continue
        norm = os.path.normcase(os.path.abspath(ruta))
        if norm in vistos:
            continue
        vistos.add(norm)
        if os.path.isfile(ruta):
            return ruta

    # 1. Consultar servicios registrados (moderno y legado)
    servicios = ("AWS.VPN.Client.Service", "AWS VPN Client OpenVPN Service")
    for nombre_srv in servicios:
        ruta_srv = rf"SYSTEM\CurrentControlSet\Services\{nombre_srv}"
        for acceso in (winreg.KEY_READ | winreg.KEY_WOW64_64KEY, winreg.KEY_READ):
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, ruta_srv, 0, acceso) as key:
                    image_path, _ = winreg.QueryValueEx(key, "ImagePath")
                exe_srv = _limpiar_ruta_ejecutable_registro(image_path)
                if exe_srv:
                    dir_srv = os.path.dirname(exe_srv)
                    for posible_dir in (dir_srv, os.path.dirname(dir_srv)):
                        for nombre_exe in NOMBRES_EXE_VPN:
                            candidato = os.path.join(posible_dir, nombre_exe)
                            if os.path.isfile(candidato):
                                return candidato
            except OSError:
                continue

    # 2. Consultar claves Uninstall de Windows (64 y 32 bits)
    ruta_uninstall = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    accesos = (
        winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        winreg.KEY_READ | winreg.KEY_WOW64_32KEY,
    )
    nombres_exe_lower = tuple(n.lower() for n in NOMBRES_EXE_VPN)
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for acceso in accesos:
            try:
                with winreg.OpenKey(hive, ruta_uninstall, 0, acceso) as key_uninst:
                    total_sub = winreg.QueryInfoKey(key_uninst)[0]
                    for idx in range(total_sub):
                        try:
                            sub_nombre = winreg.EnumKey(key_uninst, idx)
                            with winreg.OpenKey(key_uninst, sub_nombre, 0, acceso) as sub_key:
                                display_name, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                                if "aws vpn client" not in str(display_name).lower():
                                    continue
                                for campo in ("InstallLocation", "DisplayIcon"):
                                    try:
                                        val, _ = winreg.QueryValueEx(sub_key, campo)
                                    except OSError:
                                        continue
                                    if campo == "InstallLocation" and val:
                                        dir_inst = os.path.expandvars(str(val).strip('"'))
                                        for nombre_exe in NOMBRES_EXE_VPN:
                                            candidato = os.path.join(dir_inst, nombre_exe)
                                            if os.path.isfile(candidato):
                                                return candidato
                                    elif val:
                                        candidato = _limpiar_ruta_ejecutable_registro(str(val))
                                        if candidato:
                                            if (
                                                os.path.basename(candidato).lower() in nombres_exe_lower
                                                and os.path.isfile(candidato)
                                            ):
                                                return candidato
                                            dir_icon = os.path.dirname(candidato)
                                            if dir_icon:
                                                for nombre_exe in NOMBRES_EXE_VPN:
                                                    alt = os.path.join(dir_icon, nombre_exe)
                                                    if os.path.isfile(alt):
                                                        return alt
                        except OSError:
                            continue
            except OSError:
                continue

    # 3. Consultar App Paths
    for nombre_exe in NOMBRES_EXE_VPN:
        ruta_app_paths = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{nombre_exe}"
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for acceso in accesos:
                try:
                    with winreg.OpenKey(hive, ruta_app_paths, 0, acceso) as key:
                        val, _ = winreg.QueryValueEx(key, "")
                    candidato = _limpiar_ruta_ejecutable_registro(str(val))
                    if candidato and os.path.isfile(candidato):
                        return candidato
                except OSError:
                    continue

    return None


def esta_aws_vpn_instalado():
    """Indica si AWS VPN Client está instalado en el equipo."""
    return obtener_ruta_aws_vpn() is not None


def limpiar_archivos_residuales():
    """Elimina archivos temporales .tmp residuales de transferencias interrumpidas."""
    local_folder = CONFIG["LOCAL_FOLDER"]
    if os.path.isdir(local_folder):
        try:
            for nombre in os.listdir(local_folder):
                if nombre.lower().endswith(".tmp"):
                    ruta_tmp = os.path.join(local_folder, nombre)
                    try:
                        os.remove(ruta_tmp)
                        logger.info("Archivo temporal residual eliminado: %s", ruta_tmp)
                    except OSError as exc:
                        logger.warning("No se pudo eliminar temporal %s: %s", ruta_tmp, exc)
        except OSError as exc:
            logger.warning("No se pudo explorar %s para limpiar temporales: %s", local_folder, exc)

    descargas = obtener_carpeta_descargas()
    temporales_conocidos = (
        "TeamViewerQS.exe.tmp",
        "Instalar_Fox_EIDICO.zip.tmp",
        "FortiClient_x64.zip.tmp",
        "AWS_VPN_Client.msi.tmp",
    )
    for nombre in temporales_conocidos:
        ruta_tmp = os.path.join(descargas, nombre)
        if os.path.isfile(ruta_tmp):
            try:
                os.remove(ruta_tmp)
                logger.info("Descarga temporal residual eliminada: %s", ruta_tmp)
            except OSError as exc:
                logger.warning("No se pudo eliminar descarga temporal %s: %s", ruta_tmp, exc)
