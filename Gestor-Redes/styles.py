"""Hoja de estilos QSS monocromática (negro, gris y blanco) para Gestor de Redes."""

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

QLabel[statusRole="netBadge"] {
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

/* Filas horizontales y tarjetas de adaptador */
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

/* Panel inferior de log y salida de diagnóstico */
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
    padding: 6px;
}

/* Diálogos y controles */
QDialog {
    background-color: #0F1012;
}

QDialog QLabel {
    background-color: transparent;
    color: #F4F4F5;
}

QLineEdit, QComboBox, QSpinBox {
    background-color: #17191D;
    color: #F4F4F5;
    border: 1px solid #272A30;
    border-radius: 5px;
    padding: 5px 9px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border-color: #71717A;
}

QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {
    background-color: #131518;
    color: #52525B;
    border-color: #202328;
}

QComboBox QAbstractItemView {
    background-color: #17191D;
    color: #F4F4F5;
    border: 1px solid #272A30;
    selection-background-color: #2E323B;
    selection-color: #F4F4F5;
}

QCheckBox, QRadioButton {
    spacing: 7px;
    color: #E4E4E7;
    background-color: transparent;
}

QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border-radius: 8px;
    border: 2px solid #71717A;
    background-color: #0F1012;
}

QRadioButton::indicator:hover {
    border-color: #D4D4D8;
}

QRadioButton::indicator:checked {
    border: 2px solid #F4F4F5;
    background-color: #F4F4F5;
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
"""
