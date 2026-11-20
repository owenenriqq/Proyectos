"""Diálogos modales seguros para credenciales (cifradas/manuales) y progreso."""

from __future__ import annotations

import ipaddress
import os
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import QPointF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
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
