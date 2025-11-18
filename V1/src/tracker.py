# -*- coding: utf-8 -*-
"""
tracker.py
Rassemble les positions (x,y[,z]) détectées par orbbec_input et expose:
- positions en coordonnées "monde" (plan au sol)
- cellule de grille 6×6 correspondante si calibrage disponible

Intégration Phase 4:
- Injection d'un GridCalibrator pour mapper vers la grille.
"""

from typing import Dict, List, Optional, Tuple

# On suppose que orbbec_input fournit un flux de positions 2D/3D déjà filtrées
from src.orbbec_input import OrbbecStream
from src.calibration import GridCalibrator


class Tracker:
    def __init__(self, stream: OrbbecStream, calibrator: Optional[GridCalibrator] = None):
        self.stream = stream
        self.calibrator = calibrator

    def set_calibrator(self, calibrator: Optional[GridCalibrator]) -> None:
        self.calibrator = calibrator

    def get_targets(self) -> List[Dict]:
        """
        Retourne une liste d'objets cibles:
        {
          "id": int|str,
          "pos": (x,y,z?)  # coordonnées monde
          "cell": (row,col) | None  # cellule 6×6, si calibré
        }
        """
        raw = self.stream.get_positions()  # À implémentation existante (liste de dicts ou tuples)
        targets: List[Dict] = []
        for item in raw:
            # Normaliser la structure reçue
            if isinstance(item, dict):
                x = float(item.get("x", 0.0))
                y = float(item.get("y", 0.0))
                z = float(item.get("z", 0.0))
                tid = item.get("id", None)
            else:
                # Exemple: tuple (id, x, y, z)
                tid, x, y, z = item

            cell = None
            if self.calibrator is not None:
                cell = self.calibrator.world_to_cell(x, y, smooth=True)

            targets.append({
                "id": tid,
                "pos": (x, y, z),
                "cell": cell
            })
        return targets

