"""Workers QThread reutilizables para operaciones de adaptadores y diagnóstico de red."""

from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import QThread, pyqtSignal

import net_tasks


class AdapterRefreshWorker(QThread):
    """Consulta la lista de adaptadores de red de Windows en segundo plano."""

    adapters_ready = pyqtSignal(list)
    failed = pyqtSignal(str)

    def run(self) -> None:
        try:
            adapters = net_tasks.list_network_adapters()
            self.adapters_ready.emit(adapters)
        except Exception as exc:
            self.failed.emit(net_tasks.format_task_exception(exc))


class ConnectivityCheckWorker(QThread):
    """Verifica conectividad externa y resolución DNS para el indicador superior."""

    status_ready = pyqtSignal(dict)

    def __init__(self, timeout: float = 2.0) -> None:
        super().__init__()
        self._timeout = timeout

    def run(self) -> None:
        try:
            result = net_tasks.check_internet_connectivity(timeout=self._timeout)
        except Exception:
            result = {"online": False, "host": "", "latency_ms": None, "dns_ok": False}
        self.status_ready.emit(result)


class TaskWorker(QThread):
    """Ejecuta una tarea administrativa de red en segundo plano."""

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
            msg = net_tasks.format_task_exception(exc)
            self.log_message.emit(f"[ERROR] {msg}")
            self.failed.emit(msg)


class DiagnosticWorker(QThread):
    """Ejecuta pruebas de diagnóstico de red y emite la salida textual completa."""

    log_message = pyqtSignal(str)
    output_ready = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, fn: Callable[..., str], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            output = self._fn(*self._args, log=self.log_message.emit, **self._kwargs)
            self.output_ready.emit(output or "")
        except Exception as exc:
            msg = net_tasks.format_task_exception(exc)
            self.log_message.emit(f"[ERROR] {msg}")
            self.failed.emit(msg)
