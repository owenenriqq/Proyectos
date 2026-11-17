"""Workers QThread reutilizables para operaciones de red, copia, montaje ISO y tareas."""

from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
from typing import Any, Callable

from PyQt6.QtCore import QThread, pyqtSignal
import requests

from src.config import AppConfig
from src.system_tasks import process_forticlient_zip

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


class ServerCheckWorker(QThread):
    """Verifica conectividad TCP al puerto SMB de los servidores configurados."""

    status_ready = pyqtSignal(dict)

    def __init__(self, servers: dict[str, dict[str, Any]], timeout: float = 1.8) -> None:
        super().__init__()
        self._servers = servers
        self._timeout = timeout

    def run(self) -> None:
        results: dict[str, bool] = {}
        for server_id, info in self._servers.items():
            host = str(info.get("host", "")).strip()
            port = int(info.get("port", 445))
            if not host:
                results[server_id] = False
                continue
            try:
                with socket.create_connection((host, port), timeout=self._timeout):
                    results[server_id] = True
            except OSError:
                results[server_id] = False
        self.status_ready.emit(results)


class DownloadWorker(QThread):
    """Descarga HTTP/HTTPS por streaming con reporte de progreso y cancelación."""

    progress_changed = pyqtSignal(int, float, float)
    log_message = pyqtSignal(str)
    finished_success = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(
        self,
        url: str,
        dest_dir: Path,
        filename: str,
        chunk_size: int = 65536,
        open_after: bool = True,
        embedded_msi_name: str | None = None,
        embedded_reg_name: str | None = None,
    ) -> None:
        super().__init__()
        self.url = url
        self.dest_dir = dest_dir
        self.filename = filename
        self.chunk_size = chunk_size
        self.open_after = open_after
        self.embedded_msi_name = embedded_msi_name
        self.embedded_reg_name = embedded_reg_name
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        self.dest_dir.mkdir(parents=True, exist_ok=True)
        final_path = self.dest_dir / self.filename
        temp_path = self.dest_dir / f"{self.filename}.tmp"

        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass

        self.log_message.emit(f"[INFO] Iniciando descarga: {self.url}")
        try:
            with requests.get(self.url, stream=True, timeout=30) as response:
                response.raise_for_status()
                total_bytes = int(response.headers.get("Content-Length", 0) or 0)
                total_mb = total_bytes / (1024 * 1024) if total_bytes > 0 else 0.0
                downloaded = 0

                with open(temp_path, "wb") as fh:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if self._cancelled:
                            self.log_message.emit("[ADVERTENCIA] Descarga cancelada por el usuario.")
                            break
                        if not chunk:
                            continue
                        fh.write(chunk)
                        downloaded += len(chunk)
                        downloaded_mb = downloaded / (1024 * 1024)
                        percent = (
                            min(100, int((downloaded / total_bytes) * 100))
                            if total_bytes > 0
                            else 0
                        )
                        self.progress_changed.emit(percent, downloaded_mb, total_mb)

            if self._cancelled:
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)
                self.failed.emit("Descarga cancelada por el usuario.")
                return

            if final_path.exists():
                final_path.unlink()
            temp_path.replace(final_path)
            self.log_message.emit(f"[OK] Archivo descargado en: {final_path}")

            msi_ran = False
            if (self.embedded_msi_name or self.embedded_reg_name) and final_path.suffix.lower() == ".zip":
                msi_ran, _ = process_forticlient_zip(
                    zip_path=final_path,
                    msi_name=self.embedded_msi_name,
                    reg_name=self.embedded_reg_name,
                    install_msi=bool(self.embedded_msi_name),
                    import_reg=bool(self.embedded_reg_name),
                    log=self.log_message.emit,
                )

            if self.open_after and not msi_ran and os.name == "nt":
                self.log_message.emit(f"[INFO] Abriendo {final_path.name}...")
                os.startfile(str(final_path))

            self.finished_success.emit(str(final_path))
        except Exception as exc:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            msg = f"Error durante la descarga de {self.filename}: {exc}"
            self.log_message.emit(f"[ERROR] {msg}")
            self.failed.emit(msg)


class FileCopyWorker(QThread):
    """Copia archivos pesados desde red por chunks con barra de progreso y cancelación."""

    progress_changed = pyqtSignal(int, float, float)
    log_message = pyqtSignal(str)
    finished_success = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(
        self,
        source: str,
        destination: Path,
        chunk_size: int = 65536,
    ) -> None:
        super().__init__()
        self.source = source
        self.destination = destination
        self.chunk_size = chunk_size
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        src_path = Path(self.source)
        if not src_path.is_file():
            msg = f"No se encontró el archivo de origen: {self.source}"
            self.log_message.emit(f"[ERROR] {msg}")
            self.failed.emit(msg)
            return

        temp_dest = self.destination.with_suffix(self.destination.suffix + ".tmp")
        try:
            self.destination.parent.mkdir(parents=True, exist_ok=True)
            total_bytes = src_path.stat().st_size
            total_mb = total_bytes / (1024 * 1024) if total_bytes > 0 else 0.0
            copied = 0

            self.log_message.emit(f"[INFO] Copiando {src_path} -> {self.destination}...")
            with open(src_path, "rb") as src_fh, open(temp_dest, "wb") as dst_fh:
                while True:
                    if self._cancelled:
                        self.log_message.emit("[ADVERTENCIA] Copia cancelada por el usuario.")
                        break
                    chunk = src_fh.read(self.chunk_size)
                    if not chunk:
                        break
                    dst_fh.write(chunk)
                    copied += len(chunk)
                    copied_mb = copied / (1024 * 1024)
                    percent = (
                        min(100, int((copied / total_bytes) * 100))
                        if total_bytes > 0
                        else 100
                    )
                    self.progress_changed.emit(percent, copied_mb, total_mb)

            if self._cancelled:
                temp_dest.unlink(missing_ok=True)
                self.failed.emit("Copia cancelada por el usuario.")
                return

            if self.destination.exists():
                self.destination.unlink()
            temp_dest.replace(self.destination)

            self.log_message.emit(f"[OK] Archivo copiado correctamente en {self.destination}")
            self.finished_success.emit(str(self.destination))
        except Exception as exc:
            temp_dest.unlink(missing_ok=True)
            msg = f"Error al copiar {src_path.name}: {exc}"
            self.log_message.emit(f"[ERROR] {msg}")
            self.failed.emit(msg)


class IsoMountWorker(QThread):
    """Monta una imagen ISO/IMG vía PowerShell Mount-DiskImage y lanza el instalador."""

    log_message = pyqtSignal(str)
    finished_success = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, image_path: str, setup_relative_path: str, label: str) -> None:
        super().__init__()
        self.image_path = image_path
        self.setup_relative_path = setup_relative_path
        self.label = label

    def run(self) -> None:
        if not self.image_path or not self.image_path.strip():
            msg = (
                f"La ruta de imagen para '{self.label}' está vacía en config.json. "
                "Completala antes de continuar."
            )
            self.log_message.emit(f"[ADVERTENCIA] {msg}")
            self.failed.emit(msg)
            return

        img = Path(self.image_path)
        if not img.is_file():
            msg = f"No se encontró la imagen de '{self.label}' en: {self.image_path}"
            self.log_message.emit(f"[ERROR] {msg}")
            self.failed.emit(msg)
            return

        escaped = self.image_path.replace("'", "''")
        ps_cmd = (
            f"$d = Mount-DiskImage -ImagePath '{escaped}' -PassThru; "
            "Start-Sleep -Milliseconds 350; "
            "($d | Get-Volume | Select-Object -First 1).DriveLetter"
        )

        self.log_message.emit(f"[INFO] Montando imagen de {self.label}: {self.image_path}")
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                creationflags=_CREATE_NO_WINDOW,
            )
            if res.returncode != 0:
                detail = (res.stderr or res.stdout or "").strip()
                raise RuntimeError(f"Mount-DiskImage falló: {detail}")

            drive_letter = (res.stdout or "").strip().splitlines()[-1].strip() if res.stdout else ""
            if len(drive_letter) != 1 or not drive_letter.isalpha():
                raise RuntimeError(f"No se pudo obtener la letra de unidad montada ('{drive_letter}').")

            self.log_message.emit(f"[OK] Imagen montada en unidad {drive_letter}:")
            installer_path = Path(f"{drive_letter}:\\") / self.setup_relative_path
            if not installer_path.is_file():
                raise FileNotFoundError(
                    f"No se encontró el instalador en la unidad montada: {installer_path}"
                )

            self.log_message.emit(f"[INFO] Ejecutando instalador: {installer_path}")
            subprocess.Popen([str(installer_path)], cwd=str(installer_path.parent))
            self.finished_success.emit(f"Instalador de {self.label} iniciado desde {drive_letter}:")
        except Exception as exc:
            msg = f"Error al montar o iniciar {self.label}: {exc}"
            self.log_message.emit(f"[ERROR] {msg}")
            self.failed.emit(msg)


class TaskWorker(QThread):
    """Ejecuta una tarea administrativa de system_tasks en segundo plano."""

    log_message = pyqtSignal(str)
    finished_success = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, fn: Callable[..., str], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result_msg = self._fn(*self._args, log=self.log_message.emit, **self._kwargs)
            self.finished_success.emit(result_msg or "Operación completada.")
        except Exception as exc:
            msg = str(exc)
            self.log_message.emit(f"[ERROR] {msg}")
            self.failed.emit(msg)
