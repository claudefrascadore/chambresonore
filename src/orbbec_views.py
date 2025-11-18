#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OrbbecColorView / OrbbecDepthView
Version corrigée et stable pour SDK Orbbec 2.0.15.
Deux pipelines totalement séparés, sans alignement matériel,
sans post-processing (obligatoire pour éviter DisparityTransform#2).
Affichage couleur et profondeur compatibles avec grid_ui.
"""

import cv2
import numpy as np
import pyorbbecsdk as ob

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel


# -------------------------------------------------------------------------
#   OUTILS DE CONVERSION EXACTEMENT REPRIS DU MODELE D’ORIGINE
# -------------------------------------------------------------------------

def simple_color_to_bgr(frame: "ob.ColorFrame") -> np.ndarray | None:
    """Convertit un frame RGB en BGR (OpenCV)."""
    width = frame.get_width()
    height = frame.get_height()
    data = np.frombuffer(frame.get_data(), dtype=np.uint8)

    if data.size != width * height * 3:
        return None

    rgb = data.reshape((height, width, 3))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return bgr


def depth_to_colormap(frame: "ob.DepthFrame",
                      min_depth_mm: int = 150,
                      max_depth_mm: int = 2000) -> np.ndarray:
    """Conversion profondeur → colormap (Magma)."""
    width = frame.get_width()
    height = frame.get_height()

    depth_data = np.frombuffer(frame.get_data(),
                               dtype=np.uint16).reshape((height, width))

    depth_clipped = np.clip(depth_data, min_depth_mm, max_depth_mm)
    depth_inverted = max_depth_mm - depth_clipped
    depth_normalized = cv2.normalize(depth_inverted, None, 0, 255,
                                     cv2.NORM_MINMAX).astype(np.uint8)

    depth_colored = cv2.applyColorMap(depth_normalized,
                                      cv2.COLORMAP_MAGMA)
    return depth_colored


# -------------------------------------------------------------------------
#   CHOIX DES PROFILS EXACTEMENT COMME DANS LE MODELE
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


def choose_depth_profile(pipeline: "ob.Pipeline") -> "ob.VideoStreamProfile":
    profiles = pipeline.get_stream_profile_list(ob.OBSensorType.DEPTH_SENSOR)

    for p in profiles:
        if (p.get_format() == ob.OBFormat.Y16 and
                p.get_width() == 640 and
                p.get_height() == 400 and
                p.get_fps() == 30):
            print("Profil profondeur sélectionné : Y16 640x400 @ 30")
            return p

    try:
        d = profiles.get_default_video_stream_profile()
        print(f"Profil profondeur fallback : {d.get_format()} {d.get_width()}x{d.get_height()} @ {d.get_fps()}")
        return d
    except Exception:
        raise RuntimeError("Impossible d’obtenir un profil profondeur.")


# -------------------------------------------------------------------------
#   CLASSES QT — UNE POUR LA COULEUR, UNE POUR LA PROFONDEUR
# -------------------------------------------------------------------------

class OrbbecColorView(QLabel):
    """
    Pipeline couleur Orbbec autonome.
    IMPORTANT : post-processing désactivé (SDK 2.0.15)
    """

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
        print("Initialisation OrbbecColorView (pipeline couleur)…")
        self.pipeline = ob.Pipeline()
        self.config = ob.Config()

        color_p = choose_color_profile(self.pipeline)

        # COULEUR SEULE (pipeline séparé)
        self.config.enable_stream(color_p)

        # Désactivation obligatoire des filtres internes (SDK 2.0.15)
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


# -------------------------------------------------------------------------

class OrbbecDepthView(QLabel):
    """
    Pipeline profondeur Orbbec autonome.
    IMPORTANT : post-processing désactivé (SDK 2.0.15)
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background:black;border:1px solid gray;")

        self.pipeline = None
        self.config = None

        try:
            self._init_pipeline()
        except Exception as e:
            print("Erreur init OrbbecDepthView :", e)
            self.pipeline = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    # ------------------------------------------------------------------

    def _init_pipeline(self) -> None:
        print("Initialisation OrbbecDepthView (pipeline profondeur)…")
        self.pipeline = ob.Pipeline()
        self.config = ob.Config()

        depth_p = choose_depth_profile(self.pipeline)

        # PROFONDEUR SEULE (pipeline séparé)
        self.config.enable_stream(depth_p)

        # Désactivation obligatoire des filtres internes
        self.config.set_enable_post_processing(False)

        self.pipeline.start(self.config)
        print("Pipeline profondeur Orbbec démarré.")

    # ------------------------------------------------------------------

    def update_frame(self) -> None:
        if not self.pipeline:
            return

        frames = self.pipeline.wait_for_frames(1)
        if frames is None:
            return

        depth = frames.get_depth_frame()
        if depth is None:
            return

        img = depth_to_colormap(depth)

        h, w, _ = img.shape
        qimg = QImage(img.data, w, h, 3 * w, QImage.Format.Format_BGR888)
        self.setPixmap(QPixmap.fromImage(qimg))

