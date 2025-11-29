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
        fx: float = 366.1,
        fy: float = 366.1,
        cx: float = 318.2,
        cy: float = 241.1,
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
        self.offset_x = 0.0
        self.offset_y = 0.0

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
        self.R = np.eye(3, dtype=np.float32)

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

      # ------------------------------------------------------------------

    def project_to_ground(self, cloud: np.ndarray) -> np.ndarray:
        """Projette les points 3D sur un plan au sol approximatif (X = largeur, Y = profondeur).

        Hypothèses:
            - la caméra est à hauteur cam_height_m au-dessus du sol
            - Yc (après rotation) est l'axe vertical (positif vers le haut)
            - Zc est l'axe avant (en direction du regard)
            - Xc est l'axe gauche-droite

        Dans la pratique, avec les valeurs mesurées sur le système actuel :
            - Yc est très proche de 0 (≈ -0.03 à 0.00 m)
            - Zc est très petit (≈ 0.00 à 0.06 m)
        On utilise donc un facteur d'échelle sur Zc pour ramener la profondeur
        dans un ordre de grandeur cohérent avec la pièce (≈ 1–3 m).
        """

        # Aucun point → rien à projeter
        if cloud.size == 0:
            return np.zeros((0, 2), dtype=np.float32)

        # Décomposition des coordonnées caméra
        Xc = cloud[:, 0]
        Yc = cloud[:, 1]
        Zc = cloud[:, 2]

        # Filtrer les points non finis (NaN / inf)
        finite_mask = (
            np.isfinite(Xc) &
            np.isfinite(Yc) &
            np.isfinite(Zc)
        )
        if not np.any(finite_mask):
            return np.zeros((0, 2), dtype=np.float32)

        Xc = Xc[finite_mask]
        Yc = Yc[finite_mask]
        Zc = Zc[finite_mask]

        # DEBUG (si besoin) : plages typiques mesurées
        # print("DEBUG Yc min/max:", float(Yc.min()), float(Yc.max()))
        # print("DEBUG Zc min/max:", float(Zc.min()), float(Zc.max()))
        # print("DEBUG Xc min/max:", float(Xc.min()), float(Xc.max()))

        # ------------------------------------------------------------------
        # ÉCHELLE DE PROFONDEUR
        # ------------------------------------------------------------------
        # Les mesures observées donnent Zc max ≈ 0.06 m.
        # On applique un facteur d'échelle pour obtenir des profondeurs
        # exploitables pour la grille (~1–3 m) :
        #
        #   Zc_scaled = Zc * 40.0  →  0.06 * 40 ≈ 2.4 m
        #
        # print("DEBUG Zc min/max:", float(Zc.min()), float(Zc.max()))

        depth_scale = 1.0
        Zc_scaled = Zc * depth_scale
        
        # Filtre réaliste pour une pièce : 0.3 à 6 m
        depth_mask = (Zc_scaled > 0.5) & (Zc_scaled < 4.5)
        
        # NOTE IMPORTANTE :
        # On NE filtre PLUS sur une plage de profondeur stricte ici.
        # Le filtrage précédent :
        #     depth_mask = (Zc_scaled > 0.2) & (Zc_scaled < 6.0)
        #     ...
        # avait pour effet de vider complètement le nuage au sol (ground=(0,2))
        # lorsque toutes les valeurs étaient légèrement en dehors du seuil.
        #
        # On garde donc tous les points finis et non nuls, l'échelle étant
        # suffisante pour obtenir des valeurs utiles pour le barycentre.

        # ------------------------------------------------------------------
        # Position absolue dans la pièce (cas B1) :
        # - la caméra est à cam_wall_dist_m du mur latéral gauche
        # - Xc est la coordonnée locale caméra gauche-droite
        #
        # Donc :
        #   x_abs = cam_wall_dist_m + Xc
        #   y_abs = Zc_scaled   (distance devant la caméra en mètres)
        # ------------------------------------------------------------------
        x_abs = self.cam_wall_dist_m + Xc
        y_abs = Zc_scaled
        x_abs = x_abs + 6.15
        mask_phys = (
            (x_abs > 0.0) & (x_abs < 3.6) &   # largeur réelle de la pièce
            (y_abs > 0.7) & (y_abs < 4.5)     # profondeur réelle utilisable
        )

        x_abs = x_abs[mask_phys]
        y_abs = y_abs[mask_phys]

        if x_abs.size == 0:
            return np.zeros((0, 2), dtype=np.float32)

        ground_xy = np.stack([x_abs, y_abs], axis=1)
        return ground_xy

    # ------------------------------------------------------------------

    def detect_person_position(self, ground_xy: np.ndarray):
        """
        Détecte la position (x, y) de la personne dans la pièce en utilisant un
        barycentre robuste basé sur les médianes.

        ground_xy : tableau (N, 2) avec colonnes :
            - x = position gauche-droite absolue dans la pièce (m)
            - y = distance avant-arrière dans la pièce (m)

        Retourne :
            (x, y) en mètres, ou None si pas assez de points utiles.
        """

        if ground_xy is None or ground_xy.size < 20:
            return None

        xs = ground_xy[:, 0]
        ys = ground_xy[:, 1]

        # Barycentre robuste (médianes, beaucoup plus stable que moyenne)
        x_med = float(np.median(xs))
        y_med = float(np.median(ys))

        # Sanity check (évite renvoyer des trucs aberrants)
        if not (np.isfinite(x_med) and np.isfinite(y_med)):
            return None

        # Retour position en mètres
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

        # --------------------------------------------------------
        # AJOUT IMPORTANT : appliquer les offsets de calibration
        # --------------------------------------------------------
        # x += getattr(self, "offset_x", 0.0)
        # y += getattr(self, "offset_y", 0.0)

        # Si la position (corrigée) sort de la pièce : rejeter
        if not (0.0 <= x < room_width_m and 0.0 <= y < room_depth_m):
            return None

        cell_w = room_width_m / float(cols)
        cell_h = room_depth_m / float(rows)

        c = int(x // cell_w)
        r = int(y // cell_h)

        # clamp
        c = max(0, min(cols - 1, c))
        r = max(0, min(rows - 1, r))

        return (r, c)

