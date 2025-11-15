# -*- coding: utf-8 -*-
"""
grid_ui.py — Vue portrait (tablette)
Affiche une seule vue vidéo (UvcView) et permet de basculer
entre couleur (/dev/video4) et profondeur (/dev/video0),
avec grille 6×6 et panneau de calibration.
"""

from PyQt6.QtCore import Qt, QRectF, QSize, QTimer
from PyQt6.QtGui import QColor, QPen, QBrush, QFont, QPainter
from PyQt6.QtWidgets import (
    QWidget, QGraphicsScene, QGraphicsView, QGraphicsRectItem,
    QGraphicsSimpleTextItem, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSlider, QFrame
)

from src.camera_view import UvcView
from src.orbbec_depth_view import OrbbecDepthView


# ------------------------------------------------------------
# Cellule de la grille
# ------------------------------------------------------------
class GridCell(QGraphicsRectItem):
    def __init__(self, x, y, w, h, label="", parent=None):
        super().__init__(x, y, w, h, parent)
        self.setBrush(QBrush(QColor(30, 30, 30)))
        self.setPen(QPen(QColor(80, 80, 80), 1))
        self.text = QGraphicsSimpleTextItem(label, self)
        self.text.setBrush(QBrush(Qt.GlobalColor.white))
        font = QFont("Arial", 8)
        self.text.setFont(font)
        self.text.setPos(x + w * 0.5 - 14, y + h * 0.5 - 9)
        self.active = False

    def set_active(self, state=True):
        self.active = state
        color = QColor(0, 200, 120) if state else QColor(30, 30, 30)
        self.setBrush(QBrush(color))


# ------------------------------------------------------------
# Panneau de calibration
# ------------------------------------------------------------
class CalibrationPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("<b>Calibration</b>")
        layout.addWidget(title)

        self.btn_arm = QPushButton("Armer la calibration")
        self.btn_capture = QPushButton("Capturer la position")
        self.btn_save = QPushButton("Sauvegarder")
        layout.addWidget(self.btn_arm)
        layout.addWidget(self.btn_capture)
        layout.addWidget(self.btn_save)

        layout.addWidget(QLabel("Luminosité :"))
        self.slider_brightness = QSlider(Qt.Orientation.Horizontal)
        self.slider_brightness.setRange(0, 100)
        self.slider_brightness.setValue(50)
        layout.addWidget(self.slider_brightness)

        layout.addStretch(1)
        self.setLayout(layout)


# ------------------------------------------------------------
# Grille centrale
# ------------------------------------------------------------
class GridView(QGraphicsView):
    def __init__(self, rows=6, cols=6, full_width_px=480, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.cell_size = max(20, int(full_width_px // max(1, cols)))

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.cells = []
        self._init_grid()

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("background: #111;")

    def _init_grid(self):
        for i in range(self.rows):
            for j in range(self.cols):
                x, y = j * self.cell_size, i * self.cell_size
                rect = GridCell(x, y, self.cell_size, self.cell_size, f"{i},{j}")
                self.scene.addItem(rect)
                self.cells.append(rect)
        w = self.cols * self.cell_size
        h = self.rows * self.cell_size
        self.setSceneRect(QRectF(0, 0, w, h))
        self.setFixedSize(w + 2, h + 2)

    def set_cell_active(self, row, col, active=True):
        idx = row * self.cols + col
        if 0 <= idx < len(self.cells):
            self.cells[idx].set_active(active)

    def clear_active(self):
        for c in self.cells:
            c.set_active(False)


# ------------------------------------------------------------
# Interface principale
# ------------------------------------------------------------
class GridUI(QWidget):
    def __init__(self, tracker=None, calibrator=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chambre sonore — Vue portrait tablette")
        self.tracker = tracker
        self.calibrator = calibrator
        self.current_mode = "color"

        cap_w, cap_h = 640, 480
        scale = 0.75
        disp_w, disp_h = int(cap_w * scale), int(cap_h * scale)

        # ---- En-tête ----
        self.video_label = QLabel("<b>Flux caméra (couleur)</b>")
        self.btn_switch = QPushButton("→ Basculer vers profondeur")
        self.btn_switch.clicked.connect(self.toggle_mode)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.video_label)
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_switch)

        # ---- Vue vidéo ----
        self.view_video = UvcView(
            device="/dev/video4",
            cap_width=cap_w,
            cap_height=cap_h,
            fps=30,
            display_width=disp_w,
            display_height=disp_h,
            force_gray=False
        )

        vid_wrap = QHBoxLayout()
        vid_wrap.addStretch(1)
        vid_wrap.addWidget(self.view_video)
        vid_wrap.addStretch(1)

        video_zone = QWidget()
        self.video_zone = video_zone

        video_zone.setLayout(QVBoxLayout())
        video_zone.layout().setContentsMargins(0, 0, 0, 0)
        video_zone.layout().setSpacing(4)
        video_zone.layout().addLayout(btn_layout)
        video_zone.layout().addLayout(vid_wrap)

        # ---- Grille + panneau ----
        self.view_grid = GridView(rows=6, cols=6, full_width_px=disp_w)
        self.panel = CalibrationPanel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(video_zone, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.view_grid, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.panel)
        self.setLayout(layout)

        self.setFixedWidth(disp_w + 40)
        self.setMinimumHeight(900)

        self._tick = QTimer(self)
        self._tick.timeout.connect(self.update_cells)
        self._tick.start(50)

    # ---- bascule Couleur ↔ Profondeur ----
    def toggle_mode(self):
        old_view = self.view_video  # sauvegarde du widget actuel

        if self.current_mode == "color":
            self.current_mode = "depth"
            self.view_video = OrbbecDepthView()
            self.btn_switch.setText("→ Basculer vers couleur")
            self.video_label.setText("<b>Flux caméra (profondeur)</b>")
        else:
            self.current_mode = "color"
            self.view_video = UvcView(device="/dev/video4")
            self.btn_switch.setText("→ Basculer vers profondeur")
            self.video_label.setText("<b>Flux caméra (couleur)</b>")

        layout = self.video_zone.layout()
        layout.replaceWidget(old_view, self.view_video)
        old_view.setParent(None)
        self.view_video.show()

    # ---- mise à jour des cellules ----
    def update_cells(self):
        self.view_grid.clear_active()
        if not self.tracker:
            return
        try:
            targets = self.tracker.get_targets()
        except Exception:
            return
        for t in targets:
            if t.get("cell"):
                r, c = t["cell"]
                self.view_grid.set_cell_active(r, c, True)

    def closeEvent(self, event):
        try:
            self.view_video.close()
        except Exception:
            pass
        event.accept()

