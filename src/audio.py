# -*- coding: utf-8 -*-
"""
audio.py — abstraction audio:
- Essaie pygame.mixer pour jouer des WAV/OGG/MP3 simples
- Sinon bascule en simulateur (log console)
"""
from __future__ import annotations
import os

try:
    import pygame
    _PG_AVAILABLE = True
except Exception:
    _PG_AVAILABLE = False

class AudioInterface:
    def __init__(self, simulate: bool = False):
        self.simulate = simulate or (not _PG_AVAILABLE)
        if not self.simulate:
            pygame.mixer.init()
            self.channels = [pygame.mixer.Channel(i) for i in range(8)]
            self._next_ch = 0
        else:
            self.channels = []
            self._next_ch = 0

    def _get_channel(self):
        if self.simulate:
            return None
        ch = self.channels[self._next_ch % len(self.channels)]
        self._next_ch += 1
        return ch

    def play(self, path: str, volume: float = 1.0):
        if not path:
            return
        volume = max(0.0, min(1.0, float(volume)))
        if self.simulate:
            print(f"[AUDIO SIM] play '{path}' vol={volume}")
            return
        if not os.path.exists(path):
            print(f"[AUDIO WARN] Fichier introuvable: {path}")
            return
        try:
            snd = pygame.mixer.Sound(path)
            ch = self._get_channel()
            if ch:
                ch.set_volume(volume)
                ch.play(snd)
        except Exception as e:
            print(f"[AUDIO ERR] {e}")
