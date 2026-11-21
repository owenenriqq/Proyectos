"""Ventana principal de la aplicación Utilidades."""

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QFormLayout,
)
from PyQt6.QtCore import Qt

from config import APP_NAME, APP_VERSION, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT
from workers import TaskWorker
from core.system_tweaks import get_hibernation_status, set_hibernation, create_local_user
from core.shell_repair import (
    rebuild_icon_cache,
    get_max_cached_icons,
    set_max_cached_icons,
    reregister_appx_packages,
    flush_dns,
)


class MainWindow(QMainWindow):
    """Interfaz principal oscura monocromática para soporte técnico de Windows."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self._active_worker: TaskWorker | None = None
        self._action_buttons: list[QPushButton] = []
        self._setup_ui()
        self._refresh_hibernation_status()
        self._refresh_max_icons_status()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_tweaks_tab(), "Energía y Cuentas")
        self.tabs.addTab(self._build_shell_tab(), "Shell, Iconos y Red")
        main_layout.addWidget(self.tabs, stretch=2)

        log_group = QGroupBox("Registro de Actividad")
        log_layout = QVBoxLayout(log_group)
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)
        main_layout.addWidget(log_group, stretch=1)

    def _build_tweaks_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)

        # Tarjeta 1: Hibernación e Inicio Rápido
        power_group = QGroupBox("Hibernación e Inicio Rápido (powercfg)")
        power_layout = QVBoxLayout(power_group)

        self.hiber_status_label = QLabel("Estado: Verificando...")
        self.hiber_status_label.setObjectName("StatusLabel")
        power_layout.addWidget(self.hiber_status_label)

        btn_row = QHBoxLayout()
        self.btn_hiber_off = QPushButton("Desactivar Hibernación / Inicio Rápido")
        self.btn_hiber_on = QPushButton("Activar Hibernación")
        self.btn_hiber_refresh = QPushButton("Actualizar Estado")

        self.btn_hiber_off.clicked.connect(lambda: self._run_task(set_hibernation, "Desactivando hibernación...", False))
        self.btn_hiber_on.clicked.connect(lambda: self._run_task(set_hibernation, "Activando hibernación...", True))
        self.btn_hiber_refresh.clicked.connect(self._refresh_hibernation_status)

        btn_row.addWidget(self.btn_hiber_off)
        btn_row.addWidget(self.btn_hiber_on)
        btn_row.addWidget(self.btn_hiber_refresh)
        btn_row.addStretch()
        power_layout.addLayout(btn_row)
        layout.addWidget(power_group)

        # Tarjeta 2: Creación de Usuario Local
        user_group = QGroupBox("Crear Usuario Local (Windows)")
        user_layout = QVBoxLayout(user_group)

        form = QFormLayout()
        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("Ej: Soporte")
        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_password.setPlaceholderText("Contraseña segura")
        self.input_fullname = QLineEdit()
        self.input_fullname.setPlaceholderText("Opcional")

        form.addRow("Nombre de usuario:", self.input_username)
        form.addRow("Contraseña:", self.input_password)
        form.addRow("Nombre completo:", self.input_fullname)
        user_layout.addLayout(form)

        user_btn_row = QHBoxLayout()
        self.btn_create_user = QPushButton("Crear Usuario Local")
        self.btn_create_user.clicked.connect(self._handle_create_user)
        user_btn_row.addWidget(self.btn_create_user)
        user_btn_row.addStretch()
        user_layout.addLayout(user_btn_row)

        layout.addWidget(user_group)
        layout.addStretch()
        return tab

    def _build_shell_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        # Tarjeta 1: Caché de Iconos
        icon_group = QGroupBox("Caché de Iconos del Explorador")
        icon_layout = QHBoxLayout(icon_group)
        icon_desc = QLabel("Detiene explorer.exe, elimina IconCache.db / iconcache* y reinicia el Shell.")
        icon_desc.setObjectName("StatusLabel")
        self.btn_rebuild_icons = QPushButton("Reconstruir Caché de Iconos")
        self.btn_rebuild_icons.clicked.connect(lambda: self._run_task(rebuild_icon_cache, "Reconstruyendo caché de iconos..."))
        icon_layout.addWidget(icon_desc, stretch=1)
        icon_layout.addWidget(self.btn_rebuild_icons)
        layout.addWidget(icon_group)

        # Tarjeta 2: Registro Max Cached Icons
        reg_group = QGroupBox("Caché Máxima de Iconos en Registro (HKLM)")
        reg_layout = QVBoxLayout(reg_group)
        self.max_icons_label = QLabel("Valor actual: Verificando...")
        self.max_icons_label.setObjectName("StatusLabel")
        reg_layout.addWidget(self.max_icons_label)

        reg_btn_row = QHBoxLayout()
        self.btn_set_max_icons = QPushButton("Establecer Max Cached Icons = 4096")
        self.btn_set_max_icons.clicked.connect(lambda: self._run_task(lambda: set_max_cached_icons("4096"), "Actualizando Max Cached Icons..."))
        reg_btn_row.addWidget(self.btn_set_max_icons)
        reg_btn_row.addStretch()
        reg_layout.addLayout(reg_btn_row)
        layout.addWidget(reg_group)

        # Tarjeta 3: Paquetes AppX
        appx_group = QGroupBox("Aplicaciones Integradas (AppX / Shell)")
        appx_layout = QHBoxLayout(appx_group)
        appx_desc = QLabel("Verifica/inicia el servicio MpsSvc y re-registra los paquetes AppX.")
        appx_desc.setObjectName("StatusLabel")
        self.btn_reregister_appx = QPushButton("Re-registrar Paquetes AppX")
        self.btn_reregister_appx.clicked.connect(lambda: self._run_task(reregister_appx_packages, "Re-registrando paquetes AppX (puede demorar)..."))
        appx_layout.addWidget(appx_desc, stretch=1)
        appx_layout.addWidget(self.btn_reregister_appx)
        layout.addWidget(appx_group)

        # Tarjeta 4: Red / DNS
        dns_group = QGroupBox("Red y Resolución DNS")
        dns_layout = QHBoxLayout(dns_group)
        dns_desc = QLabel("Vacía la caché de resolución DNS del sistema (ipconfig /flushdns).")
        dns_desc.setObjectName("StatusLabel")
        self.btn_flush_dns = QPushButton("Limpiar Caché DNS")
        self.btn_flush_dns.clicked.connect(lambda: self._run_task(flush_dns, "Limpiando caché DNS..."))
        dns_layout.addWidget(dns_desc, stretch=1)
        dns_layout.addWidget(self.btn_flush_dns)
        layout.addWidget(dns_group)

        self._action_buttons.extend([
            self.btn_hiber_off,
            self.btn_hiber_on,
            self.btn_hiber_refresh,
            self.btn_create_user,
            self.btn_rebuild_icons,
            self.btn_set_max_icons,
            self.btn_reregister_appx,
            self.btn_flush_dns,
        ])

        layout.addStretch()
        return tab

    def _append_log(self, ok: bool, message: str) -> None:
        prefix = "[OK]" if ok else "[ERROR]"
        self.log_output.appendPlainText(f"{prefix} {message}")

    def _set_controls_enabled(self, enabled: bool) -> None:
        for btn in self._action_buttons:
            btn.setEnabled(enabled)

    def _refresh_hibernation_status(self) -> None:
        _, msg = get_hibernation_status()
        self.hiber_status_label.setText(msg)

    def _refresh_max_icons_status(self) -> None:
        _, msg = get_max_cached_icons()
        self.max_icons_label.setText(msg)

    def _handle_create_user(self) -> None:
        username = self.input_username.text()
        password = self.input_password.text()
        fullname = self.input_fullname.text()
        self._run_task(create_local_user, "Creando usuario local...", username, password, fullname)

    def _run_task(self, fn, status_msg: str = "", *args) -> None:
        if self._active_worker is not None and self._active_worker.isRunning():
            return
        if status_msg:
            self.log_output.appendPlainText(f"[INFO] {status_msg}")
        self._set_controls_enabled(False)
        self._active_worker = TaskWorker(fn, *args)
        self._active_worker.finished_signal.connect(self._on_task_finished)
        self._active_worker.start()

    def _on_task_finished(self, ok: bool, message: str) -> None:
        self._append_log(ok, message)
        self._refresh_hibernation_status()
        self._refresh_max_icons_status()
        if ok:
            self.input_password.clear()
        self._set_controls_enabled(True)
