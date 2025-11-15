# -*- coding: utf-8 -*-
"""
orbbec_input.py
Gabarit minimal cohérent avec Orbbec SDK 2.0.15 (Linux x86_64).

ATTENTION:
- Adapte ici aux bindings que tu utilises déjà (OpenNI, OrbbecSDK Python, etc.).
- L'interface attendue par Tracker est simple: get_positions() retourne
  une liste d'objets/tuples avec id et (x,y,z) en coordonnées monde (plan au sol).
- Si tu as déjà ce module, NE CHANGE RIEN d'autre que d'assurer la signature.
"""

from typing import List, Dict, Tuple

class OrbbecStream:
    def __init__(self):
        # TODO: initialiser le pipeline capteur (SDK Orbbec 2.0.15)
        pass

    def get_positions(self) -> List[Dict]:
        """
        Retourne des positions ex:
        [
          {"id": 1, "x": 0.85, "y": 1.20, "z": 0.0},
          {"id": 2, "x": 2.10, "y": 0.40, "z": 0.0}
        ]
        Les unités doivent être cohérentes (mètres ou similaire).
        """
        # TODO: remplacer par l'extraction réelle via le SDK
        return []

