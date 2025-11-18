#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OrbbecColorView
Réservée pour utilisation ultérieure dans une autre page.
Pipeline couleur seul, sans post-processing (SDK 2.0.15).
"""

import cv2
import numpy as np
import pyorbbecsdk as ob

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel


# -------------------------------------------------------------------------
#   Conversion RGB → BGR
# -------------------------------------------------------------------------

def simple_color_to_bgr(frame: "ob.ColorFrame") -> np.ndarray | None:
    width = frame.get_width()
    height = frame.get_height()
    data = np.frombuffer(frame.get_data(), dtype=np.uint8)

    if data.size != width * height * 3:
        return None

    rgb = data.reshape((height, width, 3))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return bgr


# -------------------------------------------------------------------------
#   Profil couleur
# -------------------------------------------------------------------------

def choose_color_profile(pipeline: "ob.Pipeline") -> "ob.VideoStreamProfile":
    profiles = pipeline.get_stream_profile_list(ob.OBSensorType.COLOR_SENSOR)

    for p in profiles:
        if (p.get_format() == ob.OBFormat.RGB and
                p.get_width() == 640 and
                p.get_height() == 480 and
                p.get_fps() == 30):
            print("Profil couleur sélectionné : RGB 640x480 @ 30")
            return p

    for p in profiles:
        if p.get_format() == ob.OBFormat.RGB:
            print(f"Profil couleur fallback : RGB {p.get_width()}x{p.get_height()} @ {p.get_fps()}")
            return p

    raise RuntimeError("Aucun profil RGB disponible.")


# -------------------------------------------------------------------------
#   CLASSE QT — VUE COULEUR (non utilisée pour l’instant)
# -------------------------------------------------------------------------

class OrbbecColorView(QLabel):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background:black;border:1px solid gray;")

        self.pipeline = None
        self.config = None

        try:
            self._init_pipeline()
        except Exception as e:
            print("Erreur init OrbbecColorView :", e)
            self.pipeline = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    # ------------------------------------------------------------------

    def _init_pipeline(self) -> None:
        print("Initialisation OrbbecColorView (couleur seule)…")
        self.pipeline = ob.Pipeline()
        self.config = ob.Config()

        color_p = choose_color_profile(self.pipeline)

        # Couleur seule
        self.config.enable_stream(color_p)

        # Désactivation des filtres internes
        self.config.set_enable_post_processing(False)

        self.pipeline.start(self.config)
        print("Pipeline couleur Orbbec démarré.")

    # ------------------------------------------------------------------

    def update_frame(self) -> None:
        if not self.pipeline:
            return

        frames = self.pipeline.wait_for_frames(1)
        if frames is None:
            return

        color = frames.get_color_frame()
        if color is None:
            return

        img = simple_color_to_bgr(color)
        if img is None:
            return

        h, w, _ = img.shape
        qimg = QImage(img.data, w, h, 3 * w, QImage.Format.Format_BGR888)
        self.setPixmap(QPixmap.fromImage(qimg))

