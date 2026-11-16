# Eidico.py
import sys, os, subprocess, time, webbrowser, ctypes
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QProgressBar, QLabel, QFrame, QDialog, QMenu, QSystemTrayIcon,
                             QStackedWidget)
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt, QTimer, QSharedMemory, QPoint

from config import *
from workers import *

class DialogoSoporte(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Contactar con el equipo IT"); self.setFixedSize(360, 240); self.setStyleSheet(ESTILO_GLOBAL)
        l = QVBoxLayout(self); lbl = QLabel("Seleccione un metodo de contacto.\n\nPor favor adjunte una captura del error."); lbl.setWordWrap(True); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); l.addWidget(lbl)
        b1 = QPushButton("WhatsApp (App)"); b1.clicked.connect(lambda: webbrowser.open(f"whatsapp://send?phone={CONFIG['WHATSAPP_NUM']}&text=Soporte%20Eidico"))
        b2 = QPushButton("WhatsApp (Web)"); b2.clicked.connect(lambda: webbrowser.open(f"https://web.whatsapp.com/send?phone={CONFIG['WHATSAPP_NUM']}&text=Soporte%20Eidico"))
        b3 = QPushButton("Enviar Correo Electronico"); b3.clicked.connect(lambda: webbrowser.open(f"mailto:{CONFIG['EMAIL_SOPORTE']}?subject=Soporte%20Eidico"))
        l.addWidget(b1); l.addWidget(b2); l.addWidget(b3)

class GestorEidico(QWidget):
    def __init__(self):
        super().__init__(); self.setWindowTitle(CONFIG["APP_NAME"]); self.setFixedSize(360, 275); self.setStyleSheet(ESTILO_GLOBAL) # +5% Altura
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint & ~Qt.WindowType.WindowMinimizeButtonHint)
        try: self.ico_path = resource_path("Eidico.ico"); self.setWindowIcon(QIcon(self.ico_path))
        except: self.ico_path = None
        self.configurar_bandeja_sistema(); self.configurar_ui()
        self.monitor = WorkerMonitor(CONFIG["IP_SERVER_1"], CONFIG["IP_SERVER_2"])
        self.monitor.estado_red.connect(self.actualizar_red); self.monitor.start()
        QTimer.singleShot(1500, self.iniciar_flujo_apertura)

    def configurar_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(20, 15, 20, 10)
        l_top = QHBoxLayout(); l_top.addStretch()
        
        self.btn_op = QPushButton("Opciones"); self.btn_op.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_op = QMenu(self)
        self.menu_op.setObjectName("MenuOpciones")
        
        self.menu_op.addAction("¿No puedes entrar? Haz clic aquí").triggered.connect(lambda: self.stack.setCurrentIndex(1))
        self.menu_op.addAction("Contactar con el equipo IT").triggered.connect(lambda: DialogoSoporte(self).exec())
        self.menu_op.addAction("Instructivo Instalación y Configuración VPN AWS").triggered.connect(self.abrir_instructivo)
        self.menu_op.addSeparator()
        self.menu_op.addAction("Reiniciar AWS VPN Client y Servicio").triggered.connect(self.reiniciar_vpn)
        self.menu_op.addAction("Forzar cierre de Eidico").triggered.connect(self.matar_eidico)
        self.menu_op.addAction("Restablecer conexiones de red").triggered.connect(self.limpiar_red)
        self.menu_op.addSeparator()
        self.menu_op.addAction("Descargar Instalador Eidico").triggered.connect(lambda: self.descarga_extra(CONFIG["URL_EIDICO_ZIP"], "Instalar_Eidico.zip", "Descargar Instalador Eidico"))
        self.menu_op.addAction("Descargar AWS VPN Client").triggered.connect(lambda: self.descarga_extra(CONFIG["URL_AWS_VPN"], "AWS_Client.msi", "Descargar AWS VPN Client"))
        self.menu_op.addAction("Descarga FortiClient").triggered.connect(lambda: self.descarga_extra(CONFIG["URL_FORTICLIENT"], "FortiClient.zip", "Descarga FortiClient"))
        self.menu_op.addSeparator()
        self.menu_op.addAction(f"Credencial {CONFIG['IP_SERVER_1']}").triggered.connect(lambda: self.cred_man(CONFIG["IP_SERVER_1"], CONFIG["USER_1"], get_cred(CONFIG["PASS_1_B64"]), r"\\172.31.11.146\Fileserver"))
        self.menu_op.addAction(f"Credencial {CONFIG['IP_SERVER_2']}").triggered.connect(lambda: self.cred_man(CONFIG["IP_SERVER_2"], CONFIG["USER_2"], get_cred(CONFIG["PASS_2_B64"]), r"\\172.30.0.13"))
        self.menu_op.addAction("Crear accesos directos").triggered.connect(self.accesos)
        self.menu_op.addSeparator()
        self.menu_op.addAction("Cerrar").triggered.connect(QApplication.instance().quit)
        
        self.btn_op.clicked.connect(lambda: self.menu_op.exec(self.btn_op.mapToGlobal(QPoint(0, self.btn_op.height() + 2))))
        l_top.addWidget(self.btn_op); layout.addLayout(l_top)

        self.stack = QStackedWidget()
        
        # [0] INICIO
        p_ini = QWidget(); l_ini = QHBoxLayout(p_ini); l_ini.setContentsMargins(0,10,0,10)
        self.btn_run = QPushButton("Abrir Eidico"); self.btn_run.setObjectName("BtnPrincipal"); self.btn_run.setFixedHeight(40); self.btn_run.clicked.connect(self.iniciar_flujo_apertura)
        self.btn_vpn = QPushButton("Reiniciar AWS VPN Client"); self.btn_vpn.setFixedHeight(40); self.btn_vpn.clicked.connect(self.reiniciar_vpn)
        l_ini.addWidget(self.btn_run); l_ini.addWidget(self.btn_vpn)
        
        # [1] ASISTENTE
        p_asis = QFrame(); p_asis.setStyleSheet("QFrame { background-color: #ffffff; border: 1px solid #dcdde1; border-radius: 8px; }")
        l_asis = QVBoxLayout(p_asis); l_asis.addWidget(QLabel("<b>Intenta las siguientes soluciones:</b>"), alignment=Qt.AlignmentFlag.AlignCenter)
        b1 = QPushButton("1. Reiniciar AWS VPN Client y Servicio"); b1.clicked.connect(self.reiniciar_vpn)
        b2 = QPushButton("2. Reparación de Eidico"); b2.clicked.connect(self.reparacion_integral)
        b_rev = QPushButton("Volver"); b_rev.setObjectName("BtnPrincipal"); b_rev.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        l_asis.addWidget(b1); l_asis.addWidget(b2); l_asis.addStretch(); l_asis.addWidget(b_rev)
        
        # [2] PROGRESO EN LÍNEA (Reemplazo limpio)
        p_prog = QFrame(); p_prog.setObjectName("FrameProgreso"); l_prog = QVBoxLayout(p_prog)
        self.lbl_progreso = QLabel("Procesando..."); self.lbl_progreso.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_progreso.setStyleSheet("font-weight: bold; font-size: 12px; color: #2c3e50;")
        self.pbar = QProgressBar(); self.pbar.setTextVisible(False)
        l_prog.addStretch(); l_prog.addWidget(self.lbl_progreso); l_prog.addWidget(self.pbar); l_prog.addStretch()

        self.stack.addWidget(p_ini); self.stack.addWidget(p_asis); self.stack.addWidget(p_prog)
        layout.addWidget(self.stack)

        layout.addStretch()
        self.lbl_red = QLabel("Verificando...")
        self.lbl_red.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        layout.addWidget(self.lbl_red, alignment=Qt.AlignmentFlag.AlignLeft)

    # --- CONTROL VISUAL (Progreso Integrado) ---
    def mostrar_progreso(self, msj, indeterminado=False):
        self.lbl_progreso.setText(msj)
        self.pbar.setRange(0, 0 if indeterminado else 100)
        self.stack.setCurrentIndex(2)

    def actualizar_progreso(self, msj, p=None):
        self.lbl_progreso.setText(msj)
        if p is not None: self.pbar.setValue(p)
        QApplication.processEvents()

    def ocultar_progreso(self):
        self.stack.setCurrentIndex(0)
    # -------------------------------------------

    def emitir_notificacion(self, mensaje):
        ico = QIcon(self.ico_path) if self.ico_path else QSystemTrayIcon.MessageIcon.Information
        self.tray_icon.showMessage("Eidico", mensaje, ico, 3000)

    def iniciar_flujo_apertura(self):
        self.mostrar_progreso("Verificando servidor...", True)
        if is_server_reachable(CONFIG["IP_SERVER_1"]):
            subprocess.run(f'cmdkey /add:{CONFIG["IP_SERVER_1"]} /user:{CONFIG["USER_1"]} /pass:{get_cred(CONFIG["PASS_1_B64"])}', shell=True, creationflags=0x08000000)
            src, dst = os.path.join(CONFIG["SERVER_FOLDER"], CONFIG["EXE_NAME"]), os.path.join(CONFIG["LOCAL_FOLDER"], CONFIG["EXE_NAME"])
            if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
                self.mostrar_progreso("Actualizando Eidico... (Puede demorar unos minutos)", False)
                self.worker = WorkerTransferencia(src, dst); self.worker.progreso.connect(lambda p, m: self.actualizar_progreso(m, p))
                self.worker.finalizado.connect(self.fin_apertura); self.worker.start(); return
        self.fin_apertura(True)

    def fin_apertura(self, ok):
        if ok:
            p = os.path.join(CONFIG["LOCAL_FOLDER"], CONFIG["EXE_NAME"])
            if os.path.exists(p): 
                subprocess.Popen(f'"{CONFIG["EXE_NAME"]}"', cwd=CONFIG["LOCAL_FOLDER"], shell=True)
                self.emitir_notificacion("Abrir Eidico completado exitosamente.")
                self.hide()
        self.ocultar_progreso()

    def reparacion_integral(self):
        self.mostrar_progreso("Cerrando procesos y otorgando permisos...", True)
        subprocess.run(f'taskkill /IM "{CONFIG["EXE_NAME"]}" /F', shell=True, creationflags=0x08000000, stderr=subprocess.DEVNULL)
        
        zip_p = resource_path("Produccion.zip")
        # El Worker ahora aplica los permisos de Control Total SIEMPRE, incluso si el ZIP no existe.
        self.w_zip = WorkerProcesosEspeciales(zip_p if os.path.exists(zip_p) else None, CONFIG["LOCAL_FOLDER"], CONFIG["BASE_FOLDER"])
        self.w_zip.progreso_msg.connect(lambda m: self.actualizar_progreso(m))
        self.w_zip.finalizado.connect(self.fin_zip_y_continuar_exe)
        self.w_zip.start()

    def fin_zip_y_continuar_exe(self, ok):
        src = os.path.join(CONFIG["SERVER_FOLDER"], CONFIG["EXE_NAME"])
        dst = os.path.join(CONFIG["LOCAL_FOLDER"], CONFIG["EXE_NAME"])
        self.actualizar_progreso("Actualizando EidicoPrueba.exe...")
        self.pbar.setRange(0, 100)
        self.worker = WorkerTransferencia(src, dst)
        self.worker.progreso.connect(lambda p, m: self.actualizar_progreso(m, p))
        self.worker.finalizado.connect(lambda ok, m: (self.ocultar_progreso(), self.emitir_notificacion("Reparación de Eidico completada.")))
        self.worker.start()

    def reiniciar_vpn(self):
        self.mostrar_progreso("Reiniciando AWS VPN Client y Servicio...", True)
        subprocess.run('taskkill /IM "AWSVPNClient.exe" /F', shell=True, creationflags=0x08000000)
        subprocess.run('net stop "AWS VPN Client OpenVPN Service"', shell=True, creationflags=0x08000000); time.sleep(1); subprocess.run('net start "AWS VPN Client OpenVPN Service"', shell=True, creationflags=0x08000000)
        if os.path.exists(CONFIG["VPN_EXE"]): subprocess.Popen(f'"{CONFIG["VPN_EXE"]}"', shell=True)
        self.emitir_notificacion("Reiniciar AWS VPN Client y Servicio completado."); self.ocultar_progreso()

    def matar_eidico(self): 
        subprocess.run(f'taskkill /IM "{CONFIG["EXE_NAME"]}" /F', shell=True, creationflags=0x08000000)
        self.emitir_notificacion("Forzar cierre de Eidico completado.")
        
    def limpiar_red(self): 
        self.mostrar_progreso("Restableciendo conexiones de red...", True)
        subprocess.run('net use * /delete /y', shell=True, creationflags=0x08000000)
        subprocess.run('ipconfig /flushdns', shell=True, creationflags=0x08000000)
        self.emitir_notificacion("Restablecer conexiones de red completado."); self.ocultar_progreso()
        
    def abrir_instructivo(self): 
        p = resource_path("InstructivoAWSVPN.pdf"); os.startfile(p) if os.path.exists(p) else None
    
    def actualizar_red(self, o1, o2):
        c1 = "#27ae60" if o1 else "#e74c3c"; c2 = "#27ae60" if o2 else "#e74c3c"
        t1 = "Conectado" if o1 else "Desconectado"; t2 = "Conectado" if o2 else "Desconectado"
        self.lbl_red.setText(f"<span style='color:{c1};'>● {t1} ({CONFIG['IP_SERVER_1']})</span><br><span style='color:{c2};'>● {t2} ({CONFIG['IP_SERVER_2']})</span>")
    
    def configurar_bandeja_sistema(self):
        self.tray_icon = QSystemTrayIcon(self); self.tray_icon.setIcon(QIcon(self.ico_path)) if self.ico_path else None
        m = QMenu(); m.setObjectName("MenuBandeja"); m.setStyleSheet(ESTILO_GLOBAL)
        m.addAction("Abrir").triggered.connect(self.showNormal); m.addSeparator()
        m.addAction("Abrir Eidico").triggered.connect(self.iniciar_flujo_apertura)
        m.addAction("Reiniciar AWS VPN Client y Servicio").triggered.connect(self.reiniciar_vpn)
        m.addAction("Forzar cierre de Eidico").triggered.connect(self.matar_eidico); m.addSeparator()
        m.addAction("Cerrar").triggered.connect(QApplication.instance().quit)
        self.tray_icon.setContextMenu(m); self.tray_icon.activated.connect(lambda r: self.showNormal() if r == QSystemTrayIcon.ActivationReason.Trigger else None); self.tray_icon.show()

    def accesos(self):
        self.mostrar_progreso("Creando accesos directos...", True); desk = obtener_carpeta_escritorio()
        ps = f"$ws = New-Object -ComObject WScript.Shell; $s1 = $ws.CreateShortcut('{desk}\\Fileserver (172.31.11.146).lnk'); $s1.TargetPath = '\\\\{CONFIG['IP_SERVER_1']}\\Fileserver'; $s1.Save(); $s2 = $ws.CreateShortcut('{desk}\\FILESERVER.lnk'); $s2.TargetPath = '\\\\{CONFIG['IP_SERVER_2']}'; $s2.Save()"
        subprocess.run(["powershell", "-Command", ps], creationflags=0x08000000); self.emitir_notificacion("Crear accesos directos completado."); self.ocultar_progreso()

    def cred_man(self, ip, u, p, path):
        subprocess.run(f'cmdkey /add:{ip} /user:{u} /pass:{p}', shell=True, creationflags=0x08000000); self.emitir_notificacion(f"Credencial para {ip} inyectada."); os.startfile(path)
    
    def descarga_extra(self, url, nom, titulo_accion):
        self.mostrar_progreso(f"Iniciando {titulo_accion}...", False)
        self.worker = WorkerTransferencia(url, os.path.join(obtener_carpeta_descargas(), nom), True)
        self.worker.progreso.connect(lambda p, m: self.actualizar_progreso(m, p))
        self.worker.finalizado.connect(lambda ok, r: (self.ocultar_progreso(), self.emitir_notificacion(f"{titulo_accion} completada."), os.startfile(r) if ok else None))
        self.worker.start()

    def closeEvent(self, e): e.ignore(); self.hide()

if __name__ == "__main__":
    app = QApplication(sys.argv); shared = QSharedMemory("Gestor_Eidico_Lock_2026")
    if not shared.create(1): sys.exit(0)
    app.setQuitOnLastWindowClosed(False); w = GestorEidico(); w.show(); sys.exit(app.exec())