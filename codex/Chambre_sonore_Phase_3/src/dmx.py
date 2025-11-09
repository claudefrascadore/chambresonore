# -*- coding: utf-8 -*-
"""
dmx.py — abstraction DMX.
- Essaie OLA; sinon bascule en simulateur (log console).
- Conversion couleur hex -> RGB 8 bits.
- Fonctions pour appliquer intensité/couleur et modes de base.
"""
from __future__ import annotations
import time, threading
from typing import Tuple

try:
    import ola
    from ola.ClientWrapper import ClientWrapper
    _OLA_AVAILABLE = True
except Exception:
    _OLA_AVAILABLE = False

def hex_to_rgb(color: str) -> Tuple[int, int, int]:
    s = color[1:] if color.startswith("#") else color
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    return r, g, b

class DMXInterface:
    def __init__(self, universe: int = 1, simulate: bool = False):
        self.universe = universe
        self.simulate = simulate or (not _OLA_AVAILABLE)
        if not self.simulate:
            self.wrapper = ClientWrapper()
            self.client = self.wrapper.Client()
        else:
            self.wrapper = None
            self.client = None

    def send_rgb_intensity(self, addr_r: int, addr_g: int, addr_b: int, addr_dim: int, color_hex: str, intensity: float):
        r, g, b = hex_to_rgb(color_hex)
        intensity = max(0.0, min(1.0, float(intensity)))
        # on applique la dimmer au niveau global
        r_val = int(r * intensity)
        g_val = int(g * intensity)
        b_val = int(b * intensity)

        # construire le paquet DMX (512 canaux)
        data = bytearray(512)
        if addr_r: data[addr_r-1] = r_val
        if addr_g: data[addr_g-1] = g_val
        if addr_b: data[addr_b-1] = b_val
        if addr_dim: data[addr_dim-1] = int(255 * intensity)

        if self.simulate:
            print(f"[DMX SIM] universe={self.universe} R@{addr_r}={r_val} G@{addr_g}={g_val} B@{addr_b}={b_val} DIM@{addr_dim}={int(255*intensity)}")
        else:
            self.client.SendDmx(self.universe, data, lambda state: None)

    def strobe(self, addr_strobe: int, speed_hz: float, duration_s: float):
        # simple implémentation: active/désactive dimmer au rythme voulu si pas de canal strobe dédié
        # si addr_strobe > 0: écrire directement une valeur pour vitesse; sinon fallback.
        if self.simulate:
            print(f"[DMX SIM] STROBE addr={addr_strobe} speed={speed_hz}Hz for {duration_s}s")
            time.sleep(duration_s)
            return
        # Pour un vrai projecteur: écrire sur addr_strobe (valeur dépend du fixture profile)
        # Ici on se contente d'un sleep pour l'exemple.
        time.sleep(duration_s)
