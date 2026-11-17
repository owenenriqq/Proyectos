"""Punto de entrada de EzSetup v2.0 con verificación/elevación UAC."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.config import AppConfig, ConfigError
from src.ui.main_window import MainWindow
from src.ui.styles import DARK_THEME_QSS


def is_user_admin() -> bool:
    """Retorna True si el proceso actual tiene privilegios de Administrador en Windows."""
    if os.name != "nt":
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> bool:
    """Relanza el script o ejecutable actual solicitando elevación UAC."""
    if os.name != "nt":
        return False

    if getattr(sys, "frozen", False):
        executable = sys.executable
        params = subprocess.list2cmdline(sys.argv[1:])
    else:
        executable = sys.executable
        params = subprocess.list2cmdline([os.path.abspath(__file__), *sys.argv[1:]])

    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        executable,
        params,
        None,
        1,
    )
    return int(result) > 32


def main() -> int:
    skip_uac = "--no-elevate" in sys.argv
    admin = is_user_admin()

    if not admin and not skip_uac:
        if relaunch_as_admin():
            return 0

    try:
        config = AppConfig.load()
    except ConfigError as exc:
        app = QApplication(sys.argv)
        QMessageBox.critical(None, "Error de configuración", str(exc))
        return 1

    if os.name == "nt":
        app_id = str(config.app.get("app_user_model_id", "Eidico.EzSetup.2.0"))
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName(str(config.app["name"]))
    app.setApplicationVersion(str(config.app["version"]))
    app.setStyleSheet(DARK_THEME_QSS)

    icon_path = config.get_asset_path("EzSetup.ico")
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow(config=config, is_admin=admin)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
