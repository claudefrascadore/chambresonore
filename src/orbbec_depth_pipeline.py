#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PipelineOrbbec — Pipeline profondeur seul, SANS Qt.
Initialisé avant QApplication pour éviter le bug DisparityTransform.
"""

import cv2
import numpy as np
import pyorbbecsdk as ob


class PipelineOrbbec:
    def __init__(self):
        print(">>> Initialisation PipelineOrbbec (hors Qt)…")

        self.pipeline = ob.Pipeline()
        self.config = ob.Config()

        # Récupère un profil profondeur simple
        profiles = self.pipeline.get_stream_profile_list(ob.OBSensorType.DEPTH_SENSOR)

        depth_p = None
        for p in profiles:
            if (p.get_format() == ob.OBFormat.Y16 and
                    p.get_width() == 640 and
                    p.get_height() == 400):
                depth_p = p
                print("Profil profondeur 640x400 trouvé.")
                break

        if depth_p is None:
            depth_p = profiles[0]
            print("Profil fallback sélectionné.")

        self.config.enable_stream(depth_p)

        # Pas d’alignement, pas de post-processing
        try: self.config.set_enable_post_processing(False)
        except: pass

        # Démarrage pipeline
        self.pipeline.start(self.config)
        print(">>> Pipeline Orbbec démarré.")

    # -------------------------------------------------------------

    def get_depth_frame(self):
        """Retourne une image profondeur colormap Magma."""
        frameset = self.pipeline.wait_for_frames(100)
        if frameset is None:
            return None

        depth = frameset.get_depth_frame()
        if depth is None:
            return None

        width = depth.get_width()
        height = depth.get_height()
        depth_data = np.frombuffer(depth.get_data(), dtype=np.uint16).reshape((height, width))

        # Normalisation
        depth_clipped = np.clip(depth_data, 150, 2000)
        depth_inverted = 2000 - depth_clipped
        depth_norm = cv2.normalize(depth_inverted, None, 0, 255,
                                   cv2.NORM_MINMAX).astype(np.uint8)

        return cv2.applyColorMap(depth_norm, cv2.COLORMAP_MAGMA)

