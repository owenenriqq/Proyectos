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
    "VPN_EXE": r"C:\Program Files\Amazon\AWS VPN Client\AWSVPNClient.exe",
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
