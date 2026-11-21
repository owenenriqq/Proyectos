"""Punto de entrada de la aplicación Utilidades con elevación UAC nativa."""

import ctypes
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication

# Asegura que el directorio src esté en sys.path al ejecutar como script
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import DARK_MONOCHROME_QSS
from ui.main_window import MainWindow


def is_admin() -> bool:
    """Verifica si el proceso actual cuenta con privilegios de Administrador."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def elevate_uac() -> None:
    """Relanza la aplicación solicitando elevación UAC nativa mediante ShellExecuteW."""
    script = str(Path(__file__).resolve())
    params = f'"{script}"'
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)


def main() -> int:
    """Inicializa la aplicación PyQt6 verificando privilegios administrativos."""
    if not is_admin():
        elevate_uac()
        return 0

    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_MONOCHROME_QSS)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
