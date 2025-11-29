#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sound_engine.py
===============

Moteur audio pour la Chambre Sonore.

Objectifs :
    - Lecture simultanée de plusieurs sons (.wav), un par cellule au minimum.
    - Volume contrôlé par la "masse" perçue (facteur externe fourni par le UI).
    - Spatialisation stéréo simple (pan gauche/droite selon la colonne).
    - Prévoir la possibilité d'étendre à du multi-canal plus tard.

Implémentation actuelle :
    - Utilise pygame.mixer pour la lecture audio.
    - Chaque cellule logique possède un "canal" audio dédié.
    - Si un son est déjà en cours pour une cellule, on ajuste seulement volume et pan.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Hashable, Optional, Tuple

try:
    import pygame
    from pygame import mixer
except ImportError:
    pygame = None
    mixer = None


@dataclass
class CellSoundState:
    """État audio pour une cellule logique (r, c)."""

    cell_id: Hashable
    wav_path: str
    sound: "mixer.Sound | None"
    channel: "mixer.Channel | None"


class SoundEngine:
    """Moteur audio simple pour jouer un .wav par cellule, avec volume et pan."""

    def __init__(self) -> None:
        self.enabled: bool = False
        self._initialized: bool = False
        self._cells: Dict[Hashable, CellSoundState] = {}
        self._sounds_cache: Dict[str, "mixer.Sound"] = {}

        # Initialisation paresseuse : on essaiera d'initialiser au premier play().
        if pygame is None or mixer is None:
            print("[SoundEngine] pygame.mixer non disponible. Audio désactivé.")
        else:
            # On ne fait pas encore mixer.init() ici pour éviter les erreurs
            # si aucun device audio n'est présent au moment de l'import.
            pass

    # ------------------------------------------------------------------

    def _ensure_init(self) -> None:
        """Initialise pygame.mixer si nécessaire."""
        if self._initialized:
            return

        if pygame is None or mixer is None:
            self.enabled = False
            self._initialized = True
            return

        try:
            mixer.init()  # Utilise les paramètres par défaut de la carte son
            self.enabled = True
            self._initialized = True
            print("[SoundEngine] pygame.mixer initialisé.")
        except Exception as e:
            print(f"[SoundEngine] Erreur d'initialisation du mixer : {e}")
            self.enabled = False
            self._initialized = True

    # ------------------------------------------------------------------

    def _get_or_load_sound(self, wav_path: str) -> "mixer.Sound | None":
        """Charge ou récupère en cache un son .wav."""
        if not wav_path:
            return None

        if wav_path in self._sounds_cache:
            return self._sounds_cache[wav_path]

        try:
            snd = mixer.Sound(wav_path)
            self._sounds_cache[wav_path] = snd
            return snd
        except Exception as e:
            print(f"[SoundEngine] Impossible de charger '{wav_path}' : {e}")
            return None

    # ------------------------------------------------------------------

    def play_for_cell(
        self,
        cell_id: Hashable,
        wav_path: Optional[str],
        volume: float,
        pan: float,
    ) -> None:
        """Joue (ou met à jour) le son associé à une cellule.

        Arguments :
            cell_id : identifiant logique (par ex. (r, c)).
            wav_path : chemin complet vers le fichier .wav à jouer.
            volume   : intensité globale (0.0 à 1.0).
            pan      : panoramique stéréo (0.0 = full gauche, 1.0 = full droite).
        """
        if not wav_path:
            return

        self._ensure_init()
        if not self.enabled:
            return

        snd = self._get_or_load_sound(wav_path)
        if snd is None:
            return

        # Clamp volume et pan
        vol = max(0.0, min(1.0, volume))
        pan = max(0.0, min(1.0, pan))

        # Conversion pan → gains gauche/droite
        left = 1.0 - pan
        right = pan

        # Récupérer ou créer l'état pour cette cellule
        state = self._cells.get(cell_id)
        if state is None or state.sound is None:
            state = CellSoundState(
                cell_id=cell_id,
                wav_path=wav_path,
                sound=snd,
                channel=None,
            )
            self._cells[cell_id] = state
        else:
            # Mettre à jour le son si le chemin a changé
            if state.wav_path != wav_path:
                state.sound = snd
                state.wav_path = wav_path

        # Récupérer (ou créer) un channel pour cette cellule
        ch = state.channel
        if ch is None or not ch.get_busy():
            ch = mixer.find_channel(True)
            state.channel = ch
            if ch is None:
                print("[SoundEngine] Aucun canal libre disponible.")
                return
            ch.play(state.sound, loops=-1)  # lecture en boucle (pour installation)
        else:
            # Channel occupé : on ne relance pas le son, on ajuste juste volume/pan
            pass

        ch.set_volume(left * vol, right * vol)

    # ------------------------------------------------------------------

    def stop_cell(self, cell_id: Hashable) -> None:
        """Arrête le son pour une cellule donnée."""
        state = self._cells.get(cell_id)
        if state and state.channel:
            try:
                state.channel.stop()
            except Exception:
                pass

    # ------------------------------------------------------------------

    def stop_all(self) -> None:
        """Arrête tous les sons."""
        if not self._initialized or not self.enabled:
            return
        try:
            mixer.stop()
        except Exception:
            pass

    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Arrête le moteur audio et libère les ressources."""
        self.stop_all()
        if self._initialized and self.enabled:
            try:
                mixer.quit()
            except Exception:
                pass
        self.enabled = False
        self._initialized = True
        self._cells.clear()
        self._sounds_cache.clear()
        print("[SoundEngine] Arrêt complet.")

