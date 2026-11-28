"""Vista integrada de Gestor de Redes para EzSetup (Adaptadores, Renovación y Diagnóstico)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import QPointF, QSize, Qt, QThread
from PyQt6.QtGui import QAction, QBrush, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.modules.network import net_tasks
from src.modules.network.net_tasks import NetworkAdapter
from src.modules.network.network_dialogs import (
    AdapterDetailsDialog,
    DNSConfigDialog,
    DiagnosticResultDialog,
    IPConfigDialog,
)
from src.modules.network.network_workers import (
    AdapterRefreshWorker,
    ConnectivityCheckWorker,
    DiagnosticWorker,
    NetworkTaskWorker,
)

ActionCallback = Callable[[], None]
ActionSpec = tuple[str, str, str, ActionCallback]


def _create_dots_icon() -> QIcon:
    """Dibuja un ícono vectorial de 3 puntos verticales centrado sobre 12x12."""
    pixmap = QPixmap(12, 12)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor("#E4E4E7")))
    for cy in (2.5, 6.0, 9.5):
        painter.drawEllipse(QPointF(6.0, cy), 1.15, 1.15)
    painter.end()
    return QIcon(pixmap)


class _NetworkActionRow(QFrame):
    """Fila horizontal compacta para adaptadores y utilidades de red."""

    def __init__(
        self,
        title: str,
        visible_actions: list[ActionSpec],
        overflow_actions: list[ActionSpec] | None = None,
        badge_text: str = "",
        badge_style: str = "RowBadgeOk",
        secondary_badge_text: str = "",
        secondary_badge_style: str = "RowBadgeMuted",
        meta_text: str = "",
        tooltip: str = "",
        badges_in_meta: bool = False,
        compact_buttons: bool = False,
        compact_vertical: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ActionRow")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        if tooltip:
            self.setToolTip(tooltip)

        outer = QHBoxLayout(self)
        if compact_vertical:
            outer.setContentsMargins(14, 6, 14, 6)
        else:
            outer.setContentsMargins(14, 9, 14, 9)
        outer.setSpacing(10)

        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(3)

        title_line = QHBoxLayout()
        title_line.setContentsMargins(0, 0, 0, 0)
        title_line.setSpacing(7)

        title_lbl = QLabel(title, self)
        title_lbl.setObjectName("RowTitle")
        title_lbl.setWordWrap(True)
        title_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        title_line.addWidget(title_lbl, stretch=1)

        badge_lbl = QLabel(badge_text, self)
        badge_lbl.setObjectName(badge_style)
        badge_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        badge_lbl.setVisible(bool(badge_text))

        sec_badge_lbl = QLabel(secondary_badge_text, self)
        sec_badge_lbl.setObjectName(secondary_badge_style)
        sec_badge_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sec_badge_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sec_badge_lbl.setVisible(bool(secondary_badge_text))

        left_col.addLayout(title_line)

        if badges_in_meta:
            meta_line = QHBoxLayout()
            meta_line.setContentsMargins(0, 0, 0, 0)
            meta_line.setSpacing(6)
            meta_line.addWidget(badge_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
            meta_line.addWidget(sec_badge_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
            if meta_text:
                meta_lbl = QLabel(meta_text, self)
                meta_lbl.setObjectName("RowMeta")
                meta_lbl.setWordWrap(True)
                meta_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                meta_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                meta_line.addWidget(meta_lbl, stretch=1)
            else:
                meta_line.addStretch(1)
            left_col.addLayout(meta_line)
        elif meta_text:
            meta_lbl = QLabel(meta_text, self)
            meta_lbl.setObjectName("RowMeta")
            meta_lbl.setWordWrap(True)
            meta_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            meta_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            left_col.addWidget(meta_lbl)

        outer.addLayout(left_col, stretch=1)

        if not badges_in_meta:
            if badge_text:
                outer.addWidget(badge_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
            if secondary_badge_text:
                outer.addWidget(sec_badge_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(5 if compact_buttons else 7)

        for text, obj_name, btn_tip, handler in visible_actions:
            btn = QPushButton(text, self)
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            if compact_buttons:
                btn.setProperty("compact", True)
            elif len(visible_actions) == 1:
                btn.setFixedWidth(140)
            if obj_name:
                btn.setObjectName(obj_name)
            if btn_tip:
                btn.setToolTip(btn_tip)
            btn.clicked.connect(lambda _checked=False, h=handler: h())
            btn_layout.addWidget(btn)

        if overflow_actions:
            more_btn = QPushButton("", self)
            more_btn.setObjectName("MoreButton")
            more_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            more_btn.setFixedSize(22, 22)
            more_btn.setIcon(_create_dots_icon())
            more_btn.setIconSize(QSize(12, 12))
            more_btn.setToolTip("Más acciones")
            menu = QMenu(more_btn)
            for text, _obj_name, act_tip, handler in overflow_actions:
                act = QAction(text, menu)
                if act_tip:
                    act.setToolTip(act_tip)
                act.triggered.connect(lambda _checked=False, h=handler: h())
                menu.addAction(act)
            more_btn.setMenu(menu)
            btn_layout.addWidget(more_btn)

        outer.addLayout(btn_layout)


class NetworkManagerView(QWidget):
    """Vista embebida de Gestor de Redes con pestañas de Adaptadores, Renovación y Diagnóstico."""

    def __init__(
        self,
        log_callback: Callable[[str], None],
        on_network_changed: Callable[[], None] | None = None,
        vpn_endpoints: dict[str, dict[str, Any]] | None = None,
        vpn_diagnostic_fn: Callable[[dict[str, Any], Callable[[str], None]], str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._log_callback = log_callback
        self._on_network_changed = on_network_changed
        self._vpn_endpoints = vpn_endpoints or {}
        self._vpn_diagnostic_fn = vpn_diagnostic_fn
        self._initialized = False

        self._active_workers: list[QThread] = []
        self._adapter_worker: AdapterRefreshWorker | None = None
        self._connectivity_worker: ConnectivityCheckWorker | None = None
        self._adapters: list[NetworkAdapter] = []
        self._search_query: str = ""
        self._adapter_rows: list[tuple[NetworkAdapter, str, _NetworkActionRow]] = []
        self._renewal_sections: list[tuple[QLabel, list[tuple[str, _NetworkActionRow]]]] = []
        self._diag_sections: list[tuple[QLabel, list[tuple[str, QWidget]]]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 8, 14, 10)
        root.setSpacing(6)

        # Barra superior compacta de estado y refresco con línea inferior sutil
        status_frame = QFrame(self)
        status_frame.setObjectName("NetworkStatusBar")
        status_bar = QHBoxLayout(status_frame)
        status_bar.setContentsMargins(2, 0, 2, 8)
        status_bar.setSpacing(8)

        self.net_status_badge = QLabel("● Sin verificar", status_frame)
        self.net_status_badge.setProperty("statusRole", "netBadge")
        self.net_status_badge.setProperty("statusState", "checking")
        self.net_status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.net_status_badge.setToolTip("Estado de conectividad externa (1.1.1.1 / 8.8.8.8) y DNS")
        status_bar.addWidget(self.net_status_badge)

        self.busy_badge = QLabel("", status_frame)
        self.busy_badge.setObjectName("RowBadgeMuted")
        self.busy_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.busy_badge.setVisible(False)
        status_bar.addWidget(self.busy_badge)

        status_bar.addStretch(1)

        self.refresh_btn = QPushButton("Actualizar Adaptadores", status_frame)
        self.refresh_btn.setToolTip("Recargar adaptadores de red y verificar conectividad externa")
        self.refresh_btn.clicked.connect(self.refresh_all_now)
        status_bar.addWidget(self.refresh_btn)

        root.addWidget(status_frame)

        self.pages = QStackedWidget(self)
        self.pages.addWidget(self._build_adapters_and_cache_tab())
        self.pages.addWidget(self._build_diagnostics_tab())
        self.set_subpage(0)
        root.addWidget(self.pages, stretch=1)

    def set_subpage(self, index: int) -> None:
        """Cambia la subvista activa (0: Adaptadores y Caché, 1: Diagnóstico de Red)."""
        if index < 0 or index >= self.pages.count():
            return
        self.pages.setCurrentIndex(index)
        self._on_tab_changed(index)

    def _on_tab_changed(self, index: int) -> None:
        """Ajusta QSizePolicy por subvista para que cada una scrollee solo hasta su último elemento."""
        for i in range(self.pages.count()):
            widget = self.pages.widget(i)
            if widget is None:
                continue
            if i == index:
                widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                if isinstance(widget, QScrollArea) and widget.widget() is not None:
                    content = widget.widget()
                    content.updateGeometry()
                    vp_w = max(widget.viewport().width(), content.minimumSizeHint().width())
                    if content.hasHeightForWidth():
                        target_h = content.heightForWidth(vp_w)
                        content.resize(vp_w, target_h)
            else:
                widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
            widget.updateGeometry()
        self.pages.updateGeometry()

    def _emit_log(self, line: str) -> None:
        if callable(self._log_callback):
            self._log_callback(line)

    def ensure_initialized(self) -> None:
        """Dispara la carga inicial de adaptadores y conectividad al entrar por primera vez."""
        if not self._initialized:
            self._initialized = True
            self.refresh_all_now()

    def _create_scroll_tab(self, align_top: bool = True) -> tuple[QScrollArea, QWidget, QVBoxLayout]:
        scroll = QScrollArea(self.pages)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        if align_top:
            scroll.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        container = QWidget(scroll)
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum if align_top else QSizePolicy.Policy.Preferred,
        )
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 10, 10, 16)
        layout.setSpacing(7)
        if align_top:
            layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(container)
        return scroll, container, layout

    # ------------------------------------------------------------------
    # Pestaña 1: Adaptadores y Caché
    # ------------------------------------------------------------------

    def _build_adapters_and_cache_tab(self) -> QScrollArea:
        scroll, container, layout = self._create_scroll_tab()

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        sub = QLabel("INTERFACES DETECTADAS", container)
        sub.setObjectName("SubgroupTitle")
        header_row.addWidget(sub)
        header_row.addStretch(1)

        self.only_connected_chk = QCheckBox("Solo conectados", container)
        self.only_connected_chk.setChecked(True)
        self.only_connected_chk.setToolTip("Ocultar adaptadores desconectados o deshabilitados")
        self.only_connected_chk.toggled.connect(lambda _checked: self._apply_adapters_filter())
        header_row.addWidget(self.only_connected_chk)
        layout.addLayout(header_row)

        self.adapters_empty_label = QLabel(
            "Hacé clic en 'Actualizar Adaptadores' para listar las interfaces de red.",
            container,
        )
        self.adapters_empty_label.setObjectName("LastLogEvent")
        layout.addWidget(self.adapters_empty_label)

        self.adapters_list_container = QWidget(container)
        self.adapters_list_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self.adapters_list_layout = QVBoxLayout(self.adapters_list_container)
        self.adapters_list_layout.setContentsMargins(0, 0, 0, 0)
        self.adapters_list_layout.setSpacing(7)
        layout.addWidget(self.adapters_list_container)

        self._ncpa_sub = QLabel("ACCESO DIRECTO DEL SISTEMA", container)
        self._ncpa_sub.setObjectName("SubgroupTitle")
        layout.addWidget(self._ncpa_sub)

        self._ncpa_row = _NetworkActionRow(
            title="Conexiones de Red de Windows (ncpa.cpl)",
            visible_actions=[
                (
                    "Abrir",
                    "",
                    "Abrir el panel clásico de adaptadores de Windows",
                    lambda: self._run_network_task(
                        "Conexiones de Red",
                        net_tasks.open_network_connections,
                        refresh_after=False,
                    ),
                )
            ],
            parent=container,
        )
        layout.addWidget(self._ncpa_row)

        self._append_renewal_sections(container, layout)
        return scroll

    def _render_adapters(self, adapters: list[NetworkAdapter]) -> None:
        sorted_adapters = sorted(adapters, key=lambda a: (0 if a.is_up else 1, a.name.lower()))
        self._adapters = sorted_adapters
        self._adapter_rows.clear()

        while self.adapters_list_layout.count():
            item = self.adapters_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not sorted_adapters:
            self.adapters_empty_label.setText("No se detectaron adaptadores de red en el sistema.")
            self.adapters_empty_label.setVisible(True)
            self._apply_adapters_filter()
            return

        for adp in sorted_adapters:
            mode_badge = "DHCP" if adp.dhcp_enabled else "Estática"
            toggle_label = "Habilitar" if adp.is_disabled else "Deshabilitar"
            toggle_style = "PrimaryButton" if adp.is_disabled else "DangerButton"
            toggle_target = adp.is_disabled

            visible_actions: list[ActionSpec] = [
                (
                    "DNS",
                    "",
                    f"Configurar servidores DNS en '{adp.name}'",
                    lambda a=adp: self._open_dns_dialog(a),
                ),
                (
                    "IP / DHCP",
                    "SuccessButton",
                    f"Configurar IPv4 estática o DHCP en '{adp.name}'",
                    lambda a=adp: self._open_ip_dialog(a),
                ),
                (
                    toggle_label,
                    toggle_style,
                    f"{toggle_label} adaptador '{adp.name}'",
                    lambda a=adp, en=toggle_target: self._confirm_toggle_adapter(a, en),
                ),
            ]

            overflow_actions: list[ActionSpec] = [
                (
                    "Reiniciar adaptador",
                    "",
                    f"Reiniciar '{adp.name}' mediante Restart-NetAdapter",
                    lambda a=adp: self._run_network_task(
                        f"Reiniciar {a.name}",
                        lambda log, n=a.name: net_tasks.restart_adapter(n, log=log),
                    ),
                ),
                (
                    "Renovar IP de este adaptador",
                    "",
                    f"Ejecutar release/renew en '{adp.name}'",
                    lambda a=adp: self._run_network_task(
                        f"Renovar IP ({a.name})",
                        lambda log, n=a.name: net_tasks.renew_ip_and_dns(adapter_name=n, log=log),
                    ),
                ),
                (
                    "Ver detalles completos",
                    "",
                    "Mostrar todos los parámetros del adaptador",
                    lambda a=adp: AdapterDetailsDialog(a, self).exec(),
                ),
                (
                    "Copiar dirección IPv4",
                    "",
                    "Copiar dirección IPv4 al portapapeles",
                    lambda a=adp: self._copy_adapter_ip(a),
                ),
            ]

            tooltip_parts = [adp.description]
            if adp.link_speed:
                tooltip_parts.append(f"Velocidad: {adp.link_speed}")
            if adp.mac_address:
                tooltip_parts.append(f"MAC: {adp.mac_address}")

            summary = adp.summary_line()
            row = _NetworkActionRow(
                title=adp.name,
                visible_actions=visible_actions,
                overflow_actions=overflow_actions,
                badge_text=adp.status_label,
                badge_style=adp.status_badge_style,
                secondary_badge_text=mode_badge,
                secondary_badge_style="RowBadgeMuted",
                meta_text=summary,
                tooltip=" — ".join(p for p in tooltip_parts if p),
                badges_in_meta=True,
                compact_buttons=True,
                parent=self.adapters_list_container,
            )
            search_blob = (
                f"{adp.name} {adp.description} {adp.status_label} "
                f"{mode_badge} {summary} {adp.mac_address}"
            ).lower()
            self._adapter_rows.append((adp, search_blob, row))
            self.adapters_list_layout.addWidget(row)

        self._apply_adapters_filter()

    def _apply_adapters_filter(self) -> int:
        only_connected = self.only_connected_chk.isChecked()
        query = self._search_query

        visible_adapters = 0
        for adp, blob, row in self._adapter_rows:
            matches_conn = (not only_connected) or adp.is_up
            matches_query = (not query) or (query in blob)
            visible = matches_conn and matches_query
            row.setVisible(visible)
            if visible:
                visible_adapters += 1

        ncpa_blob = "conexiones de red de windows ncpa.cpl adaptadores acceso directo".lower()
        ncpa_visible = (not query) or (query in ncpa_blob)
        self._ncpa_row.setVisible(ncpa_visible)
        self._ncpa_sub.setVisible(ncpa_visible)

        if not self._adapters:
            self.adapters_empty_label.setVisible(True)
        elif visible_adapters == 0:
            if only_connected and query:
                self.adapters_empty_label.setText(
                    "No hay adaptadores conectados que coincidan con el filtro."
                )
            elif only_connected:
                self.adapters_empty_label.setText("No hay adaptadores conectados en este momento.")
            else:
                self.adapters_empty_label.setText(
                    "No hay adaptadores que coincidan con la búsqueda."
                )
            self.adapters_empty_label.setVisible(True)
        else:
            self.adapters_empty_label.setVisible(False)

        self.adapters_list_container.updateGeometry()
        if self.pages.currentIndex() == 0:
            self._on_tab_changed(0)

        return visible_adapters + (1 if ncpa_visible else 0)

    def _append_renewal_sections(self, container: QWidget, layout: QVBoxLayout) -> None:
        """Agrega las secciones de secuencias automáticas, renovación IP/DNS y pila TCP/IP."""
        self._renewal_sections.clear()

        sub_seq = QLabel("SECUENCIAS AUTOMÁTICAS", container)
        sub_seq.setObjectName("SubgroupTitle")
        layout.addWidget(sub_seq)

        row_quick = _NetworkActionRow(
            title="Reparación Rápida (Sin reinicio)",
            meta_text="Ejecuta flushdns -> release/renew -> reinicia el adaptador conectado -> verifica conectividad",
            visible_actions=[
                (
                    "Ejecutar",
                    "PrimaryButton",
                    "Ejecutar secuencia automática de reparación rápida sin reiniciar Windows",
                    self.run_quick_repair,
                )
            ],
            parent=container,
        )
        layout.addWidget(row_quick)

        row_deep = _NetworkActionRow(
            title="Limpieza Profunda de Red",
            badge_text="Requiere reinicio",
            badge_style="RowBadgeWarn",
            meta_text="Ejecuta flushdns -> arp -d * -> netsh winsock reset -> netsh int ip reset",
            visible_actions=[
                (
                    "Ejecutar",
                    "DangerButton",
                    "Ejecutar limpieza profunda de caché y pila TCP/IP (requiere Administrador y reinicio)",
                    self._confirm_deep_cleanup,
                )
            ],
            parent=container,
        )
        layout.addWidget(row_deep)

        self._renewal_sections.append(
            (
                sub_seq,
                [
                    ("reparación rápida sin reinicio flushdns release renew conectividad secuencias", row_quick),
                    ("limpieza profunda de red flushdns arp winsock netsh int ip reset reinicio", row_deep),
                ],
            )
        )

        sub1 = QLabel("RENOVACIÓN IP Y DNS", container)
        sub1.setObjectName("SubgroupTitle")
        layout.addWidget(sub1)

        row_renew = _NetworkActionRow(
            title="Renovar IP y DNS (Completo)",
            meta_text="Ejecuta ipconfig /flushdns, /release, /renew, /registerdns y verifica salida a Internet",
            visible_actions=[
                (
                    "Renovar",
                    "PrimaryButton",
                    "Renovar concesiones DHCP y caché DNS en todos los adaptadores",
                    self.run_renew_ip_dns,
                )
            ],
            parent=container,
        )
        layout.addWidget(row_renew)

        row_flush = _NetworkActionRow(
            title="Limpiar Caché de Resolución DNS",
            meta_text="Ejecuta ipconfig /flushdns sin interrumpir conexiones activas",
            visible_actions=[
                (
                    "Limpiar",
                    "SuccessButton",
                    "Vaciar la caché DNS local de Windows",
                    lambda: self._run_network_task(
                        "Limpiar Caché DNS",
                        net_tasks.flush_dns_cache,
                        refresh_after=False,
                    ),
                )
            ],
            parent=container,
        )
        layout.addWidget(row_flush)

        row_purge = _NetworkActionRow(
            title="Purgar Sesiones de Red (SMB / Kerberos)",
            meta_text="Ejecuta net use * /delete /y y klist purge para tomar nuevos permisos sin cerrar sesión",
            visible_actions=[
                (
                    "Purgar",
                    "",
                    "Eliminar conexiones de red SMB y tickets Kerberos en caché sin cerrar sesión",
                    lambda: self._run_network_task(
                        "Purgar Sesiones de Red",
                        net_tasks.purge_network_sessions,
                        refresh_after=False,
                    ),
                )
            ],
            parent=container,
        )
        layout.addWidget(row_purge)

        self._renewal_sections.append(
            (
                sub1,
                [
                    ("renovar ip y dns completo ipconfig flushdns release renew registerdns dhcp", row_renew),
                    ("limpiar caché de resolución dns ipconfig flushdns", row_flush),
                    ("purgar sesiones de red smb kerberos net use klist purge", row_purge),
                ],
            )
        )

        sub2 = QLabel("REPARACIÓN AVANZADA DE PILA DE RED", container)
        sub2.setObjectName("SubgroupTitle")
        layout.addWidget(sub2)

        row_winsock = _NetworkActionRow(
            title="Restablecer Winsock y Pila TCP/IP",
            badge_text="Requiere reinicio",
            badge_style="RowBadgeWarn",
            meta_text="Ejecuta netsh winsock reset y netsh int ip reset para reparar corrupción de red",
            visible_actions=[
                (
                    "Restablecer",
                    "DangerButton",
                    "Restablecer catálogo Winsock y pila TCP/IP (requiere Administrador)",
                    self._confirm_reset_stack,
                )
            ],
            parent=container,
        )
        layout.addWidget(row_winsock)

        self._renewal_sections.append(
            (
                sub2,
                [
                    ("restablecer winsock y pila tcp ip netsh reset reparación avanzada", row_winsock),
                ],
            )
        )

    # ------------------------------------------------------------------
    # Pestaña 2: Diagnóstico de Red
    # ------------------------------------------------------------------

    def _build_diagnostics_tab(self) -> QScrollArea:
        scroll, container, layout = self._create_scroll_tab(align_top=False)
        layout.setContentsMargins(6, 6, 10, 10)
        layout.setSpacing(3)
        self._diag_sections.clear()

        sub1 = QLabel("PRUEBAS ACTIVAS HACIA DESTINO", container)
        sub1.setObjectName("SubgroupTitle")
        layout.addWidget(sub1)

        probe_card = QFrame(container)
        probe_card.setObjectName("ActionRow")
        probe_layout = QHBoxLayout(probe_card)
        probe_layout.setContentsMargins(10, 5, 10, 5)
        probe_layout.setSpacing(8)

        self.diag_target_input = QLineEdit(probe_card)
        self.diag_target_input.setPlaceholderText("Host o IP (ej: 1.1.1.1, google.com)")
        self.diag_target_input.setText("1.1.1.1")
        probe_layout.addWidget(self.diag_target_input, stretch=1)

        self.diag_port_input = QLineEdit(probe_card)
        self.diag_port_input.setPlaceholderText("Puerto")
        self.diag_port_input.setText("443")
        self.diag_port_input.setFixedWidth(72)
        probe_layout.addWidget(self.diag_port_input)

        ping_btn = QPushButton("Ping", probe_card)
        ping_btn.setObjectName("PrimaryButton")
        ping_btn.clicked.connect(self._run_ping_diag)
        probe_layout.addWidget(ping_btn)

        trace_btn = QPushButton("Traceroute", probe_card)
        trace_btn.clicked.connect(self._run_tracert_diag)
        probe_layout.addWidget(trace_btn)

        ns_btn = QPushButton("NSLookup", probe_card)
        ns_btn.clicked.connect(self._run_nslookup_diag)
        probe_layout.addWidget(ns_btn)

        tcp_btn = QPushButton("Probar Puerto", probe_card)
        tcp_btn.setObjectName("SuccessButton")
        tcp_btn.clicked.connect(self._run_tcp_diag)
        probe_layout.addWidget(tcp_btn)

        layout.addWidget(probe_card)

        diag_sub1_entries: list[tuple[str, QWidget]] = [
            ("pruebas activas destino ping traceroute nslookup probar puerto tcp host ip", probe_card),
        ]

        if self._vpn_endpoints and callable(self._vpn_diagnostic_fn):
            vpn_card = QFrame(container)
            vpn_card.setObjectName("ActionRow")
            vpn_layout = QHBoxLayout(vpn_card)
            vpn_layout.setContentsMargins(10, 5, 10, 5)
            vpn_layout.setSpacing(6)

            vpn_lbl = QLabel("Verificar VPN:", vpn_card)
            vpn_lbl.setObjectName("RowTitle")
            vpn_layout.addWidget(vpn_lbl)
            vpn_layout.addStretch(1)

            vpn_search_terms = ["verificar vpn enlace forticlient aws"]
            for ep_key, ep_cfg in self._vpn_endpoints.items():
                ep_name = str(ep_cfg.get("name", ep_key))
                btn_label = "AWS VPN" if ep_key == "aws_vpn" else ep_name
                ep_host = str(ep_cfg.get("host", "")).strip()
                ep_ip = str(ep_cfg.get("ip", "")).strip()
                ep_port = int(ep_cfg.get("port", 443))

                btn = QPushButton(btn_label, vpn_card)
                btn.setProperty("compact", True)
                btn.setToolTip(
                    f"Diagnóstico en 4 capas: {ep_host or ep_ip} ({ep_ip}:{ep_port})"
                )
                btn.clicked.connect(
                    lambda _c=False, cfg=dict(ep_cfg), lbl=ep_name: self._run_vpn_endpoint_diag(
                        lbl, cfg
                    )
                )
                vpn_layout.addWidget(btn)
                vpn_search_terms.append(f"{ep_name} {btn_label} {ep_host} {ep_ip} {ep_port}".lower())

            layout.addWidget(vpn_card)
            diag_sub1_entries.append((" ".join(vpn_search_terms), vpn_card))

        self._diag_sections.append((sub1, diag_sub1_entries))

        sub2 = QLabel("DIAGNÓSTICO AUTOMÁTICO Y TABLAS DEL SISTEMA", container)
        sub2.setObjectName("SubgroupTitle")
        layout.addWidget(sub2)

        diag_rows = [
            (
                "Diagnóstico Integral de Conectividad",
                "Evalúa adaptadores activos, gateway, ping externo, resolución DNS y salida HTTPS (443)",
                "Ejecutar",
                "PrimaryButton",
                lambda: self._run_diagnostic(
                    "Diagnóstico Integral",
                    lambda log: net_tasks.run_full_network_diagnostic(log=log),
                ),
            ),
            (
                "Configuración IP Detallada (ipconfig /all)",
                "Muestra concesiones DHCP, servidores DNS, MAC y sufijos de cada interfaz",
                "Consultar",
                "",
                lambda: self._run_diagnostic("ipconfig /all", net_tasks.get_ipconfig_all),
            ),
            (
                "Tabla de Enrutamiento IPv4 (route print -4)",
                "Inspecciona rutas activas, métricas y puertas de enlace",
                "Consultar",
                "",
                lambda: self._run_diagnostic("Tabla de Rutas", net_tasks.get_routing_table),
            ),
            (
                "Caché ARP Local (arp -a)",
                "Lista direcciones IP y MAC resueltas en la red local",
                "Consultar",
                "",
                lambda: self._run_diagnostic("Tabla ARP", net_tasks.get_arp_table),
            ),
            (
                "Generar Reporte Completo",
                "Ejecuta Diagnóstico Integral + ipconfig /all + route print -4 + arp -a con separadores claros",
                "Generar",
                "SuccessButton",
                lambda: self._run_diagnostic(
                    "Reporte Completo de Red",
                    lambda log: net_tasks.generate_full_diagnostic_report(log=log),
                ),
            ),
        ]

        diag_entries: list[tuple[str, QWidget]] = []
        for title, meta, btn_text, btn_style, handler in diag_rows:
            row = _NetworkActionRow(
                title=title,
                meta_text=meta,
                visible_actions=[(btn_text, btn_style, meta, handler)],
                compact_vertical=True,
                parent=container,
            )
            layout.addWidget(row)
            diag_entries.append((f"{title} {meta}".lower(), row))

        self._diag_sections.append((sub2, diag_entries))

        out_header = QHBoxLayout()
        out_header.setContentsMargins(0, 2, 0, 0)
        out_title = QLabel("SALIDA DE DIAGNÓSTICO", container)
        out_title.setObjectName("SubgroupTitle")
        out_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        out_header.addWidget(out_title, stretch=1)

        expand_btn = QPushButton("Ampliar", container)
        expand_btn.clicked.connect(self._expand_diagnostic_output)
        out_header.addWidget(expand_btn)

        export_btn = QPushButton("Exportar (.txt)", container)
        export_btn.clicked.connect(self._export_diagnostic_output)
        out_header.addWidget(export_btn)

        copy_out_btn = QPushButton("Copiar", container)
        copy_out_btn.clicked.connect(self._copy_diagnostic_output)
        out_header.addWidget(copy_out_btn)

        clear_out_btn = QPushButton("Limpiar", container)
        clear_out_btn.clicked.connect(lambda: self.diag_output.clear())
        out_header.addWidget(clear_out_btn)
        layout.addLayout(out_header)

        self.diag_output = QPlainTextEdit(container)
        self.diag_output.setObjectName("DiagnosticOutput")
        self.diag_output.setReadOnly(True)
        self.diag_output.setMinimumHeight(105)
        self.diag_output.setPlaceholderText(
            "Ejecutá una prueba de red (Ping, Traceroute, NSLookup o Diagnóstico Integral) para ver los resultados aquí..."
        )
        layout.addWidget(self.diag_output, stretch=1)

        return scroll

    def set_search_filter(self, query: str) -> int:
        """Filtra adaptadores, acciones de renovación/caché y pruebas de diagnóstico por texto."""
        self._search_query = query.strip().lower()
        q = self._search_query

        total_matches = self._apply_adapters_filter()

        for section_list in (self._renewal_sections, self._diag_sections):
            for header_lbl, entries in section_list:
                sec_matches = 0
                for blob, widget in entries:
                    matched = (not q) or (q in blob)
                    widget.setVisible(matched)
                    if matched:
                        sec_matches += 1
                header_lbl.setVisible(sec_matches > 0)
                total_matches += sec_matches

        self._on_tab_changed(self.pages.currentIndex())
        return total_matches

    # ------------------------------------------------------------------
    # Refresco asíncrono y workers
    # ------------------------------------------------------------------

    def refresh_all_now(self) -> None:
        """Recarga la lista de adaptadores y verifica conectividad externa en segundo plano."""
        self.refresh_adapters_now()
        self.check_connectivity_now()

    def refresh_adapters_now(self) -> None:
        if self._adapter_worker and self._adapter_worker.isRunning():
            return
        self.adapters_empty_label.setText("Cargando adaptadores de red...")
        if not self._adapters:
            self.adapters_empty_label.setVisible(True)

        worker = AdapterRefreshWorker()
        worker.adapters_ready.connect(self._render_adapters)
        worker.failed.connect(self._on_adapter_refresh_error)
        self._adapter_worker = worker
        worker.start()

    def _on_adapter_refresh_error(self, err: str) -> None:
        self._emit_log(f"[ERROR] No se pudieron listar adaptadores: {err}")
        if not self._adapters:
            self.adapters_empty_label.setText(f"Error al consultar adaptadores: {err}")
            self.adapters_empty_label.setVisible(True)

    def run_quick_repair(self) -> None:
        """Ejecuta la secuencia automática de reparación rápida de red sin reiniciar."""
        self._run_network_task("Reparación Rápida", net_tasks.run_quick_repair)

    def run_renew_ip_dns(self) -> None:
        """Ejecuta la renovación completa de IP y DNS."""
        self._run_network_task("Renovar IP y DNS", lambda log: net_tasks.renew_ip_and_dns(log=log))

    def set_checking_connectivity(self) -> None:
        """Muestra el estado de comprobación en la píldora de conectividad de Redes."""
        self._set_net_badge("checking", "● Comprobando...")

    def apply_connectivity_result(self, result: dict) -> None:
        """Actualiza la píldora de conectividad externa con un resultado externo."""
        self._apply_connectivity_status(result)

    def check_connectivity_now(self) -> None:
        if self._connectivity_worker and self._connectivity_worker.isRunning():
            return
        self.set_checking_connectivity()
        worker = ConnectivityCheckWorker(timeout=2.0)
        worker.status_ready.connect(self._apply_connectivity_status)
        self._connectivity_worker = worker
        worker.start()

    def _set_net_badge(self, state: str, text: str) -> None:
        self.net_status_badge.setText(text)
        self.net_status_badge.setProperty("statusState", state)
        style = self.net_status_badge.style()
        if style is not None:
            style.unpolish(self.net_status_badge)
            style.polish(self.net_status_badge)

    def _apply_connectivity_status(self, result: dict) -> None:
        if result.get("online"):
            latency = result.get("latency_ms")
            host = result.get("host", "1.1.1.1")
            dns_txt = "DNS OK" if result.get("dns_ok") else "Sin DNS"
            lat_txt = f"{latency} ms" if latency is not None else "OK"
            self._set_net_badge("online", f"● Internet OK ({lat_txt} · {dns_txt})")
            self.net_status_badge.setToolTip(f"Salida externa verificada contra {host} ({lat_txt})")
        else:
            self._set_net_badge("offline", "● Sin conexión externa")

    def _track_worker(self, worker: QThread, label: str) -> None:
        self._active_workers.append(worker)
        self.busy_badge.setText(f"Ejecutando: {label}")
        self.busy_badge.setVisible(True)

        def _cleanup() -> None:
            if worker in self._active_workers:
                self._active_workers.remove(worker)
            if not self._active_workers:
                self.busy_badge.setText("")
                self.busy_badge.setVisible(False)

        worker.finished.connect(_cleanup)

    def _run_network_task(
        self,
        label: str,
        fn: Callable[..., str],
        refresh_after: bool = True,
    ) -> None:
        worker = NetworkTaskWorker(fn)
        worker.log_message.connect(self._emit_log)
        worker.finished_success.connect(
            lambda msg: self._on_task_success(label, msg, refresh_after)
        )
        worker.failed.connect(lambda err: QMessageBox.warning(self, f"Error en {label}", err))
        self._track_worker(worker, label)
        worker.start()

    def _on_task_success(self, label: str, msg: str, refresh_after: bool) -> None:
        self._emit_log(f"[COMPLETADO] {label}: {msg}")
        if refresh_after:
            self.refresh_all_now()
            if callable(self._on_network_changed):
                self._on_network_changed()

    # ------------------------------------------------------------------
    # Acciones de adaptadores y confirmaciones
    # ------------------------------------------------------------------

    def _open_ip_dialog(self, adapter: NetworkAdapter) -> None:
        dlg = IPConfigDialog(adapter, self)
        if dlg.exec() != IPConfigDialog.DialogCode.Accepted:
            return
        cfg = dlg.get_config()
        if cfg.get("mode") == "dhcp":
            also_dns = bool(cfg.get("also_reset_dns", True))
            self._run_network_task(
                f"DHCP ({adapter.name})",
                lambda log: net_tasks.set_adapter_dhcp(
                    adapter.name, also_reset_dns=also_dns, log=log
                ),
            )
            return

        def _apply_static(log: Callable[[str], None]) -> str:
            res = net_tasks.set_adapter_static_ip(
                adapter.name,
                ip_address=cfg["ip_address"],
                subnet_mask=cfg["subnet_mask"],
                gateway=cfg.get("gateway", ""),
                log=log,
            )
            if cfg.get("apply_dns"):
                dns_list = [d for d in (cfg.get("dns_primary"), cfg.get("dns_secondary")) if d]
                net_tasks.set_adapter_dns(
                    adapter.name,
                    dns_servers=dns_list,
                    use_dhcp=not bool(dns_list),
                    log=log,
                )
            return res

        self._run_network_task(f"IP Estática ({adapter.name})", _apply_static)

    def _open_dns_dialog(self, adapter: NetworkAdapter) -> None:
        dlg = DNSConfigDialog(adapter, self)
        if dlg.exec() != DNSConfigDialog.DialogCode.Accepted:
            return
        cfg = dlg.get_config()
        self._run_network_task(
            f"DNS ({adapter.name})",
            lambda log: net_tasks.set_adapter_dns(
                adapter.name,
                dns_servers=cfg.get("dns_servers", []),
                use_dhcp=bool(cfg.get("use_dhcp", True)),
                log=log,
            ),
        )

    def _confirm_toggle_adapter(self, adapter: NetworkAdapter, enable: bool) -> None:
        if not enable:
            reply = QMessageBox.question(
                self,
                "Deshabilitar adaptador",
                f"¿Seguro que querés deshabilitar '{adapter.name}'?\n"
                "Perderás la conectividad en esa interfaz hasta volver a habilitarla.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        verb = "Habilitar" if enable else "Deshabilitar"
        self._run_network_task(
            f"{verb} {adapter.name}",
            lambda log: net_tasks.set_adapter_enabled(adapter.name, enable, log=log),
        )

    def _copy_adapter_ip(self, adapter: NetworkAdapter) -> None:
        if not adapter.ipv4_address:
            QMessageBox.information(self, "Sin IPv4", f"'{adapter.name}' no tiene IPv4 asignada.")
            return
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(adapter.ipv4_address)
        self._emit_log(f"[OK] IPv4 de '{adapter.name}' copiada: {adapter.ipv4_address}")

    def _confirm_deep_cleanup(self) -> None:
        reply = QMessageBox.question(
            self,
            "Limpieza Profunda de Red",
            "Se ejecutarán en orden:\n"
            "• ipconfig /flushdns\n"
            "• arp -d *\n"
            "• netsh winsock reset\n"
            "• netsh int ip reset\n\n"
            "Esta operación requiere privilegios de Administrador y un reinicio posterior de Windows.\n"
            "¿Deseás continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._run_network_task("Limpieza Profunda de Red", net_tasks.run_deep_network_cleanup)

    def _confirm_reset_stack(self) -> None:
        reply = QMessageBox.question(
            self,
            "Restablecer Winsock y Pila TCP/IP",
            "Se ejecutarán 'netsh winsock reset' y 'netsh int ip reset'.\n"
            "Se recomienda reiniciar el equipo al finalizar.\n\n¿Deseás continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._run_network_task(
                "Restablecer Winsock / TCP-IP",
                net_tasks.reset_winsock_and_tcpip,
                refresh_after=False,
            )

    # ------------------------------------------------------------------
    # Diagnóstico de Red
    # ------------------------------------------------------------------

    def _run_diagnostic(self, label: str, fn: Callable[..., str]) -> None:
        self.diag_output.setPlainText(f"Ejecutando {label}...")
        worker = DiagnosticWorker(fn)
        worker.log_message.connect(self._emit_log)
        worker.output_ready.connect(lambda out: self._on_diag_output(label, out))
        worker.failed.connect(lambda err: self._on_diag_error(label, err))
        self._track_worker(worker, label)
        worker.start()

    def _on_diag_output(self, label: str, output: str) -> None:
        self.diag_output.setPlainText(output or "(Sin salida)")
        self._emit_log(f"[COMPLETADO] Diagnóstico '{label}' finalizado.")

    def _on_diag_error(self, label: str, err: str) -> None:
        self.diag_output.setPlainText(f"[ERROR] {err}")
        QMessageBox.warning(self, f"Error en {label}", err)

    def _validate_target(self) -> str | None:
        try:
            return net_tasks.validate_host_or_ip(self.diag_target_input.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Destino inválido", str(exc))
            return None

    def _run_ping_diag(self) -> None:
        target = self._validate_target()
        if target is None:
            return
        self._run_diagnostic(f"Ping {target}", lambda log: net_tasks.run_ping(target, log=log))

    def _run_vpn_endpoint_diag(self, label: str, endpoint_cfg: dict[str, Any]) -> None:
        if not callable(self._vpn_diagnostic_fn):
            return
        fn = self._vpn_diagnostic_fn
        self._run_diagnostic(f"Verificar {label}", lambda log, cfg=endpoint_cfg: fn(cfg, log))

    def _run_tracert_diag(self) -> None:
        target = self._validate_target()
        if target is None:
            return
        self._run_diagnostic(
            f"Traceroute {target}",
            lambda log: net_tasks.run_traceroute(target, log=log),
        )

    def _run_nslookup_diag(self) -> None:
        target = self._validate_target()
        if target is None:
            return
        self._run_diagnostic(
            f"NSLookup {target}",
            lambda log: net_tasks.run_nslookup(target, log=log),
        )

    def _run_tcp_diag(self) -> None:
        target = self._validate_target()
        if target is None:
            return
        try:
            port = int(self.diag_port_input.text().strip())
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Puerto inválido", "Ingresá un puerto TCP entre 1 y 65535.")
            return
        self._run_diagnostic(
            f"TCP {target}:{port}",
            lambda log: net_tasks.run_tcp_port_check(target, port, log=log),
        )

    def _expand_diagnostic_output(self) -> None:
        text = self.diag_output.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Sin contenido", "No hay salida de diagnóstico para ampliar.")
            return
        DiagnosticResultDialog("Salida de Diagnóstico de Red", text, self).exec()

    def _copy_diagnostic_output(self) -> None:
        text = self.diag_output.toPlainText().strip()
        if not text:
            return
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)
        self._emit_log("[OK] Salida de diagnóstico copiada al portapapeles.")

    def _export_diagnostic_output(self) -> None:
        text = self.diag_output.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Sin contenido", "No hay salida de diagnóstico para exportar.")
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Reporte de Diagnóstico de Red",
            f"diagnostico_red_{stamp}.txt",
            "Archivos de texto (*.txt)",
        )
        if not target:
            return
        try:
            Path(target).write_text(text + "\n", encoding="utf-8")
            self._emit_log(f"[OK] Reporte de diagnóstico exportado en: {target}")
            QMessageBox.information(self, "Reporte exportado", f"Guardado en:\n{target}")
        except OSError as exc:
            QMessageBox.warning(self, "Error al exportar", str(exc))

    def shutdown(self) -> None:
        """Detiene y espera limpiamente cualquier worker de red activo antes de cerrar."""
        if self._adapter_worker and self._adapter_worker.isRunning():
            self._adapter_worker.wait(1500)
        if self._connectivity_worker and self._connectivity_worker.isRunning():
            self._connectivity_worker.wait(1500)
        for worker in list(self._active_workers):
            if worker.isRunning():
                worker.wait(1500)
