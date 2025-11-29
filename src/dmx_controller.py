#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
dmx_controller.py
Contrôleur DMX pour la Chambre Sonore.

Version simplifiée qui utilise directement la commande `ola_set_dmx`
au lieu de l'API Python d'OLA (trop fragile avec Python 3.12).

Pré-requis :
    - OLA installé et fonctionnel
    - la commande `ola_set_dmx` disponible dans le PATH
"""

import subprocess


class DMXController:
    """
    Contrôleur DMX via ola_set_dmx.

    Universe par défaut : 0 (celui de ton Enttec USB Pro).
    """

    def __init__(self, universe=0):
        self.universe = universe

    def _run_ola_set_dmx(self, values):
        """
        Envoie une liste de valeurs DMX (0–255) via ola_set_dmx.
        Exemple :
            values = [255, 0, 0] -> --dmx 255,0,0
        """
        if not values:
            return

        dmx_str = ",".join(str(int(max(0, min(255, v)))) for v in values)

        cmd = [
            "ola_set_dmx",
            "--universe", str(self.universe),
            "--dmx", dmx_str,
        ]

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            # En cas d'erreur, on se contente de l'afficher dans la console
            print(f"[DMXController] Erreur ola_set_dmx : {e}")
        except FileNotFoundError:
            print("[DMXController] Erreur : ola_set_dmx introuvable dans le PATH.")

    def send_rgb(self, r, g, b):
        """
        Envoie un RGB simple sur les 3 premiers canaux du SlimPAR.
        r, g, b : 0–255
        """
        self._run_ola_set_dmx([r, g, b])

    def send_buffer(self, values):
        """
        Envoie un buffer DMX arbitraire (liste de valeurs 0–255).
        """
        self._run_ola_set_dmx(list(values))

    def blackout(self, channels=3):
        """
        Met les 'channels' premiers canaux à zéro (par défaut 3,
        suffisant pour un SlimPAR RGB simple).
        """
        self._run_ola_set_dmx([0] * channels)

