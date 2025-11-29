#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import numpy as np
import cv2
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt


class OrbbecColorView(QLabel):
    """
    Affiche la vue couleur RGB provenant de Orbbec.
    Attendu : tableau numpy (H, W, 3) uint8 au format RGB.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background:black; border:1px solid #444;")

    def update_image(self, img):
        """
        img : numpy array (H, W, 3) uint8
        """
        if img is None:
            return
        if img.ndim != 3 or img.shape[2] != 3:
            return

        h, w, _ = img.shape

        qimg = QImage(
            img.data,
            w,
            h,
            w * 3,
            QImage.Format.Format_RGB888
        )

        self.setPixmap(QPixmap.fromImage(qimg))

