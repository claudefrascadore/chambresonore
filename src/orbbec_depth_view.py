# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# Chambre sonore — Vue profondeur (fausses couleurs, V4L2)
# ------------------------------------------------------------
import cv2
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel

__all__ = ["OrbbecDepthView"]

class OrbbecDepthView(QLabel):
    """
    Affiche la “profondeur” simulée à partir du flux IR/Depth V4L2
    (fausses couleurs pour visualisation).
    """
    def __init__(self, cap_width=640, cap_height=400, fps=30, device="/dev/video0", parent=None):
        super().__init__(parent)
        self.cap_width = cap_width
        self.cap_height = cap_height
        self.fps = fps
        self.device = device

        self.cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            print(f"⚠️ Impossible d’ouvrir {self.device} (flux profondeur)")
        else:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cap_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cap_height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            print(f"🎥 Flux profondeur actif ({self.cap_width}x{self.cap_height} @ {self.fps}fps via V4L2)")

        self.setFixedSize(self.cap_width, self.cap_height)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background:black;border:1px solid gray;")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(int(1000 / self.fps))

    def update_frame(self):
        if not self.cap or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        depth = cv2.applyColorMap(gray, cv2.COLORMAP_TURBO)
        image = QImage(depth.data, depth.shape[1], depth.shape[0], QImage.Format.Format_BGR888)
        self.setPixmap(QPixmap.fromImage(image))

    def closeEvent(self, event):
        if self.cap and self.cap.isOpened():
            self.cap.release()
        event.accept()

