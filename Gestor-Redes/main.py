"""Punto de entrada y ventana principal de Gestor de Redes con elevación UAC."""

from __future__ import annotations

import ctypes
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys
from typing import Callable

from PyQt6.QtCore import QPointF, QSize, Qt, QThread, QTimer
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QCloseEvent,
    QColor,
    QIcon,
    QKeySequence,
    QPainter,
    QPixmap,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from dialogs import AdapterDetailsDialog, DNSConfigDialog, DiagnosticResultDialog, IPConfigDialog
import net_tasks
from net_tasks import NetworkAdapter
from styles import DARK_THEME_QSS
from workers import (
    AdapterRefreshWorker,
    ConnectivityCheckWorker,
    DiagnosticWorker,
    TaskWorker,
)

APP_NAME = "Gestor de Redes"
APP_VERSION = "1.0.0"
APP_USER_MODEL_ID = "GestorRedes.App.1.0"

ActionCallback = Callable[[], None]
ActionWidgetSpec = tuple[str, str, str, ActionCallback]


def is_user_admin() -> bool:
    """Retorna True si el proceso actual tiene privilegios de Administrador en Windows."""
    if os.name != "nt":
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin(extra_args: list[str] | None = None) -> bool:
    """Relanza el script o ejecutable actual solicitando elevación UAC."""
    if os.name != "nt":
        return False

    args = [arg for arg in (extra_args if extra_args is not None else sys.argv[1:]) if arg != "--no-elevate"]
    if getattr(sys, "frozen", False):
        executable = sys.executable
        params = subprocess.list2cmdline(args)
    else:
        executable = sys.executable
        params = subprocess.list2cmdline([os.path.abspath(__file__), *args])

    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        executable,
        params,
        None,
        1,
    )
    return int(result) > 32


def _create_more_dots_icon(color: str = "#E4E4E7") -> QIcon:
    """Dibuja vectorialmente un ícono de 3 puntos verticales centrado (⋮)."""
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(color)))

    for y in (4.0, 9.0, 14.0):
        painter.drawEllipse(QPointF(9.0, y), 1.6, 1.6)

    painter.end()
    return QIcon(pixmap)


class ActionRow(QFrame):
    """Fila horizontal compacta con título, badges opcionales, subtítulo, botones y menú ⋮."""

    def __init__(
        self,
        title: str,
        visible_actions: list[ActionWidgetSpec],
        overflow_actions: list[ActionWidgetSpec] | None = None,
        badge_text: str = "",
        badge_style: str = "RowBadgeMuted",
        secondary_badge_text: str = "",
        secondary_badge_style: str = "RowBadgeMuted",
        meta_text: str = "",
        tooltip: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ActionRow")
        self.setMinimumHeight(44 if not meta_text else 58)
        if tooltip:
            self.setToolTip(tooltip)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 7, 14, 7)
        outer.setSpacing(10)

        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(3)

        title_line = QHBoxLayout()
        title_line.setContentsMargins(0, 0, 0, 0)
        title_line.setSpacing(7)

        title_lbl = QLabel(title, self)
        title_lbl.setObjectName("RowTitle")
        title_line.addWidget(title_lbl)

        self.badge_label = QLabel(badge_text, self)
        self.badge_label.setObjectName(badge_style)
        self.badge_label.setVisible(bool(badge_text))
        title_line.addWidget(self.badge_label)

        self.secondary_badge_label = QLabel(secondary_badge_text, self)
        self.secondary_badge_label.setObjectName(secondary_badge_style)
        self.secondary_badge_label.setVisible(bool(secondary_badge_text))
        title_line.addWidget(self.secondary_badge_label)

        title_line.addStretch(1)
        left_col.addLayout(title_line)

        if meta_text:
            meta_lbl = QLabel(meta_text, self)
            meta_lbl.setObjectName("RowMeta")
            meta_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            left_col.addWidget(meta_lbl)

        outer.addLayout(left_col, stretch=1)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(7)

        for text, obj_name, btn_tip, handler in visible_actions:
            btn = QPushButton(text, self)
            if obj_name:
                btn.setObjectName(obj_name)
            if btn_tip:
                btn.setToolTip(btn_tip)
            btn.clicked.connect(lambda _checked=False, h=handler: h())
            btn_layout.addWidget(btn)

        if overflow_actions:
            more_btn = QPushButton("", self)
            more_btn.setObjectName("MoreButton")
            more_btn.setFixedSize(32, 30)
            more_btn.setIcon(_create_more_dots_icon())
            more_btn.setIconSize(QSize(16, 16))
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


class MainWindow(QMainWindow):
    """Ventana principal de Gestor de Redes."""

    def __init__(self, is_admin: bool) -> None:
        super().__init__()
        self.is_admin = is_admin
        self._active_workers: list[QThread] = []
        self._adapter_worker: AdapterRefreshWorker | None = None
        self._connectivity_worker: ConnectivityCheckWorker | None = None
        self._adapters: list[NetworkAdapter] = []
        self._adapter_rows_index: list[tuple[str, ActionRow]] = []
        self._tool_rows_index: list[tuple[str, ActionRow]] = []
        self._section_titles = [
            "Adaptadores de Red",
            "Renovación y Caché",
            "Diagnóstico de Red",
        ]
        self._log_collapsed = True

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1080, 680)
        self.setMinimumSize(1040, 620)
        icon_path = _resolve_optional_icon()
        if icon_path is not None:
            self.setWindowIcon(QIcon(str(icon_path)))

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(150)
        self._search_timer.timeout.connect(self._apply_search_filter)

        self._connectivity_timer = QTimer(self)
        self._connectivity_timer.setInterval(20000)
        self._connectivity_timer.timeout.connect(self.check_connectivity_now)

        self._build_ui()
        self._setup_shortcuts()

        self.append_log(
            f"[INFO] {APP_NAME} v{APP_VERSION} iniciado "
            f"({'Administrador' if self.is_admin else 'Sin UAC'})."
        )
        self._connectivity_timer.start()
        self.refresh_all_now()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._create_top_bar(central))

        self.splitter = QSplitter(Qt.Orientation.Vertical, central)
        self.splitter.setChildrenCollapsible(False)

        body = QWidget(self.splitter)
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.sidebar = QListWidget(body)
        self.sidebar.setObjectName("SidebarNav")
        self.sidebar.setFixedWidth(220)
        for title in self._section_titles:
            self.sidebar.addItem(QListWidgetItem(title))
        self.sidebar.currentRowChanged.connect(self._on_sidebar_changed)

        content_col = QWidget(body)
        content_layout = QVBoxLayout(content_col)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        content_layout.addWidget(self._create_content_toolbar(content_col))

        self.stack = QStackedWidget(content_col)
        self.stack.addWidget(self._build_adapters_page())
        self.stack.addWidget(self._build_renewal_page())
        self.stack.addWidget(self._build_diagnostics_page())
        content_layout.addWidget(self.stack, stretch=1)

        body_layout.addWidget(self.sidebar)
        body_layout.addWidget(content_col, stretch=1)

        self.splitter.addWidget(body)
        self.splitter.addWidget(self._create_log_panel(self.splitter))
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)

        root_layout.addWidget(self.splitter, stretch=1)

        self.sidebar.setCurrentRow(0)

    def _create_top_bar(self, parent: QWidget) -> QFrame:
        bar = QFrame(parent)
        bar.setObjectName("TopBar")
        bar.setFixedHeight(48)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(8)

        title_lbl = QLabel(APP_NAME, bar)
        title_lbl.setObjectName("AppTitle")
        layout.addWidget(title_lbl)

        layout.addStretch()

        if self.is_admin:
            admin_badge = QLabel("Administrador", bar)
            admin_badge.setObjectName("AdminBadgeOk")
            layout.addWidget(admin_badge)
        else:
            admin_btn = QPushButton("Sin UAC", bar)
            admin_btn.setObjectName("AdminBadgeWarnBtn")
            admin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            admin_btn.setToolTip("Clic para reiniciar como Administrador")
            admin_btn.clicked.connect(lambda _checked=False: self._relaunch_as_admin())
            layout.addWidget(admin_btn)

        self.net_status_badge = QLabel("● Comprobando...", bar)
        self.net_status_badge.setProperty("statusRole", "netBadge")
        self.net_status_badge.setProperty("statusState", "checking")
        self.net_status_badge.setToolTip("Estado de conectividad externa (1.1.1.1 / 8.8.8.8) y DNS")
        layout.addWidget(self.net_status_badge)

        self.refresh_btn = QPushButton("Actualizar", bar)
        self.refresh_btn.setToolTip("Recargar adaptadores y verificar conectividad (F5)")
        self.refresh_btn.clicked.connect(self.refresh_all_now)
        layout.addWidget(self.refresh_btn)

        return bar

    def _create_content_toolbar(self, parent: QWidget) -> QFrame:
        toolbar = QFrame(parent)
        toolbar.setObjectName("ContentToolbar")
        toolbar.setFixedHeight(44)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(18, 6, 18, 6)
        layout.setSpacing(12)

        self.section_header_label = QLabel(self._section_titles[0], toolbar)
        self.section_header_label.setObjectName("PageHeader")
        layout.addWidget(self.section_header_label)

        layout.addStretch()

        self.search_input = QLineEdit(toolbar)
        self.search_input.setObjectName("SearchInput")
        self.search_input.setFixedWidth(260)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setPlaceholderText("Filtrar adaptador o acción... (Ctrl+F)")
        self.search_input.textChanged.connect(lambda _t: self._search_timer.start())
        layout.addWidget(self.search_input)

        return toolbar

    def _create_scroll_container(self) -> tuple[QScrollArea, QWidget, QVBoxLayout]:
        scroll = QScrollArea(self.stack)
        scroll.setWidgetResizable(True)
        container = QWidget(scroll)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 10, 18, 14)
        layout.setSpacing(7)
        scroll.setWidget(container)
        return scroll, container, layout

    # ------------------------------------------------------------------
    # Página 1: Adaptadores de Red
    # ------------------------------------------------------------------

    def _build_adapters_page(self) -> QScrollArea:
        scroll, container, layout = self._create_scroll_container()
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        sub = QLabel("INTERFACES DETECTADAS", container)
        sub.setObjectName("SubgroupTitle")
        layout.addWidget(sub)

        self.adapters_empty_label = QLabel("Cargando adaptadores de red...", container)
        self.adapters_empty_label.setObjectName("LastLogEvent")
        layout.addWidget(self.adapters_empty_label)

        self.adapters_list_container = QWidget(container)
        self.adapters_list_layout = QVBoxLayout(self.adapters_list_container)
        self.adapters_list_layout.setContentsMargins(0, 0, 0, 0)
        self.adapters_list_layout.setSpacing(7)
        layout.addWidget(self.adapters_list_container)

        quick_sub = QLabel("ACCESO DIRECTO DEL SISTEMA", container)
        quick_sub.setObjectName("SubgroupTitle")
        layout.addWidget(quick_sub)

        ncpa_row = ActionRow(
            title="Conexiones de Red de Windows (ncpa.cpl)",
            visible_actions=[
                (
                    "Abrir",
                    "",
                    "Abrir el panel clásico de adaptadores de Windows",
                    lambda: self._run_task(
                        "Conexiones de Red",
                        net_tasks.open_network_connections,
                        refresh_after=False,
                    ),
                )
            ],
            parent=container,
        )
        layout.addWidget(ncpa_row)

        layout.addStretch()
        return scroll

    def _render_adapters(self, adapters: list[NetworkAdapter]) -> None:
        self._adapters = adapters
        self._adapter_rows_index.clear()

        while self.adapters_list_layout.count():
            item = self.adapters_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not adapters:
            self.adapters_empty_label.setText("No se detectaron adaptadores de red en el sistema.")
            self.adapters_empty_label.setVisible(True)
            return

        self.adapters_empty_label.setVisible(False)

        for adp in adapters:
            mode_badge = "DHCP" if adp.dhcp_enabled else "Estática"
            toggle_label = "Habilitar" if adp.is_disabled else "Deshabilitar"
            toggle_style = "PrimaryButton" if adp.is_disabled else "DangerButton"
            toggle_target = adp.is_disabled

            visible_actions: list[ActionWidgetSpec] = [
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

            overflow_actions: list[ActionWidgetSpec] = [
                (
                    "Reiniciar adaptador",
                    "",
                    f"Reiniciar '{adp.name}' mediante Restart-NetAdapter",
                    lambda a=adp: self._run_task(
                        f"Reiniciar {a.name}",
                        lambda log, n=a.name: net_tasks.restart_adapter(n, log=log),
                    ),
                ),
                (
                    "Renovar IP de este adaptador",
                    "",
                    f"Ejecutar release/renew en '{adp.name}'",
                    lambda a=adp: self._run_task(
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
            tooltip = " — ".join(p for p in tooltip_parts if p)

            row = ActionRow(
                title=adp.name,
                visible_actions=visible_actions,
                overflow_actions=overflow_actions,
                badge_text=adp.status_label,
                badge_style=adp.status_badge_style,
                secondary_badge_text=mode_badge,
                secondary_badge_style="RowBadgeMuted",
                meta_text=adp.summary_line(),
                tooltip=tooltip,
                parent=self.adapters_list_container,
            )
            self.adapters_list_layout.addWidget(row)

            blob = (
                f"{adp.name} {adp.description} {adp.status_label} {adp.ipv4_address} "
                f"{adp.gateway} {adp.mac_address} {' '.join(adp.dns_servers)} {mode_badge}"
            ).lower()
            self._adapter_rows_index.append((blob, row))

        self._apply_search_filter()

    # ------------------------------------------------------------------
    # Página 2: Renovación y Caché
    # ------------------------------------------------------------------

    def _build_renewal_page(self) -> QScrollArea:
        scroll, container, layout = self._create_scroll_container()

        sub_seq = QLabel("SECUENCIAS AUTOMÁTICAS", container)
        sub_seq.setObjectName("SubgroupTitle")
        layout.addWidget(sub_seq)

        r_quick = ActionRow(
            title="Reparación Rápida (Sin reinicio)",
            meta_text="Ejecuta flushdns -> release/renew -> reinicia el adaptador conectado -> verifica conectividad y refresca estado",
            visible_actions=[
                (
                    "Ejecutar",
                    "PrimaryButton",
                    "Ejecutar secuencia automática de reparación rápida sin reiniciar Windows",
                    lambda: self._run_task(
                        "Reparación Rápida",
                        net_tasks.run_quick_repair,
                    ),
                )
            ],
            parent=container,
        )
        layout.addWidget(r_quick)
        self._tool_rows_index.append(
            ("secuencia automatica reparacion rapida sin reinicio flushdns release renew reiniciar adaptador", r_quick)
        )

        r_deep = ActionRow(
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
        layout.addWidget(r_deep)
        self._tool_rows_index.append(
            ("secuencia automatica limpieza profunda red flushdns arp winsock tcp ip reset reinicio", r_deep)
        )

        sub1 = QLabel("RENOVACIÓN IP Y DNS", container)
        sub1.setObjectName("SubgroupTitle")
        layout.addWidget(sub1)

        rows_spec: list[tuple[str, str, ActionRow]] = []

        r_renew = ActionRow(
            title="Renovar IP y DNS (Completo)",
            meta_text="Ejecuta ipconfig /flushdns, /release, /renew, /registerdns y verifica salida a Internet",
            visible_actions=[
                (
                    "Renovar",
                    "PrimaryButton",
                    "Renovar concesiones DHCP y caché DNS en todos los adaptadores",
                    lambda: self._run_task(
                        "Renovar IP y DNS",
                        lambda log: net_tasks.renew_ip_and_dns(log=log),
                    ),
                )
            ],
            parent=container,
        )
        rows_spec.append(("renovar ip dns flushdns release renew registerdns dhcp", "renew", r_renew))

        r_flush = ActionRow(
            title="Limpiar Caché de Resolución DNS",
            meta_text="Ejecuta ipconfig /flushdns sin interrumpir conexiones activas",
            visible_actions=[
                (
                    "Limpiar",
                    "SuccessButton",
                    "Vaciar la caché DNS local de Windows",
                    lambda: self._run_task(
                        "Limpiar Caché DNS",
                        net_tasks.flush_dns_cache,
                        refresh_after=False,
                    ),
                )
            ],
            parent=container,
        )
        rows_spec.append(("limpiar cache dns flushdns", "flush", r_flush))

        for blob, _key, row in rows_spec:
            layout.addWidget(row)
            self._tool_rows_index.append((blob, row))

        sub2 = QLabel("REPARACIÓN AVANZADA DE PILA DE RED", container)
        sub2.setObjectName("SubgroupTitle")
        layout.addWidget(sub2)

        r_reset = ActionRow(
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
        layout.addWidget(r_reset)
        self._tool_rows_index.append(("restablecer winsock tcp ip netsh reset reparar", r_reset))

        layout.addStretch()
        return scroll

    # ------------------------------------------------------------------
    # Página 3: Diagnóstico de Red
    # ------------------------------------------------------------------

    def _build_diagnostics_page(self) -> QScrollArea:
        scroll, container, layout = self._create_scroll_container()

        sub1 = QLabel("PRUEBAS ACTIVAS HACIA DESTINO", container)
        sub1.setObjectName("SubgroupTitle")
        layout.addWidget(sub1)

        probe_card = QFrame(container)
        probe_card.setObjectName("ActionRow")
        probe_layout = QHBoxLayout(probe_card)
        probe_layout.setContentsMargins(14, 10, 14, 10)
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
        ping_btn.setToolTip("Enviar 4 paquetes ICMP al destino")
        ping_btn.clicked.connect(self._run_ping_diag)
        probe_layout.addWidget(ping_btn)

        trace_btn = QPushButton("Traceroute", probe_card)
        trace_btn.setToolTip("Trazar saltos de red hacia el destino (tracert -d)")
        trace_btn.clicked.connect(self._run_tracert_diag)
        probe_layout.addWidget(trace_btn)

        ns_btn = QPushButton("NSLookup", probe_card)
        ns_btn.setToolTip("Consultar resolución DNS del destino")
        ns_btn.clicked.connect(self._run_nslookup_diag)
        probe_layout.addWidget(ns_btn)

        tcp_btn = QPushButton("Probar Puerto", probe_card)
        tcp_btn.setObjectName("SuccessButton")
        tcp_btn.setToolTip("Comprobar conectividad TCP al puerto indicado")
        tcp_btn.clicked.connect(self._run_tcp_diag)
        probe_layout.addWidget(tcp_btn)

        layout.addWidget(probe_card)

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

        for title, meta, btn_text, btn_style, handler in diag_rows:
            row = ActionRow(
                title=title,
                meta_text=meta,
                visible_actions=[(btn_text, btn_style, meta, handler)],
                parent=container,
            )
            layout.addWidget(row)
            self._tool_rows_index.append((f"{title} {meta}".lower(), row))

        out_header = QHBoxLayout()
        out_header.setContentsMargins(0, 6, 0, 0)
        out_title = QLabel("SALIDA DE DIAGNÓSTICO", container)
        out_title.setObjectName("SubgroupTitle")
        out_header.addWidget(out_title)
        out_header.addStretch()

        expand_btn = QPushButton("Ampliar", container)
        expand_btn.setToolTip("Abrir la salida actual en una ventana modal más grande")
        expand_btn.clicked.connect(self._expand_diagnostic_output)
        out_header.addWidget(expand_btn)

        export_btn = QPushButton("Exportar Reporte (.txt)", container)
        export_btn.setToolTip("Guardar la salida actual del diagnóstico en un archivo .txt")
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
        self.diag_output.setMinimumHeight(180)
        self.diag_output.setPlaceholderText(
            "Ejecutá una prueba de red (Ping, Traceroute, NSLookup o Diagnóstico Integral) para ver los resultados aquí..."
        )
        layout.addWidget(self.diag_output, stretch=1)

        return scroll

    # ------------------------------------------------------------------
    # Panel inferior de log (colapsado por defecto como en EzSetup)
    # ------------------------------------------------------------------

    def _create_log_panel(self, parent: QWidget) -> QFrame:
        panel = QFrame(parent)
        panel.setObjectName("LogPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 5, 12, 6)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(8)
        title = QLabel("Registro:", panel)
        title.setObjectName("LogHeaderLabel")
        header.addWidget(title)

        self.last_log_label = QLabel("Listo", panel)
        self.last_log_label.setObjectName("LastLogEvent")
        header.addWidget(self.last_log_label, stretch=1)

        self.active_task_label = QLabel("", panel)
        self.active_task_label.setObjectName("RowBadgeMuted")
        self.active_task_label.setVisible(False)
        header.addWidget(self.active_task_label)

        clear_btn = QPushButton("Limpiar", panel)
        clear_btn.clicked.connect(self._clear_logs)
        header.addWidget(clear_btn)

        self.toggle_log_btn = QPushButton("Mostrar Log", panel)
        self.toggle_log_btn.clicked.connect(self._toggle_log_panel)
        header.addWidget(self.toggle_log_btn)
        layout.addLayout(header)

        self.log_output = QPlainTextEdit(panel)
        self.log_output.setObjectName("LogOutput")
        self.log_output.setReadOnly(True)
        self.log_output.setVisible(False)
        layout.addWidget(self.log_output)

        panel.setMaximumHeight(38)
        self._log_panel = panel
        return panel

    def _setup_shortcuts(self) -> None:
        self._search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self._search_shortcut.activated.connect(self._focus_search)
        self._refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        self._refresh_shortcut.activated.connect(self.refresh_all_now)

    def _focus_search(self) -> None:
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _toggle_log_panel(self) -> None:
        self._log_collapsed = not self._log_collapsed
        self.log_output.setVisible(not self._log_collapsed)
        if self._log_collapsed:
            self.toggle_log_btn.setText("Mostrar Log")
            self._log_panel.setMaximumHeight(38)
        else:
            self.toggle_log_btn.setText("Ocultar Log")
            self._log_panel.setMaximumHeight(16777215)
            self.splitter.setSizes([420, 180])

    def _clear_logs(self) -> None:
        self.log_output.clear()
        self.last_log_label.setText("Registro limpio")

    # ------------------------------------------------------------------
    # Navegación y filtrado
    # ------------------------------------------------------------------

    def _on_sidebar_changed(self, row: int) -> None:
        if row < 0 or row >= len(self._section_titles):
            return
        self.stack.setCurrentIndex(row)
        self.section_header_label.setText(self._section_titles[row])
        self._apply_search_filter()

    def _apply_search_filter(self) -> None:
        query = self.search_input.text().strip().lower()
        current_idx = self.stack.currentIndex()

        if current_idx == 0:
            visible_count = 0
            for blob, row in self._adapter_rows_index:
                matched = (not query) or (query in blob)
                row.setVisible(matched)
                if matched:
                    visible_count += 1
            if self._adapters:
                if visible_count == 0 and query:
                    self.adapters_empty_label.setText(
                        f'No hay adaptadores que coincidan con "{self.search_input.text().strip()}".'
                    )
                    self.adapters_empty_label.setVisible(True)
                else:
                    self.adapters_empty_label.setVisible(False)
        else:
            for blob, row in self._tool_rows_index:
                row.setVisible((not query) or (query in blob))

    # ------------------------------------------------------------------
    # Refresco de adaptadores y conectividad
    # ------------------------------------------------------------------

    def refresh_all_now(self) -> None:
        self.refresh_adapters_now()
        self.check_connectivity_now()

    def refresh_adapters_now(self) -> None:
        if self._adapter_worker and self._adapter_worker.isRunning():
            return
        self.refresh_btn.setEnabled(False)
        worker = AdapterRefreshWorker()
        worker.adapters_ready.connect(self._on_adapters_loaded)
        worker.failed.connect(self._on_adapters_failed)
        worker.finished.connect(lambda: self.refresh_btn.setEnabled(True))
        self._adapter_worker = worker
        worker.start()

    def _on_adapters_loaded(self, adapters: list[NetworkAdapter]) -> None:
        self._render_adapters(adapters)
        up_count = sum(1 for a in adapters if a.is_up)
        self.append_log(
            f"[INFO] Adaptadores actualizados: {len(adapters)} detectado(s), {up_count} conectado(s)."
        )

    def _on_adapters_failed(self, err: str) -> None:
        self.adapters_empty_label.setText(f"Error al leer adaptadores: {err}")
        self.adapters_empty_label.setVisible(True)
        self.append_log(f"[ERROR] {err}")

    def check_connectivity_now(self) -> None:
        if self._connectivity_worker and self._connectivity_worker.isRunning():
            return
        worker = ConnectivityCheckWorker()
        worker.status_ready.connect(self._on_connectivity_status)
        self._connectivity_worker = worker
        worker.start()

    def _on_connectivity_status(self, result: dict) -> None:
        online = bool(result.get("online", False))
        dns_ok = bool(result.get("dns_ok", False))
        host = str(result.get("host", ""))
        latency = result.get("latency_ms")

        if online and dns_ok:
            ms_txt = f" {latency:.0f}ms" if isinstance(latency, (int, float)) else ""
            self.net_status_badge.setText(f"● Internet OK{ms_txt}")
            self.net_status_badge.setProperty("statusState", "online")
            self.net_status_badge.setToolTip(f"Conectividad OK vía {host} | Resolución DNS operativa")
        elif online:
            self.net_status_badge.setText("● Sin DNS")
            self.net_status_badge.setProperty("statusState", "checking")
            self.net_status_badge.setToolTip(f"Salida IP OK ({host}), pero falló la resolución DNS")
        else:
            self.net_status_badge.setText("● Sin Internet")
            self.net_status_badge.setProperty("statusState", "offline")
            self.net_status_badge.setToolTip("Sin conectividad externa hacia 1.1.1.1 / 8.8.8.8")

        self.net_status_badge.style().unpolish(self.net_status_badge)
        self.net_status_badge.style().polish(self.net_status_badge)

    # ------------------------------------------------------------------
    # Acciones sobre adaptadores
    # ------------------------------------------------------------------

    def _open_ip_dialog(self, adapter: NetworkAdapter) -> None:
        dialog = IPConfigDialog(adapter, self)
        if dialog.exec() != IPConfigDialog.DialogCode.Accepted:
            return
        cfg = dialog.get_config()
        if cfg.get("mode") == "dhcp":
            self._run_task(
                f"DHCP en {adapter.name}",
                lambda log, n=adapter.name, rd=bool(cfg.get("also_reset_dns", False)): (
                    net_tasks.set_adapter_dhcp(n, also_reset_dns=rd, log=log)
                ),
            )
        else:
            self._run_task(
                f"IP Estática en {adapter.name}",
                lambda log, n=adapter.name, c=cfg: net_tasks.set_adapter_static_ip(
                    adapter_name=n,
                    ip_address=c["ip_address"],
                    subnet_mask=c["subnet_mask"],
                    gateway=c["gateway"],
                    dns_primary=c["dns_primary"],
                    dns_secondary=c["dns_secondary"],
                    apply_dns=bool(c["apply_dns"]),
                    log=log,
                ),
            )

    def _open_dns_dialog(self, adapter: NetworkAdapter) -> None:
        dialog = DNSConfigDialog(adapter, self)
        if dialog.exec() != DNSConfigDialog.DialogCode.Accepted:
            return
        cfg = dialog.get_config()
        self._run_task(
            f"DNS en {adapter.name}",
            lambda log, n=adapter.name, c=cfg: net_tasks.set_adapter_dns(
                adapter_name=n,
                dns_servers=list(c["dns_servers"]),
                use_dhcp=bool(c["use_dhcp"]),
                log=log,
            ),
        )

    def _confirm_toggle_adapter(self, adapter: NetworkAdapter, enable: bool) -> None:
        if not enable:
            reply = QMessageBox.question(
                self,
                "Deshabilitar adaptador",
                f"¿Querés deshabilitar el adaptador '{adapter.name}'?\n"
                "Se perderá la conectividad de red en esta interfaz hasta volver a habilitarla.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        verb = "Habilitar" if enable else "Deshabilitar"
        self._run_task(
            f"{verb} {adapter.name}",
            lambda log, n=adapter.name, en=enable: net_tasks.set_adapter_enabled(n, en, log=log),
        )

    def _copy_adapter_ip(self, adapter: NetworkAdapter) -> None:
        if not adapter.ipv4_address:
            self.append_log(f"[ADVERTENCIA] '{adapter.name}' no tiene dirección IPv4 asignada.")
            return
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(adapter.ipv4_address)
            self.append_log(f"[OK] IPv4 copiada al portapapeles: {adapter.ipv4_address}")

    def _confirm_reset_stack(self) -> None:
        reply = QMessageBox.question(
            self,
            "Restablecer Winsock y TCP/IP",
            "Se restablecerá el catálogo Winsock y la pila TCP/IP de Windows.\n"
            "Será necesario reiniciar el equipo para completar los cambios.\n\n"
            "¿Deseás continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._run_task("Restablecer Winsock y TCP/IP", net_tasks.reset_winsock_and_tcpip)

    def _confirm_deep_cleanup(self) -> None:
        reply = QMessageBox.question(
            self,
            "Limpieza Profunda de Red",
            "Se ejecutará la secuencia completa:\n"
            "1. ipconfig /flushdns\n"
            "2. arp -d *\n"
            "3. netsh winsock reset\n"
            "4. netsh int ip reset\n\n"
            "Será necesario reiniciar Windows para aplicar todos los cambios.\n"
            "¿Deseás continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._run_task("Limpieza Profunda de Red", net_tasks.run_deep_network_cleanup)

    # ------------------------------------------------------------------
    # Acciones de diagnóstico
    # ------------------------------------------------------------------

    def _run_ping_diag(self) -> None:
        target = self.diag_target_input.text().strip()
        self._run_diagnostic(
            f"Ping ({target or '-'})",
            lambda log, t=target: net_tasks.run_ping(t, count=4, log=log),
        )

    def _run_tracert_diag(self) -> None:
        target = self.diag_target_input.text().strip()
        self._run_diagnostic(
            f"Traceroute ({target or '-'})",
            lambda log, t=target: net_tasks.run_traceroute(t, max_hops=20, log=log),
        )

    def _run_nslookup_diag(self) -> None:
        target = self.diag_target_input.text().strip()
        self._run_diagnostic(
            f"NSLookup ({target or '-'})",
            lambda log, t=target: net_tasks.run_nslookup(t, log=log),
        )

    def _run_tcp_diag(self) -> None:
        target = self.diag_target_input.text().strip()
        raw_port = self.diag_port_input.text().strip()
        try:
            port = int(raw_port)
        except ValueError:
            QMessageBox.warning(self, "Puerto inválido", "Ingresá un número de puerto TCP entre 1 y 65535.")
            return
        self._run_diagnostic(
            f"TCP {target}:{port}",
            lambda log, t=target, p=port: net_tasks.run_tcp_port_check(t, p, log=log),
        )

    def _run_diagnostic(self, label: str, fn: Callable[..., str]) -> None:
        self.diag_output.setPlainText(f"Ejecutando {label}...")
        worker = DiagnosticWorker(fn)
        worker.log_message.connect(self.append_log)
        worker.output_ready.connect(lambda text: self._on_diagnostic_ready(label, text))
        worker.failed.connect(lambda err: self._on_diagnostic_failed(label, err))
        self._track_worker(worker, label)
        worker.start()

    def _on_diagnostic_ready(self, label: str, text: str) -> None:
        self.diag_output.setPlainText(text)
        self.append_log(f"[COMPLETADO] {label}")

    def _on_diagnostic_failed(self, label: str, err: str) -> None:
        self.diag_output.setPlainText(f"[ERROR] {err}")
        QMessageBox.warning(self, f"Error en {label}", err)

    def _copy_diagnostic_output(self) -> None:
        text = self.diag_output.toPlainText().strip()
        if not text:
            return
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)
            self.append_log("[OK] Salida de diagnóstico copiada al portapapeles.")

    def _expand_diagnostic_output(self) -> None:
        text = self.diag_output.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Sin salida", "Todavía no hay resultados de diagnóstico para mostrar.")
            return
        DiagnosticResultDialog("Resultado de Diagnóstico de Red", text, self).exec()

    def _export_diagnostic_output(self) -> None:
        text = self.diag_output.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Sin salida", "Todavía no hay resultados de diagnóstico para exportar.")
            return
        default_name = f"reporte_red_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Reporte de Diagnóstico",
            default_name,
            "Archivos de texto (*.txt);;Todos los archivos (*.*)",
        )
        if not file_path:
            return
        try:
            Path(file_path).write_text(text + "\n", encoding="utf-8")
        except OSError as exc:
            self.append_log(f"[ERROR] No se pudo exportar el reporte: {exc}")
            QMessageBox.warning(self, "Error al exportar", f"No se pudo guardar el archivo:\n{exc}")
            return
        self.append_log(f"[OK] Reporte exportado en: {file_path}")

    # ------------------------------------------------------------------
    # Infraestructura de workers, logs y UAC
    # ------------------------------------------------------------------

    def append_log(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {message}"
        self.log_output.appendPlainText(line)
        self.last_log_label.setText(line)

    def _track_worker(self, worker: QThread, label: str) -> None:
        self._active_workers.append(worker)
        self.active_task_label.setText(f"Ejecutando: {label}")
        self.active_task_label.setVisible(True)

        def _cleanup() -> None:
            if worker in self._active_workers:
                self._active_workers.remove(worker)
            if not self._active_workers:
                self.active_task_label.setText("")
                self.active_task_label.setVisible(False)

        worker.finished.connect(_cleanup)

    def _run_task(
        self,
        label: str,
        fn: Callable[..., str],
        refresh_after: bool = True,
    ) -> None:
        worker = TaskWorker(fn)
        worker.log_message.connect(self.append_log)
        worker.finished_success.connect(
            lambda msg: self._on_task_success(label, msg, refresh_after)
        )
        worker.failed.connect(lambda err: QMessageBox.warning(self, f"Error en {label}", err))
        self._track_worker(worker, label)
        worker.start()

    def _on_task_success(self, label: str, msg: str, refresh_after: bool) -> None:
        self.append_log(f"[COMPLETADO] {label}: {msg}")
        if refresh_after:
            QTimer.singleShot(600, self.refresh_all_now)

    def _relaunch_as_admin(self) -> None:
        if relaunch_as_admin():
            self.close()
        else:
            self.append_log("[ADVERTENCIA] No se completó la elevación UAC.")

    def closeEvent(self, event: QCloseEvent) -> None:
        self._search_timer.stop()
        self._connectivity_timer.stop()
        if self._adapter_worker and self._adapter_worker.isRunning():
            self._adapter_worker.wait(1500)
        if self._connectivity_worker and self._connectivity_worker.isRunning():
            self._connectivity_worker.wait(1500)
        for worker in list(self._active_workers):
            if worker.isRunning():
                worker.wait(1500)
        super().closeEvent(event)


def _resolve_optional_icon() -> Path | None:
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    candidate = base_dir / "assets" / "icon.ico"
    return candidate if candidate.is_file() else None


def main() -> int:
    skip_uac = "--no-elevate" in sys.argv
    admin = is_user_admin()

    if not admin and not skip_uac:
        if relaunch_as_admin():
            return 0

    if os.name == "nt":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setStyleSheet(DARK_THEME_QSS)

    icon_path = _resolve_optional_icon()
    if icon_path is not None:
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow(is_admin=admin)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
