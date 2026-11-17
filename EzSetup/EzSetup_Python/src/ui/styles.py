"""Hoja de estilos QSS minimalista (tema oscuro profesional) para EzSetup."""

DARK_THEME_QSS = """
QMainWindow, QWidget {
    background-color: #0f172a;
    color: #f8fafc;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

QFrame#TopBar {
    background-color: #111c33;
    border-bottom: 1px solid #1e293b;
}

QLabel#AppTitle {
    font-size: 16px;
    font-weight: 700;
    color: #f8fafc;
}

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

QLabel[statusRole="serverBadge"] {
    background-color: #1e293b;
    color: #cbd5e1;
    border: 1px solid #334155;
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
    background-color: #1e293b;
    color: #94a3b8;
    border: 1px solid #475569;
}

QListWidget#SidebarNav {
    background-color: #111c33;
    border: none;
    border-right: 1px solid #1e293b;
    padding: 10px 8px;
    outline: 0;
}

QListWidget#SidebarNav::item {
    color: #cbd5e1;
    padding: 9px 12px;
    margin-bottom: 3px;
    border-radius: 6px;
    font-weight: 500;
}

QListWidget#SidebarNav::item:hover {
    background-color: #1e293b;
    color: #ffffff;
}

QListWidget#SidebarNav::item:selected {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
}

QFrame#ContentToolbar {
    background-color: #0f172a;
    border-bottom: 1px solid #1e293b;
}

QLineEdit#SearchInput {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
}

QLineEdit#SearchInput:focus {
    border-color: #3b82f6;
}

QScrollArea {
    border: none;
    background-color: #0f172a;
}

QLabel#PageHeader {
    font-size: 17px;
    font-weight: 700;
    color: #f8fafc;
}

QLabel#SubgroupTitle {
    font-size: 11px;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-top: 6px;
    margin-bottom: 2px;
}

QFrame#ActionRow {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 7px;
}

QFrame#ActionRow:hover {
    border-color: #475569;
}

QLabel#RowTitle {
    font-size: 13px;
    font-weight: 600;
    color: #f1f5f9;
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
    background-color: #0f172a;
    color: #94a3b8;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 1px 7px;
    font-size: 10px;
    font-weight: 600;
}

QPushButton {
    background-color: #334155;
    color: #f8fafc;
    border: 1px solid #475569;
    border-radius: 5px;
    padding: 5px 11px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #475569;
}

QPushButton:pressed {
    background-color: #1e293b;
}

QPushButton:disabled {
    background-color: #1e293b;
    color: #64748b;
    border-color: #334155;
}

QPushButton#MoreButton {
    padding: 5px 8px;
    min-width: 26px;
}

QPushButton#MoreButton::menu-indicator {
    image: none;
    width: 0px;
}

QPushButton#PrimaryButton {
    background-color: #2563eb;
    border: 1px solid #3b82f6;
    color: #ffffff;
}

QPushButton#PrimaryButton:hover {
    background-color: #3b82f6;
}

QPushButton#PrimaryButton:pressed {
    background-color: #1d4ed8;
}

QPushButton#SuccessButton {
    background-color: #059669;
    border: 1px solid #10b981;
    color: #ffffff;
}

QPushButton#SuccessButton:hover {
    background-color: #10b981;
}

QPushButton#DangerButton {
    background-color: #b91c1c;
    border: 1px solid #ef4444;
    color: #ffffff;
}

QPushButton#DangerButton:hover {
    background-color: #dc2626;
}

QMenu {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #475569;
    padding: 4px;
}

QMenu::item {
    padding: 6px 14px;
    border-radius: 4px;
    font-size: 12px;
}

QMenu::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}

QFrame#LogPanel {
    background-color: #0b1220;
    border-top: 1px solid #1e293b;
}

QLabel#LogHeaderLabel {
    font-size: 11px;
    font-weight: 700;
    color: #94a3b8;
}

QLabel#LastLogEvent {
    font-family: "Consolas", "Cascadia Mono", monospace;
    font-size: 11px;
    color: #cbd5e1;
}

QPlainTextEdit#LogOutput {
    background-color: #020617;
    color: #e2e8f0;
    border: 1px solid #1e293b;
    border-radius: 5px;
    font-family: "Consolas", "Cascadia Mono", monospace;
    font-size: 12px;
    padding: 5px;
}

QDialog {
    background-color: #0f172a;
}

QLineEdit, QComboBox {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 5px;
    padding: 5px 9px;
}

QLineEdit:focus, QComboBox:focus {
    border-color: #3b82f6;
}

QCheckBox, QRadioButton {
    spacing: 7px;
    color: #e2e8f0;
}

QProgressBar {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 5px;
    text-align: center;
    color: #f8fafc;
    height: 18px;
}

QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 4px;
}

QScrollBar:vertical {
    background: #0f172a;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
