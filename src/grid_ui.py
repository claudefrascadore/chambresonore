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
from PyQt6.QtCore import Qt, QTimer
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
    QMessageBox
)

from src.orbbec_view_depth import OrbbecDepthView
from src.zone_detector import ZoneDetector
from src.cell_config import CellConfig, CellConfigEntry, DMXConfig
from src.zone_mapper_3d import ZoneMapper3D


# ----------------------------------------------------------------------
#   CLASSE PRINCIPALE : GridUI
# ----------------------------------------------------------------------

class GridUI(QWidget):
    """
    Interface principale pour la Chambre Sonore.
    Contient :
      - une vue profondeur Orbbec
      - une grille dynamique (rows × cols)
      - un timer qui lit les données, met à jour la vue et calcule les zones
    """

    def __init__(self, pipeline, parent=None):
        super().__init__(parent)

        self.pipeline = pipeline
        print("GridUI initialisé, pipeline reçu :", self.pipeline)

        self.depth_view = None
        self.cells = []

        # Configuration pièce + matrice
        self.room_width_m = 3.0      # largeur (X)
        self.room_depth_m = 4.0      # profondeur (Y)
        self.grid_rows = 6
        self.grid_cols = 6

        # Paramètres physiques de la caméra (pour projection 3D)
        self.cam_height_m = 1.80          # hauteur
        self.cam_angle_deg = 10.0         # pitch
        self.cam_wall_dist_m = 0.30       # distance mur → début zone
        self.cam_offset_m = -2.40 + 1.90  # décalage latéral (gauche = négatif)

        # 3D Mapper
        self.mapper3d = ZoneMapper3D(
            cam_height_m=self.cam_height_m,
            cam_angle_deg=self.cam_angle_deg,
            cam_wall_dist_m=self.cam_wall_dist_m,
            cam_offset_m=self.cam_offset_m
        )

        # Config des cellules (positions + wav + DMX)
        self.cell_config = CellConfig(
            room_width_m=self.room_width_m,
            room_depth_m=self.room_depth_m,
            rows=self.grid_rows,
            cols=self.grid_cols
        )

        # Seuil de présence (profondeur max pour considérer une personne)
        self.presence_threshold_mm = 2000

        # Détecteur de zones basé sur rows/cols (image)
        self.zone_detector = ZoneDetector(
            rows=self.grid_rows,
            cols=self.grid_cols
        )

        self.setWindowTitle("Chambre Sonore — Vue profondeur")
        self.resize(900, 1500)

        self._build_ui()
        self._start_timer()

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construit l'interface : vue + grille dynamique + boutons."""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # VUE PROFONDEUR
        self.depth_view = OrbbecDepthView(self)
        main_layout.addWidget(self.depth_view, stretch=2)

        # GRILLE DYNAMIQUE
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(2)
        self._build_grid_labels()
        main_layout.addLayout(self.grid_layout, stretch=1)

        # BOUTONS
        btn_layout = QGridLayout()

        self.btn_reset = QPushButton("Réinitialiser la grille")
        self.btn_reset.clicked.connect(self.reset_cells)

        self.btn_config = QPushButton("Configurer la grille")
        self.btn_config.clicked.connect(self.open_config_dialog)

        self.btn_floor_map = QPushButton("Carte au sol")
        self.btn_floor_map.clicked.connect(self.open_floor_map_dialog)

        self.btn_quit = QPushButton("Quitter")
        self.btn_quit.clicked.connect(self.close)

        self.btn_cam = QPushButton("Config Caméra")
        self.btn_cam.clicked.connect(self.open_camera_config_dialog)

        btn_layout.addWidget(self.btn_reset,     0, 0)
        btn_layout.addWidget(self.btn_config,    0, 1)
        btn_layout.addWidget(self.btn_floor_map, 0, 2)
        btn_layout.addWidget(self.btn_quit,      0, 3)
        btn_layout.addWidget(self.btn_cam, 1, 0)

        main_layout.addLayout(btn_layout)

    # ------------------------------------------------------------------

    def _build_grid_labels(self) -> None:
        """Construit les labels de la matrice selon grid_rows/grid_cols."""
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
                label = QLabel(f"{row},{col}")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setStyleSheet(
                    "background:#222; color:white; border:1px solid #444; padding:4px;"
                )
                self.grid_layout.addWidget(label, row, col)
                row_cells.append(label)
            self.cells.append(row_cells)

    # ------------------------------------------------------------------

    def _start_timer(self) -> None:
        """Timer pour lecture pipeline + analyse zones."""
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self.update_frame_and_zones)
        self.frame_timer.start(50)

    # ------------------------------------------------------------------

    def update_frame_and_zones(self) -> None:
            ok = self.pipeline.poll()
            if not ok:
                return

            # 1. Image profondeur → mise à jour visuelle
            img = self.pipeline.get_depth_frame()
            if img is not None:
                self.depth_view.update_image(img)

            # 2. Lecture données profondeur
            depth_data = self.pipeline.get_depth_data()
            if depth_data is None:
                self._clear_grid()
                return

            # 3. Reconstruction 3D
            cloud = self.mapper3d.compute_point_cloud(depth_data)

            # 4. Projection au sol
            ground_xy = self.mapper3d.project_to_ground(cloud)

            # 5. Position XY détectée
            pos = self.mapper3d.detect_person_position(ground_xy)
            # print("Position XY détectée :", pos)

            if pos is None:
                self._clear_grid()
                return

            # 6. Conversion XY → cellule physique (r,c)
            cell = self.mapper3d.map_to_cell(
                position_xy=pos,
                room_width_m=self.room_width_m,
                room_depth_m=self.room_depth_m,
                rows=self.grid_rows,
                cols=self.grid_cols
            )

            # print("Cellule détectée :", cell)

            if cell is None:
                self._clear_grid()
                return

            r, c = cell

            # 7. Mise à jour de la grille : UNE seule cellule active
            self._clear_grid()

            if 0 <= r < self.grid_rows and 0 <= c < self.grid_cols:
                self.cells[r][c].setStyleSheet(
                    "background:#ff8800; color:black; "
                    "border:3px solid white; padding:4px;"
                )
                self.cells[r][c].setText(f"{r},{c}\nACTIVE")

            # 8. Hook pour DMX / sons
            self.handle_zone_activity_3d(pos, (r, c))

    # ------------------------------------------------------------------

    def _clear_grid(self):
        """Efface la coloration de la grille."""
        for r in range(self.grid_rows):
            for c in range(self.grid_cols):
                self.cells[r][c].setText(f"{r},{c}")
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
    def handle_zone_activity_3d(
        self,
        position_xy: tuple[float, float] | None,
        cell: tuple[int, int] | None
    ) -> None:
        """
        Hook 3D pour la suite :
          - position_xy : (x, y) en mètres dans la pièce
          - cell        : (row, col) dans la matrice physique

        Pour l’instant :
          - log texte
          - si une CellConfig existe pour cette cellule, on affiche
            son nom, son wav et sa config DMX.
        """
        if position_xy is None or cell is None:
            return

        x, y = position_xy
        r, c = cell

        print("handle_zone_activity_3d →")
        print(f"  Position XY (m) : x={x:.2f}, y={y:.2f}")
        print(f"  Cellule         : row={r}, col={c}")

        entry = self.cell_config.get_cell(r, c)
        if entry is None:
            print("  Aucune CellConfig associée à cette cellule.")
            return

        print(f"  CellConfig : id={entry.cell_id}, nom='{entry.name}'")
        print(f"    WAV      : {entry.wav or '(aucun)'}")
        print(f"    Volume   : {entry.volume}")
        print(f"    DMX      : universe={entry.dmx.universe}, "
              f"address={entry.dmx.address}, channels={entry.dmx.channels}, "
              f"color={entry.dmx.color}")


    # ------------------------------------------------------------------

    def reset_cells(self) -> None:
        self._clear_grid()

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
            self.room_width_m = dialog.room_width_m
            self.room_depth_m = dialog.room_depth_m
            self.grid_rows = dialog.rows
            self.grid_cols = dialog.cols

            print("Nouvelle configuration pièce/matrice :")
            print("  largeur      :", self.room_width_m, "m")
            print("  profondeur   :", self.room_depth_m, "m")
            print("  rows × cols  :", self.grid_rows, "x", self.grid_cols)

            self.cell_config.rebuild_grid(
                room_width_m=self.room_width_m,
                room_depth_m=self.room_depth_m,
                rows=self.grid_rows,
                cols=self.grid_cols,
                keep_existing=True
            )

            self.cell_config.save()

            self._build_grid_labels()
            self.zone_detector = ZoneDetector(
                rows=self.grid_rows,
                cols=self.grid_cols
            )

            self._clear_grid()
            self.update()
            self.repaint()

    # ------------------------------------------------------------------
    def open_floor_map_dialog(self) -> None:
        dialog = FloorMapDialog(self)
        dialog.exec()

    def open_camera_config_dialog(self) -> None:
        dialog = CameraConfigDialog(
            cam_height_m=self.cam_height_m,
            cam_angle_deg=self.cam_angle_deg,
            cam_wall_dist_m=self.cam_wall_dist_m,
            cam_offset_m=self.cam_offset_m,
            parent=self
        )
        if dialog.exec():
            self.cam_height_m = dialog.cam_height_m
            self.cam_angle_deg = dialog.cam_angle_deg
            self.cam_wall_dist_m = dialog.cam_wall_dist_m
            self.cam_offset_m = dialog.cam_offset_m

            print("Nouvelle configuration caméra :")
            print("  hauteur =", self.cam_height_m, "m")
            print("  angle   =", self.cam_angle_deg, "°")
            print("  mur→zone =", self.cam_wall_dist_m, "m")
            print("  offset  =", self.cam_offset_m, "m")
            
            self.mapper3d.cam_height_m = self.cam_height_m
            self.mapper3d.cam_angle_deg = self.cam_angle_deg
            self.mapper3d.cam_wall_dist_m = self.cam_wall_dist_m
            self.mapper3d.cam_offset_m = self.cam_offset_m
            self.mapper3d._update_rotation_matrix()



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
        layout.addWidget(buttons)
        self.setLayout(layout)

        self.room_width_m = room_width_m
        self.room_depth_m = room_depth_m
        self.rows = rows
        self.cols = cols

    def accept(self) -> None:
        self.room_width_m = float(self._room_width_spin.value())
        self.room_depth_m = float(self._room_depth_spin.value())
        self.rows = int(self._rows_spin.value())
        self.cols = int(self._cols_spin.value())
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
                btn.clicked.connect(self._edit_cell)
                grid.addWidget(btn, r, c)

        layout.addLayout(grid)

        close_btn = QPushButton("Fermer", self)
        close_btn.clicked.connect(self.accept)
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

