#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OrbbecDepthView — Vue Qt affichant uniquement les frames reçues.
NE CRÉE PAS de pipeline !
"""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QImage, QPixmap


class OrbbecDepthView(QLabel):
    def __init__(self, pipeline, parent=None):
        super().__init__(parent)

        self.pipeline = pipeline
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background:black;border:1px solid gray;")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def update_frame(self):
        img = self.pipeline.get_depth_frame()
        if img is None:
            return

        h, w, _ = img.shape
        qimg = QImage(img.data, w, h, 3 * w, QImage.Format.Format_BGR888)
        self.setPixmap(QPixmap.fromImage(qimg))

