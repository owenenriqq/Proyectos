"""Trabajadores asíncronos para ejecutar operaciones de sistema sin bloquear la UI."""

from typing import Callable, Any
from PyQt6.QtCore import QThread, pyqtSignal


class TaskWorker(QThread):
    """Ejecuta una función de backend en un hilo secundario y emite el resultado."""

    finished_signal = pyqtSignal(bool, str)

    def __init__(self, task_fn: Callable[..., tuple[bool, str]], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self._task_fn = task_fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        """Ejecuta la tarea encapsulando excepciones no controladas."""
        try:
            ok, message = self._task_fn(*self._args, **self._kwargs)
            self.finished_signal.emit(ok, message)
        except Exception as exc:
            self.finished_signal.emit(False, f"Error inesperado: {exc}")


class StreamingTaskWorker(QThread):
    """Ejecuta una tarea de larga duración emitiendo logs y progreso en tiempo real."""

    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, task_fn: Callable[..., tuple[bool, str]]) -> None:
        super().__init__()
        self._task_fn = task_fn

    def run(self) -> None:
        """Ejecuta la tarea pasando callbacks seguros hacia señales Qt."""
        try:
            ok, message = self._task_fn(self.log_signal.emit, self.progress_signal.emit)
            self.finished_signal.emit(ok, message)
        except Exception as exc:
            self.finished_signal.emit(False, f"Error inesperado: {exc}")
