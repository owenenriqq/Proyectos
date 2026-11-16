# workers.py
"""Hilos de trabajo y operaciones de red, transferencia y sistema en segundo plano."""

import os
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request
import zipfile

from PyQt6.QtCore import QThread, pyqtSignal

from config import CONFIG, get_cred, logger

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def is_server_reachable(ip, port=445, timeout=1.5):
    """Comprueba mediante conexión TCP si el servidor responde en el puerto indicado."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def inyectar_credencial_smb(ip, user, password):
    """Registra la credencial SMB en el Administrador de credenciales de Windows."""
    try:
        res = subprocess.run(
            ["cmdkey", f"/add:{ip}", f"/user:{user}", f"/pass:{password}"],
            shell=False,
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if res.returncode == 0:
            logger.info("Credencial SMB registrada para %s (usuario: %s).", ip, user)
            return True
        logger.warning(
            "cmdkey devolvió código %s al registrar credencial para %s.",
            res.returncode,
            ip,
        )
        return False
    except OSError as exc:
        logger.error("Error del sistema al ejecutar cmdkey para %s: %s", ip, exc)
        return False


def limpiar_sesiones_smb_eidico(ips_objetivo=None):
    """Cierra únicamente las sesiones SMB asociadas a los servidores de Eidico."""
    if ips_objetivo is None:
        ips_objetivo = [CONFIG["IP_SERVER_1"], CONFIG["IP_SERVER_2"]]

    recursos_a_eliminar = []

    try:
        consulta = subprocess.run(
            ["net", "use"],
            shell=False,
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW,
            check=False,
        )
        for linea in consulta.stdout.splitlines():
            for ip in ips_objetivo:
                if f"\\\\{ip}" in linea:
                    # Detectar letra de unidad mapeada si existe (ej. Z:)
                    match_unidad = re.search(r"\b([A-Za-z]:)\s+\\\\", linea)
                    if match_unidad:
                        recursos_a_eliminar.append(match_unidad.group(1))
                    # Detectar ruta UNC completa
                    match_unc = re.search(r"(\\\\[^\s]+)", linea)
                    if match_unc:
                        recursos_a_eliminar.append(match_unc.group(1))
    except OSError as exc:
        logger.warning("No se pudo consultar 'net use': %s", exc)

    for ip in ips_objetivo:
        if ip == CONFIG["IP_SERVER_1"]:
            recursos_a_eliminar.extend(
                [
                    CONFIG["SERVER_FOLDER"],
                    rf"\\{ip}\Fileserver",
                    rf"\\{ip}\IPC$",
                    rf"\\{ip}",
                ]
            )
        else:
            recursos_a_eliminar.extend([rf"\\{ip}\IPC$", rf"\\{ip}"])

    # Conservar orden y evitar duplicados
    vistos = set()
    for recurso in recursos_a_eliminar:
        clave = recurso.lower()
        if clave in vistos:
            continue
        vistos.add(clave)
        try:
            subprocess.run(
                ["net", "use", recurso, "/delete", "/y"],
                shell=False,
                creationflags=CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except OSError as exc:
            logger.warning("No se pudo desconectar el recurso SMB %s: %s", recurso, exc)

    logger.info("Sesiones SMB de Eidico depuradas para: %s", ", ".join(ips_objetivo))


def extraer_zip_seguro(zip_path, dest_dir):
    """Extrae un archivo ZIP validando que ninguna entrada escape del directorio destino."""
    dest_abs = os.path.abspath(dest_dir)
    os.makedirs(dest_abs, exist_ok=True)
    archivos_extraidos = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            target_path = os.path.abspath(os.path.join(dest_abs, member.filename))
            if os.path.commonpath([dest_abs, target_path]) != dest_abs:
                raise ValueError(f"Ruta insegura detectada en ZIP: {member.filename}")
            if not member.is_dir():
                archivos_extraidos.append(target_path)
        zf.extractall(dest_abs)

    return archivos_extraidos


class WorkerTransferencia(QThread):
    """Realiza descargas HTTP o copias SMB hacia un temporal con reemplazo atómico."""

    progreso = pyqtSignal(int, str)
    finalizado = pyqtSignal(bool, str)

    def __init__(self, origen, destino, is_url=False):
        super().__init__()
        self.origen = origen
        self.destino = destino
        self.is_url = is_url

    def run(self):
        destino_tmp = f"{self.destino}.tmp"
        try:
            carpeta_destino = os.path.dirname(self.destino)
            if carpeta_destino:
                os.makedirs(carpeta_destino, exist_ok=True)

            if self.is_url:
                self._descargar(destino_tmp)
            else:
                self._copiar(destino_tmp)

            os.replace(destino_tmp, self.destino)
            logger.info("Transferencia completada correctamente: %s", self.destino)
            self.finalizado.emit(True, self.destino)
        except Exception as exc:
            logger.exception("Error en transferencia (%s -> %s)", self.origen, self.destino)
            if os.path.exists(destino_tmp):
                try:
                    os.remove(destino_tmp)
                except OSError:
                    pass
            self.finalizado.emit(False, str(exc))

    def _descargar(self, destino_tmp):
        req = urllib.request.Request(self.origen, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp, open(destino_tmp, "wb") as f_out:
            total = int(resp.info().get("Content-Length") or 0)
            leidos = 0
            ultimo_pct = -1
            siguiente_aviso_bytes = 512 * 1024

            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f_out.write(chunk)
                leidos += len(chunk)
                if total > 0:
                    pct = min(100, int((leidos / total) * 100))
                    if pct != ultimo_pct:
                        ultimo_pct = pct
                        self.progreso.emit(
                            pct,
                            f"Descargando: {leidos / 1048576:.1f}MB / {total / 1048576:.1f}MB",
                        )
                elif leidos >= siguiente_aviso_bytes:
                    siguiente_aviso_bytes += 512 * 1024
                    self.progreso.emit(0, f"Descargando: {leidos / 1048576:.1f}MB...")

    def _copiar(self, destino_tmp):
        if not os.path.isfile(self.origen):
            raise FileNotFoundError(f"No se encontró el archivo origen: {self.origen}")

        total = os.path.getsize(self.origen)
        ultimo_pct = -1
        with open(self.origen, "rb") as f_in, open(destino_tmp, "wb") as f_out:
            leidos = 0
            while True:
                chunk = f_in.read(1024 * 1024)
                if not chunk:
                    break
                f_out.write(chunk)
                leidos += len(chunk)
                if total > 0:
                    pct = min(100, int((leidos / total) * 100))
                    if pct != ultimo_pct:
                        ultimo_pct = pct
                        self.progreso.emit(
                            pct,
                            "Actualizando Eidico... (Puede demorar unos minutos)",
                        )


class WorkerCheckRed(QThread):
    """Inyecta credenciales SMB si corresponde y verifica la accesibilidad a la ruta de red."""

    finalizado = pyqtSignal(bool, str, str)

    def __init__(self, path, timeout, msg_exito, ip=None, user=None, password=None):
        super().__init__()
        self.path = path
        self.timeout = timeout
        self.msg_exito = msg_exito
        self.ip = ip
        self.user = user
        self.password = password

    def run(self):
        try:
            if self.ip and self.user and self.password:
                limpiar_sesiones_smb_eidico([self.ip])
                inyectar_credencial_smb(self.ip, self.user, self.password)

            limite = time.monotonic() + self.timeout
            while time.monotonic() < limite:
                if os.path.exists(self.path):
                    logger.info("Acceso verificado a recurso de red: %s", self.path)
                    self.finalizado.emit(True, self.msg_exito, self.path)
                    return
                time.sleep(0.5)

            logger.warning("Tiempo agotado intentando acceder a %s", self.path)
            self.finalizado.emit(
                False,
                f"No se pudo acceder a {self.path}. Verifique la VPN.",
                self.path,
            )
        except Exception as exc:
            logger.exception("Error verificando recurso de red %s", self.path)
            self.finalizado.emit(False, f"Error de conexión: {exc}", self.path)


class WorkerVerificacionInicio(QThread):
    """Comprueba en segundo plano la disponibilidad del servidor y si requiere actualización."""

    resultado = pyqtSignal(bool, bool)

    def run(self):
        server_disponible = False
        necesita_act = False
        try:
            ip1 = CONFIG["IP_SERVER_1"]
            if is_server_reachable(ip1):
                inyectar_credencial_smb(ip1, CONFIG["USER_1"], get_cred(CONFIG["PASS_1_B64"]))
                server_folder = CONFIG["SERVER_FOLDER"]
                server_exe = os.path.join(server_folder, CONFIG["EXE_NAME"])
                if os.path.exists(server_folder) and os.path.isfile(server_exe):
                    server_disponible = True
                    local_exe = os.path.join(CONFIG["LOCAL_FOLDER"], CONFIG["EXE_NAME"])
                    if not os.path.isfile(local_exe):
                        necesita_act = True
                    else:
                        try:
                            if (
                                os.path.getmtime(server_exe) > os.path.getmtime(local_exe)
                                or os.path.getsize(local_exe) != os.path.getsize(server_exe)
                            ):
                                necesita_act = True
                        except OSError as exc:
                            logger.warning("No se pudieron comparar versiones de Eidico: %s", exc)
                            necesita_act = True
        except Exception:
            logger.exception("Error inesperado durante la verificación inicial de servidor")

        logger.info(
            "Resultado verificación inicio -> server_disponible=%s, necesita_act=%s",
            server_disponible,
            necesita_act,
        )
        self.resultado.emit(server_disponible, necesita_act)


class WorkerAccionSistema(QThread):
    """Ejecuta en segundo plano acciones de mantenimiento de red, VPN o extracción ZIP."""

    finalizado = pyqtSignal(bool, str)

    def __init__(self, accion, zip_path=None, extract_dir=None):
        super().__init__()
        self.accion = accion
        self.zip_path = zip_path
        self.extract_dir = extract_dir

    def run(self):
        try:
            if self.accion == "reiniciar_vpn":
                self._reiniciar_vpn()
            elif self.accion == "limpiar_red":
                self._limpiar_red()
            elif self.accion == "extraer_instalador":
                self._extraer_instalador()
            else:
                self.finalizado.emit(False, f"Acción desconocida: {self.accion}")
        except Exception as exc:
            logger.exception("Fallo ejecutando acción de sistema '%s'", self.accion)
            self.finalizado.emit(False, str(exc))

    def _reiniciar_vpn(self):
        logger.info("Iniciando reinicio total de AWS VPN Client y servicio OpenVPN.")
        subprocess.run(
            ["taskkill", "/IM", "AWSVPNClient.exe", "/F"],
            shell=False,
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        subprocess.run(
            ["net", "stop", "AWS VPN Client OpenVPN Service"],
            shell=False,
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        subprocess.run(
            ["ipconfig", "/flushdns"],
            shell=False,
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        time.sleep(1)
        res_start = subprocess.run(
            ["net", "start", "AWS VPN Client OpenVPN Service"],
            shell=False,
            creationflags=CREATE_NO_WINDOW,
            capture_output=True,
            text=True,
            check=False,
        )
        if res_start.returncode != 0:
            logger.warning(
                "net start del servicio AWS VPN devolvió código %s", res_start.returncode
            )
        if os.path.exists(CONFIG["VPN_EXE"]):
            subprocess.Popen([CONFIG["VPN_EXE"]], shell=False)
        self.finalizado.emit(True, "Servicios VPN reiniciados correctamente.")

    def _limpiar_red(self):
        limpiar_sesiones_smb_eidico()
        subprocess.run(
            ["ipconfig", "/flushdns"],
            shell=False,
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        self.finalizado.emit(True, "Sesiones de red limpiadas exitosamente.")

    def _extraer_instalador(self):
        archivos = extraer_zip_seguro(self.zip_path, self.extract_dir)
        exe_path = next(
            (ruta for ruta in archivos if ruta.lower().endswith((".exe", ".msi"))),
            None,
        )
        try:
            os.remove(self.zip_path)
        except OSError as exc:
            logger.warning("No se pudo eliminar el ZIP descargado %s: %s", self.zip_path, exc)

        destino_abrir = exe_path if exe_path else self.extract_dir
        logger.info("Instalador extraído correctamente en %s", self.extract_dir)
        self.finalizado.emit(True, destino_abrir)


class WorkerProcesosEspeciales(QThread):
    """Aplica permisos mínimos necesarios y despliega archivos locales desde un ZIP."""

    progreso_msg = pyqtSignal(str)
    finalizado = pyqtSignal(bool)

    def __init__(self, zip_path, dest_path, base_folder):
        super().__init__()
        self.zip_path = zip_path
        self.dest_path = dest_path
        self.base_folder = base_folder

    def run(self):
        try:
            self.progreso_msg.emit("Otorgando permisos de modificación necesarios...")
            subprocess.run(
                ["icacls", self.base_folder, "/grant", "*S-1-5-32-545:(OI)(CI)M", "/T"],
                shell=False,
                creationflags=CREATE_NO_WINDOW,
                check=True,
            )

            if self.zip_path and os.path.exists(self.zip_path):
                self.progreso_msg.emit("Instalando archivos de Producción...")
                extraer_zip_seguro(self.zip_path, self.dest_path)

            time.sleep(1)
            self.finalizado.emit(True)
        except Exception:
            logger.exception("Error en WorkerProcesosEspeciales")
            self.finalizado.emit(False)


class WorkerMonitor(QThread):
    """Monitorea periódicamente la conectividad TCP hacia los servidores corporativos."""

    estado_red = pyqtSignal(bool, bool)

    def __init__(self, ip1, ip2):
        super().__init__()
        self.ip1 = ip1
        self.ip2 = ip2
        self.running = True

    def run(self):
        while self.running:
            self.estado_red.emit(
                is_server_reachable(self.ip1),
                is_server_reachable(self.ip2),
            )
            # Espera fraccionada para permitir detención rápida al cerrar la aplicación
            for _ in range(10):
                if not self.running:
                    break
                time.sleep(0.5)

    def stop(self):
        """Detiene el bucle de monitoreo."""
        self.running = False
