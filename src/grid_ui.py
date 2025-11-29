#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
grid_ui.py
Interface principale Chambre Sonore — Vue profondeur + grille dynamique.

Pipeline :
    - PipelineOrbbec (hors Qt)
Boucle Qt :
    - update_frame_and_zones() toutes les 50 ms
"""

import numpy as np
import math

from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtWidgets import (
    QWidget,
    QGridLayout,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QDoubleSpinBox,
    QSpinBox,
    QLineEdit,
    QFileDialog,
    QMenu,
    QTextEdit,
    QMessageBox,
    QSizePolicy,
    QStackedLayout
)
from PyQt6.QtGui import QAction


from src.orbbec_view_depth import OrbbecDepthView
from src.zone_detector import ZoneDetector
from src.cell_config import CellConfig, CellConfigEntry, DMXConfig
from src.zone_mapper_3d import ZoneMapper3D
from src.sound_engine import SoundEngine
from src.orbbec_view_color import OrbbecColorView


# ----------------------------------------------------------------------
#   CLASSE PRINCIPALE : GridUI
# ----------------------------------------------------------------------

# ----------------------------------------------------------
# VALIDATION : pièce / matrice (cellule = 1 m × 1 m)
# ----------------------------------------------------------

def validate_room_and_matrix(width_m, depth_m, cols_input, rows_input):
    """
    Retourne :
    {
        "width": largeur_corrigée,
        "depth": profondeur_corrigée,
        "cols": cols_corrigées,
        "rows": rows_corrigées,
        "message": message_court
    }
    """
    message = ""

    if width_m < 1.0:
        width_m = 1.0
        message = "Largeur trop petite. Ramenée à 1,0."
    if depth_m < 1.0:
        depth_m = 1.0
        if message:
            message += " Profondeur trop petite. Ramenée à 1,0."
        else:
            message = "Profondeur trop petite. Ramenée à 1,0."

    cols_max = math.floor(width_m)
    rows_max = math.floor(depth_m)

    cols = cols_input
    rows = rows_input

    if cols_input > cols_max:
        cols = cols_max
        message = f"Dépassement de largeur ({cols_input}). Valeur ramenée à {cols_max}."

    if rows_input > rows_max:
        if message:
            message += f" Pièce de {depth_m:.1f} m. Valeur ramenée à {rows_max}."
        else:
            message = f"Pièce de {depth_m:.1f} m. Valeur ramenée à {rows_max}."
        rows = rows_max

    return {
        "width": width_m,
        "depth": depth_m,
        "cols": cols,
        "rows": rows,
        "message": message
    }

class GridUI(QWidget):
    """
    Interface principale pour la Chambre Sonore.
    Contient :
      - une vue profondeur Orbbec
      - une grille dynamique (rows × cols)
      - un timer qui lit les données, met à jour la vue et calcule les zones
    """

    def __init__(self, pipeline, dmx=None, parent=None):
        super().__init__(parent)

        self.pipeline = pipeline
        self.dmx = dmx
        print("GridUI initialisé, pipeline reçu :", self.pipeline)

        self.depth_view = None
        self.cells = []

        # Moteur audio (lecture des .wav associés aux cellules)
        self.sound_engine = SoundEngine()
        self._last_active_cell = None

        self._last_ground_xy = None
        self._calibration_active = False
        self._calibration_phase = 0
        self._calibration_wait = 0
        self._calibration_countdown = 0
        

        # Clipboard interne pour copier/coller config de cellule
        self._cell_clipboard = None

        # ------------------------------------------------------------------
        # Charger l'état système (camera + pièce + matrice)
        # ------------------------------------------------------------------
        state = self._load_system_state()

        # Camera
        self.cam_height_m    = state["camera"]["height_m"]
        self.cam_angle_deg   = state["camera"]["angle_deg"]
        self.cam_wall_dist_m = state["camera"]["wall_dist_m"]
        self.cam_offset_m    = state["camera"]["offset_m"]

        # Pièce
        self.room_width_m    = state["room"]["width_m"]
        self.room_depth_m    = state["room"]["depth_m"]

        # Matrice
        self.grid_rows       = state["grid"]["rows"]
        self.grid_cols       = state["grid"]["cols"]

        # ------------------------------------------------------------------
        # Mapper 3D à partir des paramètres chargés
        # ------------------------------------------------------------------
        self.mapper3d = ZoneMapper3D(
            cam_height_m=self.cam_height_m,
            cam_angle_deg=self.cam_angle_deg,
            cam_wall_dist_m=self.cam_wall_dist_m,
            cam_offset_m=self.cam_offset_m
        )

        # ------------------------------------------------------------------
        # Configuration des cellules
        # ------------------------------------------------------------------
        self.cell_config = CellConfig(
            room_width_m=self.room_width_m,
            room_depth_m=self.room_depth_m,
            rows=self.grid_rows,
            cols=self.grid_cols
        )


        # Seuil de présence (mm)
        self.presence_threshold_mm = 2000

        # Zone detector basé sur image (pour profondeur 2D)
        self.zone_detector = ZoneDetector(
            rows=self.grid_rows,
            cols=self.grid_cols
        )
        self._calibration_active = False
        self._calibration_countdown = 0
        self._last_ground_xy = None


        # ------------------------------------------------------------------
        # Interface principale (portrait)
        # ------------------------------------------------------------------
        self.setWindowTitle("Chambre Sonore — Vue profondeur")
        self.resize(700, 1100)
        self.setMinimumSize(650, 950)
        if self.dmx:
            self.dmx.send_rgb(255, 0, 0)  # doit virer rouge dès l'ouverture

        self._build_ui()
        self._start_timer()

    # ------------------------------------------------------------------
    def _load_system_state(self):
        import json, os
        path = "config/system_state.json"

        if not os.path.exists("config"):
            os.makedirs("config")

        # Valeurs par défaut si fichier absent
        default_state = {
            "camera": {
                "height_m": 1.75,
                "angle_deg": 10.0,
                "wall_dist_m": 0.04,
                "offset_m": 0.0
            },
            "room": {
                "width_m": 4.328,
                "depth_m": 3.235
            },
            "grid": {
                "rows": 3,
                "cols": 4
            }
        }

        # création au besoin
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump(default_state, f, indent=4)
            return default_state

        # chargement existant
        try:
            with open(path, "r") as f:
                data = json.load(f)
                return data
        except:
            return default_state


    def _save_system_state(self):
        import json, os
        data = {
            "camera": {
                "height_m": self.cam_height_m,
                "angle_deg": self.cam_angle_deg,
                "wall_dist_m": self.cam_wall_dist_m,
                "offset_m": self.cam_offset_m
            },
            "room": {
                "width_m": self.room_width_m,
                "depth_m": self.room_depth_m
            },
            "grid": {
                "rows": self.grid_rows,
                "cols": self.grid_cols
            }
        }

        if not os.path.exists("config"):
            os.makedirs("config")

        with open("config/system_state.json", "w") as f:
            json.dump(data, f, indent=4)

    # ------------------------------------------------------------------

    def toggle_view_mode(self):
        if self.view_stack.currentIndex() == 0:
            self.view_stack.setCurrentIndex(1)
        else:
            self.view_stack.setCurrentIndex(0)

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construit l'interface : vue + grille dynamique + boutons."""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # VUE PROFONDEUR
        # self.depth_view = OrbbecDepthView(self)
        # Injection du convertisseur Y16 → RGB (obligatoire)
        # self.depth_view.depth_converter = self.pipeline.depth_converter
        # main_layout.addWidget(self.depth_view, stretch=2)
        # self.depth_view.setFixedHeight(350)

        # VUES : profondeur + couleur
        self.depth_view = OrbbecDepthView(self)
        self.depth_view.depth_converter = self.pipeline.depth_converter

        self.color_view = OrbbecColorView(self)

        # Empilement des deux vues
        self.view_stack = QStackedLayout()
        self.view_stack.addWidget(self.depth_view)   # profondeur = index 0
        self.view_stack.addWidget(self.color_view)   # couleur = index 1

        # Ajouter au layout principal
        main_layout.addLayout(self.view_stack, stretch=2)
        self.depth_view.setFixedHeight(350)

        # Bouton de bascule
        self.toggle_button = QPushButton("Afficher couleur / profondeur")
        self.toggle_button.clicked.connect(self.toggle_view_mode)
        main_layout.addWidget(self.toggle_button)



        # GRILLE DYNAMIQUE
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(2)
        self._build_grid_labels()
        self.grid_layout.setHorizontalSpacing(3)
        self.grid_layout.setVerticalSpacing(3)

        grid_container = QHBoxLayout()
        grid_container.addStretch(1)
        grid_container.addLayout(self.grid_layout)
        grid_container.addStretch(1)
        main_layout.addLayout(grid_container, stretch=1)

        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.calibration_log = QTextEdit()
        self.calibration_log.setReadOnly(True)
        self.calibration_log.setMinimumHeight(120)
        self.calibration_log.setStyleSheet(
            "background:#f5f5f5; color:#000; font-size:15px; "
            "padding:8px; border:1px solid #aaa;"
        )
        main_layout.addWidget(self.calibration_log)


        # BOUTONS
        btn_layout = QHBoxLayout()

        # Taille uniforme plus grande
        btn_style = "font-size:12px; padding:8px 18px;"

        self.btn_reset = QPushButton("Réinitialiser la grille")
        self.btn_reset.setStyleSheet(btn_style)
        self.btn_reset.setFixedHeight(50)
        self.btn_reset.clicked.connect(self.reset_cells)

        self.btn_config = QPushButton("Configurer la grille")
        self.btn_config.setStyleSheet(btn_style)
        self.btn_config.setFixedHeight(50)
        self.btn_config.clicked.connect(self.open_config_dialog)

        self.btn_cam = QPushButton("Config Caméra")
        self.btn_cam.setStyleSheet(btn_style)
        self.btn_cam.setFixedHeight(50)
        self.btn_cam.clicked.connect(self.open_camera_config_dialog)

        self.btn_quit = QPushButton("Quitter")
        self.btn_quit.setStyleSheet(btn_style)
        self.btn_quit.setFixedHeight(50)
        self.btn_quit.clicked.connect(self.close)

        # Ajout au layout, centré
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addWidget(self.btn_config)
        btn_layout.addWidget(self.btn_cam)
        # Bouton Calibration
        self.btn_calibrate = QPushButton("Capturer position")
        self.btn_calibrate.setStyleSheet(btn_style)
        self.btn_calibrate.setFixedHeight(50)
        self.btn_calibrate.clicked.connect(self._start_calibration)
        btn_layout.addWidget(self.btn_calibrate)

        btn_layout.addWidget(self.btn_quit)
        btn_layout.addStretch(1)

        main_layout.addLayout(btn_layout)
    # ------------------------------------------------------------------
    def _compute_cell_size(self) -> int:
        """Calcule automatiquement la taille des cellules selon la largeur disponible."""
        available_width = self.width() - 40  # marge visuelle
        if self.grid_cols == 0:
            return 60
        size = int(available_width / self.grid_cols)
        size = max(40, min(size, 120))       # limites raisonnables
        return size

    # ------------------------------------------------------------------
    def _build_grid_labels(self) -> None:
        """Construit les cellules de la matrice comme des QPushButton cliquables."""
        # Nettoyer l'ancienne grille
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        self.cells = []

        for row in range(self.grid_rows):
            row_cells = []
            for col in range(self.grid_cols):

                btn = CellWidget(row, col, self)

                # Cellules carrées
                cell_size = self._compute_cell_size()
                btn.setFixedSize(cell_size, cell_size)

                btn.setStyleSheet(
                    "background:#222; color:white; "
                    "border:1px solid #444; padding:4px;"
                )


                self.grid_layout.addWidget(btn, row, col)
                row_cells.append(btn)

            self.cells.append(row_cells)

    # ------------------------------------------------------------------
    def _copy_cell(self, row, col):
        entry = self.cell_config.get_cell(row, col)
        if entry:
            self._cell_clipboard = entry.clone()
            print(f"[COPY] {row},{col}")

    def _paste_cell(self, row, col, display_btn):
        if self._cell_clipboard:
            entry = self.cell_config.get_cell(row, col)
            entry.apply_from(self._cell_clipboard)
            display_btn.setText(entry.name)
            self.cell_config.set_cell(entry)
            self.cell_config.save()
            print(f"[PASTE] {row},{col}")

    # ------------------------------------------------------------------

    # Petite méthode utilitaire pour édition
    def _edit_cell_from_grid_button(self, btn):
        row = btn.property("cell_row")
        col = btn.property("cell_col")
        self._edit_cell_from_grid_button_core(row, col, btn)

    def _edit_cell_from_grid_button_core(self, row, col, btn):
        entry = self.cell_config.get_cell(row, col)
        if entry is None:
            return
        dialog = CellEditorDialog(entry, parent=self)
        if dialog.exec():
            self.cell_config.set_cell(dialog.entry)
            btn.setText(dialog.entry.name)
            self.cell_config.save()

    # ------------------------------------------------------------------

    def _start_timer(self) -> None:
        """Timer pour lecture pipeline + analyse zones."""
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self.update_frame_and_zones)
        self.frame_timer.start(50)

    # ------------------------------------------------------------------

    def _map_position_to_cell_local(self, pos_xy, ground_xy):
        """Mappe une position (x, y) + le nuage au sol vers une cellule (r, c).

        - y (profondeur réelle) → rangée
        - x (largeur relative dans le nuage) → colonne
        """
        if pos_xy is None:
            return None

        x, y = pos_xy

        # ----------------------------
        # RANGÉE : basée sur la profondeur
        # ----------------------------
        if not (0 <= y < self.room_depth_m):
            return None

        cell_h = self.room_depth_m / float(self.grid_rows)
        r = int(y // cell_h)
        r = max(0, min(self.grid_rows - 1, r))

        # ----------------------------
        # COLONNE : basée sur la largeur du nuage de points
        # ----------------------------
        if ground_xy is None or ground_xy.size == 0:
            # pas d'info → colonne centrale
            c = self.grid_cols // 2
            return (r, c)

        xs = ground_xy[:, 0].astype(float)

        min_x = float(xs.min())
        max_x = float(xs.max())
        span = max_x - min_x

        if span < 0.05:
            # nuage trop étroit → personne est presque en face de la caméra
            c = self.grid_cols // 2
        else:
            ratio = (x - min_x) / span
            ratio = max(0.0, min(0.999, ratio))
            c = int(ratio * self.grid_cols)

        c = max(0, min(self.grid_cols - 1, c))
        return (r, c)


    # ------------------------------------------------------------------
    # Calibration: aucune donnée 3D disponible (déplace-toi un peu).


    def update_frame_and_zones(self) -> None:
        ok = self.pipeline.poll()
        if not ok:
            return

        # --------------------------------------------------------
        # CALIBRATION EN COURS
        # --------------------------------------------------------
        if getattr(self, "_calibration_active", False):

            # ----------------------------------------------------
            # PHASE 1 : attente avant le vrai décompte
            # ----------------------------------------------------
            if self._calibration_phase == 1:
                self._calibration_wait -= 1

                if self._calibration_wait % 20 == 0:  # toutes les ~1 sec
                    seconds_left = self._calibration_wait // 20
                    self.calibration_log.append(f"Préparation : {seconds_left} s")

                if self._calibration_wait <= 0:
                    # Activer la PHASE 2 : vrai décompte
                    self._calibration_phase = 2
                    self._calibration_last_seconds = -1
                    self._calibration_countdown = 200   # ≈10 sec
                    self.calibration_log.append("Décompte lancé…")
                return

            # ----------------------------------------------------
            # PHASE 2 : décompte réel
            # ----------------------------------------------------
            if self._calibration_phase == 2:

                self._calibration_countdown -= 1
                ticks_per_second = 20

                if self._calibration_countdown >= 0:
                    seconds_left = (self._calibration_countdown + ticks_per_second - 1) // ticks_per_second
                    if seconds_left != self._calibration_last_seconds:
                        self.calibration_log.append(f"Décompte : {seconds_left} s")
                        self._calibration_last_seconds = seconds_left

                if self._calibration_countdown <= 0:

                    if self._last_ground_xy is None:
                        self.calibration_log.append("Aucune donnée 3D capturée.")
                        self._calibration_active = False
                        return

                    pos = self.mapper3d.detect_person_position(self._last_ground_xy)
                    if pos is not None:
                        xd, yd = pos
                        self.calibration_log.append(f"POS: x={xd:.2f}, y={yd:.2f}")


                    if pos is None:
                        self.calibration_log.append("Aucune personne détectée.")
                    else:
                        xd, yd = pos
                        self.calibration_log.append(
                            f"Calibration - position détectée = ({xd:.3f}, {yd:.3f})"
                        )

                        cell_w = self.room_width_m / self.grid_cols
                        cell_h = self.room_depth_m / self.grid_rows

                        target_x = cell_w * 1.5
                        target_y = cell_h * 1.0

                        offset_x = target_x - xd
                        offset_y = target_y - yd

                        self.calibration_log.append(
                            f"Offset appliqué : x={offset_x:.3f}, y={offset_y:.3f}"
                        )

                        self.mapper3d.offset_x = offset_x
                        self.mapper3d.offset_y = offset_y
                        self._save_system_state()

                        self.calibration_log.append("Calibration complétée.")

                    self._calibration_active = False

                return

        # --------------------------------------------------------
        # PIPELINE NORMAL
        # --------------------------------------------------------

        # 1. Profondeur
        depth_img = self.pipeline.get_depth_frame()
        if depth_img is not None:
            self.depth_view.update_image(depth_img)

        # 2. Couleur
        color_img = self.pipeline.get_color_frame()
        if color_img is not None:
            self.color_view.update_image(color_img)

        # 2. Données profondeur
        depth_data = self.pipeline.get_depth_data()
        if depth_data is None:
            self._clear_grid()
            return

        # 3. Reconstruction 3D
        cloud = self.mapper3d.compute_point_cloud(depth_data)

        # 4. Projection sol
        ground_xy = self.mapper3d.project_to_ground(cloud)
        self.calibration_log.append(f"cloud={cloud.shape}, ground={ground_xy.shape}")


        # Conserver la dernière projection valide
        if ground_xy is not None and len(ground_xy) > 0:
            self._last_ground_xy = ground_xy

        # 5. Position XY
        pos = self.mapper3d.detect_person_position(ground_xy)
        if ground_xy is not None and ground_xy.size > 0:
            if hasattr(self, "calibration_log"):
                xs = ground_xy[:, 0]
                ys = ground_xy[:, 1]
                self.calibration_log.append(
                    f"XY range: x=({xs.min():.2f},{xs.max():.2f}), y=({ys.min():.2f},{ys.max():.2f})"
                )

        if pos is not None:
            xd, yd = pos
            if hasattr(self, "calibration_log"):
                self.calibration_log.append(
                    f"POS: x={xd:.2f}, y={yd:.2f}"
                )
        
        if pos is None:
            self._clear_grid()
            return

        # 6. XY → Cellule (nouvelle méthode locale)
        cell = self._map_position_to_cell_local(pos, ground_xy)

        if cell is not None and hasattr(self, "calibration_log"):
            r, c = cell
            self.calibration_log.append(f"CELL: r={r}, c={c}")

        if cell is None:
            self._clear_grid()
            return

        r, c = cell

        # 7. Mettre à jour la grille (une seule cellule active)
        self._clear_grid()

        if 0 <= r < self.grid_rows and 0 <= c < self.grid_cols:
            self.cells[r][c].setStyleSheet(
                "background:#ff8800; color:black; "
                "border:3px solid white; padding:4px;"
            )
            self.cells[r][c].setText(f"{r},{c}\nACTIVE")

        # 8. Hook DMX / sons
        self.handle_zone_activity_3d(pos, (r, c))

    # ------------------------------------------------------------------

    def _clear_grid(self):
        """Efface la coloration de la grille."""
        for r in range(self.grid_rows):
            for c in range(self.grid_cols):
                btn = self.cells[r][c]
                btn.refresh_display()

                self.cells[r][c].setStyleSheet(
                    "background:#222; color:white; border:1px solid #444; padding:4px;"
                )

    # ------------------------------------------------------------------

    def _depth_to_color(
        self,
        distance_mm: int,
        min_mm: int,
        max_mm: int,
        is_dominant: bool,
        is_active: bool
    ) -> str:

        if max_mm <= min_mm:
            t = 0.0
        else:
            t = (distance_mm - min_mm) / float(max_mm - min_mm)
            t = max(0.0, min(1.0, t))

        near_color = (255, 120, 0)
        far_color = (0, 40, 80)

        r = int(near_color[0] + (far_color[0] - near_color[0]) * t)
        g = int(near_color[1] + (far_color[1] - near_color[1]) * t)
        b = int(near_color[2] + (far_color[2] - near_color[2]) * t)

        if is_dominant:
            r = min(255, int(r * 1.3))
            g = min(255, int(g * 1.3))
            b = min(255, int(b * 1.3))
        elif not is_active:
            r = int(r * 0.5)
            g = int(g * 0.5)
            b = int(b * 0.5)

        return "#{:02x}{:02x}{:02x}".format(r, g, b)

    # ------------------------------------------------------------------

    def handle_zone_activity(
        self,
        zones_mm: np.ndarray,
        active_map: np.ndarray,
        dominant_cell: tuple[int, int],
        dominant_distance_mm: int
    ) -> None:
        dr, dc = dominant_cell
        # print("handle_zone_activity → dominant:", dominant_cell,"distance:",dominant_distance_mm) 
        # print("zones actives:\n", active_map.astype(int))

    # ------------------------------------------------------------------
    def handle_zone_activity_3d(self, pos_xy, cell_rc):
        """Déclenche lecture audio pour la cellule active."""
        if cell_rc is None:
            return

        r, c = cell_rc
        cell_info = self.cell_config.get_cell(r, c)
        if cell_info is None:
            return

        # Identifiant unique pour cette cellule
        cell_id = f"{r},{c}"

        # Si c'est la même cellule qu'à la frame précédente → ne relance pas
        if self._last_active_cell == cell_id:
            return

        # Si une cellule jouait avant : l'arrêter
        if self._last_active_cell is not None:
            self.sound_engine.release_cell(self._last_active_cell)

        # Nouveau son à jouer
        wav_path = cell_info.wav
        if wav_path:
            self.sound_engine.play_for_cell(cell_id, wav_path, volume=1.0, pan=0.0)

        # Mémoriser la cellule active
        self._last_active_cell = cell_id

    # ------------------------------------------------------------------

    # ------------------------------------------------------------------

    def reset_cells(self) -> None:
        self._clear_grid()

    # ------------------------------------------------------------------

    def _edit_cell_from_grid(self):
        """Édition directe d’une cellule en cliquant dans la grille."""
        btn = self.sender()
        row = btn.property("cell_row")
        col = btn.property("cell_col")

        entry = self.cell_config.get_cell(row, col)
        if entry is None:
            return

        dialog = CellEditorDialog(entry, parent=self)
        if dialog.exec():
            # mettre à jour
            self.cell_config.set_cell(dialog.entry)
            btn.setText(dialog.entry.name)
            self.cell_config.save()


    # ------------------------------------------------------------------
    def open_config_dialog(self) -> None:
        """Ouvre la fenêtre de configuration pièce / matrice."""
        dialog = GridConfigDialog(
            room_width_m=self.room_width_m,
            room_depth_m=self.room_depth_m,
            rows=self.grid_rows,
            cols=self.grid_cols,
            parent=self
        )
        if dialog.exec():

            # Mettre à jour les valeurs
            self.room_width_m = dialog.room_width_m
            self.room_depth_m = dialog.room_depth_m
            self.grid_rows = dialog.rows
            self.grid_cols = dialog.cols

            # print("Nouvelle configuration pièce/matrice :")
            # print("  largeur      :", self.room_width_m, "m")
            # print("  profondeur   :", self.room_depth_m, "m")
            # print("  rows × cols  :", self.grid_rows, "x", self.grid_cols)

            # Recalcul des cellules AU BON FORMAT
            self.cell_config.rebuild_grid(
                room_width_m=self.room_width_m,
                room_depth_m=self.room_depth_m,
                rows=self.grid_rows,
                cols=self.grid_cols,
                keep_existing=True
            )
            self.cell_config.save()

            # Sauvegarde globale (camera + pièce + grid)
            self._save_system_state()

            # Reconstruction UI
            self._build_grid_labels()
            self.zone_detector = ZoneDetector(
                rows=self.grid_rows,
                cols=self.grid_cols
            )

            self._clear_grid()
            self.update()
            self.repaint()

    # ------------------------------------------------------------------
    def open_camera_config_dialog(self) -> None:
        dialog = CameraConfigDialog(
            cam_height_m=self.cam_height_m,
            cam_angle_deg=self.cam_angle_deg,
            cam_wall_dist_m=self.cam_wall_dist_m,
            cam_offset_m=self.cam_offset_m,
            parent=self
        )
        if dialog.exec():

            # Mettre à jour
            self.cam_height_m    = dialog.cam_height_m
            self.cam_angle_deg   = dialog.cam_angle_deg
            self.cam_wall_dist_m = dialog.cam_wall_dist_m
            self.cam_offset_m    = dialog.cam_offset_m

            print("Nouvelle configuration caméra :")
            print("  hauteur =", self.cam_height_m, "m")
            print("  angle   =", self.cam_angle_deg, "°")
            print("  mur→zone =", self.cam_wall_dist_m, "m")
            print("  offset  =", self.cam_offset_m, "m")

            # Appliquer dans mapper 3D
            self.mapper3d.cam_height_m    = self.cam_height_m
            self.mapper3d.cam_angle_deg   = self.cam_angle_deg
            self.mapper3d.cam_wall_dist_m = self.cam_wall_dist_m
            self.mapper3d.cam_offset_m    = self.cam_offset_m
            self.mapper3d._update_rotation_matrix()

            # Sauvegarde globale
            self._save_system_state()

    def resizeEvent(self, event):
        """Recalcule la taille des cellules quand la fenêtre est redimensionnée."""
        cell_size = self._compute_cell_size()
        for row in self.cells:
            for btn in row:
                btn.setFixedSize(cell_size, cell_size)
        super().resizeEvent(event)

    def _start_calibration(self):
        """Déclenche la calibration en demandant à l’utilisateur d’aller au centre."""

        # Reset du log visuel
        if hasattr(self, "calibration_log"):
            self.calibration_log.clear()

        # Vérifier que la caméra a déjà fourni un nuage au moins une fois
        if not hasattr(self, "_last_ground_xy") or self._last_ground_xy is None:
            if hasattr(self, "calibration_log"):
                self.calibration_log.append("Caméra pas encore prête.\nBouge un peu et réessaie.")
            return

        # Afficher instructions
        if hasattr(self, "calibration_log"):
            self.calibration_log.append("=== CALIBRATION ===")
            self.calibration_log.append("Va te placer au centre entre (1,1) et (1,2).")
            self.calibration_log.append("Début du décompte dans 5 secondes…")

        # IMPORTANT : initialiser les deux variables
        self._calibration_active = True
        self._calibration_countdown = 150   # ~5 secondes à 30 FPS

    def test_cell(self, row, col):
        """
        Active la cellule en mode test :
        - Allume la SlimPAR DMX via dmx_controller
        - Joue le fichier wav associé
        - Le son joue en boucle jusqu'à nouvel appel
        """
        key = f"{row}_{col}"
        cell = self.cells.get(key)
        if not cell:
            print(f"[Test] Cellule {key} inconnue.")
            return

        # DMX : activer le projecteur
        if self.dmx is not None:
            try:
                self.dmx.set_intensity(cell.dmx_channel, 255)
            except Exception as e:
                print(f"[DMX] Erreur activation cellule {key} : {e}")

        # Audio : jouer / arrêter
        if self.audio is not None:
            if self.audio.is_playing(key):
                self.audio.stop(key)
            else:
                self.audio.play(cell.wav_path, loop=True, cell_id=key)

        print(f"[Test] Cellule {key} testée.")


# ----------------------------------------------------------------------
#   DIALOGS
# ----------------------------------------------------------------------
class CameraConfigDialog(QDialog):
    """
    Configuration des paramètres physiques de la caméra :
      - hauteur (m)
      - angle (pitch) vers le bas (°)
      - distance mur → début zone (m)
      - décalage latéral (m)
    """

    def __init__(
        self,
        cam_height_m: float,
        cam_angle_deg: float,
        cam_wall_dist_m: float,
        cam_offset_m: float,
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Configuration Caméra 3D (position réelle)")

        # Hauteur caméra
        self._cam_height = QDoubleSpinBox(self)
        self._cam_height.setRange(0.1, 5.0)
        self._cam_height.setDecimals(2)
        self._cam_height.setSingleStep(0.05)
        self._cam_height.setValue(cam_height_m)

        # Angle vers le bas
        self._cam_angle = QDoubleSpinBox(self)
        self._cam_angle.setRange(-30.0, 90.0)
        self._cam_angle.setDecimals(1)
        self._cam_angle.setSingleStep(0.5)
        self._cam_angle.setValue(cam_angle_deg)

        # Distance mur → début de la zone au sol
        self._cam_wall = QDoubleSpinBox(self)
        self._cam_wall.setRange(0.0, 10.0)
        self._cam_wall.setDecimals(2)
        self._cam_wall.setSingleStep(0.1)
        self._cam_wall.setValue(cam_wall_dist_m)

        # Décalage latéral caméra ←→ centre zone
        self._cam_offset = QDoubleSpinBox(self)
        self._cam_offset.setRange(-5.0, 5.0)
        self._cam_offset.setDecimals(2)
        self._cam_offset.setSingleStep(0.05)
        self._cam_offset.setValue(cam_offset_m)

        # Layout
        form = QFormLayout()
        form.addRow("Hauteur caméra (m) :", self._cam_height)
        form.addRow("Angle vers le bas (°) :", self._cam_angle)
        form.addRow("Distance mur → zone (m) :", self._cam_wall)
        form.addRow("Décalage latéral (m) :", self._cam_offset)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel,
            parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

        # valeurs exposées
        self.cam_height_m = cam_height_m
        self.cam_angle_deg = cam_angle_deg
        self.cam_wall_dist_m = cam_wall_dist_m
        self.cam_offset_m = cam_offset_m

    # Quand on ferme la boîte avec OK
    def accept(self) -> None:
        self.cam_height_m = float(self._cam_height.value())
        self.cam_angle_deg = float(self._cam_angle.value())
        self.cam_wall_dist_m = float(self._cam_wall.value())
        self.cam_offset_m = float(self._cam_offset.value())
        super().accept()




class GridConfigDialog(QDialog):
    """
    Configuration pièce / matrice.
    """

    def __init__(
        self,
        room_width_m: float,
        room_depth_m: float,
        rows: int,
        cols: int,
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Configuration pièce / matrice")

        self._room_width_spin = QDoubleSpinBox(self)
        self._room_width_spin.setRange(1.0, 50.0)
        self._room_width_spin.setDecimals(2)
        self._room_width_spin.setSingleStep(0.1)
        self._room_width_spin.setValue(room_width_m)

        self._room_depth_spin = QDoubleSpinBox(self)
        self._room_depth_spin.setRange(1.0, 50.0)
        self._room_depth_spin.setDecimals(2)
        self._room_depth_spin.setSingleStep(0.1)
        self._room_depth_spin.setValue(room_depth_m)

        self._rows_spin = QSpinBox(self)
        self._rows_spin.setRange(1, 64)
        self._rows_spin.setValue(rows)

        self._cols_spin = QSpinBox(self)
        self._cols_spin.setRange(1, 64)
        self._cols_spin.setValue(cols)

        form = QFormLayout()
        form.addRow("Largeur de la pièce (m) :", self._room_width_spin)
        form.addRow("Profondeur de la pièce (m) :", self._room_depth_spin)
        form.addRow("Rangées :", self._rows_spin)
        form.addRow("Colonnes :", self._cols_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel,
            parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)

        self.error_label = QLabel("", self)
        self.error_label.setStyleSheet("color:#cc3333; font-size:13px;")
        layout.addWidget(self.error_label)

        self.auto_button = QPushButton("Calcul automatique", self)
        self.auto_button.clicked.connect(self.auto_compute_matrix)
        layout.addWidget(self.auto_button)

        layout.addWidget(buttons)
        self.setLayout(layout)

        self.room_width_m = room_width_m
        self.room_depth_m = room_depth_m
        self.rows = rows
        self.cols = cols

    def auto_compute_matrix(self) -> None:
        width = float(self._room_width_spin.value())
        depth = float(self._room_depth_spin.value())

        cols_auto = math.floor(width)
        rows_auto = math.floor(depth)

        result = validate_room_and_matrix(width, depth, cols_auto, rows_auto)

        self._room_width_spin.setValue(result["width"])
        self._room_depth_spin.setValue(result["depth"])
        self._rows_spin.setValue(result["rows"])
        self._cols_spin.setValue(result["cols"])

        self.error_label.setText(result["message"])

    def accept(self) -> None:
        width = float(self._room_width_spin.value())
        depth = float(self._room_depth_spin.value())
        rows_in = int(self._rows_spin.value())
        cols_in = int(self._cols_spin.value())

        result = validate_room_and_matrix(width, depth, cols_in, rows_in)

        self._room_width_spin.setValue(result["width"])
        self._room_depth_spin.setValue(result["depth"])
        self._rows_spin.setValue(result["rows"])
        self._cols_spin.setValue(result["cols"])

        self.error_label.setText(result["message"])

        self.room_width_m = result["width"]
        self.room_depth_m = result["depth"]
        self.rows = result["rows"]
        self.cols = result["cols"]

        if result["message"]:
            return

        super().accept()


# ----------------------------------------------------------------------

class CellEditorDialog(QDialog):
    """
    Éditeur pour une cellule individuelle (wav + DMX).
    """

    def __init__(self, entry: CellConfigEntry, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Cellule {entry.cell_id}")
        self.entry = entry

        form = QFormLayout()

        self.name_edit = QLineEdit(self)
        self.name_edit.setText(entry.name)
        form.addRow("Nom :", self.name_edit)

        pos_label = QLabel(
            f"X: {entry.x_min:.2f}–{entry.x_max:.2f} m\n"
            f"Y: {entry.y_min:.2f}–{entry.y_max:.2f} m",
            self
        )
        form.addRow("Position au sol :", pos_label)

        self.wav_edit = QLineEdit(self)
        self.wav_edit.setText(entry.wav)
        btn_browse = QPushButton("Parcourir…", self)
        btn_browse.clicked.connect(self._browse_wav)

        wav_layout = QHBoxLayout()
        wav_layout.addWidget(self.wav_edit)
        wav_layout.addWidget(btn_browse)
        form.addRow("Fichier WAV :", wav_layout)

        self.volume_spin = QDoubleSpinBox(self)
        self.volume_spin.setRange(0.0, 2.0)
        self.volume_spin.setSingleStep(0.05)
        self.volume_spin.setValue(entry.volume)
        form.addRow("Volume :", self.volume_spin)

        self.universe_spin = QSpinBox(self)
        self.universe_spin.setRange(0, 10)
        self.universe_spin.setValue(entry.dmx.universe)
        form.addRow("DMX universe :", self.universe_spin)

        self.address_spin = QSpinBox(self)
        self.address_spin.setRange(1, 512)
        self.address_spin.setValue(entry.dmx.address)
        form.addRow("Adresse DMX :", self.address_spin)

        self.channels_spin = QSpinBox(self)
        self.channels_spin.setRange(1, 16)
        self.channels_spin.setValue(entry.dmx.channels)
        form.addRow("Canaux DMX :", self.channels_spin)

        self.color_r = QSpinBox(self)
        self.color_r.setRange(0, 255)
        self.color_r.setValue(entry.dmx.color[0])

        self.color_g = QSpinBox(self)
        self.color_g.setRange(0, 255)
        self.color_g.setValue(entry.dmx.color[1])

        self.color_b = QSpinBox(self)
        self.color_b.setRange(0, 255)
        self.color_b.setValue(entry.dmx.color[2])

        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("R :", self))
        color_layout.addWidget(self.color_r)
        color_layout.addWidget(QLabel("G :", self))
        color_layout.addWidget(self.color_g)
        color_layout.addWidget(QLabel("B :", self))
        color_layout.addWidget(self.color_b)
        form.addRow("Couleur DMX :", color_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel,
            parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _browse_wav(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir un fichier WAV",
            "",
            "Fichiers WAV (*.wav);;Tous les fichiers (*)"
        )
        if path:
            self.wav_edit.setText(path)

    def accept(self) -> None:
        self.entry.name = self.name_edit.text().strip() or self.entry.cell_id
        self.entry.wav = self.wav_edit.text().strip()
        self.entry.volume = float(self.volume_spin.value())
        self.entry.dmx = DMXConfig(
            universe=int(self.universe_spin.value()),
            address=int(self.address_spin.value()),
            channels=int(self.channels_spin.value()),
            color=(
                int(self.color_r.value()),
                int(self.color_g.value()),
                int(self.color_b.value())
            )
        )
        super().accept()

# ----------------------------------------------------------------------

class FloorMapDialog(QDialog):
    """
    Vue du dessus de la matrice : permet de visualiser & éditer les cellules.
    """

    def __init__(self, parent: GridUI):
        super().__init__(parent)
        self.setWindowTitle("Carte au sol — matrice")
        self.parent_ui = parent

        layout = QVBoxLayout()
        info = QLabel(
            f"Pièce : {parent.room_width_m:.2f} m × {parent.room_depth_m:.2f} m\n"
            f"Matrice : {parent.grid_rows} × {parent.grid_cols}",
            self
        )
        layout.addWidget(info)

        grid = QGridLayout()
        grid.setSpacing(2)

        for r in range(parent.grid_rows):
            for c in range(parent.grid_cols):
                entry = parent.cell_config.get_cell(r, c)
                label = entry.name if entry else f"{r},{c}"

                btn = QPushButton(label, self)
                btn.setProperty("cell_row", r)
                btn.setProperty("cell_col", c)                
                grid.addWidget(btn, r, c)

        layout.addLayout(grid)

        close_btn = QPushButton("Fermer", self)
        
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def _edit_cell(self) -> None:
        btn = self.sender()
        row = btn.property("cell_row")
        col = btn.property("cell_col")
        parent = self.parent_ui

        entry = parent.cell_config.get_cell(row, col)
        if entry is None:
            QMessageBox.warning(self, "Erreur", f"Aucune cellule définie pour {row},{col}")
            return

        dialog = CellEditorDialog(entry, parent=self)
        if dialog.exec():
            parent.cell_config.set_cell(dialog.entry)
            btn.setText(dialog.entry.name)



class CellWidget(QWidget):
    def __init__(self, row, col, parent_ui):
        super().__init__(parent_ui)
        self.row = row
        self.col = col
        self.parent_ui = parent_ui

        # Layout principal vertical
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1) Zone TEST (3/5)
        self.btn_test = QPushButton(f"{row},{col}\nTEST", self)
        self.btn_test.setStyleSheet(
            "background:#333; color:white; border:1px solid #555; font-size:18px;"
        )
        self.btn_test.clicked.connect(lambda: parent_ui.test_cell(row, col))
        self.btn_test.setSizePolicy(QSizePolicy.Policy.Expanding,
                                    QSizePolicy.Policy.Expanding)

        # stretch = 3 pour occuper 3/5
        layout.addWidget(self.btn_test, 3)

        # 2) Zone boutons bas (2/5)
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(0)

        # Styles uniformes
        style_bottom = "background:#555; color:white; border:1px solid #333; font-size:14px;"

        # Modifier
        self.btn_edit = QPushButton("Modifier", self)
        self.btn_edit.setStyleSheet(style_bottom)
        self.btn_edit.clicked.connect(
            lambda: parent_ui._edit_cell_from_grid_button_core(row, col, self.btn_test)
        )
        self.btn_edit.setSizePolicy(QSizePolicy.Policy.Expanding,
                                    QSizePolicy.Policy.Expanding)
        bottom.addWidget(self.btn_edit)

        # Copier
        self.btn_copy = QPushButton("Copier", self)
        self.btn_copy.setStyleSheet(style_bottom)
        self.btn_copy.clicked.connect(lambda: parent_ui._copy_cell(row, col))
        self.btn_copy.setSizePolicy(QSizePolicy.Policy.Expanding,
                                    QSizePolicy.Policy.Expanding)
        bottom.addWidget(self.btn_copy)

        # Coller
        self.btn_paste = QPushButton("Coller", self)
        self.btn_paste.setStyleSheet(style_bottom)
        self.btn_paste.clicked.connect(
            lambda: parent_ui._paste_cell(row, col, self.btn_test)
        )
        self.btn_paste.setSizePolicy(QSizePolicy.Policy.Expanding,
                                     QSizePolicy.Policy.Expanding)
        bottom.addWidget(self.btn_paste)

        # stretch = 2 pour occuper 2/5
        layout.addLayout(bottom, 2)

    def refresh_display(self):
        """
        Met à jour le texte du bouton TEST :
            ligne 1 : "row,col"
            ligne 2 : adresse DMX (ex: 001)
        Sans toucher à l’icône.
        """
        entry = self.parent_ui.cell_config.get_cell(self.row, self.col)

        # Format row,col
        coord = f"{self.row},{self.col}"

        # Adresse DMX (3 chiffres)
        if entry is not None and hasattr(entry, "dmx") and entry.dmx is not None:
            try:
                dmx_addr = int(entry.dmx.address)
                dmx_str = f"{dmx_addr:03d}"
            except Exception:
                dmx_str = "---"
        else:
            dmx_str = "---"

        self.btn_test.setText(f"{coord}\n{dmx_str}")

