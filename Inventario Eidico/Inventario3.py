import sys
import os
import socket
import math
import subprocess
import wmi
import ctypes
import pythoncom
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, 
                             QProgressBar, QLabel, QLineEdit, QMessageBox, 
                             QComboBox, QDateEdit, QCalendarWidget, QPlainTextEdit, QSpinBox)
from PyQt6.QtGui import QPalette, QColor, QFont, QIcon
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate

# --------------------------------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------------------------------
CARPETA_RED = r"\\fileserver2025\IT\SOFT-INVENTARIO"
NOMBRE_ARCHIVO = "Inventario.txt"
RUTA_COMPLETA = os.path.join(CARPETA_RED, NOMBRE_ARCHIVO)

# --------------------------------------------------------------------------
# UTILS
# --------------------------------------------------------------------------
def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def es_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

if not es_admin():
    try: ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{sys.argv[0]}"', None, 1)
    except: pass
    sys.exit()

# --------------------------------------------------------------------------
# LÓGICA DE HARDWARE
# --------------------------------------------------------------------------
def obtener_discos_powershell():
    script = "Get-PhysicalDisk | Select-Object MediaType, BusType, Size | ConvertTo-Csv -NoTypeInformation"
    try:
        resultado = subprocess.run(["powershell", "-Command", script], capture_output=True, text=True, creationflags=0x08000000)
        lineas = resultado.stdout.strip().split('\n')
        discos_resumen = []
        for linea in lineas[1:]:
            if not linea.strip(): continue
            parts = linea.replace('"', '').split(',')
            if len(parts) >= 3:
                media_type = parts[0]
                bus_type = parts[1]
                size_gb = int(int(parts[2]) / (1024**3))
                tipo_final = "HDD"
                if media_type == "SSD":
                    tipo_final = "SSD SATA"
                    if bus_type == "NVMe": tipo_final = "NVMe"
                elif bus_type == "NVMe": tipo_final = "NVMe"
                discos_resumen.append(f"{size_gb}GB {tipo_final}")
        return " + ".join(discos_resumen)
    except: return "Error discos"

def analizar_ram(c):
    ram_bytes = 0
    modulos = c.Win32_PhysicalMemory()
    slots_usados = len(modulos)
    tipos = set()
    for m in modulos:
        ram_bytes += int(m.Capacity)
        ff = getattr(m, 'FormFactor', 0)
        if ff == 8: tipos.add("UDIMM")
        elif ff == 12: tipos.add("SODIMM")
        elif ff == 0: tipos.add("Integrada")
        else: tipos.add("DIMM")
    ram_total_gb = math.ceil(ram_bytes / (1024**3))
    tipo_str = "/".join(tipos) if tipos else "Integrada"
    detalle = f"{tipo_str} - {slots_usados} ranuras" if slots_usados > 0 else "Integrada"
    return f"{ram_total_gb} GB ({detalle})"

# --------------------------------------------------------------------------
# WORKER
# --------------------------------------------------------------------------
class WorkerInventario(QThread):
    progreso = pyqtSignal(int)
    finalizado = pyqtSignal(bool, str)

    def __init__(self, datos_input):
        super().__init__()
        self.datos = datos_input

    def run(self):
        try:
            pythoncom.CoInitialize()
            self.progreso.emit(10)
            c = wmi.WMI()
            
            # Hardware
            hostname = socket.gethostname()
            proc = c.Win32_Processor()[0]
            cpu = proc.Name.strip()
            self.progreso.emit(40)

            ram_info = analizar_ram(c)
            self.progreso.emit(60)

            discos_info = obtener_discos_powershell()
            self.progreso.emit(80)

            os_info = c.Win32_OperatingSystem()[0]
            so = os_info.Caption.strip()
            self.progreso.emit(90)

            if not os.path.exists(CARPETA_RED):
                raise Exception(f"No se encuentra la ruta: {CARPETA_RED}")

            registro = (
                f"AD: {self.datos['ad']} | "
                f"Correo: {self.datos['correo']} | "
                f"Equipo: {hostname} | "
                f"Puesto: {self.datos['puesto']} | "
                f"Antigüedad: {self.datos['antiguedad']} | "
                f"Depto: {self.datos['area']} | "
                f"Propiedad: {self.datos['propiedad']} | "
                f"Compra: {self.datos['compra']} | "
                f"CPU/GPU: {cpu} | "
                f"RAM: {ram_info} | "
                f"Discos: {discos_info} | "
                f"SO: {so} | "
                f"Obs: {self.datos['obs']}\n"
                f"{'-'*150}\n"
            )

            with open(RUTA_COMPLETA, mode='a', encoding='utf-8') as f:
                f.write(registro)

            self.progreso.emit(100)
            self.finalizado.emit(True, f"Guardado correctamente en:\n{NOMBRE_ARCHIVO}")

        except PermissionError:
            self.finalizado.emit(False, f"El archivo '{NOMBRE_ARCHIVO}' está abierto.\nCiérrelo e intente de nuevo.")
        except Exception as e:
            self.finalizado.emit(False, str(e))
        finally:
             pythoncom.CoUninitialize()

# --------------------------------------------------------------------------
# INTERFAZ GRÁFICA FINAL
# --------------------------------------------------------------------------
class InventarioApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inventario")
        # 3. REDUCCIÓN DE VERTICAL (Ahora 300px)
        self.resize(350, 300) 
        self.setWindowIcon(QIcon(resource_path("Inventario.ico")))

        # --- ICONOS BASE64 ---
        # Flecha Blanca (Para el botón Azul de Propiedad)
        self.ICONO_FLECHA_BLANCA = "url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAMCAYAAABWdVznAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAbElEQVR4nGP4//8/AymG/f///x8Q/wXif2QMxv9g8Q0wBrL4DxDfRsfLgPgxEAtgMwDIQRb7g8QvQDEQ2wGIn5GjGAuAxQ6gYh+QYmQgO0i/jhQDAwMDg/T09P9EGej7+z8DAwMDw9OnT/EkAwC+2R2B6/37YgAAAABJRU5ErkJggg==)"
        
        # Calendario Icono (Para las fechas)
        self.ICONO_CALENDARIO = "url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAvklEQVR4nK2TvQ3CMBCEv790ARURMAmjMAmTMAmjMAmTMAmToBR6fOQVK2nppPjmJI7tfNpa6707lzRLWnfOuRhjXnvvNd8tESHpruA6gN6q/4H8A36viC+Qf8XxDfo/4L4AA8rS1N84f4vFt8PYyCL/wDxbXS8DIgfA7EANgOAHOSwP0j8AhQDsR2A+Bk5irEAWKwAKvYBKUYGsoP060gxMDAwMEhPT/9PlIG+v/8zMDAwMDx9+hRPMgDgN97+d4t7/wAAAABJRU5ErkJggg==)"

        # Color Principal (Azul Oscuro)
        C_MAIN = "#2c3e50"

        self.setStyleSheet(f"""
            QWidget {{ 
                font-family: 'Segoe UI', sans-serif; 
                font-size: 11px;
                color: #2d3436; 
                background-color: #f5f6fa; 
            }}
            
            /* --- INPUTS & CAMPOS --- */
            QLineEdit {{ 
                border: 1px solid #dcdde1; 
                border-radius: 4px; 
                padding: 3px 8px; 
                background-color: white; 
                color: #2f3640;
                min-height: 18px;
                selection-background-color: {C_MAIN};
                selection-color: white;
            }}
            QLineEdit:focus {{ border: 1px solid {C_MAIN}; }}
            
            /* --- COMBOBOX (PROPIEDAD) --- */
            QComboBox {{
                border: 1px solid #dcdde1;
                border-radius: 4px;
                padding: 3px;
                padding-right: 20px;
                background-color: white;
                min-height: 18px;
                selection-background-color: {C_MAIN};
            }}
            QComboBox:focus {{ border: 1px solid {C_MAIN}; }}

            /* 5. BOTÓN AZUL OSCURO PARA COMBOBOX */
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 22px;
                border: 0px;
                background-color: {C_MAIN}; /* AZUL OSCURO SOLIDO */
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
            QComboBox::down-arrow {{
                image: {self.ICONO_FLECHA_BLANCA};
                width: 10px; height: 10px;
            }}

            /* --- DATE EDIT (FECHAS) --- */
            QDateEdit {{
                border: 1px solid #dcdde1;
                border-radius: 4px;
                padding: 3px;
                padding-right: 20px;
                background-color: white;
                min-height: 18px;
                selection-background-color: {C_MAIN};
            }}
            QDateEdit:focus {{ border: 1px solid {C_MAIN}; }}

            /* 4. BOTÓN AZUL OSCURO PARA CALENDARIO (IDENTICO A PROPIEDAD) */
            QDateEdit::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 22px;
                border: 0px;
                background-color: {C_MAIN}; /* AZUL OSCURO SOLIDO */
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
            QDateEdit::down-arrow {{
                image: {self.ICONO_CALENDARIO};
                width: 14px; height: 14px;
            }}
            
            /* --- LISTAS DESPLEGABLES --- */
            QComboBox QAbstractItemView {{
                border: 1px solid {C_MAIN};
                selection-background-color: {C_MAIN}; /* AZUL */
                selection-color: white;
                background-color: white;
                outline: 0;
            }}
            /* FORZAR COLOR AZUL EN HOVER PARA ELIMINAR EL MORADO */
            QComboBox QAbstractItemView::item:hover {{
                background-color: {C_MAIN};
                color: white;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {C_MAIN};
                color: white;
            }}

            /* --- CALENDARIO POPUP --- */
            /* AQUI ESTA LA CORRECCIÓN: Tamaño mínimo forzado para que no se corte */
            QCalendarWidget {{
                min-width: 300px;
                min-height: 220px;
            }}
            
            QCalendarWidget QWidget {{ background-color: white; }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{ background-color: {C_MAIN}; min-height: 28px; }}
            QCalendarWidget QToolButton {{ color: white; background: transparent; font-weight: bold; border: none; }}
            QCalendarWidget QToolButton:hover {{ background: rgba(255,255,255,0.2); border-radius: 4px; }}
            QCalendarWidget QToolButton::menu-indicator {{ image: none; }}
            
            /* Flechas del Calendario Blancas */
            QCalendarWidget QToolButton#qt_calendar_prevmonth {{
                qproperty-icon: none;
                image: {self.ICONO_FLECHA_BLANCA};
                width: 12px; height: 12px;
                transform: rotate(90deg); 
            }}
            QCalendarWidget QToolButton#qt_calendar_nextmonth {{
                qproperty-icon: none;
                image: {self.ICONO_FLECHA_BLANCA};
                width: 12px; height: 12px;
                transform: rotate(-90deg); 
            }}

            QCalendarWidget QAbstractItemView {{
                selection-background-color: {C_MAIN}; 
                selection-color: white; 
                outline: 0;
            }}
            QCalendarWidget QSpinBox {{
                selection-background-color: {C_MAIN};
                selection-color: white;
            }}

            QLabel {{ font-weight: bold; margin-top: 1px; margin-bottom: 0px; }}
            
            /* --- OBSERVACIONES (SIN SCROLLBAR) --- */
            QPlainTextEdit {{
                border: 1px solid #dcdde1; 
                border-radius: 4px; 
                padding: 3px 8px; 
                background-color: white; 
                color: #2f3640;
                selection-background-color: {C_MAIN};
                selection-color: white;
            }}
            QPlainTextEdit:focus {{ border: 1px solid {C_MAIN}; }}
        """)

        self.layout = QVBoxLayout()
        self.layout.setSpacing(3) 
        self.layout.setContentsMargins(10, 10, 10, 10) 
        self.setLayout(self.layout)

        lbl_titulo = QLabel("Datos del equipo y usuario")
        lbl_titulo.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(lbl_titulo)
        self.layout.addSpacing(3)

        self.frm_layout = QVBoxLayout()
        self.frm_layout.setSpacing(3)

        # 1. AD
        self.frm_layout.addWidget(QLabel("Usuario AD:"))
        self.inp_ad = QLineEdit()
        self.frm_layout.addWidget(self.inp_ad)

        # 2. Correo
        self.frm_layout.addWidget(QLabel("Correo electrónico:"))
        self.inp_correo = QLineEdit()
        self.frm_layout.addWidget(self.inp_correo)
        
        # 3. Puesto
        self.frm_layout.addWidget(QLabel("Puesto:"))
        self.inp_puesto = QLineEdit()
        self.frm_layout.addWidget(self.inp_puesto)

        # 4. Antigüedad (Icono Calendario con botón azul)
        self.frm_layout.addWidget(QLabel("Antigüedad:"))
        self.inp_antiguedad = QDateEdit()
        self.inp_antiguedad.setCalendarPopup(True)
        self.inp_antiguedad.setDate(QDate.currentDate())
        self.inp_antiguedad.setCursor(Qt.CursorShape.PointingHandCursor)
        self.frm_layout.addWidget(self.inp_antiguedad)
        
        # 5. Depto
        self.frm_layout.addWidget(QLabel("Departamento / Área:"))
        self.inp_area = QLineEdit()
        self.frm_layout.addWidget(self.inp_area)
        
        # 6. Propiedad (Botón Azul)
        self.frm_layout.addWidget(QLabel("Propiedad de:"))
        self.cmb_propiedad = QComboBox()
        self.cmb_propiedad.addItems(["EIDICO", "Urbis", "Órbita", "Personal", "Barrio"])
        self.cmb_propiedad.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cmb_propiedad.currentTextChanged.connect(self.verificar_barrio)
        self.frm_layout.addWidget(self.cmb_propiedad)

        # Campo Extra
        self.inp_barrio_nombre = QLineEdit()
        self.inp_barrio_nombre.setPlaceholderText("Nombre del Barrio...")
        self.inp_barrio_nombre.setVisible(False)
        self.frm_layout.addWidget(self.inp_barrio_nombre)

        # 7. Compra (Icono Calendario con botón azul)
        self.frm_layout.addWidget(QLabel("Fecha de compra:"))
        self.inp_compra = QDateEdit()
        self.inp_compra.setCalendarPopup(True)
        self.inp_compra.setDate(QDate.currentDate())
        self.inp_compra.setCursor(Qt.CursorShape.PointingHandCursor)
        self.frm_layout.addWidget(self.inp_compra)

        # 8. Obs (SIN SCROLLBAR VISIBLE)
        self.frm_layout.addWidget(QLabel("Observaciones:"))
        self.inp_obs = QPlainTextEdit() 
        self.inp_obs.setFixedHeight(45) 
        # MODIFICACIÓN: Quitar barra de scroll
        self.inp_obs.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.frm_layout.addWidget(self.inp_obs)

        self.layout.addLayout(self.frm_layout)
        self.layout.addSpacing(6)

        # 2. FRANJA GRIS ELIMINADA (Barra oculta por defecto)
        self.pbar = QProgressBar()
        self.pbar.setTextVisible(False)
        self.pbar.setFixedHeight(5)
        self.pbar.setVisible(False) # Oculta hasta que arranque
        self.pbar.setStyleSheet("""
            QProgressBar { border: 0px; background: #dfe6e9; border-radius: 2px; }
            QProgressBar::chunk { background-color: #27ae60; border-radius: 2px; }
        """)
        self.layout.addWidget(self.pbar)

        self.btn_enviar = QPushButton("Subir datos")
        self.btn_enviar.setFixedHeight(35)
        self.btn_enviar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_enviar.setStyleSheet(f"""
            QPushButton {{ background-color: {C_MAIN}; color: white; border-radius: 5px; font-weight: bold; font-size: 12px; }}
            QPushButton:hover {{ background-color: #34495e; }}
            QPushButton:pressed {{ background-color: #1abc9c; }}
        """)
        self.btn_enviar.clicked.connect(self.iniciar_proceso)
        self.layout.addWidget(self.btn_enviar)

    def verificar_barrio(self, texto):
        if texto == "Barrio":
            self.inp_barrio_nombre.setVisible(True)
            self.inp_barrio_nombre.setFocus()
        else:
            self.inp_barrio_nombre.setVisible(False)
            self.inp_barrio_nombre.clear()

    def iniciar_proceso(self):
        errores = []
        if not self.inp_ad.text().strip():
            errores.append("Falta el Usuario AD.")
        
        propiedad_seleccionada = self.cmb_propiedad.currentText()
        if propiedad_seleccionada == "Barrio" and not self.inp_barrio_nombre.text().strip():
            errores.append("Especifique el nombre del Barrio.")

        if errores:
            QMessageBox.warning(self, "Atención", "\n".join(errores))
            return

        txt_propiedad = propiedad_seleccionada
        if propiedad_seleccionada == "Barrio":
            txt_propiedad = f"Barrio ({self.inp_barrio_nombre.text().strip()})"

        # Limpiar observaciones de saltos de línea para el TXT
        obs_texto = self.inp_obs.toPlainText().replace('\n', ' | ')

        datos = {
            "ad": self.inp_ad.text().strip(),
            "correo": self.inp_correo.text().strip(),
            "puesto": self.inp_puesto.text().strip(),
            "antiguedad": self.inp_antiguedad.date().toString("dd/MM/yyyy"),
            "area": self.inp_area.text().strip(),
            "propiedad": txt_propiedad,
            "compra": self.inp_compra.date().toString("dd/MM/yyyy"),
            "obs": obs_texto
        }
        
        self.btn_enviar.setEnabled(False)
        self.btn_enviar.setText("Procesando...")
        self.pbar.setVisible(True) # Ahora sí mostramos la barra
        self.worker = WorkerInventario(datos)
        self.worker.progreso.connect(self.pbar.setValue)
        self.worker.finalizado.connect(self.proceso_terminado)
        self.worker.start()

    def proceso_terminado(self, exito, mensaje):
        self.btn_enviar.setEnabled(True)
        self.btn_enviar.setText("Subir datos")
        
        if exito:
            QMessageBox.information(self, "Éxito", mensaje)
            self.inp_correo.clear()
            self.inp_puesto.clear()
            self.inp_area.clear()
            self.inp_barrio_nombre.clear()
            self.inp_obs.clear()
            self.cmb_propiedad.setCurrentIndex(0) 
            self.inp_antiguedad.setDate(QDate.currentDate())
            self.inp_compra.setDate(QDate.currentDate())
        else:
            QMessageBox.critical(self, "Error", mensaje)
            
        self.pbar.setValue(0)
        self.pbar.setVisible(False) # Ocultamos la barra al terminar

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InventarioApp()
    window.show()
    sys.exit(app.exec())