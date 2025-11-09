# -*- coding: utf-8 -*-
"""
main.py — boucle principale: charge la config, lance l'UI, écoute le tracker,
applique audio/DMX selon cellule et volume, gère la durée auto/fixe.
"""
from __future__ import annotations
import sys, time
from typing import Dict, Any
from PyQt6 import QtWidgets, QtCore

from matrice import load_config, dict_to_cellule
from gui import MainWindow
from dmx import DMXInterface
from audio import AudioInterface
from tracker import TrackerSimulator, TrackerEvent

CONFIG_PATH = "config_matrice.json"

class Controller(QtCore.QObject):
    def __init__(self, win: MainWindow):
        super().__init__()
        self.win = win
        self.dmx = DMXInterface(universe=1, simulate=True)   # mettre simulate=False si OLA dispo
        self.audio = AudioInterface(simulate=True)           # mettre simulate=False si pygame dispo
        self._last_cell_key = None
        self._cell_enter_time = 0.0

        # Connexions UI
        self.win.request_test.connect(self._on_test_cell)

        # Tracker simulé
        self.tracker = TrackerSimulator(on_event=self._on_tracker_event, period_s=1.0)
        self.tracker.start()

    def _on_test_cell(self, payload: Dict[str, Any]):
        # jouer le son (var 1 si présente) et appliquer la lumière
        cell = dict_to_cellule(payload | {"x":0,"y":0})
        wav = ""
        for v in cell.variations:
            if v.fichier:
                wav = v.fichier
                break
        self.audio.play(wav, volume=1.0)
        # Exemple d'adresses DMX: R,G,B,Dim à configurer selon votre patch
        self.dmx.send_rgb_intensity(addr_r=1, addr_g=2, addr_b=3, addr_dim=4,
                                    color_hex=cell.eclairage.couleur,
                                    intensity=cell.eclairage.intensite)

    def _on_tracker_event(self, evt: TrackerEvent):
        data = self.win.get_data()
        # obtenir la cellule courante
        try:
            c_dict = next(c for c in data["cells"] if c["x"] == evt.x and c["y"] == evt.y)
        except StopIteration:
            return
        cell = dict_to_cellule(c_dict)

        # gestion du temps de présence "dwell"
        cell_key = (evt.x, evt.y)
        if cell_key != self._last_cell_key:
            self._last_cell_key = cell_key
            self._cell_enter_time = time.time()
            dwell = 0.0
        else:
            dwell = evt.dwell_s

        # sélection variation audio par volume
        wav = cell.select_variation_by_volume(evt.volume)
        if wav:
            # on mappe evt.volume sur le niveau de sortie audio pour la démo
            self.audio.play(wav, volume=max(0.1, min(1.0, evt.volume)))

        # éclairage
        # durée: auto => dwell, fixe => valeur
        if cell.eclairage.duree.type == "auto":
            duration = max(0.05, float(dwell))
        else:
            duration = cell.eclairage.duree.valeur

        # Applique un état simple (pas d'animation temps réel complexe dans ce proto):
        self.dmx.send_rgb_intensity(addr_r=1, addr_g=2, addr_b=3, addr_dim=4,
                                    color_hex=cell.eclairage.couleur,
                                    intensity=cell.eclairage.intensite)

        # Pour les modes spéciaux, on pourrait lancer un thread d'animation.
        if cell.eclairage.mode == "strobe":
            self.dmx.strobe(addr_strobe=5, speed_hz=8.0, duration_s=duration)
        # "fondu", "fondu_up", "fondu_down" seraient gérés par une boucle d'interpolation
        # (à implémenter selon votre fixture et votre besoin).

def main():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow(CONFIG_PATH)
    ctrl = Controller(win)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
