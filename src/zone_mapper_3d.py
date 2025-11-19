#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zone_mapper_3d.py
==================

Version révisée pour Chambre Sonore.

Objectif : fournir une position (x, y) cohérente dans la pièce à partir
de la carte de profondeur, en supposant :
  - la caméra placée à une hauteur connue
  - la caméra orientée le long de la largeur de la pièce (cas B1)
  - la personne est l'objet principal dans le champ

On travaille de façon pragmatique :
  1) reconstruction d'un nuage de points approximatif
  2) filtrage des points plausibles pour le corps
  3) utilisation de X (gauche-droite) et Z (avant-arrière) comme plan au sol
  4) barycentre robuste pour la position
  5) mappage dans la grille physique (rows x cols)
"""

from __future__ import annotations

import numpy as np


class ZoneMapper3D:
    """Convertit la profondeur en position (x, y) dans la pièce + cellule (r, c)."""

    def __init__(
        self,
        cam_height_m: float = 1.8,
        cam_angle_deg: float = 10.0,
        cam_wall_dist_m: float = 0.30,
        cam_offset_m: float = 0.0,
        fx: float = 580.0,
        fy: float = 580.0,
        cx: float = 320.0,
        cy: float = 200.0,
    ) -> None:
        """Initialise le mapper 3D.

        Paramètres:
            cam_height_m: hauteur de la caméra par rapport au sol (m).
            cam_angle_deg: pitch vers le bas (degrés, positif = regarde vers le sol).
            cam_wall_dist_m: distance entre la caméra et le mur latéral gauche
                de la pièce (cas B1). Sert à approximer la coordonnée X absolue
                dans la pièce.
            cam_offset_m: offset supplémentaire éventuel (non utilisé pour l'instant,
                gardé pour compatibilité).
            fx, fy, cx, cy: paramètres intrinsèques approximatifs de la caméra.
        """
        self.cam_height_m = cam_height_m
        self.cam_angle_deg = cam_angle_deg
        self.cam_wall_dist_m = cam_wall_dist_m
        self.cam_offset_m = cam_offset_m

        self.fx = fx
        self.fy = fy
        self.cx = cx
        self.cy = cy

        self._update_rotation_matrix()

    # ------------------------------------------------------------------

    def _update_rotation_matrix(self) -> None:
        """Construit la matrice de rotation à partir du pitch (rotation autour de X)."""
        pitch_rad = np.radians(self.cam_angle_deg)

        # Rotation autour de l'axe X (caméra qui regarde vers le bas)
        self.R = np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, np.cos(pitch_rad), -np.sin(pitch_rad)],
                [0.0, np.sin(pitch_rad), np.cos(pitch_rad)],
            ],
            dtype=np.float32,
        )

    # ------------------------------------------------------------------

    def compute_point_cloud(self, depth_data: np.ndarray) -> np.ndarray:
        """Convertit la carte de profondeur (mm) en nuage de points 3D (m) dans le repère caméra.

        depth_data: tableau (H, W) en millimètres.

        Retourne:
            cloud: tableau (N, 3) de points [Xc, Yc, Zc] en mètres, dans le repère caméra,
                   après rotation pour tenir compte du pitch, mais avant translation.
        """
        if depth_data is None:
            return np.zeros((0, 3), dtype=np.float32)

        H, W = depth_data.shape

        # Coordonnées de pixel
        xs = np.tile(np.arange(W, dtype=np.float32), H)
        ys = np.repeat(np.arange(H, dtype=np.float32), W)

        d = depth_data.reshape(-1).astype(np.float32) / 1000.0  # m
        valid = d > 0.2  # ignorer les valeurs trop proches ou nulles

        xs = xs[valid]
        ys = ys[valid]
        d = d[valid]

        # Projection pinhole inverse
        Xc = (xs - self.cx) * d / self.fx
        Yc = (ys - self.cy) * d / self.fy
        Zc = d

        pts = np.stack([Xc, Yc, Zc], axis=1)  # (N,3)

        # Appliquer la rotation de pitch
        rotated = pts @ self.R.T  # (N,3)

        return rotated  # repère caméra incliné

    # ------------------------------------------------------------------

    def project_to_ground(self, cloud: np.ndarray) -> np.ndarray:
        """Projette les points 3D sur un plan au sol approximatif (X = largeur, Y = profondeur).

        Hypothèses:
            - la caméra est à hauteur cam_height_m au-dessus du sol
            - Yc (après rotation) est l'axe vertical (positif vers le haut)
            - Zc est l'axe avant (en direction du regard)
            - Xc est l'axe gauche-droite

        On approxime que les points du corps se trouvent entre
        0.1 m et 2.2 m de hauteur (au-dessus du sol), et à une distance raisonnable
        devant la caméra (Zc entre 0.2 m et 6 m).

        Retourne:
            ground_xy: tableau (M, 2) où chaque ligne est [x_m, y_m] en mètres,
                       avec:
                           x_m ~ position gauche-droite absolue dans la pièce
                           y_m ~ distance avant-arrière dans la pièce
        """
        if cloud.size == 0:
            return np.zeros((0, 2), dtype=np.float32)

        Xc = cloud[:, 0]
        Yc = cloud[:, 1]
        Zc = cloud[:, 2]

        # Hauteur relative au sol (caméra à cam_height au-dessus du sol)
        # Approximation : Yc=0 ~ axe de la caméra, donc hauteur au-dessus du sol
        #     h = cam_height_m - Yc
        height_above_ground = self.cam_height_m - Yc

        # Filtrer les points plausibles pour le corps
        mask = (
            (height_above_ground > 0.1)
            & (height_above_ground < 2.2)
            & (Zc > 0.2)
            & (Zc < 6.0)
        )

        if not np.any(mask):
            return np.zeros((0, 2), dtype=np.float32)

        Xc = Xc[mask]
        Zc = Zc[mask]

        # Position absolue dans la pièce (cas B1) :
        # - la caméra est à cam_wall_dist_m du mur latéral gauche
        # - Xc est la coordonnée locale caméra gauche-droite
        #
        # Donc :
        #   x_abs = cam_wall_dist_m + Xc
        #   y_abs = Zc   (distance devant la caméra)
        x_abs = self.cam_wall_dist_m + Xc
        y_abs = Zc

        ground_xy = np.stack([x_abs, y_abs], axis=1)
        return ground_xy

    # ------------------------------------------------------------------

    def detect_person_position(self, ground_xy: np.ndarray) -> tuple[float, float] | None:
        """Détecte une position (x, y) représentative de la personne.

        Approche robuste :
            - garder les points devant la caméra et dans les bornes de la pièce
            - chercher la zone la plus proche (petites y)
            - faire un barycentre robuste (médian) dans cette zone
        """
        if ground_xy.size == 0:
            return None

        xs = ground_xy[:, 0]
        ys = ground_xy[:, 1]

        # On s'intéresse à ce qui est devant la caméra
        valid = (xs >= 0.0) & (ys >= 0.0)
        xs = xs[valid]
        ys = ys[valid]

        if xs.size == 0:
            return None

        # Zone la plus proche (personne plutôt vers le bas de l'image)
        y_near = np.percentile(ys, 30.0)
        near_mask = ys <= (y_near + 0.7)  # bande de 70 cm

        xs_near = xs[near_mask]
        ys_near = ys[near_mask]

        if xs_near.size == 0:
            return None

        x_med = float(np.median(xs_near))
        y_med = float(np.median(ys_near))

        return (x_med, y_med)

    # ------------------------------------------------------------------

    def map_to_cell(
        self,
        position_xy: tuple[float, float] | None,
        room_width_m: float,
        room_depth_m: float,
        rows: int,
        cols: int,
    ) -> tuple[int, int] | None:
        """Mappe une position (x, y) à une cellule (row, col) dans la matrice.

        La grille couvre :
            - en X : [0, room_width_m]
            - en Y : [0, room_depth_m] (0 = caméra, room_depth_m = fond de la pièce)
        """
        if position_xy is None:
            return None

        x, y = position_xy

        if not (0.0 <= x < room_width_m and 0.0 <= y < room_depth_m):
            return None

        cell_w = room_width_m / float(cols)
        cell_h = room_depth_m / float(rows)

        c = int(x // cell_w)
        r = int(y // cell_h)

        c = max(0, min(cols - 1, c))
        r = max(0, min(rows - 1, r))

        return (r, c)

