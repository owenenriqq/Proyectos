# main.py
"""Interfaz principal del Gestor Eidico para lanzamiento, VPN, red y actualizaciones."""

import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import webbrowser

from PyQt6.QtCore import QPropertyAnimation, QSharedMemory, QTimer, Qt
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from config import (
    CONFIG,
    ESTILO_GLOBAL,
    LOG_PATH,
    TIEMPO_VERIFICACION,
    es_admin,
    esta_aws_vpn_instalado,
    get_cred,
    limpiar_archivos_residuales,
    logger,
    obtener_carpeta_descargas,
    obtener_carpeta_escritorio,
    obtener_ruta_aws_vpn,
    resource_path,
)
from workers import (
    WorkerAccionSistema,
    WorkerCheckRed,
    WorkerMonitor,
    WorkerTransferencia,
    WorkerVerificacionInicio,
    lanzar_proceso_desacoplado,
)

if not es_admin():
    try:
        if getattr(sys, "frozen", False):
            parametros = subprocess.list2cmdline(sys.argv[1:]) if len(sys.argv) > 1 else None
        else:
            parametros = subprocess.list2cmdline(sys.argv)
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, parametros, None, 1)
    except (OSError, AttributeError) as exc:
        logger.error("No se pudo solicitar elevación UAC: %s", exc)
    sys.exit()


class DialogoSoporte(QDialog):
    """Ventana modal con accesos directos para contactar a Soporte Técnico IT."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Soporte Tecnico IT")
        self.setFixedSize(350, 220)
        self.setStyleSheet(ESTILO_GLOBAL)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        lbl = QLabel(
            "Seleccione un metodo para contactar a Soporte IT.\n\n"
            "Importante: Por favor adjunte una captura de pantalla del error si le es posible."
        )
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        num = CONFIG["WHATSAPP_NUM"]
        btn_wp_app = QPushButton("WhatsApp (Aplicacion)")
        btn_wp_app.clicked.connect(
            lambda: self.abrir_link(
                f"whatsapp://send?phone={num}&text=Hola,%20necesito%20soporte%20con%20el%20Sistema%20Fox.%20Adjunto%20captura:"
            )
        )
        btn_wp_web = QPushButton("WhatsApp (Web)")
        btn_wp_web.clicked.connect(
            lambda: self.abrir_link(
                f"https://web.whatsapp.com/send?phone={num}&text=Hola,%20necesito%20soporte%20con%20el%20Sistema%20Fox.%20Adjunto%20captura:"
            )
        )
        btn_email = QPushButton("Correo Electronico")
        btn_email.clicked.connect(
            lambda: self.abrir_link(
                f"mailto:{CONFIG['EMAIL_SOPORTE']}?subject=Soporte%20Sistema%20Fox&body=Por%20favor%20adjunte%20una%20captura%20del%20error%20aqui."
            )
        )

        layout.addWidget(btn_wp_app)
        layout.addWidget(btn_wp_web)
        layout.addWidget(btn_email)

    def abrir_link(self, url):
        """Abre el enlace de soporte en la aplicación o navegador predeterminado."""
        try:
            webbrowser.open(url)
        except Exception:
            logger.exception("No se pudo abrir el enlace de soporte técnico")
        self.accept()


class GestorEidico(QWidget):
    """Ventana principal del lanzador corporativo Eidico y su ícono en bandeja."""

    def __init__(self):
        super().__init__()
        logger.info("Iniciando Gestor Eidico.")
        limpiar_archivos_residuales()

        self.worker = None
        self.worker_red = None
        self.worker_inicio = None
        self.worker_accion = None
        self._anim_actual = None

        self.setWindowTitle("Gestor Eidico")
        self.setFixedSize(360, 355)
        self.setStyleSheet(ESTILO_GLOBAL)
        self.setWindowFlags(
            self.windowFlags()
            & ~Qt.WindowType.WindowMaximizeButtonHint
            & ~Qt.WindowType.WindowMinimizeButtonHint
        )

        ruta_icono = resource_path("Eidico.ico")
        if os.path.exists(ruta_icono):
            self.setWindowIcon(QIcon(ruta_icono))
        else:
            logger.warning("No se encontró el icono de ventana en %s", ruta_icono)

        self.contador_segundos = TIEMPO_VERIFICACION
        self.ciclos_verificacion_vpn = 0
        self.timer_countdown = QTimer(self)
        self.timer_countdown.timeout.connect(self.actualizar_conteo_visible)

        self.configurar_bandeja_sistema()
        self.configurar_ui()
        self._actualizar_estado_acciones_vpn()

        self.monitor = WorkerMonitor(CONFIG["IP_SERVER_1"], CONFIG["IP_SERVER_2"])
        self.monitor.estado_red.connect(self.actualizar_indicador_red)
        self.monitor.start()

        self.vista_trabajando(True, indeterminado=True, mensaje_barra="Iniciando Eidico...")
        QTimer.singleShot(2000, self.iniciar_flujo_apertura)

    def configurar_ui(self):
        """Construye los paneles, botones, barra de progreso y menús de la ventana."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 15)

        l_top = QHBoxLayout()
        l_top.addStretch()
        self.btn_opciones = QPushButton("Opciones")
        self.btn_opciones.setObjectName("BtnOpciones")
        self.btn_opciones.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_opciones = QMenu(self)

        self.menu_opciones.addAction("Que hacer si Eidico no abre").triggered.connect(
            self.mostrar_asistente
        )
        self.menu_opciones.addAction("Solicitar Soporte Tecnico").triggered.connect(
            self.solicitar_soporte_tv
        )
        self.menu_opciones.addAction("Como configurar mi usuario a AWS (PDF)").triggered.connect(
            self.abrir_instructivo
        )
        self.accion_menu_abrir_vpn = self.menu_opciones.addAction("Abrir AWS VPN Client")
        self.accion_menu_abrir_vpn.triggered.connect(self.abrir_aws_client)
        self.accion_menu_instalar_vpn = self.menu_opciones.addAction("Instalar VPN")
        self.accion_menu_instalar_vpn.triggered.connect(self.descargar_e_instalar_vpn)
        self.menu_opciones.aboutToShow.connect(self._actualizar_estado_acciones_vpn)
        self.menu_opciones.addSeparator()
        self.menu_opciones.addAction("Forzar cierre de Eidico").triggered.connect(
            self.forzar_cierre_eidico
        )
        self.menu_opciones.addAction("Limpiar Sesion de Red").triggered.connect(
            self.limpiar_sesion_red
        )
        self.menu_opciones.addSeparator()
        self.menu_opciones.addAction("Descargar Instalador Eidico").triggered.connect(
            self.descargar_e_instalar_eidico
        )
        self.accion_menu_reinstalar_vpn = self.menu_opciones.addAction("Reinstalar AWS VPN Client")
        self.accion_menu_reinstalar_vpn.triggered.connect(self.reinstalar_aws)
        self.menu_opciones.addAction("Descarga FortiClient").triggered.connect(
            self.descargar_forticlient
        )
        self.menu_opciones.addSeparator()
        self.menu_opciones.addAction("Agregar credencial 172.31.11.146").triggered.connect(
            lambda: self.agregar_credencial_y_abrir(
                CONFIG["IP_SERVER_1"],
                CONFIG["USER_1"],
                CONFIG["PASS_1_B64"],
                r"\\172.31.11.146\Fileserver",
                20,
                "172.31.11.146 conectado",
            )
        )
        self.menu_opciones.addAction("Agregar credencial 172.30.0.13").triggered.connect(
            lambda: self.agregar_credencial_y_abrir(
                CONFIG["IP_SERVER_2"],
                CONFIG["USER_2"],
                CONFIG["PASS_2_B64"],
                r"\\172.30.0.13",
                20,
                "172.30.0.13 conectado",
            )
        )
        self.menu_opciones.addAction("Crear accesos directos").triggered.connect(
            self.crear_accesos_directos
        )
        self.menu_opciones.addSeparator()
        self.menu_opciones.addAction("Ver Logs").triggered.connect(self.abrir_logs)

        self.btn_opciones.setMenu(self.menu_opciones)
        l_top.addWidget(self.btn_opciones)
        layout.addLayout(l_top)
        layout.addSpacing(5)

        self.panel_botones = QWidget()
        l_btns = QHBoxLayout(self.panel_botones)
        l_btns.setContentsMargins(0, 0, 0, 0)

        self.btn_eidico = QPushButton("Abrir Eidico")
        self.btn_eidico.setObjectName("BtnPrincipal")
        self.btn_eidico.setFixedHeight(35)
        self.btn_eidico.clicked.connect(self.iniciar_flujo_apertura)

        self.btn_vpn_action = QPushButton("Reiniciar VPN")
        self.btn_vpn_action.setFixedHeight(35)

        l_btns.addWidget(self.btn_eidico)
        l_btns.addWidget(self.btn_vpn_action)

        self.panel_progreso = QWidget()
        l_prog = QVBoxLayout(self.panel_progreso)
        l_prog.setContentsMargins(0, 0, 0, 0)
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(22)
        l_prog.addWidget(self.pbar)

        self.panel_asistente = QFrame()
        self.panel_asistente.setStyleSheet(
            "QFrame { background-color: #ffffff; border: 1px solid #dcdde1; border-radius: 8px; }"
        )
        l_asis = QVBoxLayout(self.panel_asistente)
        l_asis.setContentsMargins(10, 15, 10, 15)
        lbl_asis = QLabel("<b>Guia de Resolucion:</b>")
        lbl_asis.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_asis.addWidget(lbl_asis)

        b1 = QPushButton("1. Reiniciar AWS VPN (Cliente y Servicio)")
        b1.clicked.connect(self.reiniciar_vpn_total)
        b2 = QPushButton("2. Reparacion de EidicoPrueba.exe")
        b2.clicked.connect(self.forzar_actualizacion_eidico)
        b_volver = QPushButton("Volver al Inicio")
        b_volver.setObjectName("BtnPrincipal")
        b_volver.clicked.connect(self.restaurar_menu_principal)

        l_asis.addWidget(b1)
        l_asis.addWidget(b2)
        l_asis.addSpacing(10)
        l_asis.addWidget(b_volver)

        self.panel_sin_vpn = QFrame()
        self.panel_sin_vpn.setStyleSheet(
            "QFrame { background-color: #ffffff; border: 1px solid #dcdde1; border-radius: 8px; }"
        )
        l_sin_vpn = QVBoxLayout(self.panel_sin_vpn)
        l_sin_vpn.setContentsMargins(14, 12, 14, 12)
        l_sin_vpn.setSpacing(6)

        self.lbl_sin_vpn_titulo = QLabel()
        self.lbl_sin_vpn_titulo.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_sin_vpn_titulo.setStyleSheet("font-size: 12px; font-weight: bold; color: #2d3436;")
        self.lbl_sin_vpn_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_sin_vpn_titulo.setWordWrap(True)
        l_sin_vpn.addWidget(self.lbl_sin_vpn_titulo)

        self.lbl_sin_vpn_subtitulo = QLabel()
        self.lbl_sin_vpn_subtitulo.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_sin_vpn_subtitulo.setStyleSheet("font-size: 11px; color: #2d3436;")
        self.lbl_sin_vpn_subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_sin_vpn_subtitulo.setWordWrap(True)
        self.lbl_sin_vpn_subtitulo.setMinimumHeight(36)
        l_sin_vpn.addWidget(self.lbl_sin_vpn_subtitulo)

        self.btn_sin_vpn_abrir_eidico = QPushButton("Abrir Eidico")
        self.btn_sin_vpn_abrir_eidico.setObjectName("BtnPrincipal")
        self.btn_sin_vpn_abrir_eidico.clicked.connect(self.iniciar_flujo_apertura)

        self.btn_sin_vpn_abrir_vpn = QPushButton("Abrir AWS VPN Client")
        self.btn_sin_vpn_abrir_vpn.setObjectName("BtnPrincipal")
        self.btn_sin_vpn_abrir_vpn.clicked.connect(self.abrir_aws_client)

        self.btn_sin_vpn_instructivo = QPushButton("Ver instructivo AWS VPN (PDF)")
        self.btn_sin_vpn_instructivo.setObjectName("BtnPrincipal")
        self.btn_sin_vpn_instructivo.clicked.connect(self.abrir_instructivo)

        self.btn_sin_vpn_instalar = QPushButton("Instalar VPN")
        self.btn_sin_vpn_instalar.clicked.connect(self.descargar_e_instalar_vpn)

        self.btn_sin_vpn_reintentar = QPushButton("Reintentar conexión")
        self.btn_sin_vpn_reintentar.clicked.connect(self.iniciar_flujo_apertura)

        self.btn_sin_vpn_volver = QPushButton("Volver al Inicio")
        self.btn_sin_vpn_volver.clicked.connect(self.restaurar_menu_principal)

        l_sin_vpn.addWidget(self.btn_sin_vpn_abrir_eidico)
        l_sin_vpn.addWidget(self.btn_sin_vpn_abrir_vpn)
        l_sin_vpn.addWidget(self.btn_sin_vpn_instructivo)
        l_sin_vpn.addWidget(self.btn_sin_vpn_instalar)
        l_sin_vpn.addWidget(self.btn_sin_vpn_reintentar)
        l_sin_vpn.addWidget(self.btn_sin_vpn_volver)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.panel_botones)
        self.stack.addWidget(self.panel_progreso)
        self.stack.addWidget(self.panel_asistente)
        self.stack.addWidget(self.panel_sin_vpn)
        layout.addWidget(self.stack)

        layout.addStretch()

        l_bottom = QHBoxLayout()
        self.lbl_estado_red = QLabel("Verificando servidores...")
        self.lbl_estado_red.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_estado_red.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.lbl_estado_red.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        l_bottom.addWidget(self.lbl_estado_red)
        l_bottom.addStretch()
        layout.addLayout(l_bottom)

        self.actualizar_boton_vpn()

    def _hay_tarea_en_curso(self):
        """Indica si existe algún hilo secundario de operación aún en ejecución."""
        for attr in ("worker", "worker_red", "worker_inicio", "worker_accion"):
            hilo = getattr(self, attr, None)
            if hilo is not None and hilo.isRunning():
                return True
        return False

    def _mostrar_panel(self, widget_objetivo):
        """Cambia el panel activo en el QStackedWidget con una transición suave."""
        if self._anim_actual is not None:
            self._anim_actual.stop()
            self._anim_actual = None

        actual = self.stack.currentWidget()
        if actual is not None:
            actual.setGraphicsEffect(None)

        if actual is widget_objetivo:
            return

        self.stack.setCurrentWidget(widget_objetivo)
        efecto = QGraphicsOpacityEffect(widget_objetivo)
        widget_objetivo.setGraphicsEffect(efecto)
        anim = QPropertyAnimation(efecto, b"opacity", self)
        anim.setDuration(150)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        def al_terminar():
            widget_objetivo.setGraphicsEffect(None)
            if self._anim_actual is anim:
                self._anim_actual = None

        anim.finished.connect(al_terminar)
        self._anim_actual = anim
        anim.start()

    def vista_trabajando(self, ocupado, indeterminado=False, mensaje_barra=""):
        """Muestra la barra de progreso o vuelve al panel de botones principales."""
        self.btn_opciones.setEnabled(not ocupado)
        if ocupado:
            if indeterminado:
                self.pbar.setRange(0, 0)
                self.pbar.setFormat(mensaje_barra)
            else:
                self.pbar.setRange(0, 100)
                self.pbar.setValue(0)
                self.pbar.setFormat(f"%p% - {mensaje_barra}")
            self._mostrar_panel(self.panel_progreso)
        else:
            self._mostrar_panel(self.panel_botones)

    def restaurar_menu_principal(self):
        """Restablece la vista de botones principales y actualiza el botón VPN."""
        self.vista_trabajando(False)
        self.actualizar_boton_vpn()

    def mostrar_asistente(self):
        """Muestra la guía rápida de resolución de problemas."""
        self._mostrar_panel(self.panel_asistente)

    def configurar_bandeja_sistema(self):
        """Inicializa el ícono y menú contextual en la bandeja del sistema."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("Eidico")
        ruta_icono = resource_path("Eidico.ico")
        if os.path.exists(ruta_icono):
            self.tray_icon.setIcon(QIcon(ruta_icono))

        tray_menu = QMenu()
        tray_menu.setStyleSheet(ESTILO_GLOBAL)

        tray_menu.addAction("Abrir").triggered.connect(self.showNormal)
        tray_menu.addAction("Abrir Eidico").triggered.connect(self.iniciar_flujo_apertura)
        self.accion_tray_abrir_vpn = tray_menu.addAction("Abrir AWS VPN Client")
        self.accion_tray_abrir_vpn.triggered.connect(self.abrir_aws_client)
        self.accion_tray_instalar_vpn = tray_menu.addAction("Instalar VPN")
        self.accion_tray_instalar_vpn.triggered.connect(self.descargar_e_instalar_vpn)
        tray_menu.addAction("Forzar cierre de Eidico").triggered.connect(
            self.forzar_cierre_eidico
        )
        tray_menu.addSeparator()
        tray_menu.addAction("Cerrar").triggered.connect(self.cerrar_aplicacion_total)
        tray_menu.aboutToShow.connect(self._actualizar_estado_acciones_vpn)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.al_hacer_click_tray)
        self.tray_icon.show()

    def al_hacer_click_tray(self, razon):
        """Restaura la ventana al hacer clic o doble clic en el ícono de bandeja."""
        if razon in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.showNormal()
            self.activateWindow()

    def emitir_notificacion(self, titulo, mensaje):
        """Muestra una notificación en la bandeja del sistema."""
        ruta_icono = resource_path("Eidico.ico")
        if os.path.exists(ruta_icono):
            icono = QIcon(ruta_icono)
        else:
            icono = QSystemTrayIcon.MessageIcon.Information
        self.tray_icon.showMessage(titulo, mensaje, icono, 3000)

    def closeEvent(self, event):
        """Minimiza la aplicación a la bandeja al cerrar la ventana."""
        event.ignore()
        self.hide()

    def cerrar_aplicacion_total(self):
        """Detiene hilos secundarios de forma ordenada y finaliza la aplicación."""
        logger.info("Cerrando Gestor Eidico por solicitud del usuario.")
        self.monitor.stop()
        self.monitor.wait(2000)
        for attr in ("worker", "worker_red", "worker_inicio", "worker_accion"):
            hilo = getattr(self, attr, None)
            if hilo is not None and hilo.isRunning():
                hilo.wait(2000)
        QApplication.instance().quit()

    def abrir_logs(self):
        """Abre el archivo de registro de eventos con el visor predeterminado."""
        try:
            if os.path.exists(LOG_PATH):
                os.startfile(LOG_PATH)
            else:
                self.emitir_notificacion("Aviso", "Aún no se generó el archivo de logs.")
        except OSError:
            logger.exception("No se pudo abrir el archivo de logs en %s", LOG_PATH)
            self.emitir_notificacion("Aviso", "No se pudo abrir el archivo de logs.")

    def _actualizar_estado_acciones_vpn(self):
        """Muestra 'Abrir/Reinstalar AWS VPN Client' o 'Instalar VPN' de forma exclusiva."""
        instalado = esta_aws_vpn_instalado()
        for accion in (
            getattr(self, "accion_menu_abrir_vpn", None),
            getattr(self, "accion_tray_abrir_vpn", None),
            getattr(self, "accion_menu_reinstalar_vpn", None),
        ):
            if accion is not None:
                accion.setVisible(instalado)
                accion.setEnabled(instalado)

        for accion in (
            getattr(self, "accion_menu_instalar_vpn", None),
            getattr(self, "accion_tray_instalar_vpn", None),
        ):
            if accion is not None:
                accion.setVisible(not instalado)
                accion.setEnabled(not instalado)

        if hasattr(self, "btn_vpn_action") and not self.timer_countdown.isActive():
            self.actualizar_boton_vpn()

    def abrir_aws_client(self):
        """Inicia la interfaz gráfica de AWS VPN Client de forma desacoplada si está instalada."""
        ruta_vpn = obtener_ruta_aws_vpn()
        if ruta_vpn:
            try:
                lanzar_proceso_desacoplado(ruta_vpn)
                logger.info("AWS VPN Client iniciado desde %s", ruta_vpn)
            except OSError:
                logger.exception("Error al abrir AWS VPN Client en %s", ruta_vpn)
                self.emitir_notificacion("Aviso", "No se pudo abrir AWS VPN Client.")
        else:
            self.emitir_notificacion("Aviso", "AWS VPN Client no encontrado en el equipo.")

    def limpiar_sesion_red(self):
        """Limpia en segundo plano las sesiones SMB de Eidico y la caché DNS."""
        if self._hay_tarea_en_curso():
            self.emitir_notificacion("Aviso", "Hay una operación en curso. Aguarde un momento.")
            return
        self.vista_trabajando(
            True, indeterminado=True, mensaje_barra="Limpiando sesiones de red..."
        )
        self.worker_accion = WorkerAccionSistema("limpiar_red")
        self.worker_accion.finalizado.connect(self._fin_accion_sistema)
        self.worker_accion.start()

    def forzar_cierre_eidico(self):
        """Fuerza en segundo plano la finalización del proceso local EidicoPrueba.exe."""
        if self._hay_tarea_en_curso():
            self.emitir_notificacion("Aviso", "Hay una operación en curso. Aguarde un momento.")
            return
        self.vista_trabajando(True, indeterminado=True, mensaje_barra="Cerrando procesos...")
        self.worker_accion = WorkerAccionSistema("forzar_cierre_eidico")
        self.worker_accion.finalizado.connect(self._fin_accion_sistema)
        self.worker_accion.start()

    def reiniciar_vpn_total(self):
        """Reinicia el cliente y el servicio de AWS VPN en segundo plano."""
        if self._hay_tarea_en_curso():
            self.emitir_notificacion("Aviso", "Hay una operación en curso. Aguarde un momento.")
            return
        self.emitir_notificacion("Eidico", "Reiniciando servicios VPN...")
        self.vista_trabajando(True, indeterminado=True, mensaje_barra="Reiniciando AWS VPN...")
        self.worker_accion = WorkerAccionSistema("reiniciar_vpn")
        self.worker_accion.finalizado.connect(self._fin_accion_sistema)
        self.worker_accion.start()

    def _fin_accion_sistema(self, exito, mensaje):
        """Notifica el resultado de una acción de sistema ejecutada en segundo plano."""
        if exito:
            self.emitir_notificacion("Eidico", mensaje)
        else:
            self.emitir_notificacion("Aviso", f"No se pudo completar la operación: {mensaje}")
        QTimer.singleShot(1200, self.restaurar_menu_principal)

    def forzar_actualizacion_eidico(self):
        """Descarga y reemplaza EidicoPrueba.exe desde la carpeta compartida del servidor."""
        self.emitir_notificacion("Eidico", "Iniciando reparacion de archivos.")
        self.iniciar_descarga(
            "",
            is_url=False,
            src=CONFIG["SERVER_FOLDER"],
            nombre=CONFIG["EXE_NAME"],
            fin_callback=self.fin_proceso_actualizacion,
        )

    def actualizar_indicador_red(self, on_146, on_13):
        """Actualiza las etiquetas de estado de conectividad y reacciona si la VPN reconecta."""
        c_146 = "#27ae60" if on_146 else "#e74c3c"
        c_13 = "#27ae60" if on_13 else "#e74c3c"
        t_146 = f"Conectado {CONFIG['IP_SERVER_1']}" if on_146 else f"Desconectado {CONFIG['IP_SERVER_1']}"
        t_13 = f"Conectado {CONFIG['IP_SERVER_2']}" if on_13 else f"Desconectado {CONFIG['IP_SERVER_2']}"
        self.lbl_estado_red.setText(
            f"<div align='left'><span style='color:{c_146};'>{t_146}</span><br>"
            f"<span style='color:{c_13};'>{t_13}</span></div>"
        )

        if self.stack.currentWidget() is self.panel_sin_vpn and on_146:
            self._mostrar_panel_sin_vpn_reconectado()

    def solicitar_soporte_tv(self):
        """Descarga TeamViewer QuickSupport y muestra las opciones de contacto IT."""
        self.emitir_notificacion("Eidico", "Descargando modulo de soporte tecnico...")
        self.iniciar_descarga(
            "",
            is_url=True,
            src=CONFIG["URL_TEAMVIEWER"],
            nombre="TeamViewerQS.exe",
            fin_callback=self.fin_descarga_tv,
        )

    def fin_descarga_tv(self, exito, resultado):
        """Ejecuta TeamViewerQS y abre el diálogo de contacto con Soporte IT."""
        if exito:
            try:
                os.startfile(resultado)
                DialogoSoporte(self).exec()
            except OSError:
                logger.exception("No se pudo abrir TeamViewerQS en %s", resultado)
                self.emitir_notificacion("Aviso", "No se pudo abrir TeamViewer.")
        else:
            self.emitir_notificacion("Aviso", "Fallo al descargar modulo de soporte.")
        self.restaurar_menu_principal()

    def descargar_e_instalar_eidico(self):
        """Descarga el paquete ZIP del instalador de Eidico."""
        self.emitir_notificacion("Eidico", "Iniciando descarga del instalador de Eidico.")
        self.iniciar_descarga(
            "",
            is_url=True,
            src=CONFIG["URL_EIDICO_ZIP"],
            nombre="Instalar_Fox_EIDICO.zip",
            fin_callback=self.fin_descarga_eidico,
        )

    def fin_descarga_eidico(self, exito, resultado):
        """Extrae de forma segura el instalador descargado en un hilo secundario."""
        if exito:
            self.vista_trabajando(True, indeterminado=True, mensaje_barra="Extrayendo archivos...")
            extract_dir = os.path.join(obtener_carpeta_descargas(), "Instalador_Eidico")
            self.worker_accion = WorkerAccionSistema(
                "extraer_instalador", zip_path=resultado, extract_dir=extract_dir
            )
            self.worker_accion.finalizado.connect(self._fin_extraccion_eidico)
            self.worker_accion.start()
        else:
            self.emitir_notificacion("Aviso", "Descarga del instalador fallida.")
            QTimer.singleShot(1500, self.restaurar_menu_principal)

    def _fin_extraccion_eidico(self, exito, destino_abrir):
        """Abre el instalador extraído o la carpeta contenedora al terminar la extracción."""
        if exito:
            try:
                os.startfile(destino_abrir)
                self.emitir_notificacion("Eidico", "Instalador de Eidico preparado.")
            except OSError:
                logger.exception("No se pudo abrir el instalador extraído en %s", destino_abrir)
                self.emitir_notificacion("Aviso", "Fallo al abrir el instalador extraído.")
        else:
            self.emitir_notificacion("Aviso", "Fallo al extraer el instalador.")
        QTimer.singleShot(1500, self.restaurar_menu_principal)

    def descargar_forticlient(self):
        """Descarga el instalador de FortiClient."""
        self.emitir_notificacion("Eidico", "Iniciando descarga de FortiClient.")
        self.iniciar_descarga(
            "",
            is_url=True,
            src=CONFIG["URL_FORTICLIENT"],
            nombre="FortiClient_x64.zip",
            fin_callback=lambda ok, res: self.fin_descarga_simple(ok, res, "FortiClient"),
        )

    def reinstalar_aws(self):
        """Descarga el instalador MSI de AWS VPN Client para reinstalación."""
        self.emitir_notificacion("Eidico", "Iniciando descarga de AWS VPN Client.")
        self.iniciar_descarga(
            "",
            is_url=True,
            src=CONFIG["URL_AWS_VPN"],
            nombre="AWS_VPN_Client.msi",
            fin_callback=self.fin_descarga_vpn,
        )

    def descargar_e_instalar_vpn(self):
        """Descarga e instala AWS VPN Client cuando no se encuentra en el equipo."""
        self.emitir_notificacion("Eidico", "Iniciando descarga de AWS VPN Client.")
        self.iniciar_descarga(
            "",
            is_url=True,
            src=CONFIG["URL_AWS_VPN"],
            nombre="AWS_VPN_Client.msi",
            fin_callback=self.fin_descarga_vpn,
        )

    def fin_descarga_vpn(self, exito, resultado):
        """Ejecuta el instalador MSI de AWS VPN y comienza la verificación periódica."""
        if exito:
            try:
                os.startfile(resultado)
                self.iniciar_ciclo_verificacion()
                return
            except OSError:
                logger.exception("No se pudo ejecutar el instalador AWS en %s", resultado)
                self.emitir_notificacion("Aviso", "No se pudo ejecutar el instalador AWS.")
        else:
            self.emitir_notificacion("Aviso", "Fallo en la descarga del instalador VPN.")
        self.restaurar_menu_principal()

    def fin_descarga_simple(self, exito, resultado, nombre):
        """Abre un archivo descargado genérico y notifica el resultado."""
        if exito:
            try:
                os.startfile(resultado)
                self.emitir_notificacion(
                    "Eidico", f"Instalador {nombre} abierto correctamente."
                )
            except OSError:
                logger.exception("Fallo al abrir el instalador %s en %s", nombre, resultado)
                self.emitir_notificacion("Aviso", "Fallo al abrir el instalador descargado.")
        else:
            self.emitir_notificacion("Aviso", f"Error descargando el instalador de {nombre}.")
        self.restaurar_menu_principal()

    def agregar_credencial_y_abrir(self, ip, user, pass_b64, path, timeout, msg_exito):
        """Inyecta la credencial SMB en segundo plano y verifica conectividad sin abrir carpetas."""
        if self._hay_tarea_en_curso():
            self.emitir_notificacion("Aviso", "Hay una operación en curso. Aguarde un momento.")
            return
        self.emitir_notificacion("Eidico", f"Inyectando credenciales para {ip}...")
        self.vista_trabajando(True, indeterminado=True, mensaje_barra=f"Conectando a {ip}...")
        password = get_cred(pass_b64)
        self.worker_red = WorkerCheckRed(
            path, timeout, msg_exito, ip=ip, user=user, password=password
        )
        self.worker_red.finalizado.connect(self.fin_check_red)
        self.worker_red.start()

    def fin_check_red(self, exito, msj, path):
        """Informa el resultado de la verificación de credencial y conectividad."""
        if exito:
            self.emitir_notificacion("Eidico", msj)
        else:
            self.emitir_notificacion("Aviso", msj)
        self.restaurar_menu_principal()

    def crear_accesos_directos(self):
        """Crea en segundo plano los accesos directos en el Escritorio."""
        if self._hay_tarea_en_curso():
            self.emitir_notificacion("Aviso", "Hay una operación en curso. Aguarde un momento.")
            return
        self.vista_trabajando(
            True, indeterminado=True, mensaje_barra="Creando accesos directos..."
        )
        self.worker_accion = WorkerAccionSistema(
            "crear_accesos_directos", escritorio=obtener_carpeta_escritorio()
        )
        self.worker_accion.finalizado.connect(self._fin_accion_sistema)
        self.worker_accion.start()

    def actualizar_boton_vpn(self):
        """Ajusta el texto y la acción del botón VPN según si AWS VPN está instalado."""
        try:
            self.btn_vpn_action.clicked.disconnect()
        except TypeError:
            pass
        if esta_aws_vpn_instalado():
            self.btn_vpn_action.setText("Reiniciar VPN")
            self.btn_vpn_action.clicked.connect(self.reiniciar_vpn_total)
        else:
            self.btn_vpn_action.setText("Instalar VPN")
            self.btn_vpn_action.clicked.connect(self.descargar_e_instalar_vpn)

    def iniciar_ciclo_verificacion(self):
        """Oculta el botón principal e inicia la cuenta regresiva esperando AWS VPN."""
        self.vista_trabajando(False)
        self.btn_eidico.setVisible(False)
        self.btn_vpn_action.setVisible(True)
        self.btn_vpn_action.setEnabled(False)
        self.contador_segundos = TIEMPO_VERIFICACION
        self.ciclos_verificacion_vpn = 0
        self.timer_countdown.start(1000)

    def actualizar_conteo_visible(self):
        """Actualiza el contador regresivo y verifica si finalizó la instalación VPN."""
        if esta_aws_vpn_instalado():
            self.timer_countdown.stop()
            self.emitir_notificacion("Eidico", "Instalacion de AWS VPN detectada.")
            self.btn_eidico.setVisible(True)
            self.btn_vpn_action.setEnabled(True)
            self._actualizar_estado_acciones_vpn()
            self.restaurar_menu_principal()
            return

        self.contador_segundos -= 1
        self.btn_vpn_action.setText(f"Verificando VPN ({self.contador_segundos}s)")
        if self.contador_segundos <= 0:
            self.ciclos_verificacion_vpn += 1
            if self.ciclos_verificacion_vpn >= 3:
                self.timer_countdown.stop()
                self.btn_eidico.setVisible(True)
                self.btn_vpn_action.setEnabled(True)
                self.emitir_notificacion(
                    "Aviso",
                    "No se detectó la instalación de AWS VPN Client. Puede reintentar cuando finalice.",
                )
                self.restaurar_menu_principal()
            else:
                self.contador_segundos = TIEMPO_VERIFICACION

    def iniciar_flujo_apertura(self):
        """Comienza la verificación del servidor en segundo plano antes de abrir Eidico."""
        if self._hay_tarea_en_curso():
            self.emitir_notificacion("Aviso", "Hay una operación en curso. Aguarde un momento.")
            return
        self.vista_trabajando(
            True, indeterminado=True, mensaje_barra="Verificando acceso al servidor..."
        )
        QTimer.singleShot(300, self.ejecutar_verificacion)

    def ejecutar_verificacion(self):
        """Lanza el hilo WorkerVerificacionInicio para evitar bloquear la interfaz gráfica."""
        if self._hay_tarea_en_curso():
            return
        self.worker_inicio = WorkerVerificacionInicio()
        self.worker_inicio.resultado.connect(self._procesar_resultado_verificacion)
        self.worker_inicio.start()

    def _procesar_resultado_verificacion(self, server_disponible, necesita_act):
        """Decide entre modo online (con posible actualización) o modo offline."""
        if server_disponible:
            self.iniciar_logica_online(necesita_act)
        else:
            self.manejar_modo_offline()

    def manejar_modo_offline(self):
        """Muestra un aviso claro sin abrir AWS VPN Client ni Eidico automáticamente."""
        vpn_instalado = esta_aws_vpn_instalado()
        self.btn_opciones.setEnabled(True)
        self.btn_sin_vpn_abrir_eidico.setVisible(False)
        self.btn_sin_vpn_abrir_eidico.setEnabled(False)
        self.btn_sin_vpn_reintentar.setVisible(True)
        self.btn_sin_vpn_volver.setVisible(True)

        if vpn_instalado:
            self.lbl_sin_vpn_titulo.setText("Sin conexión a la VPN de Eidico")
            self.lbl_sin_vpn_subtitulo.setText(
                "AWS VPN Client está instalado pero desconectado. Ábrelo y conéctate para continuar."
            )
            self.btn_sin_vpn_abrir_vpn.setVisible(True)
            self.btn_sin_vpn_instructivo.setVisible(False)
            self.btn_sin_vpn_instalar.setVisible(False)
            self.emitir_notificacion(
                "Sin conexión VPN",
                "AWS VPN Client está instalado pero desconectado. Ábrelo y conéctate para continuar.",
            )
        else:
            self.lbl_sin_vpn_titulo.setText("Sin conexión VPN ni cliente instalado")
            self.lbl_sin_vpn_subtitulo.setText(
                "No se detectó AWS VPN Client en este equipo. Consulta el instructivo o instálalo para conectarte."
            )
            self.btn_sin_vpn_abrir_vpn.setVisible(False)
            self.btn_sin_vpn_instructivo.setVisible(True)
            self.btn_sin_vpn_instalar.setVisible(True)
            self.emitir_notificacion(
                "AWS VPN Client no detectado",
                "No se detectó AWS VPN Client. Consulta el instructivo o instálalo para conectarte.",
            )

        self._mostrar_panel(self.panel_sin_vpn)

    def _mostrar_panel_sin_vpn_reconectado(self):
        """Actualiza el panel de aviso cuando la VPN reconecta y habilita Abrir Eidico."""
        self.lbl_sin_vpn_titulo.setText(
            "<span style='color:#27ae60;'>Conexión VPN detectada</span>"
        )
        self.lbl_sin_vpn_subtitulo.setText(
            "La conexión con los servidores de Eidico está activa. Ya puedes abrir el sistema."
        )
        self.btn_sin_vpn_abrir_eidico.setVisible(True)
        self.btn_sin_vpn_abrir_eidico.setEnabled(True)
        self.btn_sin_vpn_abrir_vpn.setVisible(False)
        self.btn_sin_vpn_instructivo.setVisible(False)
        self.btn_sin_vpn_instalar.setVisible(False)
        self.btn_sin_vpn_reintentar.setVisible(False)

    def iniciar_logica_online(self, necesita_act):
        """Actualiza el ejecutable desde el servidor si hace falta o lo inicia directamente."""
        if necesita_act:
            self.iniciar_descarga(
                "",
                is_url=False,
                src=CONFIG["SERVER_FOLDER"],
                nombre=CONFIG["EXE_NAME"],
                fin_callback=self.fin_proceso_actualizacion,
            )
        else:
            self.emitir_notificacion("Eidico", "Iniciando Eidico...")
            QTimer.singleShot(1000, self.lanzar_eidico)

    def iniciar_descarga(self, titulo, is_url=True, src="", nombre="", fin_callback=None):
        """Prepara y ejecuta WorkerTransferencia evitando ejecuciones concurrentes."""
        if self._hay_tarea_en_curso():
            self.emitir_notificacion("Aviso", "Hay una operación en curso. Aguarde un momento.")
            return

        self.vista_trabajando(True, mensaje_barra="Preparando transferencia...")
        origen = src if is_url else os.path.join(src, nombre)
        destino = (
            os.path.join(obtener_carpeta_descargas(), nombre)
            if is_url
            else os.path.join(CONFIG["LOCAL_FOLDER"], nombre)
        )

        self.worker = WorkerTransferencia(origen, destino, is_url)
        self.worker.progreso.connect(self.actualizar_barra)
        if fin_callback is not None:
            self.worker.finalizado.connect(fin_callback)
        self.worker.start()

    def actualizar_barra(self, porcentaje, texto):
        """Actualiza el valor porcentual y la etiqueta de la barra de progreso."""
        self.pbar.setValue(porcentaje)
        self.pbar.setFormat(texto)

    def fin_proceso_actualizacion(self, exito, error):
        """Lanza Eidico tras una actualización exitosa o informa el fallo."""
        if exito:
            self.emitir_notificacion("Eidico", "Eidico actualizado exitosamente.")
            QTimer.singleShot(1000, self.lanzar_eidico)
        else:
            logger.error("Fallo la actualización de Eidico: %s", error)
            self.emitir_notificacion("Aviso", "No se pudo actualizar Eidico.")
            self.restaurar_menu_principal()

    def lanzar_eidico(self):
        """Inicia el ejecutable local EidicoPrueba.exe con shell=False."""
        local_exe = os.path.join(CONFIG["LOCAL_FOLDER"], CONFIG["EXE_NAME"])
        if os.path.exists(local_exe):
            try:
                subprocess.Popen([local_exe], cwd=CONFIG["LOCAL_FOLDER"], shell=False)
                logger.info("Sistema local iniciado: %s", local_exe)
                self.hide()
            except OSError:
                logger.exception("No se pudo ejecutar %s", local_exe)
                self.emitir_notificacion("Aviso", "No se pudo ejecutar el sistema local.")
        else:
            logger.warning("No se encontró el ejecutable local al lanzar: %s", local_exe)
            self.emitir_notificacion("Aviso", "Archivo ejecutable no detectado.")
        self.restaurar_menu_principal()

    def abrir_instructivo(self):
        """Copia el instructivo PDF fuera de _MEIPASS cuando está compilado y lo abre."""
        ruta_origen = resource_path("InstructivoAWSVPN.pdf")
        if not os.path.exists(ruta_origen):
            logger.warning("Instructivo PDF no encontrado en %s", ruta_origen)
            self.emitir_notificacion("Aviso", "No se encontró el instructivo en el sistema.")
            return

        ruta_a_abrir = ruta_origen
        if getattr(sys, "frozen", False):
            ruta_copia = None
            for carpeta_base in (obtener_carpeta_descargas(), tempfile.gettempdir()):
                try:
                    os.makedirs(carpeta_base, exist_ok=True)
                    candidato = os.path.join(carpeta_base, "InstructivoAWSVPN.pdf")
                    shutil.copy2(ruta_origen, candidato)
                    ruta_copia = candidato
                    break
                except OSError as exc:
                    logger.warning(
                        "No se pudo copiar el instructivo a %s: %s", carpeta_base, exc
                    )
            if ruta_copia:
                ruta_a_abrir = ruta_copia

        try:
            os.startfile(ruta_a_abrir)
            logger.info("Instructivo PDF abierto desde %s", ruta_a_abrir)
        except OSError:
            logger.exception("Error al abrir el instructivo PDF en %s", ruta_a_abrir)
            self.emitir_notificacion("Aviso", "Error al abrir el PDF.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Eidico")
    app.setApplicationDisplayName("Eidico")
    shared_mem = QSharedMemory("Gestor_Eidico_Lock_2026")
    if not shared_mem.create(1):
        sys.exit(0)
    app.setQuitOnLastWindowClosed(False)
    window = GestorEidico()
    window.show()
    sys.exit(app.exec())
