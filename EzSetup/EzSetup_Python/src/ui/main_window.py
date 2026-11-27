"""Ventana principal minimalista y extensible por catálogo JSON de EzSetup."""

from __future__ import annotations

import ctypes
from datetime import datetime
import os
import subprocess
import sys
from typing import Any, Callable

from PyQt6.QtCore import QPoint, QPointF, QSize, Qt, QThread, QTimer
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
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src import system_tasks
from src.config import AppConfig, ConfigError
from src.modules import m365_wrapper, utilities_tasks
from src.ui.dialogs import (
    CreateLocalUserDialog,
    CredentialDialog,
    HardwareDiagnosticsDialog,
    InventoryDialog,
    M365SanitizerDialog,
    PrinterInstallDialog,
    ProgressDialog,
)
from src.ui.network_view import NetworkManagerView
from src.workers import (
    DownloadWorker,
    FileCopyWorker,
    InstalledSoftwareCheckWorker,
    IsoMountWorker,
    ServerCheckWorker,
    TaskWorker,
    ZipExtractWorker,
)

ActionCallback = Callable[[], None]
ActionWidgetSpec = tuple[str, str, str, ActionCallback]


def _create_more_dots_icon(color: str = "#E4E4E7") -> QIcon:
    """Dibuja vectorialmente un ícono de 3 puntos verticales centrado (12x12)."""
    pixmap = QPixmap(12, 12)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(color)))

    for y in (2.5, 6.0, 9.5):
        painter.drawEllipse(QPointF(6.0, y), 1.15, 1.15)

    painter.end()
    return QIcon(pixmap)


class ActionRow(QFrame):
    """Fila horizontal compacta con título, subtítulo opcional, badge, botón blanco único y menú ⋮."""

    def __init__(
        self,
        title: str,
        primary_action: ActionWidgetSpec,
        secondary_actions: list[ActionWidgetSpec] | None = None,
        subtitle: str = "",
        badge_text: str = "",
        badge_style: str = "RowBadgeMuted",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ActionRow")
        self.setMinimumHeight(44)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 7, 14, 7)
        layout.setSpacing(10)

        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(3)

        title_lbl = QLabel(title, self)
        title_lbl.setObjectName("RowTitle")
        title_lbl.setWordWrap(True)
        title_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        left_col.addWidget(title_lbl)

        if subtitle:
            subtitle_lbl = QLabel(subtitle, self)
            subtitle_lbl.setObjectName("RowSubtitle")
            subtitle_lbl.setWordWrap(True)
            subtitle_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            left_col.addWidget(subtitle_lbl)

        layout.addLayout(left_col, stretch=1)

        self.badge_label = QLabel(badge_text, self)
        self.badge_label.setObjectName(badge_style)
        self.badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.badge_label.setVisible(bool(badge_text))
        layout.addWidget(self.badge_label)

        action_col = QWidget(self)
        action_col.setObjectName("ActionColumn")
        action_col.setFixedWidth(168)
        action_col.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        action_layout = QHBoxLayout(action_col)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(6)

        p_text, _p_obj_name, p_tooltip, p_handler = primary_action

        self.primary_button = QPushButton(p_text, action_col)
        self.primary_button.setObjectName("PrimaryButton")
        self.primary_button.setFixedWidth(140)
        self.primary_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        if p_tooltip:
            self.primary_button.setToolTip(p_tooltip)
        self.primary_button.clicked.connect(lambda _checked=False, h=p_handler: h())
        action_layout.addWidget(self.primary_button)

        self.menu_button: QPushButton | None = None
        self.more_menu: QMenu | None = None
        self.menu_spacer: QWidget | None = None
        if secondary_actions:
            menu_btn = QPushButton("", action_col)
            menu_btn.setObjectName("MoreButton")
            menu_btn.setFixedSize(22, 22)
            menu_btn.setIcon(_create_more_dots_icon())
            menu_btn.setIconSize(QSize(12, 12))
            menu_btn.setToolTip("Más acciones")
            menu = QMenu(menu_btn)
            for text, _obj_name, tooltip, handler in secondary_actions:
                act = QAction(text, menu)
                if tooltip:
                    act.setToolTip(tooltip)
                act.triggered.connect(lambda _checked=False, h=handler: h())
                menu.addAction(act)
            menu_btn.clicked.connect(lambda _checked=False: self._open_more_menu())
            action_layout.addWidget(menu_btn)
            self.menu_button = menu_btn
            self.more_menu = menu
        else:
            spacer = QWidget(action_col)
            spacer.setFixedSize(22, 22)
            spacer.setStyleSheet("background: transparent;")
            action_layout.addWidget(spacer)
            self.menu_spacer = spacer

        layout.addWidget(action_col)

    def _compute_menu_pos(self) -> QPoint:
        """Calcula la posición global para alinear el borde derecho del QMenu con el botón ⋮."""
        assert self.menu_button is not None and self.more_menu is not None
        self.more_menu.ensurePolished()
        menu_size = self.more_menu.sizeHint()
        btn_bottom_right = self.menu_button.mapToGlobal(
            QPoint(self.menu_button.width(), self.menu_button.height() + 4)
        )
        return QPoint(max(0, btn_bottom_right.x() - menu_size.width()), btn_bottom_right.y())

    def _open_more_menu(self) -> None:
        if self.menu_button is None or self.more_menu is None:
            return
        self.more_menu.popup(self._compute_menu_pos())

    def set_badge(self, text: str, style_name: str, tooltip: str = "") -> None:
        self.badge_label.setText(text)
        self.badge_label.setObjectName(style_name)
        self.badge_label.setToolTip(tooltip)
        self.badge_label.setVisible(bool(text))
        self.badge_label.style().unpolish(self.badge_label)
        self.badge_label.style().polish(self.badge_label)


class MainWindow(QMainWindow):
    """Ventana principal de EzSetup v3.0.0."""

    _LOG_COLLAPSED_HEIGHT = 40
    _NETWORK_SUBPAGES = ("Adaptadores de Red", "Renovación y Caché", "Diagnóstico de Red")

    def __init__(self, config: AppConfig, is_admin: bool) -> None:
        super().__init__()
        self.config = config
        self.is_admin = is_admin
        self._active_workers: list[QThread] = []
        self._server_badges: dict[str, QLabel] = {}
        self._server_check_worker: ServerCheckWorker | None = None
        self._install_check_worker: InstalledSoftwareCheckWorker | None = None
        self._dotnet_rows: list[ActionRow] = []
        self._creds_rows: list[ActionRow] = []
        self._item_rows_by_id: dict[str, list[ActionRow]] = {}
        self._search_rows_index: list[tuple[str, ActionRow]] = []
        self._search_empty_label: QLabel | None = None
        self._category_titles: list[str] = []
        self._network_view: NetworkManagerView | None = None
        self._network_page_index: int = -1
        self._network_subpage_index: int = 0
        self._network_submenu_expanded: bool = False
        self._nav_buttons: list[QPushButton] = []
        self._network_nav_btn: QPushButton | None = None
        self._network_submenu: QWidget | None = None
        self._network_sub_buttons: list[QPushButton] = []
        self._last_selected_row: int = 0
        self._log_collapsed = True
        self._last_log_height: int = 180

        self.resize(1080, 650)
        self.setMinimumSize(900, 540)

        icon_path = self.config.get_asset_path("EzSetup.ico")
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(150)
        self._search_timer.timeout.connect(self._apply_search_filter)

        self._build_ui()
        self._setup_shortcuts()
        self._setup_server_monitor()
        self._rebuild_catalog_views()
        self.append_log(f"[INFO] Configuración cargada: {self.config.source_path}")
        self.check_servers_now()
        self.check_installed_software_now()
        QTimer.singleShot(250, self._preload_network_view)

    @property
    def network_view(self) -> NetworkManagerView | None:
        return self._network_view

    def _preload_network_view(self) -> None:
        if self._network_view is not None:
            self._network_view.ensure_initialized()

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
        body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._body_widget = body
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.sidebar_panel = QFrame(body)
        self.sidebar_panel.setObjectName("SidebarPanel")
        self.sidebar_panel.setFixedWidth(220)
        self._sidebar_layout = QVBoxLayout(self.sidebar_panel)
        self._sidebar_layout.setContentsMargins(8, 10, 8, 10)
        self._sidebar_layout.setSpacing(4)

        content_col = QWidget(body)
        content_layout = QVBoxLayout(content_col)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        content_layout.addWidget(self._create_content_toolbar(content_col))

        self.stack = QStackedWidget(content_col)
        content_layout.addWidget(self.stack, stretch=1)

        body_layout.addWidget(self.sidebar_panel)
        body_layout.addWidget(content_col, stretch=1)

        self.splitter.addWidget(body)
        self.splitter.addWidget(self._create_log_panel(self.splitter))
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self._apply_log_panel_state(collapsed=True)

        root_layout.addWidget(self.splitter, stretch=1)

    def _create_top_bar(self, parent: QWidget) -> QFrame:
        bar = QFrame(parent)
        bar.setObjectName("TopBar")
        bar.setFixedHeight(48)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(8)

        self.header_title_lbl = QLabel(bar)
        self.header_title_lbl.setObjectName("AppTitle")
        layout.addWidget(self.header_title_lbl)

        layout.addStretch()

        if self.is_admin:
            admin_badge = QLabel("Administrador", bar)
            admin_badge.setObjectName("AdminBadgeOk")
            admin_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(admin_badge)
        else:
            admin_btn = QPushButton("Sin UAC", bar)
            admin_btn.setObjectName("AdminBadgeWarnBtn")
            admin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            admin_btn.setToolTip("Clic para reiniciar como Administrador")
            admin_btn.clicked.connect(lambda _checked=False: self._relaunch_as_admin())
            layout.addWidget(admin_btn)

        self.server_badges_layout = QHBoxLayout()
        self.server_badges_layout.setSpacing(6)
        layout.addLayout(self.server_badges_layout)

        self.refresh_net_btn = QPushButton("Verificar Red", bar)
        self.refresh_net_btn.setToolTip("Comprobar conectividad TCP/SMB con los servidores configurados")
        self.refresh_net_btn.clicked.connect(self.check_servers_now)
        layout.addWidget(self.refresh_net_btn)

        self._top_bar = bar
        self._sync_header_metadata()
        return bar

    def _sync_header_metadata(self) -> None:
        app_cfg = self.config.app
        self.setWindowTitle(f"{app_cfg['name']} v{app_cfg['version']}")
        self.header_title_lbl.setText(str(app_cfg["name"]))

        while self.server_badges_layout.count():
            item = self.server_badges_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._server_badges.clear()

        for server_id, info in self.config.get_servers().items():
            badge = QLabel(f"● {info['host']}", self._top_bar)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setProperty("statusRole", "serverBadge")
            badge.setProperty("statusState", "checking")
            badge.setToolTip(f"{info.get('label', server_id)} — {info.get('unc_root', info['host'])}")
            self._server_badges[server_id] = badge
            self.server_badges_layout.addWidget(badge)

    def _create_content_toolbar(self, parent: QWidget) -> QFrame:
        toolbar = QFrame(parent)
        toolbar.setObjectName("ContentToolbar")
        toolbar.setFixedHeight(44)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(18, 6, 18, 6)
        layout.setSpacing(12)

        self.section_header_label = QLabel("", toolbar)
        self.section_header_label.setObjectName("PageHeader")
        layout.addWidget(self.section_header_label)

        layout.addStretch()

        self.search_input = QLineEdit(toolbar)
        self.search_input.setObjectName("SearchInput")
        self.search_input.setFixedWidth(250)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setPlaceholderText("Buscar herramienta... (Ctrl+F)")
        self.search_input.textChanged.connect(self._on_search_text_edited)
        layout.addWidget(self.search_input)

        return toolbar

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
        self.active_task_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.active_task_label.setVisible(False)
        header.addWidget(self.active_task_label)

        copy_btn = QPushButton("Copiar", panel)
        copy_btn.setToolTip("Copiar contenido completo del registro al portapapeles")
        copy_btn.clicked.connect(lambda _c=False: self._copy_logs())
        header.addWidget(copy_btn)

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

        self._log_panel = panel
        return panel

    def _setup_shortcuts(self) -> None:
        self._search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self._search_shortcut.activated.connect(self._focus_search)
        self._reload_shortcut = QShortcut(QKeySequence("F5"), self)
        self._reload_shortcut.activated.connect(self._reload_config)

    def _focus_search(self) -> None:
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _apply_log_panel_state(self, collapsed: bool) -> None:
        """Alterna el estado del panel de log ajustando el QSplitter sin dejar espacio vacío."""
        self._log_collapsed = collapsed
        if collapsed:
            if self.splitter.count() == 2:
                sizes = self.splitter.sizes()
                if len(sizes) == 2 and sizes[1] > self._LOG_COLLAPSED_HEIGHT + 20:
                    self._last_log_height = sizes[1]

            self.log_output.setVisible(False)
            self.toggle_log_btn.setText("Mostrar Log")
            self._log_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._log_panel.setFixedHeight(self._LOG_COLLAPSED_HEIGHT)
            self.splitter.setHandleWidth(0)
            if self.splitter.count() >= 2:
                handle = self.splitter.handle(1)
                if handle is not None:
                    handle.setEnabled(False)

            total = max(self.splitter.height(), sum(self.splitter.sizes()), 600)
            self.splitter.setSizes(
                [max(1, total - self._LOG_COLLAPSED_HEIGHT), self._LOG_COLLAPSED_HEIGHT]
            )
        else:
            self.toggle_log_btn.setText("Ocultar Log")
            self._log_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            self._log_panel.setMinimumHeight(110)
            self._log_panel.setMaximumHeight(16777215)
            self.log_output.setVisible(True)
            self.splitter.setHandleWidth(4)
            if self.splitter.count() >= 2:
                handle = self.splitter.handle(1)
                if handle is not None:
                    handle.setEnabled(True)

            total = max(self.splitter.height(), sum(self.splitter.sizes()), 600)
            target_log = min(max(self._last_log_height, 140), max(180, total // 2))
            self.splitter.setSizes([max(200, total - target_log), target_log])

        self._log_panel.updateGeometry()
        self.splitter.updateGeometry()

    def _toggle_log_panel(self) -> None:
        self._apply_log_panel_state(not self._log_collapsed)

    def _copy_logs(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        text = self.log_output.toPlainText()
        clipboard.setText(text)
        self.last_log_label.setText(
            "Log copiado al portapapeles" if text.strip() else "Log vacío copiado al portapapeles"
        )

    def _clear_logs(self) -> None:
        self.log_output.clear()
        self.last_log_label.setText("Registro limpio")

    # ------------------------------------------------------------------
    # Construcción dinámica del catálogo desde config.json
    # ------------------------------------------------------------------

    def _clear_sidebar_items(self) -> None:
        while self._sidebar_layout.count():
            item = self._sidebar_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._nav_buttons.clear()
        self._network_nav_btn = None
        self._network_submenu = None
        self._network_sub_buttons.clear()

    def _rebuild_catalog_views(self) -> None:
        previous_row = self._last_selected_row
        was_net_expanded = self._network_submenu_expanded
        prev_subpage = self._network_subpage_index
        self.stack.setUpdatesEnabled(False)
        try:
            if self._network_view is not None:
                self._network_view.shutdown()
                self._network_view = None
            self._network_page_index = -1

            self._clear_sidebar_items()

            while self.stack.count():
                widget = self.stack.widget(0)
                self.stack.removeWidget(widget)
                widget.deleteLater()

            self._dotnet_rows.clear()
            self._creds_rows.clear()
            self._item_rows_by_id.clear()
            self._search_rows_index.clear()
            self._category_titles.clear()

            search_scroll, search_container, search_layout = self._create_scroll_container()
            self._search_page_scroll = search_scroll
            self._search_empty_label = QLabel(
                "No se encontraron herramientas que coincidan con la búsqueda.",
                search_container,
            )
            self._search_empty_label.setObjectName("LastLogEvent")
            self._search_empty_label.setVisible(False)
            search_layout.addWidget(self._search_empty_label)

            for idx, menu_item in enumerate(self.config.menus):
                title = str(menu_item["title"])

                nav_btn = QPushButton(title, self.sidebar_panel)
                nav_btn.setObjectName("NavButton")
                nav_btn.setCheckable(True)
                nav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                nav_btn.clicked.connect(lambda _c=False, i=idx: self._on_nav_clicked(i))
                self._sidebar_layout.addWidget(nav_btn)
                self._nav_buttons.append(nav_btn)
                self._category_titles.append(title)

                page = self._build_menu_page(
                    title,
                    menu_item.get("subgroups", []),
                    search_container,
                    search_layout,
                )
                self.stack.addWidget(page)

            # Vista dedicada integrada de Gestor de Redes con submenú desplegable
            net_idx = len(self._nav_buttons)
            net_btn = QPushButton("Redes ▸", self.sidebar_panel)
            net_btn.setObjectName("NavButton")
            net_btn.setCheckable(True)
            net_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            net_btn.clicked.connect(lambda _c=False, i=net_idx: self._on_nav_clicked(i))
            self._sidebar_layout.addWidget(net_btn)
            self._nav_buttons.append(net_btn)
            self._network_nav_btn = net_btn
            self._category_titles.append("Redes")

            submenu = QWidget(self.sidebar_panel)
            submenu_layout = QVBoxLayout(submenu)
            submenu_layout.setContentsMargins(0, 2, 0, 2)
            submenu_layout.setSpacing(2)
            for sub_idx, sub_title in enumerate(self._NETWORK_SUBPAGES):
                sub_btn = QPushButton(sub_title, submenu)
                sub_btn.setObjectName("SubNavButton")
                sub_btn.setCheckable(True)
                sub_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                sub_btn.clicked.connect(lambda _c=False, si=sub_idx: self._on_network_subnav_clicked(si))
                submenu_layout.addWidget(sub_btn)
                self._network_sub_buttons.append(sub_btn)
            submenu.setVisible(False)
            self._sidebar_layout.addWidget(submenu)
            self._network_submenu = submenu

            self._sidebar_layout.addStretch(1)

            internet_probe = str(self.config.app.get("internet_probe_host", "1.1.1.1")).strip() or "1.1.1.1"
            vpn_endpoints = self.config.get_vpn_endpoints()
            backup_ep = vpn_endpoints.get("forticlient_backup", {})
            backup_hint = (
                f"Probar {backup_ep['name']}: {backup_ep.get('host') or backup_ep.get('ip')}"
                if backup_ep
                else ""
            )
            self._network_view = NetworkManagerView(
                log_callback=self.append_log,
                on_network_changed=self.check_servers_now,
                vpn_endpoints=vpn_endpoints,
                vpn_diagnostic_fn=lambda ep, log, probe=internet_probe, bhint=backup_hint: (
                    system_tasks.diagnose_vpn_endpoint(
                        ep,
                        internet_probe_host=probe,
                        backup_hint=bhint if ep.get("key") == "forticlient_primary" else "",
                        log=log,
                    )
                ),
                parent=self.stack,
            )
            self.stack.addWidget(self._network_view)
            self._network_page_index = self.stack.indexOf(self._network_view)

            search_layout.addStretch()
            self.stack.addWidget(self._search_page_scroll)

            if self._nav_buttons:
                target_row = previous_row if 0 <= previous_row < len(self._nav_buttons) else 0
                if target_row == self._network_page_index:
                    self._set_network_submenu_expanded(was_net_expanded)
                    self._on_network_subnav_clicked(prev_subpage)
                else:
                    self._set_network_submenu_expanded(False)
                    self._on_nav_clicked(target_row)
        finally:
            self.stack.setUpdatesEnabled(True)

        self._refresh_dotnet_badge()
        self._refresh_creds_badge()
        self._apply_search_filter()

    def _create_scroll_container(self) -> tuple[QScrollArea, QWidget, QVBoxLayout]:
        scroll = QScrollArea(self.stack)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget(scroll)
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 10, 18, 16)
        layout.setSpacing(6)
        scroll.setWidget(container)
        return scroll, container, layout

    def _build_menu_page(
        self,
        category_title: str,
        subgroups: list[dict[str, Any]],
        search_container: QWidget,
        search_layout: QVBoxLayout,
    ) -> QScrollArea:
        scroll, container, layout = self._create_scroll_container()

        for subgroup in subgroups:
            sub_title = str(subgroup.get("title", "")).strip()
            items = subgroup.get("items", [])
            visible_rows: list[ActionRow] = []

            for item in items:
                if self._should_hide_item(item):
                    continue
                row = self._build_item_row(item, parent=container)
                visible_rows.append(row)

                # Pre-crear fila de búsqueda fija con parent explícito para evitar popups o parpadeo
                search_row = self._build_item_row(
                    item,
                    override_badge=category_title,
                    parent=search_container,
                )
                search_row.setVisible(False)
                search_layout.addWidget(search_row)
                blob = (
                    f"{item.get('title', '')} "
                    f"{item.get('subtitle', '')} "
                    f"{category_title} {sub_title}"
                ).lower()
                self._search_rows_index.append((blob, search_row))

            if visible_rows:
                if sub_title:
                    sub_lbl = QLabel(sub_title, container)
                    sub_lbl.setObjectName("SubgroupTitle")
                    layout.addWidget(sub_lbl)
                for row in visible_rows:
                    layout.addWidget(row)

        layout.addStretch()
        return scroll

    @staticmethod
    def _should_hide_item(item: dict[str, Any]) -> bool:
        if not item.get("hide_if_empty", False):
            return False
        actions = item.get("actions", [])
        if not actions:
            return True
        path_types = {"exe", "msi", "iso", "ps1", "reg"}
        for act in actions:
            act_type = str(act.get("type", "")).lower()
            if act_type in path_types and not str(act.get("path", "")).strip():
                return True
            if act_type == "copy" and not str(act.get("source", "")).strip():
                return True
        return False

    def _build_item_row(
        self,
        item: dict[str, Any],
        override_badge: str = "",
        parent: QWidget | None = None,
    ) -> ActionRow:
        title = str(item["title"])
        subtitle = str(item.get("subtitle", "")).strip()
        item_id = str(item.get("id", ""))
        actions: list[dict[str, Any]] = list(item.get("actions", []))

        specs: list[ActionWidgetSpec] = []
        for act in actions:
            label = str(act["label"])
            style = str(act.get("style", ""))
            tooltip = self._resolve_action_tooltip(act)
            handler = self._make_action_handler(title, act)
            specs.append((label, style, tooltip, handler))

        if not specs:
            specs.append((
                "Abrir",
                "PrimaryButton",
                "",
                lambda t=title: QMessageBox.information(self, t, "Sin acciones configuradas."),
            ))

        primary_idx = next(
            (idx for idx, (_lbl, style, _tip, _fn) in enumerate(specs) if style == "PrimaryButton"),
            0,
        )
        primary_action = specs[primary_idx]
        secondary_actions = [spec for idx, spec in enumerate(specs) if idx != primary_idx]

        badge_text = override_badge or str(item.get("badge", ""))
        badge_style = "RowBadgeMuted" if override_badge else str(item.get("badge_style", "RowBadgeMuted"))

        row = ActionRow(
            title=title,
            primary_action=primary_action,
            secondary_actions=secondary_actions,
            subtitle=subtitle,
            badge_text=badge_text,
            badge_style=badge_style,
            parent=parent,
        )

        if not override_badge:
            if item_id:
                self._item_rows_by_id.setdefault(item_id, []).append(row)
            status_source = str(item.get("status_source", ""))
            if status_source == "dotnet35":
                self._dotnet_rows.append(row)
            elif status_source == "credentials_enc":
                self._creds_rows.append(row)

        return row

    def _resolve_action_tooltip(self, act: dict[str, Any]) -> str:
        explicit = str(act.get("tooltip", "")).strip()
        if explicit:
            return explicit

        act_type = str(act.get("type", "")).lower()
        if act_type in {"exe", "msi", "iso", "ps1", "reg", "explorer", "open", "bat"}:
            return str(act.get("path", ""))
        if act_type == "copy":
            return f"{act.get('source', '')} -> {act.get('dest', '')}"
        if act_type == "url":
            url_key = str(act.get("url_key", "")).strip()
            if url_key:
                try:
                    return str(self.config.get_url_info(url_key)["url"])
                except ConfigError:
                    return ""
            return str(act.get("url", ""))
        return ""

    def _make_action_handler(self, item_title: str, act: dict[str, Any]) -> ActionCallback:
        handler = self._build_raw_action_handler(item_title, act)
        confirm_msg = str(act.get("confirm", "")).strip()
        if not confirm_msg:
            return handler

        def _confirmed_handler(
            cb: ActionCallback = handler,
            title: str = item_title,
            msg: str = confirm_msg,
        ) -> None:
            reply = QMessageBox.question(
                self,
                title,
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                cb()

        return _confirmed_handler

    def _build_raw_action_handler(self, item_title: str, act: dict[str, Any]) -> ActionCallback:
        act_type = str(act.get("type", "")).lower()
        act_label = str(act.get("label", item_title))
        full_label = f"{item_title} ({act_label})"
        refresh_net = bool(act.get("refresh_network", False))
        on_ok = (lambda _m: self.check_servers_now()) if refresh_net else None

        if act_type == "exe":
            path = str(act.get("path", ""))
            args = list(act.get("args", []))
            return lambda p=path, a=args, lbl=full_label: self._run_task(
                lbl,
                lambda cfg, log: system_tasks.run_generic_exe(p, lbl, a or None, log, config=cfg),
            )

        if act_type == "msi":
            path = str(act.get("path", ""))
            args = list(act.get("args", []))
            return lambda p=path, a=args, lbl=full_label: self._run_task(
                lbl,
                lambda cfg, log: system_tasks.run_generic_msi(p, lbl, a or None, log, config=cfg),
            )

        if act_type == "iso":
            path = str(act.get("path", ""))
            setup_rel = str(act.get("setup_rel", "Setup.exe"))
            return lambda p=path, s=setup_rel, t=item_title: self._mount_and_install(p, s, t)

        if act_type == "ps1":
            path = str(act.get("path", ""))
            args = list(act.get("args", []))
            return lambda p=path, a=args, lbl=full_label: self._run_task(
                lbl,
                lambda cfg, log: system_tasks.run_generic_ps1(p, lbl, a or None, log, config=cfg),
            )

        if act_type == "reg":
            path = str(act.get("path", ""))
            return lambda p=path, lbl=full_label: self._run_task(
                lbl,
                lambda cfg, log: system_tasks.run_generic_reg(p, lbl, log, config=cfg),
            )

        if act_type == "explorer":
            path = str(act.get("path", ""))
            select = bool(act.get("select", False))
            return lambda p=path, sel=select, lbl=full_label: self._run_task(
                lbl,
                lambda cfg, log: system_tasks.run_generic_explorer(
                    p, lbl, select=sel, log=log, config=cfg
                ),
            )

        if act_type == "open":
            path = str(act.get("path", ""))
            return lambda p=path, lbl=full_label: self._run_task(
                lbl,
                lambda cfg, log: system_tasks.run_generic_open(p, lbl, log=log, config=cfg),
            )

        if act_type == "bat":
            path = str(act.get("path", ""))
            return lambda p=path, lbl=full_label: self._run_task(
                lbl,
                lambda cfg, log: system_tasks.run_generic_bat(p, lbl, log=log, config=cfg),
            )

        if act_type == "copy":
            src = str(act.get("source", ""))
            dst = str(act.get("dest", ""))
            return lambda s=src, d=dst, lbl=full_label: self._run_task(
                lbl,
                lambda cfg, log: system_tasks.copy_generic_item(cfg, s, d, lbl, log),
            )

        if act_type == "url":
            url_key = str(act.get("url_key", "")).strip()
            direct_url = str(act.get("url", "")).strip()
            direct_filename = str(act.get("filename", "")).strip()
            import_reg = bool(act.get("import_embedded_reg", False))
            install_msi = bool(act.get("install_embedded_msi", False))
            return lambda uk=url_key, du=direct_url, df=direct_filename, t=item_title, ir=import_reg, im=install_msi: (
                self._start_download(
                    url_key=uk,
                    label=t,
                    import_embedded_reg=ir,
                    install_embedded_msi=im,
                    direct_url=du,
                    direct_filename=df,
                )
            )

        if act_type == "task":
            task_name = str(act.get("task", ""))
            if task_name == "fox_configure_workstation":
                return self._run_sistema_contable_combo
            if task_name == "copy_eidico_prueba":
                return self._start_copy_eidico_prueba
            if task_name == "extract_produccion_zip":
                return self._start_extract_produccion_zip
            if task_name == "open_credentials_dialog":
                return self._open_credentials_dialog
            if task_name == "open_printer_dialog":
                return self._open_printer_dialog
            if task_name == "open_m365_sanitizer_dialog":
                return self._open_m365_sanitizer_dialog
            if task_name == "open_create_local_user_dialog":
                return self._open_create_local_user_dialog
            if task_name == "open_hardware_diagnostics_dialog":
                return self._open_hardware_diagnostics_dialog
            if task_name == "open_inventory_dialog":
                return self._open_inventory_dialog
            if task_name == "open_network_manager_view":
                return self._open_network_manager_view
            if task_name == "refresh_dotnet35_status":
                return self._refresh_dotnet_badge

            fn = (
                system_tasks.TASK_REGISTRY.get(task_name)
                or utilities_tasks.UTILITIES_TASK_REGISTRY.get(task_name)
            )
            if fn is not None:
                return lambda f=fn, lbl=full_label, cb=on_ok: self._run_task(lbl, f, on_success=cb)

        return lambda lbl=full_label, t=act_type: QMessageBox.warning(
            self,
            "Acción no soportada",
            f"No se pudo resolver la acción '{lbl}' (tipo: '{t}').",
        )

    # ------------------------------------------------------------------
    # Buscador sin parpadeo (debounce 150ms) y recarga en caliente
    # ------------------------------------------------------------------

    def _set_network_submenu_expanded(self, expanded: bool) -> None:
        self._network_submenu_expanded = expanded
        if self._network_submenu is not None:
            self._network_submenu.setVisible(expanded)
        if self._network_nav_btn is not None:
            self._network_nav_btn.setText("Redes ▾" if expanded else "Redes ▸")

    def _sync_nav_checked(self, active_idx: int, active_sub_idx: int | None = None) -> None:
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == active_idx)
        if self._network_nav_btn is not None:
            submenu_active = (
                active_idx == self._network_page_index
                and self._network_submenu_expanded
                and active_sub_idx is not None
            )
            self._network_nav_btn.setProperty("submenuActive", submenu_active)
            style = self._network_nav_btn.style()
            if style is not None:
                style.unpolish(self._network_nav_btn)
                style.polish(self._network_nav_btn)
        for j, sub_btn in enumerate(self._network_sub_buttons):
            sub_btn.setChecked(active_sub_idx is not None and j == active_sub_idx)

    def _on_nav_clicked(self, row: int) -> None:
        if row < 0 or row >= len(self._category_titles):
            return
        if row == self._network_page_index:
            next_expanded = not self._network_submenu_expanded
            self._set_network_submenu_expanded(next_expanded)
            if next_expanded:
                self._on_network_subnav_clicked(0)
            else:
                self._sync_nav_checked(self._network_page_index, self._network_subpage_index)
                self._last_selected_row = row
                self._activate_stack_index(row)
                sub_title = self._NETWORK_SUBPAGES[self._network_subpage_index]
                self.section_header_label.setText(f"Redes — {sub_title}")
            return

        self._last_selected_row = row
        self._search_timer.stop()
        if self.search_input.text():
            self.search_input.blockSignals(True)
            self.search_input.clear()
            self.search_input.blockSignals(False)
        if self._network_view is not None:
            self._network_view.set_search_filter("")
        self._sync_nav_checked(row, None)
        self._activate_stack_index(row)
        self.section_header_label.setText(self._category_titles[row])

    def _on_network_subnav_clicked(self, sub_idx: int) -> None:
        if sub_idx < 0 or sub_idx >= len(self._NETWORK_SUBPAGES):
            sub_idx = 0
        was_other_category = self._last_selected_row != self._network_page_index
        self._last_selected_row = self._network_page_index
        self._network_subpage_index = sub_idx

        if was_other_category and self.search_input.text():
            self.search_input.blockSignals(True)
            self.search_input.clear()
            self.search_input.blockSignals(False)
            if self._network_view is not None:
                self._network_view.set_search_filter("")

        self._set_network_submenu_expanded(True)
        self._sync_nav_checked(self._network_page_index, sub_idx)
        self._activate_stack_index(self._network_page_index)
        if self._network_view is not None:
            self._network_view.ensure_initialized()
            self._network_view.set_subpage(sub_idx)
        sub_title = self._NETWORK_SUBPAGES[sub_idx]
        if self.search_input.text().strip():
            self._apply_search_filter()
        else:
            self.section_header_label.setText(f"Redes — {sub_title}")

    def _activate_stack_index(self, index: int) -> None:
        """Actualiza QSizePolicy del QStackedWidget para no heredar altura de otras categorías."""
        for i in range(self.stack.count()):
            page = self.stack.widget(i)
            if page is None:
                continue
            if i == index:
                page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            else:
                page.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
            page.updateGeometry()
        self.stack.setCurrentIndex(index)
        self.stack.updateGeometry()

    def _on_search_text_edited(self, _text: str) -> None:
        self._search_timer.start()

    def _apply_search_filter(self) -> None:
        raw_text = self.search_input.text().strip()
        query = raw_text.lower()

        self.stack.setUpdatesEnabled(False)
        try:
            if (
                self._last_selected_row == self._network_page_index
                and self._network_view is not None
            ):
                matches = self._network_view.set_search_filter(query)
                self._activate_stack_index(self._network_page_index)
                if query:
                    self.section_header_label.setText(f'Redes — Filtro: "{raw_text}" ({matches})')
                else:
                    self.section_header_label.setText(self._category_titles[self._last_selected_row])
                return

            if not query:
                if 0 <= self._last_selected_row < len(self._category_titles):
                    self._activate_stack_index(self._last_selected_row)
                    self.section_header_label.setText(self._category_titles[self._last_selected_row])
                return

            matches_count = 0
            for blob, row in self._search_rows_index:
                matched = query in blob
                row.setVisible(matched)
                if matched:
                    matches_count += 1

            if self._search_empty_label is not None:
                self._search_empty_label.setVisible(matches_count == 0)

            self.section_header_label.setText(f'Búsqueda: "{raw_text}" ({matches_count})')
            self._activate_stack_index(self.stack.indexOf(self._search_page_scroll))
        finally:
            self.stack.setUpdatesEnabled(True)

    def _reload_config(self) -> None:
        try:
            new_cfg = AppConfig.load()
        except ConfigError as exc:
            QMessageBox.warning(self, "Error al recargar config.json", str(exc))
            self.append_log(f"[ERROR] Falló recarga de config.json: {exc}")
            return

        self.config = new_cfg
        self._sync_header_metadata()
        interval = int(self.config.app.get("server_check_interval_ms", 15000))
        if hasattr(self, "_server_timer"):
            self._server_timer.setInterval(interval)
        self._rebuild_catalog_views()
        self.check_servers_now()
        self.check_installed_software_now()
        self.append_log(f"[OK] Configuración recargada en caliente: {self.config.source_path}")

    # ------------------------------------------------------------------
    # Monitoreo de red, detección de software instalado y workers
    # ------------------------------------------------------------------

    def _setup_server_monitor(self) -> None:
        interval = int(self.config.app.get("server_check_interval_ms", 15000))
        self._server_timer = QTimer(self)
        self._server_timer.setInterval(interval)
        self._server_timer.timeout.connect(self.check_servers_now)
        self._server_timer.start()

    def check_servers_now(self) -> None:
        if self._server_check_worker and self._server_check_worker.isRunning():
            return
        self.refresh_net_btn.setEnabled(False)
        worker = ServerCheckWorker(self.config.get_servers())
        worker.status_ready.connect(self._on_server_status)
        worker.finished.connect(lambda: self.refresh_net_btn.setEnabled(True))
        self._server_check_worker = worker
        worker.start()

    def _on_server_status(self, results: dict[str, bool]) -> None:
        servers = self.config.get_servers()
        for server_id, online in results.items():
            badge = self._server_badges.get(server_id)
            if not badge:
                continue
            host = servers[server_id]["host"]
            if online:
                badge.setText(f"● {host} OK")
                badge.setProperty("statusState", "online")
            else:
                badge.setText(f"● {host} Off")
                badge.setProperty("statusState", "offline")
            badge.style().unpolish(badge)
            badge.style().polish(badge)
        self._refresh_creds_badge()

    def check_installed_software_now(self) -> None:
        if self._install_check_worker and self._install_check_worker.isRunning():
            return
        worker = InstalledSoftwareCheckWorker(self.config)
        worker.status_ready.connect(self._on_installed_software_status)
        self._install_check_worker = worker
        worker.start()

    def _on_installed_software_status(self, results: dict[str, dict[str, Any]]) -> None:
        for item_id, info in results.items():
            if not isinstance(info, dict) or not info.get("installed"):
                continue
            ver = str(info.get("version", "")).strip()
            tooltip = f"Instalado (v{ver})" if ver else "Instalado en el equipo"
            for row in self._item_rows_by_id.get(item_id, []):
                row.set_badge("Instalado", "RowBadgeOk", tooltip=tooltip)

    def _relaunch_as_admin(self) -> None:
        if os.name != "nt":
            return
        extra_args = [arg for arg in sys.argv[1:] if arg != "--no-elevate"]
        if getattr(sys, "frozen", False):
            executable = sys.executable
            params = subprocess.list2cmdline(extra_args)
        else:
            executable = sys.executable
            entry_script = str(self.config.source_path.parent / "main.py")
            params = subprocess.list2cmdline([entry_script, *extra_args])

        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            executable,
            params,
            None,
            1,
        )
        if int(result) > 32:
            self.close()
        else:
            self.append_log("[ADVERTENCIA] No se completó la elevación UAC.")

    def _refresh_dotnet_badge(self) -> None:
        if not self._dotnet_rows:
            return
        installed = system_tasks.check_dotnet35_installed(self.config)
        for row in self._dotnet_rows:
            if installed:
                row.set_badge("Instalado", "RowBadgeOk")
            else:
                row.set_badge("No detectado", "RowBadgeWarn")

    def _refresh_creds_badge(self) -> None:
        if not self._creds_rows:
            return
        enc_path = self.config.resolve_credentials_enc_path()
        for row in self._creds_rows:
            if enc_path is not None:
                row.set_badge(
                    "Almacén Cifrado",
                    "RowBadgeOk",
                    tooltip=f"Ruta resuelta: {enc_path}",
                )
            else:
                row.set_badge(
                    "Modo manual",
                    "RowBadgeMuted",
                    tooltip="No se detectó credentials.enc en rutas locales, paquete interno ni UNC",
                )

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
            self.check_installed_software_now()

        worker.finished.connect(_cleanup)

    def _run_task(
        self,
        label: str,
        fn: Callable[..., str],
        on_success: Callable[[str], None] | None = None,
    ) -> None:
        if not callable(fn):
            self._handle_task_error(label, f"Manejador de tarea inválido: {fn!r}")
            return
        worker = TaskWorker(fn, self.config)
        worker.log_message.connect(self.append_log)
        worker.finished_success.connect(
            lambda msg: self._handle_task_success(label, msg, on_success)
        )
        worker.failed.connect(lambda err: self._handle_task_error(label, err))
        self._track_worker(worker, label)
        worker.start()

    def _handle_task_success(
        self,
        label: str,
        msg: str,
        on_success: Callable[[str], None] | None = None,
    ) -> None:
        self.append_log(f"[COMPLETADO] {label}: {msg}")
        if callable(on_success):
            on_success(msg)

    def _handle_task_error(self, label: str, err: str) -> None:
        QMessageBox.warning(self, f"Error en {label}", err)

    def _start_download(
        self,
        url_key: str,
        label: str,
        import_embedded_reg: bool = False,
        install_embedded_msi: bool = False,
        direct_url: str = "",
        direct_filename: str = "",
    ) -> None:
        if url_key:
            info = self.config.get_url_info(url_key)
        else:
            info = {"url": direct_url, "filename": direct_filename, "open_after_download": True}

        dest_dir = self.config.get_downloads_dir()
        chunk_size = int(self.config.app.get("copy_chunk_size_bytes", 65536))
        embedded_msi = info.get("embedded_msi_name") if install_embedded_msi else None
        embedded_reg = info.get("embedded_reg_name") if import_embedded_reg else None

        dialog = ProgressDialog(f"Descargando {label}", f"Descargando {info['filename']}...", self)
        worker = DownloadWorker(
            url=str(info["url"]),
            dest_dir=dest_dir,
            filename=str(info["filename"]),
            chunk_size=chunk_size,
            open_after=bool(info.get("open_after_download", True)),
            embedded_msi_name=embedded_msi,
            embedded_reg_name=embedded_reg,
        )
        worker.progress_changed.connect(dialog.update_progress)
        worker.log_message.connect(self.append_log)
        dialog.cancel_requested.connect(worker.cancel)
        worker.finished_success.connect(lambda _p: dialog.accept())
        worker.failed.connect(lambda err: self._on_transfer_failed(dialog, label, err))

        self._track_worker(worker, f"Descarga {label}")
        worker.start()
        dialog.exec()

    def _start_copy_eidico_prueba(
        self,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        src = str(self.config.get_unc("eidico", "eidico_prueba_exe"))
        dst = self.config.get_local_path("eidico_exe_dest")
        chunk_size = int(self.config.app.get("copy_chunk_size_bytes", 65536))

        dialog = ProgressDialog("Copiando EidicoPrueba.EXE", f"Transfiriendo hacia {dst}...", self)
        worker = FileCopyWorker(
            source=src,
            destination=dst,
            chunk_size=chunk_size,
            allowed_hosts=self.config.get_allowed_unc_hosts(),
        )
        worker.progress_changed.connect(dialog.update_progress)
        worker.log_message.connect(self.append_log)
        dialog.cancel_requested.connect(worker.cancel)
        worker.finished_success.connect(lambda _p: dialog.accept())
        worker.failed.connect(lambda err: self._on_transfer_failed(dialog, "Copia EidicoPrueba.EXE", err))

        self._track_worker(worker, "Copia EidicoPrueba.EXE")
        worker.start()
        result = dialog.exec()
        if result == ProgressDialog.DialogCode.Accepted and callable(on_finished):
            on_finished()

    def _start_extract_produccion_zip(self) -> None:
        zip_src = str(self.config.get_unc("eidico", "produccion_zip"))
        dest_dir = self.config.get_local_path("eidico_dir")

        dialog = ProgressDialog("Extrayendo Produccion.zip", f"Descomprimiendo en {dest_dir}...", self)
        worker = ZipExtractWorker(
            zip_path=zip_src,
            dest_dir=dest_dir,
            allowed_hosts=self.config.get_allowed_unc_hosts(),
        )
        worker.progress_changed.connect(dialog.update_progress)
        worker.log_message.connect(self.append_log)
        dialog.cancel_requested.connect(worker.cancel)
        worker.finished_success.connect(lambda _p: dialog.accept())
        worker.failed.connect(lambda err: self._on_transfer_failed(dialog, "Extraer Produccion.zip", err))

        self._track_worker(worker, "Extracción Produccion.zip")
        worker.start()
        dialog.exec()

    def _on_transfer_failed(self, dialog: ProgressDialog, label: str, err: str) -> None:
        dialog.reject()
        if "cancelada por el usuario" not in err.lower():
            QMessageBox.warning(self, f"Error en {label}", err)

    def _run_sistema_contable_combo(self) -> None:
        def _steps_3_4_5(config: AppConfig, log: Callable[[str], None]) -> str:
            system_tasks.fix_eidico_shortcut(config, log)
            system_tasks.set_sol_sistemas_permissions(config, log)
            system_tasks.copy_eidico_vbs(config, log)
            return "Pasos 3, 4 y 5 completados."

        self._run_task(
            "Configuración Sistema Contable (3-4-5)",
            _steps_3_4_5,
            on_success=lambda _m: self._start_copy_eidico_prueba(
                on_finished=lambda: self.append_log(
                    "[OK] Flujo completo de Sistema Contable (pasos 3, 4, 5 y 6) finalizado."
                )
            ),
        )

    def _mount_and_install(self, image_path: str, setup_rel: str, label: str) -> None:
        worker = IsoMountWorker(
            image_path=image_path,
            setup_relative_path=setup_rel,
            label=label,
            allowed_hosts=self.config.get_allowed_unc_hosts(),
        )
        worker.log_message.connect(self.append_log)
        worker.finished_success.connect(lambda msg: self.append_log(f"[COMPLETADO] {msg}"))
        worker.failed.connect(lambda err: QMessageBox.warning(self, label, err))
        self._track_worker(worker, f"Montaje {label}")
        worker.start()

    def _open_credentials_dialog(self) -> None:
        dialog = CredentialDialog(self.config, self, log_callback=self.append_log)
        if dialog.exec() != CredentialDialog.DialogCode.Accepted:
            return

        entries = dialog.get_entries()

        def _apply_all(config: AppConfig, log: Callable[[str], None]) -> str:
            for item in entries:
                system_tasks.register_server_credential(
                    config=config,
                    server_key=item["server_key"],
                    username=item["username"],
                    password=item["password"],
                    create_shortcut=item["create_shortcut"],
                    log=log,
                )
            return f"Se registraron {len(entries)} credencial(es) correctamente."

        self._run_task("Registro de Credenciales", _apply_all)

    def _open_printer_dialog(self) -> None:
        dialog = PrinterInstallDialog(self.config, self)
        if dialog.exec() != PrinterInstallDialog.DialogCode.Accepted:
            return

        selected = dialog.get_selected_printers()
        self._run_task(
            f"Instalación de Impresoras ({len(selected)})",
            lambda cfg, log: system_tasks.install_network_printers(cfg, selected, log),
        )

    def _open_m365_sanitizer_dialog(self) -> None:
        dialog = M365SanitizerDialog(self)
        if dialog.exec() != M365SanitizerDialog.DialogCode.Accepted:
            return

        opts = dialog.get_options()
        action = opts.get("action", "diagnostics")
        label = str(opts.get("label", "Sanitizer O365"))
        what_if = bool(opts.get("what_if", True))
        license_mode = str(opts.get("license_mode", "Selectivo"))

        if action == "diagnostics":
            self._run_task(label, m365_wrapper.run_office_diagnostics)
        elif action == "stop_apps":
            self._run_task(
                f"{label} ({'Simulación' if what_if else 'Real'})",
                lambda cfg, log: m365_wrapper.run_stop_office_processes(
                    cfg, what_if=what_if, log=log
                ),
            )
        elif action == "identity":
            self._run_task(
                f"{label} ({'Simulación' if what_if else 'Real'})",
                lambda cfg, log: m365_wrapper.run_clear_identity_cache(
                    cfg, what_if=what_if, log=log
                ),
            )
        elif action == "licenses":
            self._run_task(
                f"{label} ({'Simulación' if what_if else 'Real'})",
                lambda cfg, log: m365_wrapper.run_reset_office_licenses(
                    cfg, mode=license_mode, what_if=what_if, log=log
                ),
            )
        elif action == "uninstall_selective":
            product_ids = list(opts.get("product_ids", []))
            self._run_task(
                f"{label} ({'Simulación' if what_if else 'Real'})",
                lambda cfg, log: m365_wrapper.run_uninstall_selected_office_products(
                    cfg, product_ids=product_ids, what_if=what_if, log=log
                ),
            )
        elif action == "uninstall":
            self._run_task(
                f"{label} ({'Simulación' if what_if else 'Real'})",
                lambda cfg, log: m365_wrapper.run_uninstall_office_products(
                    cfg, what_if=what_if, log=log
                ),
            )

    def _open_create_local_user_dialog(self) -> None:
        dialog = CreateLocalUserDialog(self)
        if dialog.exec() != CreateLocalUserDialog.DialogCode.Accepted:
            return

        data = dialog.get_user_data()
        username = str(data["username"])
        self._run_task(
            f"Crear Usuario Local ({username})",
            lambda cfg, log: utilities_tasks.task_create_local_user(
                cfg,
                username=username,
                password=str(data["password"]),
                full_name=str(data["full_name"]),
                add_to_admins=bool(data["add_to_admins"]),
                log=log,
            ),
        )

    def _open_hardware_diagnostics_dialog(self) -> None:
        dialog = HardwareDiagnosticsDialog(log_callback=self.append_log, parent=self)
        dialog.exec()

    def _open_inventory_dialog(self) -> None:
        dialog = InventoryDialog(self.config, log_callback=self.append_log, parent=self)
        dialog.exec()

    def _open_network_manager_view(self) -> None:
        if 0 <= self._network_page_index < len(self._nav_buttons):
            if self.search_input.text():
                self.search_input.clear()
            self._set_network_submenu_expanded(True)
            self._on_network_subnav_clicked(0)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._search_timer.stop()
        if hasattr(self, "_server_timer"):
            self._server_timer.stop()
        if self._network_view is not None:
            self._network_view.shutdown()
        if self._server_check_worker and self._server_check_worker.isRunning():
            self._server_check_worker.wait(1500)
        if self._install_check_worker and self._install_check_worker.isRunning():
            self._install_check_worker.wait(1500)
        for worker in list(self._active_workers):
            if worker.isRunning():
                if hasattr(worker, "cancel"):
                    getattr(worker, "cancel")()
                worker.wait(1500)
        system_tasks.cleanup_registered_temp_dirs(self.append_log)
        super().closeEvent(event)
