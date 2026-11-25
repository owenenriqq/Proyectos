"""Diálogos modales seguros para credenciales (cifradas/manuales) y progreso."""

from __future__ import annotations

import ipaddress
import os
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import QDate, QPointF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.config import AppConfig
from src.crypto_store import (
    CredentialCryptoError,
    CredentialIntegrityError,
    CredentialIOError,
    load_encrypted_credentials,
)
from src.modules.inventory.inventory_tasks import (
    collect_hardware_info,
    export_inventory_record_local,
    format_hardware_preview,
    format_inventory_record,
    save_inventory_record,
)
from src.modules.utilities.diagnostics import (
    export_diagnostic_report,
    get_battery_report_path,
    run_full_diagnostics,
)
from src.workers import TaskWorker


def _create_eye_icon(crossed: bool = False) -> QIcon:
    """Dibuja vectorialmente un ícono de ojo abierto o tachado para campos de contraseña."""
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor("#e2e8f0"), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    eye_path = QPainterPath()
    eye_path.moveTo(2.5, 10.0)
    eye_path.quadTo(10.0, 3.5, 17.5, 10.0)
    eye_path.quadTo(10.0, 16.5, 2.5, 10.0)
    painter.drawPath(eye_path)
    painter.drawEllipse(QPointF(10.0, 10.0), 2.4, 2.4)

    if crossed:
        painter.drawLine(QPointF(3.5, 16.5), QPointF(16.5, 3.5))

    painter.end()
    return QIcon(pixmap)


class _CredentialEntryBlock(QFrame):
    """Bloque de entrada manual de usuario y contraseña para un servidor."""

    def __init__(self, server_key: str, server_info: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.server_key = server_key
        self.server_info = server_info
        self.setObjectName("ActionRow")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel(f"{server_info.get('label', server_key)} ({server_info.get('host', '')})", self)
        title.setObjectName("RowTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(6)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Usuario (ej: dominio\\usuario)")
        hint = str(server_info.get("default_user_hint", "")).strip()
        if hint:
            self.username_edit.setText(hint)

        pwd_row = QHBoxLayout()
        pwd_row.setSpacing(6)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Ingresá la contraseña")

        self.toggle_btn = QPushButton("", self)
        self.toggle_btn.setObjectName("EyeButton")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setFixedSize(32, 30)
        self.toggle_btn.setIcon(_create_eye_icon(False))
        self.toggle_btn.setIconSize(QSize(18, 18))
        self.toggle_btn.setToolTip("Mostrar contraseña")
        self.toggle_btn.toggled.connect(self._on_toggle_password)

        pwd_row.addWidget(self.password_edit)
        pwd_row.addWidget(self.toggle_btn)

        form.addRow("Usuario:", self.username_edit)
        form.addRow("Contraseña:", pwd_row)
        layout.addLayout(form)

    def _on_toggle_password(self, checked: bool) -> None:
        if checked:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_btn.setIcon(_create_eye_icon(True))
            self.toggle_btn.setToolTip("Ocultar contraseña")
        else:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_btn.setIcon(_create_eye_icon(False))
            self.toggle_btn.setToolTip("Mostrar contraseña")

    def get_values(self) -> tuple[str, str]:
        return self.username_edit.text().strip(), self.password_edit.text()


class CredentialDialog(QDialog):
    """Diálogo de credenciales con soporte para credentials.enc (AES-256-GCM) o ingreso manual."""

    def __init__(
        self,
        config: AppConfig,
        parent: QWidget | None = None,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self._log_callback = log_callback
        self._servers = config.get_servers()
        self._blocks: dict[str, _CredentialEntryBlock] = {}
        self._enc_path: Path | None = config.resolve_credentials_enc_path()
        self._resolved_entries: list[dict[str, Any]] = []

        self.setWindowTitle("Configurar Credenciales de Red")
        self.setMinimumWidth(490)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(14)
        self.master_radio = QRadioButton("Archivo cifrado (credentials.enc)")
        self.manual_radio = QRadioButton("Ingreso manual")
        self.master_radio.toggled.connect(self._on_mode_changed)
        mode_row.addWidget(self.master_radio)
        mode_row.addWidget(self.manual_radio)
        mode_row.addStretch()
        root.addLayout(mode_row)

        self.mode_stack = QStackedWidget()
        self.mode_stack.addWidget(self._build_master_page())
        self.mode_stack.addWidget(self._build_manual_page())
        root.addWidget(self.mode_stack)

        self.shortcut_checkbox = QCheckBox("Crear accesos directos en el Escritorio")
        self.shortcut_checkbox.setChecked(True)
        root.addWidget(self.shortcut_checkbox)

        buttons_row = QHBoxLayout()
        buttons_row.addStretch()
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn = QPushButton("Registrar")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self._on_accept)
        buttons_row.addWidget(self.cancel_btn)
        buttons_row.addWidget(self.save_btn)
        root.addLayout(buttons_row)

        if self._enc_path is not None:
            self.master_radio.setChecked(True)
        else:
            self.manual_radio.setChecked(True)
        self._on_mode_changed()

    def _build_master_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

        card = QFrame()
        card.setObjectName("ActionRow")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(8)

        file_row = QHBoxLayout()
        self.enc_path_edit = QLineEdit()
        self.enc_path_edit.setReadOnly(True)
        self.enc_path_edit.setPlaceholderText("Archivo credentials.enc no detectado")
        if self._enc_path is not None:
            self.enc_path_edit.setText(str(self._enc_path))
        browse_btn = QPushButton("Examinar...")
        browse_btn.clicked.connect(self._browse_enc_file)
        file_row.addWidget(self.enc_path_edit, stretch=1)
        file_row.addWidget(browse_btn)
        card_layout.addLayout(file_row)

        form = QFormLayout()
        form.setSpacing(6)
        pwd_row = QHBoxLayout()
        pwd_row.setSpacing(6)
        self.master_pwd_edit = QLineEdit()
        self.master_pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.master_pwd_edit.setPlaceholderText("Ingresá la Contraseña Maestra de IT")
        self.master_toggle_btn = QPushButton("", card)
        self.master_toggle_btn.setObjectName("EyeButton")
        self.master_toggle_btn.setCheckable(True)
        self.master_toggle_btn.setFixedSize(32, 30)
        self.master_toggle_btn.setIcon(_create_eye_icon(False))
        self.master_toggle_btn.setIconSize(QSize(18, 18))
        self.master_toggle_btn.setToolTip("Mostrar contraseña")
        self.master_toggle_btn.toggled.connect(self._on_toggle_master_pwd)
        pwd_row.addWidget(self.master_pwd_edit)
        pwd_row.addWidget(self.master_toggle_btn)

        form.addRow("Contraseña Maestra:", pwd_row)
        card_layout.addLayout(form)
        layout.addWidget(card)
        return page

    def _build_manual_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Servidor:"))
        self.target_combo = QComboBox()
        for key, info in self._servers.items():
            display = f"{info.get('label', key)} ({info.get('host', '')})"
            self.target_combo.addItem(display, userData=key)
        if len(self._servers) > 1:
            self.target_combo.addItem("Todos los servidores", userData="__all__")
        self.target_combo.currentIndexChanged.connect(self._refresh_visible_blocks)
        selector_row.addWidget(self.target_combo, stretch=1)
        layout.addLayout(selector_row)

        for key, info in self._servers.items():
            block = _CredentialEntryBlock(key, info, page)
            self._blocks[key] = block
            layout.addWidget(block)

        self._refresh_visible_blocks()
        return page

    def _on_toggle_master_pwd(self, checked: bool) -> None:
        if checked:
            self.master_pwd_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.master_toggle_btn.setIcon(_create_eye_icon(True))
            self.master_toggle_btn.setToolTip("Ocultar contraseña")
        else:
            self.master_pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.master_toggle_btn.setIcon(_create_eye_icon(False))
            self.master_toggle_btn.setToolTip("Mostrar contraseña")

    def _browse_enc_file(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo cifrado",
            str(self.config.get_default_credentials_enc_path().parent),
            "Credenciales cifradas (*.enc);;Todos los archivos (*.*)",
        )
        if selected:
            self._enc_path = Path(selected)
            self.enc_path_edit.setText(selected)

    def _on_mode_changed(self, _checked: bool = False) -> None:
        if self.master_radio.isChecked():
            self.mode_stack.setCurrentIndex(0)
            self.master_pwd_edit.setFocus()
        else:
            self.mode_stack.setCurrentIndex(1)
        self.adjustSize()

    def _active_server_keys(self) -> list[str]:
        selected = self.target_combo.currentData()
        if selected == "__all__":
            return list(self._servers.keys())
        return [str(selected)]

    def _refresh_visible_blocks(self, _index: int = 0) -> None:
        active = set(self._active_server_keys())
        for key, block in self._blocks.items():
            block.setVisible(key in active)
        self.adjustSize()

    def _emit_log(self, msg: str) -> None:
        if self._log_callback is not None:
            self._log_callback(msg)

    def _on_accept(self) -> None:
        create_lnk = self.shortcut_checkbox.isChecked()

        if self.master_radio.isChecked():
            raw_path = self.enc_path_edit.text().strip()
            if not raw_path:
                QMessageBox.warning(
                    self,
                    "Archivo faltante",
                    "Seleccioná un archivo credentials.enc o usá el modo de ingreso manual.",
                )
                return

            if not os.path.isfile(raw_path):
                self._emit_log(
                    f"[ERROR] Almacén credentials.enc inexistente o sin acceso: {raw_path}"
                )
                QMessageBox.warning(
                    self,
                    "Archivo no encontrado",
                    f"No se encontró credentials.enc o no hay acceso a la ruta:\n{raw_path}",
                )
                return

            master_pwd = self.master_pwd_edit.text()
            if not master_pwd:
                QMessageBox.warning(
                    self,
                    "Contraseña requerida",
                    "Ingresá la Contraseña Maestra de IT.",
                )
                return

            try:
                decrypted = load_encrypted_credentials(Path(raw_path), master_pwd)
            except CredentialIntegrityError as exc:
                self._emit_log(f"[ERROR] Fallo de descifrado AES-GCM ({raw_path}): {exc}")
                QMessageBox.warning(
                    self,
                    "Contraseña incorrecta o archivo modificado",
                    f"{exc}\n\nVerificá la Contraseña Maestra de IT.",
                )
                return
            except CredentialIOError as exc:
                self._emit_log(f"[ERROR] Error de E/S accediendo a {raw_path}: {exc}")
                QMessageBox.warning(self, "Error de acceso al archivo", str(exc))
                return
            except CredentialCryptoError as exc:
                self._emit_log(f"[ERROR] Error general en almacén cifrado ({raw_path}): {exc}")
                QMessageBox.warning(self, "Error de descifrado", str(exc))
                return

            entries: list[dict[str, Any]] = []
            for server_key in self._servers:
                item = decrypted.get(server_key)
                if not item:
                    continue
                entries.append(
                    {
                        "server_key": server_key,
                        "username": item["username"],
                        "password": item["password"],
                        "create_shortcut": create_lnk,
                    }
                )

            if not entries:
                QMessageBox.warning(
                    self,
                    "Sin coincidencias",
                    "El archivo descifrado no contiene credenciales para los servidores configurados.",
                )
                return

            self._resolved_entries = entries
            self.accept()
            return

        manual_entries: list[dict[str, Any]] = []
        for key in self._active_server_keys():
            user, pwd = self._blocks[key].get_values()
            if not user or not pwd:
                label = self._servers[key].get("label", key)
                QMessageBox.warning(
                    self,
                    "Campos incompletos",
                    f"Completá usuario y contraseña para {label}.",
                )
                return

            hint = str(self._servers[key].get("default_user_hint", "")).strip()
            if "\\" not in user and "\\" in hint:
                domain_prefix = hint.split("\\", 1)[0]
                user = f"{domain_prefix}\\{user}"

            manual_entries.append(
                {
                    "server_key": key,
                    "username": user,
                    "password": pwd,
                    "create_shortcut": create_lnk,
                }
            )

        self._resolved_entries = manual_entries
        self.accept()

    def get_entries(self) -> list[dict[str, Any]]:
        """Devuelve las credenciales listas para aplicar con cmdkey."""
        return list(self._resolved_entries)


class ProgressDialog(QDialog):
    """Diálogo de progreso con soporte de cancelación para descargas y copias."""

    cancel_requested = pyqtSignal()

    def __init__(self, title: str, status_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.status_label = QLabel(status_text)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.detail_label = QLabel("Preparando operación...")
        self.detail_label.setObjectName("LastLogEvent")
        layout.addWidget(self.detail_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.setObjectName("DangerButton")
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self.cancel_btn)
        layout.addLayout(btn_row)

    def _on_cancel(self) -> None:
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("Cancelando operación...")
        self.cancel_requested.emit()

    def update_progress(self, percent: int, current_mb: float, total_mb: float) -> None:
        if total_mb > 0:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(percent)
            self.detail_label.setText(f"{current_mb:.2f} MB / {total_mb:.2f} MB ({percent}%)")
        else:
            self.progress_bar.setRange(0, 0)
            self.detail_label.setText(f"{current_mb:.2f} MB transferidos...")


class PrinterInstallDialog(QDialog):
    """Diálogo modal monocromático para instalar impresoras de red por IP."""

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self._printers_cfg = config.get_printers_config()
        self._drivers: dict[str, dict[str, Any]] = dict(self._printers_cfg.get("drivers", {}))
        self._catalog: list[dict[str, Any]] = list(self._printers_cfg.get("catalog", []))
        self._catalog_checks: list[tuple[QCheckBox, dict[str, str]]] = []
        self._selected_printers: list[dict[str, str]] = []

        self.setWindowTitle("Instalar Impresoras de Oficina por IP")
        self.setMinimumWidth(520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("Seleccioná las impresoras a instalar:"))
        header_row.addStretch()
        select_all_btn = QPushButton("Seleccionar todas")
        select_all_btn.clicked.connect(lambda _c=False: self._set_all_checked(True))
        clear_all_btn = QPushButton("Limpiar selección")
        clear_all_btn.clicked.connect(lambda _c=False: self._set_all_checked(False))
        header_row.addWidget(select_all_btn)
        header_row.addWidget(clear_all_btn)
        root.addLayout(header_row)

        catalog_card = QFrame()
        catalog_card.setObjectName("CredentialCard")
        catalog_card_layout = QVBoxLayout(catalog_card)
        catalog_card_layout.setContentsMargins(10, 8, 10, 8)
        catalog_card_layout.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMaximumHeight(230)
        scroll_inner = QWidget()
        scroll_layout = QVBoxLayout(scroll_inner)
        scroll_layout.setContentsMargins(2, 2, 2, 2)
        scroll_layout.setSpacing(5)

        for entry in self._catalog:
            name = str(entry.get("name", "")).strip()
            ip_str = str(entry.get("ip", "")).strip()
            driver_key = str(entry.get("driver_key", "")).strip()
            driver_info = self._drivers.get(driver_key, {})
            driver_name = str(driver_info.get("driver_name", "")).strip()
            inf_path = str(driver_info.get("inf_path", "")).strip()
            driver_label = str(driver_info.get("label", driver_name or driver_key))

            chk = QCheckBox(f"{name} ({ip_str}) — {driver_label}")
            scroll_layout.addWidget(chk)
            self._catalog_checks.append(
                (
                    chk,
                    {
                        "name": name,
                        "ip": ip_str,
                        "driver_name": driver_name,
                        "inf_path": inf_path,
                    },
                )
            )
        scroll_layout.addStretch()
        scroll.setWidget(scroll_inner)
        catalog_card_layout.addWidget(scroll)
        root.addWidget(catalog_card)

        manual_card = QFrame()
        manual_card.setObjectName("CredentialCard")
        manual_layout = QVBoxLayout(manual_card)
        manual_layout.setContentsMargins(12, 10, 12, 10)
        manual_layout.setSpacing(8)

        self.manual_enable_chk = QCheckBox("Agregar impresora manual por IP")
        self.manual_enable_chk.toggled.connect(self._on_manual_toggled)
        manual_layout.addWidget(self.manual_enable_chk)

        manual_form = QFormLayout()
        manual_form.setSpacing(8)

        self.manual_name_edit = QLineEdit()
        self.manual_name_edit.setPlaceholderText("Ej: HP Sala de Reuniones")
        self.manual_ip_edit = QLineEdit()
        self.manual_ip_edit.setPlaceholderText("Ej: 192.168.1.50")

        self.manual_driver_combo = QComboBox()
        for d_key, d_info in self._drivers.items():
            d_label = str(d_info.get("label") or d_info.get("driver_name") or d_key)
            self.manual_driver_combo.addItem(d_label, userData=d_key)

        manual_form.addRow("Nombre:", self.manual_name_edit)
        manual_form.addRow("Dirección IP:", self.manual_ip_edit)
        manual_form.addRow("Driver:", self.manual_driver_combo)
        manual_layout.addLayout(manual_form)
        root.addWidget(manual_card)

        self._on_manual_toggled(False)

        buttons_row = QHBoxLayout()
        buttons_row.addStretch()
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        self.accept_btn = QPushButton("Instalar Seleccionadas")
        self.accept_btn.setObjectName("PrimaryButton")
        self.accept_btn.clicked.connect(self._on_accept)
        buttons_row.addWidget(self.cancel_btn)
        buttons_row.addWidget(self.accept_btn)
        root.addLayout(buttons_row)

    def _set_all_checked(self, checked: bool) -> None:
        for chk, _ in self._catalog_checks:
            chk.setChecked(checked)

    def _on_manual_toggled(self, enabled: bool) -> None:
        self.manual_name_edit.setEnabled(enabled)
        self.manual_ip_edit.setEnabled(enabled)
        self.manual_driver_combo.setEnabled(enabled)

    def _on_accept(self) -> None:
        selected: list[dict[str, str]] = [
            data for chk, data in self._catalog_checks if chk.isChecked()
        ]

        if self.manual_enable_chk.isChecked():
            m_name = self.manual_name_edit.text().strip()
            m_ip = self.manual_ip_edit.text().strip()
            d_key = str(self.manual_driver_combo.currentData() or "")
            d_info = self._drivers.get(d_key, {})

            if not m_name:
                QMessageBox.warning(
                    self,
                    "Nombre faltante",
                    "Ingresá un nombre para la impresora manual.",
                )
                return
            try:
                ipaddress.ip_address(m_ip)
            except ValueError:
                QMessageBox.warning(
                    self,
                    "IP inválida",
                    f"La dirección IP '{m_ip}' no es válida.",
                )
                return
            if not d_info:
                QMessageBox.warning(
                    self,
                    "Driver requerido",
                    "Seleccioná un driver válido en config.json.",
                )
                return

            selected.append(
                {
                    "name": m_name,
                    "ip": m_ip,
                    "driver_name": str(d_info.get("driver_name", "")).strip(),
                    "inf_path": str(d_info.get("inf_path", "")).strip(),
                }
            )

        if not selected:
            QMessageBox.warning(
                self,
                "Sin selección",
                "Seleccioná al menos una impresora de la lista o habilitá una IP manual.",
            )
            return

        self._selected_printers = selected
        self.accept()

    def get_selected_printers(self) -> list[dict[str, str]]:
        return list(self._selected_printers)


class M365SanitizerDialog(QDialog):
    """Diálogo selector para ejecutar acciones no interactivas de Suite-M365-Saneamiento."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Suite-M365-Saneamiento")
        self.setMinimumWidth(520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setModal(True)

        self._selected_options: dict[str, Any] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        header = QLabel("Saneamiento de Microsoft 365 y Office")
        header.setObjectName("SectionTitle")
        root.addWidget(header)

        subtitle = QLabel(
            "Seleccioná la operación a ejecutar. Se prioriza el modo simulación (-WhatIf) "
            "para validar el impacto antes de aplicar cambios reales."
        )
        subtitle.setObjectName("MutedText")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        card = QFrame()
        card.setObjectName("SectionCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)

        self.rb_diagnostics = QRadioButton(
            "1. Diagnóstico de Office y Licencias (solo lectura)"
        )
        self.rb_diagnostics.setChecked(True)
        card_layout.addWidget(self.rb_diagnostics)

        self.rb_identity = QRadioButton(
            "2. Limpiar caché de identidad (WAM, OneAuth, IdentityCache, cmdkey)"
        )
        card_layout.addWidget(self.rb_identity)

        self.rb_licenses = QRadioButton(
            "3. Restablecer licencias y sppc.dll (Ohook / vNext)"
        )
        card_layout.addWidget(self.rb_licenses)

        lic_mode_row = QHBoxLayout()
        lic_mode_row.setContentsMargins(24, 0, 0, 0)
        lic_mode_row.setSpacing(8)
        self.lic_mode_label = QLabel("Modo de licencias:")
        self.lic_mode_label.setObjectName("MutedText")
        self.lic_mode_combo = QComboBox()
        self.lic_mode_combo.addItem("Selectivo (conserva Project / Visio)", "Selectivo")
        self.lic_mode_combo.addItem("Total (elimina todas las claves)", "Total")
        lic_mode_row.addWidget(self.lic_mode_label)
        lic_mode_row.addWidget(self.lic_mode_combo, 1)
        card_layout.addLayout(lic_mode_row)

        self.rb_uninstall = QRadioButton(
            "4. Desinstalación total y limpieza profunda de Office"
        )
        card_layout.addWidget(self.rb_uninstall)

        root.addWidget(card)

        self.whatif_chk = QCheckBox(
            "Ejecutar en modo simulación (-WhatIf, no realiza cambios reales)"
        )
        self.whatif_chk.setChecked(True)
        root.addWidget(self.whatif_chk)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.run_btn = QPushButton("Ejecutar")
        self.run_btn.setObjectName("PrimaryButton")
        self.run_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(self.run_btn)
        root.addLayout(btn_row)

        for rb in (
            self.rb_diagnostics,
            self.rb_identity,
            self.rb_licenses,
            self.rb_uninstall,
        ):
            rb.toggled.connect(self._update_controls_state)
        self._update_controls_state()

    def _update_controls_state(self) -> None:
        is_diag = self.rb_diagnostics.isChecked()
        is_lic = self.rb_licenses.isChecked()
        self.lic_mode_label.setEnabled(is_lic)
        self.lic_mode_combo.setEnabled(is_lic)
        self.whatif_chk.setEnabled(not is_diag)

    def _on_accept(self) -> None:
        what_if = self.whatif_chk.isChecked()
        if self.rb_diagnostics.isChecked():
            action = "diagnostics"
            label = "Diagnóstico M365 (solo lectura)"
            what_if = True
        elif self.rb_identity.isChecked():
            action = "identity"
            label = "Limpieza de Caché de Identidad M365"
        elif self.rb_licenses.isChecked():
            action = "licenses"
            label = f"Restablecer Licencias Office ({self.lic_mode_combo.currentData()})"
        else:
            action = "uninstall"
            label = "Desinstalación y Limpieza Profunda Office"

        if action != "diagnostics" and not what_if:
            warning_text = (
                f"Vas a ejecutar '{label}' en MODO REAL.\n\n"
                "Esta operación modificará cachés, credenciales o productos de Microsoft Office en el equipo.\n"
                "¿Confirmás que deseás continuar?"
            )
            if action == "uninstall":
                warning_text = (
                    "ADVERTENCIA CRÍTICA: Vas a desinstalar TODOS los productos de Office/Project/Visio "
                    "detectados y ejecutar limpieza profunda en MODO REAL.\n\n"
                    "¿Confirmás continuar?"
                )
            reply = QMessageBox.question(
                self,
                "Confirmar ejecución real",
                warning_text,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._selected_options = {
            "action": action,
            "label": label,
            "license_mode": str(self.lic_mode_combo.currentData() or "Selectivo"),
            "what_if": what_if,
        }
        self.accept()

    def get_options(self) -> dict[str, Any]:
        """Devuelve la acción y parámetros seleccionados por el operador."""
        return dict(self._selected_options)


class CreateLocalUserDialog(QDialog):
    """Diálogo modal para crear una cuenta de usuario local en Windows."""

    _FORBIDDEN_CHARS = ('"', "'", "\\", "/", ":", ";", "|", "=", ",", "+", "*", "?", "<", ">")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Crear Usuario Local (Windows)")
        self.setMinimumWidth(480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setModal(True)

        self._user_data: dict[str, Any] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        header = QLabel("Nueva cuenta local de Windows")
        header.setObjectName("PageHeader")
        root.addWidget(header)

        card = QFrame()
        card.setObjectName("ActionRow")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Ej: Soporte")

        pwd_row = QHBoxLayout()
        pwd_row.setSpacing(6)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Ingresá una contraseña")

        self.toggle_pwd_btn = QPushButton("", self)
        self.toggle_pwd_btn.setObjectName("EyeButton")
        self.toggle_pwd_btn.setCheckable(True)
        self.toggle_pwd_btn.setFixedSize(32, 30)
        self.toggle_pwd_btn.setIcon(_create_eye_icon(False))
        self.toggle_pwd_btn.setIconSize(QSize(18, 18))
        self.toggle_pwd_btn.setToolTip("Mostrar contraseña")
        self.toggle_pwd_btn.toggled.connect(self._on_toggle_password)

        pwd_row.addWidget(self.password_edit)
        pwd_row.addWidget(self.toggle_pwd_btn)

        self.fullname_edit = QLineEdit()
        self.fullname_edit.setPlaceholderText("Opcional")

        form.addRow("Usuario:", self.username_edit)
        form.addRow("Contraseña:", pwd_row)
        form.addRow("Nombre completo:", self.fullname_edit)
        card_layout.addLayout(form)

        self.admin_chk = QCheckBox("Agregar al grupo Administradores (SID S-1-5-32-544)")
        card_layout.addWidget(self.admin_chk)

        root.addWidget(card)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.create_btn = QPushButton("Crear Usuario")
        self.create_btn.setObjectName("PrimaryButton")
        self.create_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(self.create_btn)
        root.addLayout(btn_row)

    def _on_toggle_password(self, checked: bool) -> None:
        self.password_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self.toggle_pwd_btn.setIcon(_create_eye_icon(checked))
        self.toggle_pwd_btn.setToolTip("Ocultar contraseña" if checked else "Mostrar contraseña")

    def _on_accept(self) -> None:
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        full_name = self.fullname_edit.text().strip()

        if not username:
            QMessageBox.warning(self, "Usuario requerido", "Ingresá un nombre de usuario.")
            return
        if any(ch in username for ch in self._FORBIDDEN_CHARS):
            QMessageBox.warning(
                self,
                "Nombre inválido",
                "El nombre de usuario contiene caracteres no permitidos en Windows.",
            )
            return
        if not password:
            QMessageBox.warning(self, "Contraseña requerida", "Ingresá una contraseña.")
            return

        self._user_data = {
            "username": username,
            "password": password,
            "full_name": full_name,
            "add_to_admins": self.admin_chk.isChecked(),
        }
        self.accept()

    def get_user_data(self) -> dict[str, Any]:
        """Devuelve los datos validados del usuario a crear."""
        return dict(self._user_data)


class HardwareDiagnosticsDialog(QDialog):
    """Diálogo modal de diagnóstico de hardware, S.M.A.R.T., batería y estabilidad BSOD."""

    def __init__(
        self,
        log_callback: Callable[[str], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Diagnóstico de Hardware y Estabilidad")
        self.setMinimumSize(680, 560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setModal(True)

        self._log_callback = log_callback
        self._worker: TaskWorker | None = None
        self._diag_results: dict[str, str] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(10)

        header = QLabel("Diagnóstico de Hardware y Estabilidad")
        header.setObjectName("PageHeader")
        root.addWidget(header)

        placeholder = "Sin datos. Hacé clic en 'Ejecutar Diagnóstico' para consultar."

        self.smart_output = self._add_section(root, "DISCOS FÍSICOS (S.M.A.R.T. — SIN USB)", placeholder, 95)
        self.partitions_output = self._add_section(root, "PARTICIONES FIJAS (DRIVETYPE = 3)", placeholder, 85)
        self.battery_output = self._add_section(root, "SALUD DE BATERÍA (%TEMP%\\battery.html)", placeholder, 65)
        self.stability_output = self._add_section(root, "ESTABILIDAD, RAM, UPTIME Y BSOD (30 DÍAS)", placeholder, 105)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.run_btn = QPushButton("Ejecutar Diagnóstico")
        self.run_btn.setObjectName("PrimaryButton")
        self.run_btn.clicked.connect(self._start_diagnostics)
        btn_row.addWidget(self.run_btn)

        self.open_battery_btn = QPushButton("Abrir Batería HTML")
        self.open_battery_btn.setEnabled(get_battery_report_path().is_file())
        self.open_battery_btn.clicked.connect(self._open_battery_html)
        btn_row.addWidget(self.open_battery_btn)

        self.export_btn = QPushButton("Exportar (.txt)")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export_report)
        btn_row.addWidget(self.export_btn)

        btn_row.addStretch(1)

        self.close_btn = QPushButton("Cerrar")
        self.close_btn.clicked.connect(self.close)
        btn_row.addWidget(self.close_btn)
        root.addLayout(btn_row)

    @staticmethod
    def _add_section(
        parent_layout: QVBoxLayout,
        title: str,
        initial_text: str,
        min_height: int,
    ) -> QPlainTextEdit:
        lbl = QLabel(title)
        lbl.setObjectName("SubgroupTitle")
        parent_layout.addWidget(lbl)

        box = QPlainTextEdit()
        box.setObjectName("LogOutput")
        box.setReadOnly(True)
        box.setMinimumHeight(min_height)
        box.setMaximumHeight(min_height + 25)
        box.setPlainText(initial_text)
        parent_layout.addWidget(box)
        return box

    def _emit_log(self, line: str) -> None:
        if callable(self._log_callback):
            self._log_callback(line)

    def _start_diagnostics(self) -> None:
        if self._worker and self._worker.isRunning():
            return

        self.run_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.open_battery_btn.setEnabled(False)
        self.run_btn.setText("Consultando...")

        captured: dict[str, str] = {}

        def _task(log: Callable[[str], None]) -> str:
            all_ok, results = run_full_diagnostics(log_cb=log)
            captured.update(results)
            return "Diagnóstico de hardware completado." if all_ok else "Diagnóstico completado con advertencias."

        worker = TaskWorker(_task)
        worker.log_message.connect(self._emit_log)
        worker.finished_success.connect(lambda msg: self._on_diag_finished(captured, msg))
        worker.failed.connect(self._on_diag_failed)
        self._worker = worker
        worker.start()

    def _on_diag_finished(self, results: dict[str, str], _msg: str) -> None:
        self._diag_results = dict(results)
        self.smart_output.setPlainText(results.get("smart", "Sin datos."))
        self.partitions_output.setPlainText(results.get("partitions", "Sin datos."))
        self.battery_output.setPlainText(results.get("battery", "Sin datos."))
        self.stability_output.setPlainText(results.get("stability", "Sin datos."))

        self.run_btn.setText("Ejecutar Diagnóstico")
        self.run_btn.setEnabled(True)
        self.export_btn.setEnabled(bool(self._diag_results))
        self.open_battery_btn.setEnabled(get_battery_report_path().is_file())

    def _on_diag_failed(self, err: str) -> None:
        self.run_btn.setText("Ejecutar Diagnóstico")
        self.run_btn.setEnabled(True)
        self.open_battery_btn.setEnabled(get_battery_report_path().is_file())
        QMessageBox.warning(self, "Error en diagnóstico", err)

    def _open_battery_html(self) -> None:
        report_path = get_battery_report_path()
        if not report_path.is_file():
            QMessageBox.information(
                self,
                "Reporte no disponible",
                f"No se encontró el archivo {report_path}.",
            )
            return
        if os.name == "nt":
            os.startfile(str(report_path))

    def _export_report(self) -> None:
        if not self._diag_results:
            return
        default_name = f"diagnostico_{os.environ.get('COMPUTERNAME', 'equipo')}.txt"
        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Reporte de Diagnóstico",
            default_name,
            "Archivos de texto (*.txt)",
        )
        if not target_path:
            return
        ok, msg = export_diagnostic_report(target_path, self._diag_results)
        if ok:
            self._emit_log(f"[OK] {msg}")
            QMessageBox.information(self, "Reporte exportado", msg)
        else:
            self._emit_log(f"[ERROR] {msg}")
            QMessageBox.warning(self, "Error al exportar", msg)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.wait(1500)
        super().closeEvent(event)


class InventoryDialog(QDialog):
    """Diálogo modal de relevamiento de inventario de hardware y datos administrativos."""

    def __init__(
        self,
        config: AppConfig,
        log_callback: Callable[[str], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self._log_callback = log_callback
        self._worker: TaskWorker | None = None
        self._hw_snapshot: dict[str, str] | None = None

        self.setWindowTitle("Inventario de Equipo — Eidico")
        self.setMinimumSize(700, 620)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setModal(True)

        inv_cfg = config.get_inventory_config()
        dest_preview = str(Path(inv_cfg["network_dir"]) / inv_cfg["output_filename"])

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(10)

        header = QLabel("Inventario de Equipo y Usuario")
        header.setObjectName("PageHeader")
        root.addWidget(header)

        form_card = QFrame()
        form_card.setObjectName("ActionRow")
        form_layout = QFormLayout(form_card)
        form_layout.setContentsMargins(14, 12, 14, 12)
        form_layout.setSpacing(8)

        self.ad_edit = QLineEdit()
        self.ad_edit.setPlaceholderText("Ej: jperez")

        self.correo_edit = QLineEdit()
        self.correo_edit.setPlaceholderText("usuario@eidico.com.ar")

        self.puesto_edit = QLineEdit()

        self.antiguedad_edit = QDateEdit()
        self.antiguedad_edit.setCalendarPopup(True)
        self.antiguedad_edit.setDisplayFormat("dd/MM/yyyy")
        self.antiguedad_edit.setDate(QDate.currentDate())

        self.area_edit = QLineEdit()

        self.propiedad_combo = QComboBox()
        self.propiedad_combo.addItems(inv_cfg["property_options"])
        self.propiedad_combo.currentTextChanged.connect(self._on_property_changed)

        self.barrio_edit = QLineEdit()
        self.barrio_edit.setPlaceholderText("Nombre del Barrio...")
        self.barrio_edit.setVisible(False)

        self.compra_edit = QDateEdit()
        self.compra_edit.setCalendarPopup(True)
        self.compra_edit.setDisplayFormat("dd/MM/yyyy")
        self.compra_edit.setDate(QDate.currentDate())

        self.obs_edit = QPlainTextEdit()
        self.obs_edit.setFixedHeight(56)
        self.obs_edit.setPlaceholderText("Observaciones opcionales...")

        form_layout.addRow("Usuario AD:", self.ad_edit)
        form_layout.addRow("Correo electrónico:", self.correo_edit)
        form_layout.addRow("Puesto:", self.puesto_edit)
        form_layout.addRow("Antigüedad:", self.antiguedad_edit)
        form_layout.addRow("Departamento / Área:", self.area_edit)
        form_layout.addRow("Propiedad de:", self.propiedad_combo)
        form_layout.addRow("Barrio:", self.barrio_edit)
        form_layout.addRow("Fecha de compra:", self.compra_edit)
        form_layout.addRow("Observaciones:", self.obs_edit)
        root.addWidget(form_card)

        hw_lbl = QLabel("HARDWARE RELEVADO (WMI / POWERSHELL)")
        hw_lbl.setObjectName("SubgroupTitle")
        root.addWidget(hw_lbl)

        self.hw_preview = QPlainTextEdit()
        self.hw_preview.setObjectName("LogOutput")
        self.hw_preview.setReadOnly(True)
        self.hw_preview.setFixedHeight(105)
        self.hw_preview.setPlainText(
            "Sin relevar. Hacé clic en 'Relevar Hardware' o directamente en 'Guardar en Red'."
        )
        root.addWidget(self.hw_preview)

        dest_lbl = QLabel(f"Destino configurado: {dest_preview}")
        dest_lbl.setObjectName("LastLogEvent")
        root.addWidget(dest_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.refresh_hw_btn = QPushButton("Relevar Hardware")
        self.refresh_hw_btn.clicked.connect(self._start_hardware_scan)
        btn_row.addWidget(self.refresh_hw_btn)

        self.copy_btn = QPushButton("Copiar")
        self.copy_btn.clicked.connect(self._copy_record)
        btn_row.addWidget(self.copy_btn)

        self.export_btn = QPushButton("Exportar (.txt)")
        self.export_btn.clicked.connect(self._export_local)
        btn_row.addWidget(self.export_btn)

        btn_row.addStretch(1)

        self.close_btn = QPushButton("Cerrar")
        self.close_btn.clicked.connect(self.close)
        btn_row.addWidget(self.close_btn)

        self.save_btn = QPushButton("Guardar en Red")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self._start_save_network)
        btn_row.addWidget(self.save_btn)

        root.addLayout(btn_row)
        self._on_property_changed(self.propiedad_combo.currentText())

    def _emit_log(self, line: str) -> None:
        if callable(self._log_callback):
            self._log_callback(line)

    def _on_property_changed(self, value: str) -> None:
        is_barrio = value == "Barrio"
        self.barrio_edit.setVisible(is_barrio)
        if not is_barrio:
            self.barrio_edit.clear()

    def _set_busy(self, busy: bool, action_text: str = "") -> None:
        for btn in (self.refresh_hw_btn, self.copy_btn, self.export_btn, self.save_btn):
            btn.setEnabled(not busy)
        if busy and action_text:
            self.save_btn.setText(action_text)
        else:
            self.save_btn.setText("Guardar en Red")

    def _collect_admin_data(self, require_ad: bool = True) -> dict[str, str] | None:
        ad_user = self.ad_edit.text().strip()
        prop_sel = self.propiedad_combo.currentText().strip()
        barrio = self.barrio_edit.text().strip()

        errors: list[str] = []
        if require_ad and not ad_user:
            errors.append("Ingresá el Usuario AD.")
        if prop_sel == "Barrio" and not barrio:
            errors.append("Especificá el nombre del Barrio.")

        if errors:
            QMessageBox.warning(self, "Datos incompletos", "\n".join(errors))
            return None

        propiedad_final = f"Barrio ({barrio})" if prop_sel == "Barrio" else prop_sel
        return {
            "ad": ad_user,
            "correo": self.correo_edit.text().strip(),
            "puesto": self.puesto_edit.text().strip(),
            "antiguedad": self.antiguedad_edit.date().toString("dd/MM/yyyy"),
            "area": self.area_edit.text().strip(),
            "propiedad": propiedad_final,
            "compra": self.compra_edit.date().toString("dd/MM/yyyy"),
            "obs": self.obs_edit.toPlainText(),
        }

    def _start_hardware_scan(self) -> None:
        if self._worker and self._worker.isRunning():
            return

        self._set_busy(True, "Relevando...")
        captured: dict[str, str] = {}

        def _task(log: Callable[[str], None]) -> str:
            hw = collect_hardware_info(log=log)
            captured.update(hw)
            return "Hardware relevado correctamente."

        worker = TaskWorker(_task)
        worker.log_message.connect(self._emit_log)
        worker.finished_success.connect(lambda _m: self._on_hw_scan_done(captured))
        worker.failed.connect(self._on_worker_error)
        self._worker = worker
        worker.start()

    def _on_hw_scan_done(self, hw: dict[str, str]) -> None:
        self._hw_snapshot = dict(hw)
        self.hw_preview.setPlainText(format_hardware_preview(hw))
        self._set_busy(False)

    def _copy_record(self) -> None:
        admin_data = self._collect_admin_data(require_ad=True)
        if admin_data is None:
            return
        if self._hw_snapshot is None:
            QMessageBox.information(
                self,
                "Hardware pendiente",
                "Hacé clic primero en 'Relevar Hardware' para incluir los datos del equipo.",
            )
            return

        record = format_inventory_record(admin_data, self._hw_snapshot)
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(record)
        self._emit_log("[OK] Registro de inventario copiado al portapapeles.")
        QMessageBox.information(
            self,
            "Copiado",
            "Registro de inventario copiado al portapapeles.",
        )

    def _export_local(self) -> None:
        admin_data = self._collect_admin_data(require_ad=True)
        if admin_data is None:
            return
        if self._hw_snapshot is None:
            QMessageBox.information(
                self,
                "Hardware pendiente",
                "Hacé clic primero en 'Relevar Hardware' para exportar el registro completo.",
            )
            return

        hostname = self._hw_snapshot.get("hostname", "equipo")
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Registro de Inventario",
            f"Inventario_{hostname}.txt",
            "Archivos de texto (*.txt)",
        )
        if not target:
            return
        try:
            msg = export_inventory_record_local(Path(target), admin_data, self._hw_snapshot)
            self._emit_log(f"[OK] {msg}")
            QMessageBox.information(self, "Exportado", msg)
        except OSError as exc:
            self._emit_log(f"[ERROR] No se pudo exportar inventario: {exc}")
            QMessageBox.warning(self, "Error al exportar", str(exc))

    def _start_save_network(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        admin_data = self._collect_admin_data(require_ad=True)
        if admin_data is None:
            return

        self._set_busy(True, "Guardando...")
        captured_hw: dict[str, str] = {}

        def _task(log: Callable[[str], None]) -> str:
            hw = self._hw_snapshot if self._hw_snapshot is not None else collect_hardware_info(log=log)
            captured_hw.update(hw)
            return save_inventory_record(self.config, admin_data, hw=hw, log=log)

        worker = TaskWorker(_task)
        worker.log_message.connect(self._emit_log)
        worker.finished_success.connect(lambda msg: self._on_save_done(captured_hw, msg))
        worker.failed.connect(self._on_worker_error)
        self._worker = worker
        worker.start()

    def _on_save_done(self, hw: dict[str, str], msg: str) -> None:
        if hw:
            self._hw_snapshot = dict(hw)
            self.hw_preview.setPlainText(format_hardware_preview(hw))
        self._set_busy(False)
        QMessageBox.information(self, "Inventario guardado", msg)

        self.correo_edit.clear()
        self.puesto_edit.clear()
        self.area_edit.clear()
        self.barrio_edit.clear()
        self.obs_edit.clear()
        self.propiedad_combo.setCurrentIndex(0)
        self.antiguedad_edit.setDate(QDate.currentDate())
        self.compra_edit.setDate(QDate.currentDate())

    def _on_worker_error(self, err: str) -> None:
        self._set_busy(False)
        QMessageBox.warning(self, "Error en inventario", err)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.wait(1500)
        super().closeEvent(event)
