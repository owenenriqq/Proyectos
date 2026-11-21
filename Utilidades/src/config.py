"""Configuración global, constantes y estilos de la aplicación Utilidades."""

import sys
from pathlib import Path

APP_NAME = "Utilidades de Soporte Técnico"
APP_VERSION = "1.0.0"
WINDOW_MIN_WIDTH = 1040
WINDOW_MIN_HEIGHT = 620


def resolve_resource_path(relative_path: str) -> Path:
    """Resuelve rutas de recursos tanto en desarrollo como en binario congelado PyInstaller."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relative_path

# Hoja de estilos oscura monocromática consistente con el repositorio
DARK_MONOCHROME_QSS = """
QMainWindow, QWidget {
    background-color: #121212;
    color: #e0e0e0;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #2a2a2a;
    background-color: #161616;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #1a1a1a;
    color: #9e9e9e;
    padding: 8px 16px;
    border: 1px solid #2a2a2a;
    border-bottom: none;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #242424;
    color: #ffffff;
    font-weight: bold;
}

QGroupBox {
    border: 1px solid #2c2c2c;
    border-radius: 6px;
    margin-top: 12px;
    padding: 12px;
    background-color: #181818;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #cccccc;
}

QLineEdit {
    background-color: #1e1e1e;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 6px 10px;
    color: #ffffff;
}

QLineEdit:focus {
    border: 1px solid #666666;
}

QPushButton {
    background-color: #262626;
    color: #f0f0f0;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    padding: 7px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #323232;
    border-color: #555555;
}

QPushButton:pressed {
    background-color: #1e1e1e;
}

QPushButton:disabled {
    background-color: #1a1a1a;
    color: #555555;
    border-color: #262626;
}

QPlainTextEdit {
    background-color: #0e0e0e;
    color: #d4d4d4;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    font-family: "Consolas", monospace;
    font-size: 12px;
    padding: 8px;
}

QLabel#StatusLabel {
    color: #a0a0a0;
    font-size: 12px;
}
"""
