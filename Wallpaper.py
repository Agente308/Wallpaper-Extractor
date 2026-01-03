from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QProgressBar, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPointF
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QRadialGradient
import os
import shutil
import subprocess
import sys
import random
import math
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(os.path.expanduser("~"), "Desktop", "Wallpapers")
TEMP = os.path.join(os.environ["TEMP"], "RePKGTemp")
REPKG_NEW = os.path.join(SCRIPT_DIR, "RePKG040alpha.exe")
REPKG_OLD = os.path.join(SCRIPT_DIR, "RePKG022.exe")
EXTS_VALIDAS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".mp4", ".webm", ".mov", ".avi")

class ExtractThread(QThread):
    progress_signal = Signal(int)
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, rutas):
        super().__init__()
        self.rutas = rutas
        self.archivos_extraidos = []

    def run(self):
        rutas_list = []
        for line in self.rutas.splitlines():
            for part in line.split(","):
                ruta = part.strip().strip('"')
                if ruta:
                    rutas_list.append(ruta)

        total = len(rutas_list)
        if total == 0:
            self.log_signal.emit("No se detectaron rutas validas")
            self.finished_signal.emit()
            return

        os.makedirs(OUTPUT, exist_ok=True)

        for idx, ruta in enumerate(rutas_list, 1):
            self.log_signal.emit(f"\nProcesando: {ruta}")
            self.progress_signal.emit(int((idx - 1) / total * 100))

            if not os.path.exists(ruta):
                self.log_signal.emit("Ruta no encontrada")
                continue

            try:
                for file in os.listdir(ruta):
                    if file.lower().endswith(EXTS_VALIDAS) and not file.lower().startswith("preview"):
                        f_lower = file.lower()
                        if "mask" in f_lower or "waterwaves" in f_lower or "waterripplenormal" in f_lower:
                            self.log_signal.emit(f"Ignorado (filtro): {file}")
                        else:
                            self.copy_file(os.path.join(ruta, file))
            except Exception as e:
                self.log_signal.emit(f"Error listando carpeta: {e}")

            try:
                pkg_files = [
                    f for f in os.listdir(ruta)
                    if f.lower().endswith(".pkg") and not f.lower().startswith("preview")
                ]
            except:
                pkg_files = []

            if not pkg_files:
                self.log_signal.emit("No se encontraron archivos .pkg para extraer")
                continue

            for pkg in pkg_files:
                pkg_path = os.path.join(ruta, pkg)
                self.log_signal.emit(f"Extrayendo paquete: {pkg_path}")

                if os.path.exists(TEMP):
                    try:
                        shutil.rmtree(TEMP)
                    except:
                        pass
                os.makedirs(TEMP, exist_ok=True)

                if not self.extraer_con_fallback(pkg_path, TEMP):
                    self.log_signal.emit(f"No se pudo extraer: {pkg}")
                    continue

                for root, dirs, files in os.walk(TEMP):
                    for file in files:
                        f_lower = file.lower()
                        if f_lower.endswith(EXTS_VALIDAS) and not f_lower.startswith("preview"):
                            if "mask" in f_lower or "waterwaves" in f_lower or "waterripplenormal" in f_lower:
                                self.log_signal.emit(f"Ignorado (filtro): {file}")
                            else:
                                self.copy_file(os.path.join(root, file))

                try:
                    shutil.rmtree(TEMP)
                except:
                    pass

        self.progress_signal.emit(100)
        self.log_signal.emit("\nExtraccion finalizada")
        self.log_signal.emit(f"Total de archivos extraidos: {len(self.archivos_extraidos)}")

        try:
            os.startfile(OUTPUT)
        except:
            pass

        if self.archivos_extraidos:
            self.log_signal.emit(f"\nAbriendo {len(self.archivos_extraidos)} archivo(s)")
            for archivo in self.archivos_extraidos:
                try:
                    os.startfile(archivo)
                    time.sleep(0.1)
                except Exception as e:
                    self.log_signal.emit(f"No se pudo abrir: {os.path.basename(archivo)}")

        self.finished_signal.emit()

    def copy_file(self, src):
        file = os.path.basename(src)
        dest = os.path.join(OUTPUT, file)
        counter = 1
        while os.path.exists(dest):
            name, ext = os.path.splitext(file)
            dest = os.path.join(OUTPUT, f"{name}_{counter}{ext}")
            counter += 1
        shutil.copy2(src, dest)
        self.archivos_extraidos.append(dest)
        self.log_signal.emit(f"Copiado: {file}")

    def extraer_con_fallback(self, pkg, temp_dir):
        try:
            subprocess.run([REPKG_NEW, "extract", pkg, "-o", temp_dir], check=True)
            return True
        except Exception:
            pass

        try:
            subprocess.run([REPKG_OLD, "extract", pkg, "-o", temp_dir], check=True)
            return True
        except Exception:
            return False

class Particle:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.reset(w, h, force_spread=True)

    def reset(self, w, h, force_spread=False):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        speed = random.uniform(0.05, 0.9)
        angle = random.uniform(0, 2 * math.pi)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.size = random.uniform(0.8, 3.2)
        base = 150 + random.randint(-40, 60)
        self.color = QColor(base, 60, base + 60, 180)
        self.w = w
        self.h = h

class ParticleWidget(QWidget):
    def __init__(self, parent=None, count=120):
        super().__init__(parent)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setAutoFillBackground(False)
        self.particles = []
        self.count = count
        self.timer = QTimer(self)
        self.timer.setInterval(12)
        self.timer.timeout.connect(self.tick)
        self.last_time = time.time()
        self.lines_enabled = True
        self.max_link_distance = 120
        self._init_particles()
        self.timer.start()

    def _init_particles(self):
        w = max(200, self.width())
        h = max(200, self.height())
        if not self.particles:
            self.particles = [Particle(w, h) for _ in range(self.count)]
        else:
            for p in self.particles:
                p.reset(w, h, force_spread=True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = max(200, self.width())
        h = max(200, self.height())
        for p in self.particles:
            old_w = p.w
            old_h = p.h
            if old_w > 0 and old_h > 0:
                p.x = (p.x / old_w) * w
                p.y = (p.y / old_h) * h
            p.w = w
            p.h = h

    def tick(self):
        if not self.particles:
            return
            
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        if dt <= 0 or dt > 0.1:
            dt = 0.016
        for p in self.particles:
            p.x += p.vx * dt * 60
            p.y += p.vy * dt * 60
            p.vx += math.sin((p.x + p.y) * 0.001) * 0.002
            p.vy += math.cos((p.x - p.y) * 0.001) * 0.002

            if p.x < -50 or p.x > p.w + 50 or p.y < -50 or p.y > p.h + 50:
                p.reset(p.w, p.h)

        self.update()

    def paintEvent(self, event):
        if not self.particles:
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor(0, 0, 0))
            painter.end()
            return
            
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            w = self.width()
            h = self.height()

            grad = QRadialGradient(QPointF(w/2, h/2), max(w, h)*0.8)
            grad.setColorAt(0.0, QColor(74, 0, 102))
            grad.setColorAt(0.6, QColor(18, 2, 24))
            grad.setColorAt(1.0, QColor(0, 0, 0))
            painter.fillRect(0, 0, w, h, grad)

            if self.lines_enabled:
                pen = QPen()
                pen.setWidthF(0.7)
                for i in range(len(self.particles)):
                    a = self.particles[i]
                    for j in range(i+1, len(self.particles)):
                        b = self.particles[j]
                        dx = a.x - b.x
                        dy = a.y - b.y
                        dist = math.hypot(dx, dy)
                        if dist < self.max_link_distance:
                            opacity = max(0.0, 1.0 - (dist / self.max_link_distance))
                            col = QColor(170, 100, 255, int(90 * opacity))
                            pen.setColor(col)
                            painter.setPen(pen)
                            painter.drawLine(QPointF(a.x, a.y), QPointF(b.x, b.y))

            for p in self.particles:
                color = p.color
                alpha = color.alpha()
                glow = QRadialGradient(QPointF(p.x, p.y), p.size * 6)
                glow.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), int(alpha * 0.9)))
                glow.setColorAt(0.6, QColor(color.red(), color.green(), color.blue(), int(alpha * 0.25)))
                glow.setColorAt(1.0, QColor(0, 0, 0, 0))
                painter.setBrush(QBrush(glow))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(p.x, p.y), p.size * 6, p.size * 6)

            for p in self.particles:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(p.color)))
                painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)

        finally:
            painter.end()

class WallpaperExtractor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wallpaper Extractor")
        self.setGeometry(200, 100, 980, 640)

        self.particle_bg = ParticleWidget(self, count=140)
        self.particle_bg.setObjectName("particle_bg")
        self.particle_bg.setGeometry(0, 0, 980, 640)
        self.particle_bg.lower()

        self.container = QFrame(self)
        self.container.setStyleSheet("""
            QFrame {
                background: rgba(20, 12, 24, 210);
                border-radius: 14px;
            }
            QTextEdit {
                background: rgba(12, 8, 15, 170);
                color: #e9d6ff;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                             stop:0 #7b2cff, stop:1 #4a00a6);
                color: white;
                padding: 8px 14px;
                border-radius: 8px;
                border: none;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                             stop:0 #9a4dff, stop:1 #5b2cff);
            }
            QProgressBar {
                background: rgba(0,0,0,120);
                color: #e9d6ff;
                border-radius: 6px;
                height: 18px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                             stop:0 #9a4dff, stop:1 #6b2cff);
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        self.entry = QTextEdit()
        self.entry.setPlaceholderText("Pega aqui las rutas de los wallpapers")
        layout.addWidget(self.entry)

        btns = QHBoxLayout()
        self.btn_clear = QPushButton("Limpiar")
        self.btn_extract = QPushButton("Extraer")
        btns.addWidget(self.btn_clear)
        btns.addWidget(self.btn_extract)
        layout.addLayout(btns)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.btn_clear.clicked.connect(self.entry.clear)
        self.btn_extract.clicked.connect(self.start_extraction)

    def resizeEvent(self, event):
        self.particle_bg.setGeometry(0, 0, self.width(), self.height())
        cw = int(self.width() * 0.62)
        ch = int(self.height() * 0.72)
        self.container.resize(cw, ch)
        self.container.move(int((self.width() - cw) / 2), int((self.height() - ch) / 2))
        super().resizeEvent(event)

    def start_extraction(self):
        rutas = self.entry.toPlainText()
        if not rutas.strip():
            self.log.append("Ingresa rutas primero")
            return

        self.thread = ExtractThread(rutas)
        self.thread.progress_signal.connect(self.progress.setValue)
        self.thread.log_signal.connect(lambda msg: self.log.append(msg))
        self.thread.finished_signal.connect(lambda: self.log.append("Proceso completado"))
        self.thread.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WallpaperExtractor()
    window.show()
    sys.exit(app.exec())