# -*- coding: utf-8 -*-
"""
calibration.py
Gestion du calibrage spatial entre les coordonnées du capteur Orbbec (plan au sol)
et la grille 6×6 de la Chambre sonore.

Principe:
- On enregistre 4 coins dans l'espace "monde" (en mètres ou unités cohérentes),
  correspondant aux coins du rectangle opératoire au sol: Top-Left, Top-Right,
  Bottom-Right, Bottom-Left (ordre anti-horaire recommandé).
- À partir de ces 4 points, on calcule une homographie (transformée projective)
  pour projeter toute coordonnée (x, y) du plan au sol vers des coordonnées
  normalisées u,v ∈ [0,1]×[0,1]. On quantifie ensuite u,v en cellules 6×6.

Hypothèses:
- orbbec_input/tracker fournissent des positions au sol (x,y), z étant ignoré ici.
- Le rectangle de travail est approximativement plan, points non colinéaires.

Fichier de config:
- calibration.json : contient les 4 coins, le sens, et options (filtrage, marges).
"""

import json
import os
from typing import Dict, List, Optional, Tuple

import numpy as np


class GridCalibrator:
    """
    Calibre une surface rectangulaire observée par le capteur vers une grille 6×6.
    """

    def __init__(self,
                 grid_rows: int = 6,
                 grid_cols: int = 6,
                 config_path: str = "calibration.json"):
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.config_path = config_path

        # Liste de 4 coins dans l'ordre: TL, TR, BR, BL (anti-horaire)
        # Chaque coin est un tuple (x, y) en coordonnées "sol".
        self.corners: List[Tuple[float, float]] = []

        # Matrice d'homographie 3×3 (numpy) de l'espace capteur → espace normalisé [0,1]^2
        self.H: Optional[np.ndarray] = None

        # Paramètres optionnels
        self.margin_u: float = 0.0  # marge de sécurité horizontale dans l'espace normalisé
        self.margin_v: float = 0.0  # marge de sécurité verticale dans l'espace normalisé
        self.smooth_alpha: float = 0.4  # lissage EMA pour positions (optionnel)

        # Mémoire pour lissage
        self._ema_u: Optional[float] = None
        self._ema_v: Optional[float] = None

        # Chargement si un fichier existe
        self.load_if_exists()

    # ----------------------
    # Persistance
    # ----------------------
    def load_if_exists(self) -> bool:
        if os.path.isfile(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.grid_rows = int(data.get("grid_rows", self.grid_rows))
                self.grid_cols = int(data.get("grid_cols", self.grid_cols))
                self.margin_u = float(data.get("margin_u", 0.0))
                self.margin_v = float(data.get("margin_v", 0.0))
                self.smooth_alpha = float(data.get("smooth_alpha", 0.4))
                corners = data.get("corners", [])
                if len(corners) == 4:
                    self.corners = [(float(p[0]), float(p[1])) for p in corners]
                    self.compute_homography()
                return True
            except Exception:
                return False
        return False

    def save(self) -> None:
        data = {
            "grid_rows": self.grid_rows,
            "grid_cols": self.grid_cols,
            "margin_u": self.margin_u,
            "margin_v": self.margin_v,
            "smooth_alpha": self.smooth_alpha,
            "corners": self.corners
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ----------------------
    # Gestion des coins
    # ----------------------
    def clear_corners(self) -> None:
        self.corners = []
        self.H = None
        self._ema_u = None
        self._ema_v = None

    def add_corner(self, x: float, y: float) -> int:
        """
        Ajoute un coin (x,y). L'ordre attendu: TL, TR, BR, BL.
        Retourne le nombre de coins enregistrés après ajout.
        """
        self.corners.append((float(x), float(y)))
        if len(self.corners) == 4:
            self.compute_homography()
        return len(self.corners)

    # ----------------------
    # Calcul de l'homographie
    # ----------------------
    def compute_homography(self) -> None:
        """
        Calcule la matrice d'homographie H telle que:
        [u, v, 1]^T ≈ H · [x, y, 1]^T
        où (u,v) sont dans [0,1]×[0,1] si (x,y) est dans le quadrilatère des coins.
        La cible est le rectangle unité: TL=(0,0), TR=(1,0), BR=(1,1), BL=(0,1).
        """
        if len(self.corners) != 4:
            self.H = None
            return

        src = np.array(self.corners, dtype=np.float64)  # TL, TR, BR, BL
        dst = np.array([
            [0.0, 0.0],  # TL
            [1.0, 0.0],  # TR
            [1.0, 1.0],  # BR
            [0.0, 1.0]   # BL
        ], dtype=np.float64)

        self.H = self._find_homography(src, dst)

    @staticmethod
    def _find_homography(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
        """
        Calcule H (DLT) à partir de 4 correspondances 2D → 2D.
        src: (4,2), dst: (4,2)
        """
        A = []
        for (x, y), (u, v) in zip(src, dst):
            A.append([x, y, 1, 0, 0, 0, -u*x, -u*y, -u])
            A.append([0, 0, 0, x, y, 1, -v*x, -v*y, -v])
        A = np.asarray(A, dtype=np.float64)
        # SVD
        _, _, Vt = np.linalg.svd(A)
        h = Vt[-1, :]
        H = h.reshape((3, 3))
        return H

    # ----------------------
    # Transformations
    # ----------------------
    def world_to_unit(self, x: float, y: float, smooth: bool = True) -> Optional[Tuple[float, float]]:
        """
        Transforme (x,y) monde → (u,v) normalisé via H.
        Applique un lissage EMA optionnel et les marges.
        Retourne None si H non défini.
        """
        if self.H is None:
            return None
        X = np.array([x, y, 1.0], dtype=np.float64)
        uvw = self.H @ X
        if abs(uvw[2]) < 1e-9:
            return None
        u = uvw[0] / uvw[2]
        v = uvw[1] / uvw[2]

        # Lissage EMA
        if smooth:
            if self._ema_u is None:
                self._ema_u, self._ema_v = u, v
            else:
                a = self.smooth_alpha
                self._ema_u = a * u + (1 - a) * self._ema_u
                self._ema_v = a * v + (1 - a) * self._ema_v
            u, v = self._ema_u, self._ema_v

        # Marges (rogner)
        u = min(max(u, 0.0 + self.margin_u), 1.0 - self.margin_u)
        v = min(max(v, 0.0 + self.margin_v), 1.0 - self.margin_v)
        return (u, v)

    def unit_to_cell(self, u: float, v: float) -> Tuple[int, int]:
        """
        Convertit (u,v) ∈ [0,1]^2 en indices (row, col) dans la grille 6×6.
        Clamp et bordure incluse: u=1 → col=5, v=1 → row=5.
        """
        col = int(np.floor(u * self.grid_cols))
        row = int(np.floor(v * self.grid_rows))
        col = min(max(col, 0), self.grid_cols - 1)
        row = min(max(row, 0), self.grid_rows - 1)
        return (row, col)

    def world_to_cell(self, x: float, y: float, smooth: bool = True) -> Optional[Tuple[int, int]]:
        """
        Chaîne complète: (x,y) monde → (u,v) → (row,col). None si non calibré.
        """
        uv = self.world_to_unit(x, y, smooth=smooth)
        if uv is None:
            return None
        return self.unit_to_cell(*uv)

