"""
y16_depth_converter.py
Chambre Sonore – Conversion Y16 → profondeur lisible (Z-map)

Compatible Gemini 336 + SDK v2.x

Convertit :
    - un tableau Y16 brut
    - en carte de profondeur en millimètres
    - avec option de filtrage bilatéral (OpenCV)
"""

import numpy as np
import cv2


class Y16DepthConverter:
    """
    Convertisseur Y16 → carte de profondeur en millimètres.
    """

    def __init__(self, shift_bits: int = 2, bilateral: bool = True):
        """
        shift_bits : nombre de bits à décaler pour corriger
            le codage interne du flux Y16 de la Gemini 336.
            La 336 encode souvent la profondeur << 2.
        bilateral : appliquer ou non un filtre bilatéral.
        """
        self.shift_bits = shift_bits
        self.bilateral = bilateral

    # ------------------------------------------------------------------

    def convert(self, y16_image: np.ndarray) -> np.ndarray:
        """
        Convertit une image Y16 brute en profondeur (mm).

        y16_image : tableau numpy 2D (uint16)

        Retourne :
            depth_mm : profondeur en millimètres (uint16)
        """

        if y16_image is None:
            return None

        # Correction du shift interne
        depth_mm = (y16_image >> self.shift_bits).astype(np.uint16)

        # Pour l’instant, on ne filtre plus (éviter segfault OpenCV)
        return depth_mm

    # ------------------------------------------------------------------

    def to_display_gray(self, depth_mm: np.ndarray) -> np.ndarray:
        """
        Convertit la profondeur en niveaux de gris pour affichage.

        depth_mm : tableau 2D uint16 (millimètres)

        Retourne :
            depth_rgb : image 8-bit RGB (H, W, 3)
        """

        if depth_mm is None:
            return None

        # Normalisation simple (mm → 8-bit)
        depth8 = np.clip(depth_mm / 16, 0, 255).astype(np.uint8)

        # Conversion gris → RGB (Qt exige du RGB)
        depth_rgb = cv2.cvtColor(depth8, cv2.COLOR_GRAY2RGB)

        return depth_rgb

