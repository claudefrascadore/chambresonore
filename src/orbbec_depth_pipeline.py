"""
orbbec_depth_pipeline.py
Version : SDK v2 – Python 3.12 – Chambre Sonore

Pipeline Orbbec basé sur libobsensor 2.x et pyorbbecsdk 2.x.
Compatible Gemini 336, Gemini 2, Gemini 435Le.

Fonctions fournies :
    poll() -> bool
    get_depth_frame() -> ndarray uint16
    get_color_frame() -> ndarray uint8 (H, W, 3)
    get_depth_data() -> alias profondeur

Aucune simulation.
Pipeline double : profondeur + couleur.
"""

from __future__ import annotations

import numpy as np
import cv2

from typing import Optional
from dataclasses import dataclass

from pyorbbecsdk import (
    Pipeline,
    Config,
    OBFormat,
    OBSensorType
)

from src.y16_depth_converter import Y16DepthConverter



# ----------------------------------------------------------------------
# Paramètres par défaut
# ----------------------------------------------------------------------

@dataclass
class PipelineConfig:
    depth_width: int = 640
    depth_height: int = 480
    depth_fps: int = 30

    color_width: int = 640
    color_height: int = 480
    color_fps: int = 30

    enable_color: bool = True


# ----------------------------------------------------------------------
# Pipeline Orbbec pour Chambre Sonore (SDK v2)
# ----------------------------------------------------------------------

class PipelineOrbbec:
    def __init__(self, config: Optional[PipelineConfig] = None) -> None:
        self.cfg = config or PipelineConfig()

        self.pipeline = Pipeline()
        self.config = Config()

        self._last_depth_raw: Optional[np.ndarray] = None
        self._last_color_rgb: Optional[np.ndarray] = None

        # Profondeur
        self._setup_depth_stream()

        # ---------------------------------------------------------------
        # PATCH : activer un mode profondeur longue portée si disponible
        # ---------------------------------------------------------------
        try:
            dev = self.pipeline.get_device()
            sensor = dev.get_sensor(OB_SENSOR_DEPTH)
            modes = sensor.get_supported_depth_work_modes()

            long_range = [
                m for m in modes
                if "long" in m.lower() or "range" in m.lower()
            ]

            if long_range:
                sensor.set_depth_work_mode(long_range[0])
                print("Mode profondeur activé :", long_range[0])
            else:
                print("Aucun mode longue portée disponible.")
        except Exception as e:
            print("Impossible de configurer le depth_work_mode :", e)
        # ---------------------------------------------------------------

        # Conversion de la profondeur
        self.depth_converter = Y16DepthConverter(shift_bits=2, bilateral=True)

        # Couleur
        if self.cfg.enable_color:
            self._setup_color_stream()

        # Démarre le pipeline
        self.pipeline.start(self.config)

    # ------------------------------------------------------------------

    def _setup_depth_stream(self):
        print("=== _setup_depth_stream() : activation simple du flux DEPTH ===")

        try:
            self.config.enable_stream(OBSensorType.DEPTH_SENSOR)
            print("→ Flux profondeur activé (profil automatique sélectionné par Orbbec).")
        except Exception as e:
            raise RuntimeError(f"Impossible d'activer le flux profondeur → {e}")
    # ------------------------------------------------------------------

    def _setup_color_stream(self) -> None:
        try:
            plist = self.pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)
        except OBException:
            self._color_enabled = False
            return

        try:
            profile = plist.get_video_stream_profile(
                self.cfg.color_width,
                self.cfg.color_height,
                OBFormat.RGB,
                self.cfg.color_fps,
            )
        except OBException:
            try:
                profile = plist.get_default_video_stream_profile()
            except OBException:
                self._color_enabled = False
                return

        self.config.enable_stream(profile)
        self._color_enabled = True

    # ------------------------------------------------------------------
    # Lecture des frames
    # ------------------------------------------------------------------

    def poll(self, timeout: int = 1) -> bool:
        """
        Récupère une paire de frames (profondeur + couleur).
        Retourne True si une profondeur valide est reçue.
        """

        try:
            frameset = self.pipeline.wait_for_frames(timeout)
        except OBException:
            return False

        if frameset is None:
            return False

        # Frame profondeur
        depth = frameset.get_depth_frame()
        if depth is None:
            # Frame invalide → caméra hors portée ou perte de synchro
            self._last_depth_mm = None
            return False

        # Échelle officielle Orbbec
        scale = depth.get_depth_scale()

        if depth is None:
            return False

        h = depth.get_height()
        w = depth.get_width()

        buffer = depth.get_data()              # buffer brut
        size = depth.get_data_size()           # taille en bytes

        # Construire tableau numpy avec la taille exacte
        y16 = np.frombuffer(buffer, dtype=np.uint16, count=size // 2).reshape(h, w)
        depth_mm = (y16.astype(np.float32) * scale).astype(np.float32)
        self._last_depth_raw = depth_mm


        # Frame couleur
        color = frameset.get_color_frame()

        if color is not None:
            fmt = color.get_format()

            if fmt == OBFormat.RGB:
                ch = color.get_height()
                cw = color.get_width()
                color_data = color.get_data()
                color_np = np.frombuffer(color_data, dtype=np.uint8).reshape(ch, cw, 3)
                self._last_color_rgb = color_np
            else:
                print("DEBUG COLOR: format non géré :", fmt)

        return True

    # ------------------------------------------------------------------
    # Méthode de colorisation Orbbec
    # ------------------------------------------------------------------
    def depth_to_orbbec_colormap(self, depth_mm: np.ndarray) -> np.ndarray:
        # Échelle fixe Orbbec (mm)
        MIN_MM = 600
        MAX_MM = 3500

        # Protection contre frames vides
        if depth_mm is None or depth_mm.size == 0:
            return None

        # Ramener dans la plage visible
        clipped = np.clip(depth_mm, MIN_MM, MAX_MM)

        # Normalisation 0–255
        norm = ((clipped - MIN_MM) / (MAX_MM - MIN_MM)) * 255.0
        norm8 = norm.astype(np.uint8)

        # Application du colormap « style Orbbec »
        colored = cv2.applyColorMap(norm8, cv2.COLORMAP_TURBO)

        return colored

    # ------------------------------------------------------------------
    # Accès aux données
    # ------------------------------------------------------------------

    def get_depth_frame(self):        
        return self._last_depth_raw

    def get_color_frame(self) -> Optional[np.ndarray]:
        return self._last_color_rgb

    def get_depth_data(self) -> Optional[np.ndarray]:
        return self._last_depth_raw

    # ------------------------------------------------------------------

    def stop(self) -> None:
        try:
            self.pipeline.stop()
        except Exception:
            pass

    def __del__(self) -> None:
        self.stop()

