#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
grid_ui.py (version corrigée et nettoyée)
Interface principale de la Chambre Sonore
— Vue profondeur uniquement —
Compatible avec orbbec_view_depth.py
"""

import sys
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QGridLayout,
    QVBoxLayout,
    QPushButton,
    QLabel
)

# Vue profondeur Orbbec (pipeline séparé)
from src.orbbec_view_depth import OrbbecDepthView


# -------------------------------------------------------------------------
#   CLASSE PRINCIPALE : GRIDUI (sans tracker, sans calibrator)
# -------------------------------------------------------------------------

class GridUI(QWidget):
    """
    Interface principale pour la Chambre Sonore.
    Contient :
      - une vue profondeur Orbbec (colormap magma)
      - une grille 6×6 pour les zones spatiales
      - des boutons de contrôle
    """

    def __init__(self, pipeline, parent=None):
        super().__init__(parent)
        self.pipeline = pipeline
        
        self.setWindowTitle("Chambre Sonore — Vue profondeur")
        self.depth_view = None
        self.cells = []

        self._build_ui()
        self._start_timers()

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construit la fenêtre Qt : vue + grille + boutons."""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # SECTION — Vue profondeur Orbbec
        self.depth_view = OrbbecDepthView(self.pipeline, self)
        main_layout.addWidget(self.depth_view, stretch=2)

        # SECTION — Grille 6×6
        grid = QGridLayout()
        grid.setSpacing(2)

        for row in range(6):
            row_cells = []
            for col in range(6):
                label = QLabel(f"{row},{col}")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setStyleSheet(
                    "background:#222; color:white; border:1px solid #444; padding:4px;"
                )
                grid.addWidget(label, row, col)
                row_cells.append(label)
            self.cells.append(row_cells)

        main_layout.addLayout(grid, stretch=1)

        # SECTION — Boutons divers
        btn_layout = QGridLayout()

        self.btn_reset = QPushButton("Réinitialiser la grille")
        self.btn_reset.clicked.connect(self.reset_cells)

        self.btn_quit = QPushButton("Quitter")
        self.btn_quit.clicked.connect(self.close)

        btn_layout.addWidget(self.btn_reset, 0, 0)
        btn_layout.addWidget(self.btn_quit, 0, 1)

        main_layout.addLayout(btn_layout)

    # ------------------------------------------------------------------

    def _start_timers(self) -> None:
        """Démarre un timer pour mettre à jour périodiquement la grille."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_cells)
        self.timer.start(250)

    # ------------------------------------------------------------------

    def update_cells(self) -> None:
        """
        Mise à jour visuelle simple (placeholder).
        La logique réelle sera alimentée plus tard par les données profondeur.
        """
        for row in range(6):
            for col in range(6):
                self.cells[row][col].setStyleSheet(
                    "background:#333; color:white; border:1px solid #444; padding:4px;"
                )

    # ------------------------------------------------------------------

    def reset_cells(self) -> None:
        """Réinitialise l’apparence des 36 cellules."""
        for row in range(6):
            for col in range(6):
                self.cells[row][col].setStyleSheet(
                    "background:#222; color:white; border:1px solid #444; padding:4px;"
                )


# -------------------------------------------------------------------------
#   POINT D’ENTRÉE (utilisé seulement si lancé directement)
# -------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    ui = GridUI()
    ui.resize(900, 900)
    ui.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

