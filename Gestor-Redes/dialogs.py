"""Diálogos modales para configuración IPv4/DHCP, DNS y detalles de adaptadores."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

import net_tasks
from net_tasks import DNS_PRESETS, NetworkAdapter


class IPConfigDialog(QDialog):
    """Diálogo modal para configurar dirección IPv4 (DHCP o estática) en un adaptador."""

    def __init__(self, adapter: NetworkAdapter, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.adapter = adapter
        self._result_config: dict[str, Any] = {}

        self.setWindowTitle(f"Configurar IPv4 — {adapter.name}")
        self.setMinimumWidth(460)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header_card = QFrame(self)
        header_card.setObjectName("ActionRow")
        h_layout = QVBoxLayout(header_card)
        h_layout.setContentsMargins(12, 8, 12, 8)
        h_layout.setSpacing(2)

        name_lbl = QLabel(adapter.name, header_card)
        name_lbl.setObjectName("RowTitle")
        desc_lbl = QLabel(adapter.description or "Adaptador de red", header_card)
        desc_lbl.setObjectName("RowSubtitle")
        h_layout.addWidget(name_lbl)
        h_layout.addWidget(desc_lbl)
        root.addWidget(header_card)

        self.dhcp_radio = QRadioButton("Obtener dirección IP automáticamente (DHCP)", self)
        self.static_radio = QRadioButton("Usar dirección IPv4 estática", self)
        self.dhcp_radio.toggled.connect(self._sync_mode)
        root.addWidget(self.dhcp_radio)
        root.addWidget(self.static_radio)

        self.dhcp_reset_dns_cb = QCheckBox("Restablecer también servidores DNS a automático (DHCP)", self)
        self.dhcp_reset_dns_cb.setChecked(True)
        root.addWidget(self.dhcp_reset_dns_cb)

        self.static_card = QFrame(self)
        self.static_card.setObjectName("ActionRow")
        form = QFormLayout(self.static_card)
        form.setContentsMargins(12, 10, 12, 10)
        form.setSpacing(8)

        self.ip_edit = QLineEdit(self.static_card)
        self.ip_edit.setPlaceholderText("Ej: 192.168.1.50")
        if adapter.ipv4_address:
            self.ip_edit.setText(adapter.ipv4_address)

        self.mask_edit = QLineEdit(self.static_card)
        self.mask_edit.setPlaceholderText("Ej: 255.255.255.0")
        self.mask_edit.setText(adapter.subnet_mask or "255.255.255.0")

        self.gateway_edit = QLineEdit(self.static_card)
        self.gateway_edit.setPlaceholderText("Opcional (ej: 192.168.1.1)")
        if adapter.gateway:
            self.gateway_edit.setText(adapter.gateway)

        self.apply_dns_cb = QCheckBox("Configurar DNS junto con la IP estática", self.static_card)
        self.apply_dns_cb.setChecked(bool(adapter.dns_servers) and not adapter.dns_dhcp)
        self.apply_dns_cb.toggled.connect(self._sync_dns_fields)

        self.dns1_edit = QLineEdit(self.static_card)
        self.dns1_edit.setPlaceholderText("Ej: 1.1.1.1")
        if len(adapter.dns_servers) >= 1:
            self.dns1_edit.setText(adapter.dns_servers[0])

        self.dns2_edit = QLineEdit(self.static_card)
        self.dns2_edit.setPlaceholderText("Opcional (ej: 1.0.0.1)")
        if len(adapter.dns_servers) >= 2:
            self.dns2_edit.setText(adapter.dns_servers[1])

        form.addRow("Dirección IPv4:", self.ip_edit)
        form.addRow("Máscara de subred:", self.mask_edit)
        form.addRow("Puerta de enlace:", self.gateway_edit)
        form.addRow("", self.apply_dns_cb)
        form.addRow("DNS Primario:", self.dns1_edit)
        form.addRow("DNS Secundario:", self.dns2_edit)
        root.addWidget(self.static_card)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancelar", self)
        cancel_btn.clicked.connect(self.reject)
        apply_btn = QPushButton("Aplicar", self)
        apply_btn.setObjectName("PrimaryButton")
        apply_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(apply_btn)
        root.addLayout(btn_row)

        if adapter.dhcp_enabled:
            self.dhcp_radio.setChecked(True)
        else:
            self.static_radio.setChecked(True)
        self._sync_mode()

    def _sync_mode(self) -> None:
        is_dhcp = self.dhcp_radio.isChecked()
        self.dhcp_reset_dns_cb.setVisible(is_dhcp)
        self.static_card.setEnabled(not is_dhcp)
        self._sync_dns_fields()
        self.adjustSize()

    def _sync_dns_fields(self) -> None:
        dns_enabled = (not self.dhcp_radio.isChecked()) and self.apply_dns_cb.isChecked()
        self.dns1_edit.setEnabled(dns_enabled)
        self.dns2_edit.setEnabled(dns_enabled)

    def _on_accept(self) -> None:
        if self.dhcp_radio.isChecked():
            self._result_config = {
                "mode": "dhcp",
                "also_reset_dns": self.dhcp_reset_dns_cb.isChecked(),
            }
            self.accept()
            return

        try:
            ip_val = net_tasks.validate_ipv4(self.ip_edit.text(), "Dirección IPv4")
            mask_val, _ = net_tasks.validate_subnet_mask(self.mask_edit.text())
            gw_val = net_tasks.validate_ipv4(
                self.gateway_edit.text(), "Puerta de enlace", allow_empty=True
            )
            apply_dns = self.apply_dns_cb.isChecked()
            dns1 = ""
            dns2 = ""
            if apply_dns:
                dns1 = net_tasks.validate_ipv4(
                    self.dns1_edit.text(), "DNS Primario", allow_empty=True
                )
                dns2 = net_tasks.validate_ipv4(
                    self.dns2_edit.text(), "DNS Secundario", allow_empty=True
                )
                if dns2 and not dns1:
                    raise ValueError("Completá el DNS Primario antes de indicar un DNS Secundario.")
        except ValueError as exc:
            QMessageBox.warning(self, "Datos inválidos", str(exc))
            return

        self._result_config = {
            "mode": "static",
            "ip_address": ip_val,
            "subnet_mask": mask_val,
            "gateway": gw_val,
            "apply_dns": apply_dns,
            "dns_primary": dns1,
            "dns_secondary": dns2,
        }
        self.accept()

    def get_config(self) -> dict[str, Any]:
        return dict(self._result_config)


class DNSConfigDialog(QDialog):
    """Diálogo modal para configurar servidores DNS (automático, presets o personalizado)."""

    def __init__(self, adapter: NetworkAdapter, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.adapter = adapter
        self._result_config: dict[str, Any] = {}

        self.setWindowTitle(f"Configurar DNS — {adapter.name}")
        self.setMinimumWidth(440)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header_card = QFrame(self)
        header_card.setObjectName("ActionRow")
        h_layout = QVBoxLayout(header_card)
        h_layout.setContentsMargins(12, 8, 12, 8)
        h_layout.setSpacing(2)

        name_lbl = QLabel(adapter.name, header_card)
        name_lbl.setObjectName("RowTitle")
        current_dns = ", ".join(adapter.dns_servers) if adapter.dns_servers else "Automático (DHCP)"
        cur_lbl = QLabel(f"DNS actual: {current_dns}", header_card)
        cur_lbl.setObjectName("RowMeta")
        h_layout.addWidget(name_lbl)
        h_layout.addWidget(cur_lbl)
        root.addWidget(header_card)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Perfil rápido:", self))
        self.preset_combo = QComboBox(self)
        self.preset_combo.addItem("Personalizado", userData=None)
        for label, servers in DNS_PRESETS.items():
            self.preset_combo.addItem(label, userData=servers)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        preset_row.addWidget(self.preset_combo, stretch=1)
        root.addLayout(preset_row)

        self.dhcp_radio = QRadioButton("Obtener servidores DNS automáticamente (DHCP)", self)
        self.static_radio = QRadioButton("Usar las siguientes direcciones de servidor DNS", self)
        self.dhcp_radio.toggled.connect(self._sync_mode)
        root.addWidget(self.dhcp_radio)
        root.addWidget(self.static_radio)

        self.dns_card = QFrame(self)
        self.dns_card.setObjectName("ActionRow")
        form = QFormLayout(self.dns_card)
        form.setContentsMargins(12, 10, 12, 10)
        form.setSpacing(8)

        self.dns1_edit = QLineEdit(self.dns_card)
        self.dns1_edit.setPlaceholderText("Ej: 1.1.1.1")
        if len(adapter.dns_servers) >= 1:
            self.dns1_edit.setText(adapter.dns_servers[0])

        self.dns2_edit = QLineEdit(self.dns_card)
        self.dns2_edit.setPlaceholderText("Opcional (ej: 1.0.0.1)")
        if len(adapter.dns_servers) >= 2:
            self.dns2_edit.setText(adapter.dns_servers[1])

        form.addRow("DNS Primario:", self.dns1_edit)
        form.addRow("DNS Secundario:", self.dns2_edit)
        root.addWidget(self.dns_card)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancelar", self)
        cancel_btn.clicked.connect(self.reject)
        apply_btn = QPushButton("Aplicar DNS", self)
        apply_btn.setObjectName("PrimaryButton")
        apply_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(apply_btn)
        root.addLayout(btn_row)

        if adapter.dns_dhcp:
            self.dhcp_radio.setChecked(True)
        else:
            self.static_radio.setChecked(True)
        self._sync_mode()

    def _on_preset_selected(self, _index: int) -> None:
        servers = self.preset_combo.currentData()
        if servers is None:
            return
        if not servers:
            self.dhcp_radio.setChecked(True)
            return
        self.static_radio.setChecked(True)
        self.dns1_edit.setText(servers[0] if len(servers) >= 1 else "")
        self.dns2_edit.setText(servers[1] if len(servers) >= 2 else "")

    def _sync_mode(self) -> None:
        self.dns_card.setEnabled(self.static_radio.isChecked())

    def _on_accept(self) -> None:
        if self.dhcp_radio.isChecked():
            self._result_config = {"use_dhcp": True, "dns_servers": []}
            self.accept()
            return

        try:
            dns1 = net_tasks.validate_ipv4(self.dns1_edit.text(), "DNS Primario")
            dns2 = net_tasks.validate_ipv4(
                self.dns2_edit.text(), "DNS Secundario", allow_empty=True
            )
        except ValueError as exc:
            QMessageBox.warning(self, "DNS inválido", str(exc))
            return

        servers = [dns1]
        if dns2 and dns2 != dns1:
            servers.append(dns2)

        self._result_config = {"use_dhcp": False, "dns_servers": servers}
        self.accept()

    def get_config(self) -> dict[str, Any]:
        return dict(self._result_config)


class AdapterDetailsDialog(QDialog):
    """Muestra toda la información detallada de un adaptador con opción de copiar."""

    def __init__(self, adapter: NetworkAdapter, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.adapter = adapter
        self.setWindowTitle(f"Detalles del Adaptador — {adapter.name}")
        self.setMinimumWidth(480)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        card = QFrame(self)
        card.setObjectName("ActionRow")
        form = QFormLayout(card)
        form.setContentsMargins(14, 12, 14, 12)
        form.setSpacing(7)

        ip_display = (
            f"{adapter.ipv4_address} /{adapter.prefix_length}"
            if adapter.ipv4_address and adapter.prefix_length is not None
            else (adapter.ipv4_address or "Sin asignar")
        )
        dns_mode = "Automático (DHCP)" if adapter.dns_dhcp else "Estático"
        dns_vals = ", ".join(adapter.dns_servers) if adapter.dns_servers else "Sin servidores DNS"

        rows = [
            ("Nombre:", adapter.name),
            ("Descripción:", adapter.description or "-"),
            ("Estado:", f"{adapter.status_label} ({adapter.status})"),
            ("Índice de interfaz:", str(adapter.if_index)),
            ("Dirección MAC:", adapter.mac_address or "-"),
            ("Velocidad de enlace:", adapter.link_speed or "-"),
            ("Modo IPv4:", "DHCP (Automático)" if adapter.dhcp_enabled else "Estático"),
            ("Dirección IPv4:", ip_display),
            ("Máscara de subred:", adapter.subnet_mask or "-"),
            ("Puerta de enlace:", adapter.gateway or "-"),
            ("Modo DNS:", dns_mode),
            ("Servidores DNS:", dns_vals),
        ]

        self._plain_summary = "\n".join(f"{k} {v}" for k, v in rows)

        for label, value in rows:
            val_lbl = QLabel(value, card)
            val_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            val_lbl.setWordWrap(True)
            form.addRow(label, val_lbl)

        root.addWidget(card)

        btn_row = QHBoxLayout()
        copy_btn = QPushButton("Copiar resumen", self)
        copy_btn.clicked.connect(self._copy_summary)
        close_btn = QPushButton("Cerrar", self)
        close_btn.setObjectName("PrimaryButton")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(copy_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    def _copy_summary(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._plain_summary)


class DiagnosticResultDialog(QDialog):
    """Visor modal monoespaciado para resultados extensos de diagnóstico."""

    def __init__(self, title: str, content: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(700, 460)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        self.viewer = QPlainTextEdit(self)
        self.viewer.setObjectName("DiagnosticOutput")
        self.viewer.setReadOnly(True)
        self.viewer.setPlainText(content)
        root.addWidget(self.viewer, stretch=1)

        btn_row = QHBoxLayout()
        copy_btn = QPushButton("Copiar al Portapapeles", self)
        copy_btn.clicked.connect(self._copy_text)
        close_btn = QPushButton("Cerrar", self)
        close_btn.setObjectName("PrimaryButton")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(copy_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    def _copy_text(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.viewer.toPlainText())
