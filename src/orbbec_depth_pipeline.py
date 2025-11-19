#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
orbbec_depth_pipeline.py
Pipeline profondeur Orbbec séparé, SANS Qt.
Une seule lecture de frames via poll(), avec buffering :
    - last_depth_raw      : profondeur brute (mm)
    - last_depth_colormap : image BGR colormap Magma
"""

import cv2
import numpy as np
import pyorbbecsdk as ob


class PipelineOrbbec:
    def __init__(self):
        print(">>> Initialisation PipelineOrbbec (hors Qt)…")

        self.pipeline = ob.Pipeline()
        self.config = ob.Config()

        # Sélection d'un profil profondeur 640x400 si disponible
        profiles = self.pipeline.get_stream_profile_list(ob.OBSensorType.DEPTH_SENSOR)

        depth_p = None
        for p in profiles:
            try:
                if (p.get_format() == ob.OBFormat.Y16 and
                        p.get_width() == 640 and
                        p.get_height() == 400 and
                        p.get_fps() == 30):
                    depth_p = p
                    print("Profil profondeur 640x400 @30 trouvé.")
                    break
            except Exception:
                pass

        if depth_p is None:
            depth_p = profiles[0]
            print("Profil profondeur fallback sélectionné :",
                  depth_p.get_width(), "x", depth_p.get_height(),
                  "@", depth_p.get_fps())

        self.config.enable_stream(depth_p)

        try:
            self.config.set_enable_post_processing(False)
        except Exception:
            pass

        self.pipeline.start(self.config)
        print(">>> Pipeline Orbbec démarré.")

        self.last_depth_raw = None
        self.last_depth_colormap = None

    # ------------------------------------------------------------------

    def _depth_to_colormap(self, depth_data,
                           min_depth_mm: int = 150,
                           max_depth_mm: int = 2000):
        depth_clipped = np.clip(depth_data, min_depth_mm, max_depth_mm)
        depth_inverted = max_depth_mm - depth_clipped
        depth_norm = cv2.normalize(depth_inverted, None, 0, 255,
                                   cv2.NORM_MINMAX).astype(np.uint8)
        return cv2.applyColorMap(depth_norm, cv2.COLORMAP_MAGMA)

    # ------------------------------------------------------------------

    def poll(self) -> bool:
        """
        Lit UNE frame profondeur depuis le pipeline et met à jour les buffers :
            - last_depth_raw
            - last_depth_colormap
        Retourne True si une frame valide a été lue, False sinon.
        """
        frameset = self.pipeline.wait_for_frames(1)
        if frameset is None:
            return False

        depth = frameset.get_depth_frame()
        if depth is None:
            return False

        w = depth.get_width()
        h = depth.get_height()

        depth_data = np.frombuffer(depth.get_data(),
                                   dtype=np.uint16).reshape((h, w))

        self.last_depth_raw = depth_data
        self.last_depth_colormap = self._depth_to_colormap(depth_data)
        return True

    # ------------------------------------------------------------------

    def get_depth_data(self):
        """Retourne la dernière matrice profondeur brute (mm) ou None."""
        return self.last_depth_raw

    # ------------------------------------------------------------------

    def get_depth_frame(self):
        """Retourne la dernière image BGR colormap ou None."""
        return self.last_depth_colormap

