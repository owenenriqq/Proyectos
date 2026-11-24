"""Ventana principal de la aplicación Utilidades."""

import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QMainWindow,
    QMessageBox,
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
    QProgressBar,
    QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent, QIcon

from config import APP_NAME, APP_VERSION, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, resolve_resource_path
from workers import TaskWorker, StreamingTaskWorker
from core.system_tweaks import get_hibernation_status, set_hibernation, create_local_user
from core.shell_repair import (
    rebuild_icon_cache,
    get_max_cached_icons,
    set_max_cached_icons,
    reregister_appx_packages,
    clean_temp_and_update_cache,
    restart_print_spooler,
)
from core.system_repair import (
    dism_scan_health,
    dism_restore_health,
    dism_component_cleanup,
    sfc_scannow,
    run_full_repair,
)
from core.diagnostics import (
    get_smart_health,
    get_fixed_partitions,
    get_battery_health,
    get_system_stability,
    export_diagnostic_report,
)


class MainWindow(QMainWindow):
    """Interfaz principal oscura monocromática para soporte técnico de Windows."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(1080, 680)
        icon_path = resolve_resource_path("assets/icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self._active_worker: TaskWorker | None = None
        self._action_buttons: list[QPushButton] = []
        self._diag_results: dict[str, str] = {}
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
        self.tabs.addTab(self._build_repair_tab(), "Reparación de Sistema")
        self.tabs.addTab(self._build_diagnostics_tab(), "Diagnóstico y Hardware")
        self.tabs.addTab(self._build_tweaks_tab(), "Energía y Cuentas")
        self.tabs.addTab(self._build_shell_tab(), "Shell y Mantenimiento")
        main_layout.addWidget(self.tabs, stretch=2)

        self.repair_progress = QProgressBar()
        self.repair_progress.setRange(0, 100)
        self.repair_progress.setValue(0)
        self.repair_progress.setVisible(False)
        main_layout.addWidget(self.repair_progress)

        log_group = QGroupBox("Registro de Actividad")
        log_layout = QVBoxLayout(log_group)

        log_header = QHBoxLayout()
        log_header.addStretch()
        self.btn_log_copy = QPushButton("Copiar")
        self.btn_log_clear = QPushButton("Limpiar")
        self.btn_log_save = QPushButton("Guardar .log")
        for btn in (self.btn_log_copy, self.btn_log_clear, self.btn_log_save):
            btn.setMinimumHeight(30)
            btn.setStyleSheet("padding: 2px 12px;")
        self.btn_log_copy.clicked.connect(self._handle_copy_log)
        self.btn_log_clear.clicked.connect(self._handle_clear_log)
        self.btn_log_save.clicked.connect(self._handle_save_log)
        log_header.addWidget(self.btn_log_copy)
        log_header.addWidget(self.btn_log_clear)
        log_header.addWidget(self.btn_log_save)
        log_layout.addLayout(log_header)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)
        main_layout.addWidget(log_group, stretch=1)

    def _build_repair_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        # Tarjeta 1: DISM ScanHealth y RestoreHealth
        dism_group = QGroupBox("Almacén de Componentes de Windows (DISM)")
        dism_layout = QVBoxLayout(dism_group)
        dism_desc = QLabel("Analiza o repara la imagen del sistema operativo sin reiniciar el equipo.")
        dism_layout.addWidget(dism_desc)

        dism_btns = QHBoxLayout()
        self.btn_dism_scan = QPushButton("DISM /ScanHealth")
        self.btn_dism_restore = QPushButton("DISM /RestoreHealth")
        self.btn_dism_cleanup = QPushButton("DISM /StartComponentCleanup")
        self.btn_dism_scan.clicked.connect(lambda: self._run_streaming_task(dism_scan_health, "Ejecutando DISM /ScanHealth..."))
        self.btn_dism_restore.clicked.connect(lambda: self._run_streaming_task(dism_restore_health, "Ejecutando DISM /RestoreHealth..."))
        self.btn_dism_cleanup.clicked.connect(lambda: self._run_streaming_task(dism_component_cleanup, "Ejecutando DISM /StartComponentCleanup..."))
        dism_btns.addWidget(self.btn_dism_scan)
        dism_btns.addWidget(self.btn_dism_restore)
        dism_btns.addWidget(self.btn_dism_cleanup)
        dism_layout.addLayout(dism_btns)
        layout.addWidget(dism_group)

        # Tarjeta 2: SFC /scannow
        sfc_group = QGroupBox("Comprobador de Archivos de Sistema (SFC)")
        sfc_layout = QVBoxLayout(sfc_group)
        sfc_desc = QLabel("Verifica y repara archivos protegidos del sistema Windows (sfc /scannow).")
        sfc_layout.addWidget(sfc_desc)
        self.btn_sfc = QPushButton("Ejecutar SFC /scannow")
        self.btn_sfc.clicked.connect(lambda: self._run_streaming_task(sfc_scannow, "Ejecutando SFC /scannow..."))
        sfc_layout.addWidget(self.btn_sfc)
        layout.addWidget(sfc_group)

        # Tarjeta 3: Reparación Completa Automática
        full_group = QGroupBox("Secuencia Guiada")
        full_layout = QVBoxLayout(full_group)
        full_desc = QLabel("Ejecuta en orden: ScanHealth -> RestoreHealth (si aplica) -> SFC /scannow -> StartComponentCleanup.")
        full_layout.addWidget(full_desc)
        self.btn_full_repair = QPushButton("Reparación Completa Automática")
        self.btn_full_repair.clicked.connect(self._handle_full_repair)
        full_layout.addWidget(self.btn_full_repair)
        layout.addWidget(full_group)

        self._action_buttons.extend([
            self.btn_dism_scan,
            self.btn_dism_restore,
            self.btn_dism_cleanup,
            self.btn_sfc,
            self.btn_full_repair,
        ])

        layout.addStretch()
        return tab

    def _build_diagnostics_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        smart_group = QGroupBox("Discos Físicos y Particiones (S.M.A.R.T.)")
        smart_layout = QVBoxLayout(smart_group)
        self.smart_label = QLabel("Sin datos. Ejecutá el diagnóstico para consultar.")
        self.smart_label.setWordWrap(True)
        smart_layout.addWidget(self.smart_label)
        layout.addWidget(smart_group)

        battery_group = QGroupBox("Salud de Batería")
        battery_layout = QHBoxLayout(battery_group)
        self.battery_label = QLabel("Sin datos. Ejecutá el diagnóstico para consultar.")
        self.battery_label.setWordWrap(True)
        self.btn_open_battery_html = QPushButton("Abrir reporte HTML")
        self.btn_open_battery_html.setEnabled(self._get_battery_report_path().exists())
        self.btn_open_battery_html.clicked.connect(self._handle_open_battery_html)
        battery_layout.addWidget(self.battery_label, stretch=1)
        battery_layout.addWidget(self.btn_open_battery_html)
        layout.addWidget(battery_group)

        stability_group = QGroupBox("Estabilidad, RAM y Eventos Críticos (BSOD)")
        stability_layout = QVBoxLayout(stability_group)
        self.stability_label = QLabel("Sin datos. Ejecutá el diagnóstico para consultar.")
        self.stability_label.setWordWrap(True)
        stability_layout.addWidget(self.stability_label)
        layout.addWidget(stability_group)

        btn_row = QHBoxLayout()
        self.btn_run_diag = QPushButton("Ejecutar Diagnóstico Completo")
        self.btn_export_diag = QPushButton("Exportar Reporte (.txt)")
        self.btn_export_diag.setEnabled(False)
        self.btn_run_diag.clicked.connect(self._handle_run_diagnostics)
        self.btn_export_diag.clicked.connect(self._handle_export_diagnostics)
        btn_row.addWidget(self.btn_run_diag)
        btn_row.addWidget(self.btn_export_diag)
        layout.addLayout(btn_row)

        self._action_buttons.append(self.btn_run_diag)
        layout.addStretch()
        return tab

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

        pass_row = QHBoxLayout()
        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_password.setPlaceholderText("Contraseña segura")
        self.btn_toggle_pass = QPushButton("Ver")
        self.btn_toggle_pass.setCheckable(True)
        self.btn_toggle_pass.setFixedWidth(72)
        self.btn_toggle_pass.toggled.connect(self._toggle_password_visibility)
        pass_row.addWidget(self.input_password, stretch=1)
        pass_row.addWidget(self.btn_toggle_pass)

        self.input_fullname = QLineEdit()
        self.input_fullname.setPlaceholderText("Opcional")

        form.addRow("Nombre de usuario:", self.input_username)
        form.addRow("Contraseña:", pass_row)
        form.addRow("Nombre completo:", self.input_fullname)
        user_layout.addLayout(form)

        self.chk_admin_group = QCheckBox("Agregar al grupo Administradores")
        user_layout.addWidget(self.chk_admin_group)

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
        self.btn_rebuild_icons.clicked.connect(self._handle_rebuild_icons)
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
        self.btn_reregister_appx.clicked.connect(self._handle_reregister_appx)
        appx_layout.addWidget(appx_desc, stretch=1)
        appx_layout.addWidget(self.btn_reregister_appx)
        layout.addWidget(appx_group)

        # Tarjeta 4: Limpieza de Temporales y Caché de Windows Update
        temp_group = QGroupBox("Limpieza de Temporales y Caché de Windows Update")
        temp_layout = QVBoxLayout(temp_group)
        temp_top = QHBoxLayout()
        temp_desc = QLabel("Limpia %TEMP% y C:\\Windows\\Temp ignorando archivos en uso.")
        temp_desc.setObjectName("StatusLabel")
        self.btn_clean_temp = QPushButton("Limpiar Temporales")
        self.btn_clean_temp.clicked.connect(self._handle_clean_temp)
        temp_top.addWidget(temp_desc, stretch=1)
        temp_top.addWidget(self.btn_clean_temp)
        temp_layout.addLayout(temp_top)

        self.chk_clean_wu = QCheckBox("Incluir caché de Windows Update (detiene wuauserv/bits y limpia SoftwareDistribution\\Download)")
        temp_layout.addWidget(self.chk_clean_wu)
        layout.addWidget(temp_group)

        # Tarjeta 5: Cola de Impresión (Spooler)
        spool_group = QGroupBox("Cola de Impresión (Spooler)")
        spool_layout = QHBoxLayout(spool_group)
        spool_desc = QLabel("Detiene Spooler, vacía trabajos atascados en PRINTERS y reinicia el servicio.")
        spool_desc.setObjectName("StatusLabel")
        self.btn_restart_spooler = QPushButton("Reiniciar Cola de Impresión")
        self.btn_restart_spooler.clicked.connect(self._handle_restart_spooler)
        spool_layout.addWidget(spool_desc, stretch=1)
        spool_layout.addWidget(self.btn_restart_spooler)
        layout.addWidget(spool_group)

        self._action_buttons.extend([
            self.btn_hiber_off,
            self.btn_hiber_on,
            self.btn_hiber_refresh,
            self.btn_create_user,
            self.btn_rebuild_icons,
            self.btn_set_max_icons,
            self.btn_reregister_appx,
            self.btn_clean_temp,
            self.btn_restart_spooler,
        ])

        layout.addStretch()
        return tab

    def _append_log(self, ok: bool, message: str) -> None:
        prefix = "[OK]" if ok else "[ERROR]"
        self.log_output.appendPlainText(f"{prefix} {message}")

    def _set_controls_enabled(self, enabled: bool) -> None:
        for btn in self._action_buttons:
            btn.setEnabled(enabled)
        self.btn_export_diag.setEnabled(enabled and bool(self._diag_results))
        self.btn_open_battery_html.setEnabled(enabled and self._get_battery_report_path().exists())

    def _get_battery_report_path(self) -> Path:
        return Path(os.environ.get("TEMP", "")) / "battery.html"

    def _confirm_action(self, title: str, text: str) -> bool:
        reply = QMessageBox.question(
            self,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def _handle_copy_log(self) -> None:
        text = self.log_output.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self._append_log(True, "Registro copiado al portapapeles.")

    def _handle_clear_log(self) -> None:
        self.log_output.clear()

    def _handle_save_log(self) -> None:
        text = self.log_output.toPlainText()
        if not text.strip():
            self._append_log(False, "No hay contenido en el registro para guardar.")
            return
        default_name = f"{os.environ.get('COMPUTERNAME', 'EQUIPO')}-Actividad.log"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Registro de Actividad",
            default_name,
            "Archivos de registro (*.log);;Archivos de texto (*.txt)",
        )
        if not path:
            return
        try:
            Path(path).write_text(text, encoding="utf-8")
            self._append_log(True, f"Registro guardado en: {path}")
        except OSError as exc:
            self._append_log(False, f"No se pudo guardar el registro: {exc}")

    def _handle_full_repair(self) -> None:
        if self._confirm_action(
            "Confirmar Reparación Completa",
            "Se ejecutará la secuencia completa (DISM ScanHealth, RestoreHealth, SFC /scannow y StartComponentCleanup).\n\n"
            "Este proceso puede demorar varios minutos. ¿Deseás continuar?",
        ):
            self._run_streaming_task(run_full_repair, "Iniciando reparación completa automática...")

    def _handle_rebuild_icons(self) -> None:
        if self._confirm_action(
            "Confirmar Reconstrucción de Caché de Iconos",
            "Esta acción detendrá temporalmente explorer.exe y cerrará todas las ventanas abiertas del Explorador de Windows.\n\n"
            "¿Deseás continuar?",
        ):
            self._run_task(rebuild_icon_cache, "Reconstruyendo caché de iconos...")

    def _handle_reregister_appx(self) -> None:
        if self._confirm_action(
            "Confirmar Re-registro de Paquetes AppX",
            "Se verificará el servicio MpsSvc y se re-registrarán todas las aplicaciones integradas (AppX) para todos los usuarios.\n\n"
            "Este proceso puede demorar varios minutos. ¿Deseás continuar?",
        ):
            self._run_task(reregister_appx_packages, "Re-registrando paquetes AppX (puede demorar)...")

    def _handle_clean_temp(self) -> None:
        include_wu = self.chk_clean_wu.isChecked()
        if include_wu and not self._confirm_action(
            "Confirmar Limpieza con Windows Update",
            "Se limpiarán los archivos temporales y se detendrán temporalmente los servicios wuauserv y bits para vaciar SoftwareDistribution\\Download.\n\n"
            "¿Deseás continuar?",
        ):
            return
        msg = "Limpiando temporales y caché de Windows Update..." if include_wu else "Limpiando archivos temporales..."
        self._run_task(clean_temp_and_update_cache, msg, include_wu)

    def _handle_restart_spooler(self) -> None:
        if self._confirm_action(
            "Confirmar Reinicio de Cola de Impresión",
            "Se detendrá el servicio Spooler, se eliminarán todos los documentos pendientes en spool\\PRINTERS y se reiniciará el servicio.\n\n"
            "¿Deseás continuar?",
        ):
            self._run_task(restart_print_spooler, "Reiniciando cola de impresión (Spooler)...")

    def _handle_open_battery_html(self) -> None:
        report_path = self._get_battery_report_path()
        if not report_path.exists():
            self._append_log(False, f"No se encontró el reporte de batería en: {report_path}")
            self.btn_open_battery_html.setEnabled(False)
            return
        try:
            os.startfile(str(report_path))
            self._append_log(True, f"Abriendo reporte de batería: {report_path}")
        except OSError as exc:
            self._append_log(False, f"No se pudo abrir el reporte HTML: {exc}")

    def _toggle_password_visibility(self, checked: bool) -> None:
        if checked:
            self.input_password.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_pass.setText("Ocultar")
        else:
            self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_pass.setText("Ver")

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
        add_to_admins = self.chk_admin_group.isChecked()
        self._run_task(
            create_local_user,
            "Creando usuario local...",
            username,
            password,
            fullname,
            "Cuenta local creada con Utilidades",
            add_to_admins,
        )

    def _run_diagnostics_bundle(self) -> tuple[bool, str]:
        _, smart_msg = get_smart_health()
        _, part_msg = get_fixed_partitions()
        _, battery_msg = get_battery_health()
        _, stability_msg = get_system_stability()
        self._diag_results = {
            "smart": smart_msg,
            "partitions": part_msg,
            "battery": battery_msg,
            "stability": stability_msg,
        }
        return True, "Diagnóstico completo finalizado."

    def _handle_run_diagnostics(self) -> None:
        if self._active_worker is not None and self._active_worker.isRunning():
            return
        self.log_output.appendPlainText("[INFO] Ejecutando diagnóstico completo de hardware y sistema...")
        self._set_controls_enabled(False)
        self._active_worker = TaskWorker(self._run_diagnostics_bundle)
        self._active_worker.finished_signal.connect(self._on_diagnostics_finished)
        self._active_worker.start()

    def _on_diagnostics_finished(self, ok: bool, message: str) -> None:
        if self._diag_results:
            smart_txt = self._diag_results.get("smart", "N/D")
            part_txt = self._diag_results.get("partitions", "")
            combined_disks = f"{smart_txt}\n\nParticiones fijas:\n{part_txt}" if part_txt else smart_txt
            self.smart_label.setText(combined_disks)
            self.battery_label.setText(self._diag_results.get("battery", "N/D"))
            self.stability_label.setText(self._diag_results.get("stability", "N/D"))
        self._append_log(ok, message)
        self._set_controls_enabled(True)

    def _handle_export_diagnostics(self) -> None:
        if not self._diag_results:
            self._append_log(False, "Ejecutá primero el Diagnóstico Completo antes de exportar.")
            return
        import os
        default_name = f"{os.environ.get('COMPUTERNAME', 'EQUIPO')}-Reporte.txt"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Reporte de Diagnóstico",
            default_name,
            "Archivos de texto (*.txt)",
        )
        if not path:
            return
        ok, msg = export_diagnostic_report(path, self._diag_results)
        self._append_log(ok, msg)

    def _run_task(self, fn, status_msg: str = "", *args) -> None:
        if self._active_worker is not None and self._active_worker.isRunning():
            return
        if status_msg:
            self.log_output.appendPlainText(f"[INFO] {status_msg}")
        self._set_controls_enabled(False)
        self._active_worker = TaskWorker(fn, *args)
        self._active_worker.finished_signal.connect(self._on_task_finished)
        self._active_worker.start()

    def _run_streaming_task(self, fn, status_msg: str = "") -> None:
        if self._active_worker is not None and self._active_worker.isRunning():
            return
        if status_msg:
            self.log_output.appendPlainText(f"[INFO] {status_msg}")
        self._set_controls_enabled(False)
        self.repair_progress.setRange(0, 0)
        self.repair_progress.setVisible(True)
        worker = StreamingTaskWorker(fn)
        worker.log_signal.connect(self.log_output.appendPlainText)
        worker.progress_signal.connect(self._on_progress_update)
        worker.finished_signal.connect(self._on_task_finished)
        self._active_worker = worker
        worker.start()

    def _on_progress_update(self, value: int) -> None:
        if value < 0:
            self.repair_progress.setRange(0, 0)
        else:
            self.repair_progress.setRange(0, 100)
            self.repair_progress.setValue(value)

    def _on_task_finished(self, ok: bool, message: str) -> None:
        self.repair_progress.setVisible(False)
        self._append_log(ok, message)
        self._refresh_hibernation_status()
        self._refresh_max_icons_status()
        if ok:
            self.input_password.clear()
        self._set_controls_enabled(True)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._active_worker is not None and self._active_worker.isRunning():
            confirm = self._confirm_action(
                "Tarea en ejecución",
                "Hay una operación de sistema en curso. Cerrar la aplicación ahora podría interrumpirla.\n\n"
                "¿Deseás cerrar de todos modos?",
            )
            if not confirm:
                event.ignore()
                return
        event.accept()
