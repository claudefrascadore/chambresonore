#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel

class OrbbecDepthView(QLabel):
    """
    Widget Qt simple qui affiche une image BGR (colormap déjà généré).
    Aucune logique pipeline ici : on ne fait qu'afficher.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background:black; border:1px solid #444;")

    # ---------------------------------------------------------

    def update_image(self, img):
        """
        Reçoit une image BGR numpy (640×400 par ex.)
        et l'affiche dans le QLabel.
        """

        h, w, _ = img.shape
        qimg = QImage(
            img.data, w, h,
            3 * w,
            QImage.Format.Format_BGR888
        )

        self.setPixmap(QPixmap.fromImage(qimg))

