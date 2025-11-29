#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel

class OrbbecDepthView(QLabel):
    """
    Widget Qt simple qui affiche une image de profondeur convertie en RGB.
    Le pipeline fournit une matrice (H, W) uint16 avec profondeur en mm.
    ICI on convertit en niveaux de gris 8-bit puis RGB pour Qt.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background:black; border:1px solid #444;")
        self.depth_converter = None   # assigné par GridUI au démarrage

    # ---------------------------------------------------------

    def update_image_ancienne(self, depth_mm):
        """
        Reçoit une image profondeur en millimètres (np.uint16, shape h×w).
        Applique une colormap, puis l'envoie au QLabel.
        """
        if depth_mm is None:
            return

        # 1. Échelle 0–255 pour la colormap (ton mappage réel dépendra)
        depth_8u = np.clip(depth_mm / 10, 0, 255).astype(np.uint8)

        # 2. Colormap Turbo (lisible et continue)
        colored = cv2.applyColorMap(depth_8u, cv2.COLORMAP_TURBO)

        # 3. Convertir BGR → RGB pour Qt
        colored_rgb = cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)

        # 4. Construire QImage
        h, w, _ = colored_rgb.shape
        qimg = QImage(colored_rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)

        # 5. Afficher
        pix = QPixmap.fromImage(qimg)
        self.setPixmap(pix)


    def update_image(self, depth_mm: np.ndarray):
        """
        Reçoit une image profondeur (en mm) produite par PipelineOrbbec
        et demande au pipeline de produire une colorisation Orbbec.
        """

        # Récupération du parent (GridUI) qui possède le pipeline
        if not hasattr(self.parent(), "pipeline"):
            return

        pipeline = self.parent().pipeline

        # Utiliser la colorisation du pipeline
        colored = pipeline.depth_to_orbbec_colormap(depth_mm)
        if colored is None:
            return

        # Conversion BGR→RGB pour Qt
        rgb = cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)

        h, w, _ = rgb.shape
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        self.setPixmap(QPixmap.fromImage(qimg))

