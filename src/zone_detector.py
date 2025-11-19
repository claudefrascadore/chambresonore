# -*- coding: utf-8 -*-

import numpy as np

class ZoneDetector:
    def __init__(self, rows=6, cols=6, frame_w=640, frame_h=400):
        self.rows = rows
        self.cols = cols
        self.frame_w = frame_w
        self.frame_h = frame_h

        self.cell_w = frame_w // cols
        self.cell_h = frame_h // rows

    # --------------------------------------------------------------

    def analyze(self, depth_data):
        """
        Retourne une matrice 6×6 contenant la distance (mm) dans chaque zone.
        Méthode : médiane des pixels (robuste au bruit).
        """

        zones = np.zeros((self.rows, self.cols), dtype=np.uint16)

        for r in range(self.rows):
            for c in range(self.cols):
                x1 = c * self.cell_w
                y1 = r * self.cell_h
                x2 = x1 + self.cell_w
                y2 = y1 + self.cell_h

                cell = depth_data[y1:y2, x1:x2]

                d = np.median(cell)
                zones[r, c] = int(d)

        return zones

    def activation_map(self, zones_mm, threshold=1200):
        """
        Retourne une matrice 6×6 de booléens :
        True  = zone active (présence détectée)
        False = zone inactive
        """
        active = (zones_mm > 0) & (zones_mm < threshold)
        return active

