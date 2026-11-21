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


class MainWindow(QMainWindow):
    """Interfaz principal oscura monocromática para soporte técnico de Windows."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self._active_worker: TaskWorker | None = None
        self._setup_ui()
        self._refresh_hibernation_status()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_tweaks_tab(), "Energía y Cuentas")
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

        self.btn_hiber_off.clicked.connect(lambda: self._run_task(set_hibernation, False))
        self.btn_hiber_on.clicked.connect(lambda: self._run_task(set_hibernation, True))
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

    def _append_log(self, ok: bool, message: str) -> None:
        prefix = "[OK]" if ok else "[ERROR]"
        self.log_output.appendPlainText(f"{prefix} {message}")

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.btn_hiber_off.setEnabled(enabled)
        self.btn_hiber_on.setEnabled(enabled)
        self.btn_hiber_refresh.setEnabled(enabled)
        self.btn_create_user.setEnabled(enabled)

    def _refresh_hibernation_status(self) -> None:
        _, msg = get_hibernation_status()
        self.hiber_status_label.setText(msg)

    def _handle_create_user(self) -> None:
        username = self.input_username.text()
        password = self.input_password.text()
        fullname = self.input_fullname.text()
        self._run_task(create_local_user, username, password, fullname)

    def _run_task(self, fn, *args) -> None:
        if self._active_worker is not None and self._active_worker.isRunning():
            return
        self._set_controls_enabled(False)
        self._active_worker = TaskWorker(fn, *args)
        self._active_worker.finished_signal.connect(self._on_task_finished)
        self._active_worker.start()

    def _on_task_finished(self, ok: bool, message: str) -> None:
        self._append_log(ok, message)
        self._refresh_hibernation_status()
        if ok:
            self.input_password.clear()
        self._set_controls_enabled(True)
