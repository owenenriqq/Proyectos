"""Hoja de estilos QSS monocromática (negro, gris y blanco) para EzSetup."""

from __future__ import annotations

from pathlib import Path
import sys


def _resolve_check_icon_rule() -> str:
    """Resuelve la ruta de assets/check_dark.png para QCheckBox::indicator:checked."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / "assets" / "check_dark.png")
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass).resolve() / "assets" / "check_dark.png")
    candidates.append(Path(__file__).resolve().parents[2] / "assets" / "check_dark.png")

    for icon_path in candidates:
        if icon_path.is_file():
            return f'    image: url("{icon_path.as_posix()}");'
    return ""


_CHECK_ICON_RULE = _resolve_check_icon_rule()

DARK_THEME_QSS = """
QMainWindow, QWidget {
    background-color: #0F1012;
    color: #F4F4F5;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

QFrame#TopBar {
    background-color: #17191D;
    border-bottom: 1px solid #272A30;
}

QLabel#AppTitle {
    font-size: 16px;
    font-weight: 700;
    color: #F4F4F5;
    background-color: transparent;
}

/* Badges semánticos de estado */
QLabel#AdminBadgeOk {
    background-color: #064e3b;
    color: #6ee7b7;
    border: 1px solid #10b981;
    border-radius: 9px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#AdminBadgeWarn {
    background-color: #451a03;
    color: #fcd34d;
    border: 1px solid #f59e0b;
    border-radius: 9px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 600;
}

QPushButton#AdminBadgeWarnBtn {
    background-color: #451a03;
    color: #fcd34d;
    border: 1px solid #f59e0b;
    border-radius: 9px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 600;
}

QPushButton#AdminBadgeWarnBtn:hover {
    background-color: #78350f;
    color: #fef3c7;
}

QLabel[statusRole="serverBadge"], QLabel[statusRole="netBadge"] {
    background-color: #1F2228;
    color: #A1A1AA;
    border: 1px solid #272A30;
    border-radius: 9px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 600;
}

QLabel[statusState="online"] {
    background-color: #064e3b;
    color: #6ee7b7;
    border: 1px solid #10b981;
}

QLabel[statusState="offline"] {
    background-color: #450a0a;
    color: #fca5a5;
    border: 1px solid #ef4444;
}

QLabel[statusState="checking"] {
    background-color: #1F2228;
    color: #A1A1AA;
    border: 1px solid #323640;
}

/* Navegación lateral */
QListWidget#SidebarNav {
    background-color: #17191D;
    border: none;
    border-right: 1px solid #272A30;
    padding: 10px 8px;
    outline: 0;
}

QListWidget#SidebarNav::item {
    color: #A1A1AA;
    padding: 9px 12px;
    margin-bottom: 3px;
    border-left: 3px solid transparent;
    border-radius: 5px;
    font-weight: 500;
}

QListWidget#SidebarNav::item:hover {
    background-color: #1F2228;
    color: #F4F4F5;
}

QListWidget#SidebarNav::item:selected {
    background-color: #24272E;
    border-left: 3px solid #F4F4F5;
    color: #F4F4F5;
    font-weight: 600;
}

QFrame#ContentToolbar {
    background-color: #0F1012;
    border-bottom: 1px solid #272A30;
}

QLineEdit#SearchInput {
    background-color: #17191D;
    color: #F4F4F5;
    border: 1px solid #272A30;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
}

QLineEdit#SearchInput:focus {
    border-color: #71717A;
}

QScrollArea {
    border: none;
    background-color: #0F1012;
}

QLabel#PageHeader {
    font-size: 17px;
    font-weight: 700;
    color: #F4F4F5;
    background-color: transparent;
}

QLabel#SubgroupTitle {
    font-size: 11px;
    font-weight: 700;
    color: #71717A;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-top: 6px;
    margin-bottom: 2px;
    background-color: transparent;
}

/* Filas horizontales */
QFrame#ActionRow {
    background-color: #17191D;
    border: 1px solid #272A30;
    border-radius: 7px;
}

QFrame#ActionRow:hover {
    border-color: #3A3F48;
}

QLabel#RowTitle {
    font-size: 13px;
    font-weight: 600;
    color: #F4F4F5;
    background-color: transparent;
}

QLabel#RowMeta {
    font-family: "Consolas", "Cascadia Mono", monospace;
    font-size: 11px;
    color: #A1A1AA;
    background-color: transparent;
}

QLabel#RowSubtitle {
    font-size: 11px;
    color: #71717A;
    background-color: transparent;
}

QLabel#RowBadgeOk {
    background-color: #064e3b;
    color: #6ee7b7;
    border: 1px solid #10b981;
    border-radius: 8px;
    padding: 1px 7px;
    font-size: 10px;
    font-weight: 600;
}

QLabel#RowBadgeWarn {
    background-color: #451a03;
    color: #fcd34d;
    border: 1px solid #f59e0b;
    border-radius: 8px;
    padding: 1px 7px;
    font-size: 10px;
    font-weight: 600;
}

QLabel#RowBadgeMuted {
    background-color: #1F2228;
    color: #A1A1AA;
    border: 1px solid #272A30;
    border-radius: 8px;
    padding: 1px 7px;
    font-size: 10px;
    font-weight: 600;
}

/* Botones monocromáticos */
QPushButton {
    background-color: #1F2228;
    color: #E4E4E7;
    border: 1px solid #323640;
    border-radius: 5px;
    padding: 5px 11px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton[compact="true"] {
    padding: 4px 8px;
}

QPushButton:hover {
    background-color: #2A2E37;
    border-color: #3E434F;
}

QPushButton:pressed {
    background-color: #17191D;
}

QPushButton:disabled {
    background-color: #17191D;
    color: #52525B;
    border-color: #272A30;
}

QPushButton#MoreButton {
    padding: 0px;
    min-width: 32px;
    max-width: 32px;
    min-height: 30px;
    max-height: 30px;
}

QPushButton#MoreButton::menu-indicator {
    image: none;
    width: 0px;
}

QPushButton#EyeButton {
    padding: 0px;
    min-width: 32px;
    max-width: 32px;
    min-height: 30px;
    max-height: 30px;
}

QPushButton#PrimaryButton {
    background-color: #F4F4F5;
    border: 1px solid #F4F4F5;
    color: #111111;
}

QPushButton#PrimaryButton:hover {
    background-color: #DCDCE0;
    border-color: #DCDCE0;
}

QPushButton#PrimaryButton:pressed {
    background-color: #C4C4CA;
    border-color: #C4C4CA;
}

QPushButton#SuccessButton {
    background-color: #2E323B;
    border: 1px solid #525866;
    color: #F4F4F5;
}

QPushButton#SuccessButton:hover {
    background-color: #3A3F4B;
    border-color: #6B7280;
}

QPushButton#SuccessButton:pressed {
    background-color: #24272E;
}

QPushButton#DangerButton {
    background-color: #450a0a;
    border: 1px solid #b91c1c;
    color: #fecaca;
}

QPushButton#DangerButton:hover {
    background-color: #7f1d1d;
}

QMenu {
    background-color: #17191D;
    color: #F4F4F5;
    border: 1px solid #272A30;
    padding: 4px;
}

QMenu::item {
    padding: 6px 14px;
    border-radius: 4px;
    font-size: 12px;
}

QMenu::item:selected {
    background-color: #2E323B;
    color: #F4F4F5;
}

/* Panel inferior de log */
QFrame#LogPanel {
    background-color: #17191D;
    border-top: 1px solid #272A30;
}

QLabel#LogHeaderLabel {
    font-size: 11px;
    font-weight: 700;
    color: #A1A1AA;
    background-color: transparent;
}

QLabel#LastLogEvent {
    font-family: "Consolas", "Cascadia Mono", monospace;
    font-size: 11px;
    color: #D4D4D8;
    background-color: transparent;
}

QPlainTextEdit#LogOutput, QPlainTextEdit#DiagnosticOutput {
    background-color: #0A0B0D;
    color: #E4E4E7;
    border: 1px solid #272A30;
    border-radius: 5px;
    font-family: "Consolas", "Cascadia Mono", monospace;
    font-size: 12px;
    padding: 5px;
}

/* Diálogos y controles */
QDialog {
    background-color: #0F1012;
}

QDialog QLabel {
    background-color: transparent;
    color: #F4F4F5;
}

QLineEdit, QComboBox, QDateEdit, QSpinBox, QPlainTextEdit {
    background-color: #17191D;
    color: #F4F4F5;
    border: 1px solid #272A30;
    border-radius: 5px;
    padding: 5px 9px;
}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QPlainTextEdit:focus {
    border-color: #71717A;
}

QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled, QSpinBox:disabled {
    background-color: #131518;
    color: #52525B;
    border-color: #202328;
}

QComboBox:disabled {
    background-color: #15171B;
    color: #8E8E98;
    border-color: #272A30;
}

QTabWidget::pane {
    border: none;
    border-top: 1px solid #272A30;
    background-color: #0F1012;
}

QTabBar::tab {
    background-color: #17191D;
    color: #A1A1AA;
    border: 1px solid #272A30;
    border-bottom: none;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    padding: 7px 14px;
    margin-right: 4px;
    font-size: 12px;
    font-weight: 600;
}

QTabBar::tab:hover {
    background-color: #1F2228;
    color: #F4F4F5;
}

QTabBar::tab:selected {
    background-color: #24272E;
    color: #F4F4F5;
    border-color: #3A3F48;
}

QComboBox QAbstractItemView {
    background-color: #17191D;
    color: #F4F4F5;
    border: 1px solid #272A30;
    selection-background-color: #2E323B;
    selection-color: #F4F4F5;
}

QCalendarWidget {
    min-width: 300px;
    min-height: 220px;
    background-color: #17191D;
    color: #F4F4F5;
    border: 1px solid #272A30;
}

QCalendarWidget QWidget {
    background-color: #17191D;
    color: #F4F4F5;
}

QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #24272E;
    min-height: 30px;
    border-bottom: 1px solid #272A30;
}

QCalendarWidget QToolButton {
    color: #F4F4F5;
    background-color: transparent;
    font-weight: 600;
    border: none;
    padding: 3px 6px;
}

QCalendarWidget QToolButton:hover {
    background-color: #2E323B;
    border-radius: 4px;
}

QCalendarWidget QAbstractItemView {
    background-color: #17191D;
    color: #F4F4F5;
    selection-background-color: #F4F4F5;
    selection-color: #111111;
    outline: 0;
}

QCalendarWidget QSpinBox {
    background-color: #17191D;
    color: #F4F4F5;
    border: 1px solid #272A30;
    border-radius: 4px;
}

QCheckBox, QRadioButton {
    spacing: 7px;
    color: #E4E4E7;
    background-color: transparent;
}

QCheckBox:disabled {
    color: #71717A;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #52525B;
    background-color: #17191D;
    border-radius: 4px;
}

QCheckBox::indicator:hover {
    border-color: #A1A1AA;
    background-color: #1F2228;
}

QCheckBox::indicator:checked {
    border: 1px solid #F4F4F5;
    background-color: #F4F4F5;
__CHECK_ICON_RULE__
}

QCheckBox::indicator:checked:hover {
    border-color: #DCDCE0;
    background-color: #DCDCE0;
}

QCheckBox::indicator:disabled {
    border-color: #323640;
    background-color: #131518;
}

QCheckBox::indicator:checked:disabled {
    border-color: #71717A;
    background-color: #71717A;
__CHECK_ICON_RULE__
}

QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border-radius: 9px;
    border: 2px solid #71717A;
    background-color: #17191D;
}

QRadioButton::indicator:hover {
    border-color: #D4D4D8;
}

QRadioButton::indicator:checked {
    border: 2px solid #F4F4F5;
    background-color: qradialgradient(
        cx: 0.5, cy: 0.5, radius: 0.5,
        fx: 0.5, fy: 0.5,
        stop: 0.0 #F4F4F5,
        stop: 0.42 #F4F4F5,
        stop: 0.48 #17191D,
        stop: 1.0 #17191D
    );
}

QRadioButton::indicator:disabled {
    border-color: #3A3F48;
    background-color: #131518;
}

QProgressBar {
    background-color: #17191D;
    border: 1px solid #272A30;
    border-radius: 5px;
    text-align: center;
    color: #F4F4F5;
    height: 18px;
}

QProgressBar::chunk {
    background-color: #525866;
    border-radius: 4px;
}

QScrollBar:vertical {
    background: #0F1012;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #272A30;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #3A3F48;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
""".replace("__CHECK_ICON_RULE__", _CHECK_ICON_RULE)
