# -*- coding: utf-8 -*-
"""
tracker.py — simulateur d'événements de tracking.
Contrat minimal: publier des objets TrackerEvent(x, y, volume, dwell_s)
Remplacer cette source par l'intégration Orbbec réelle.
"""
from __future__ import annotations
from dataclasses import dataclass
import random, time, threading
from typing import Callable, Optional

@dataclass
class TrackerEvent:
    x: int          # 0..5
    y: int          # 0..5
    volume: float   # 0..1
    dwell_s: float  # temps passé dans la cellule (s)

class TrackerSimulator:
    def __init__(self, on_event: Callable[[TrackerEvent], None], period_s: float = 1.0):
        self.on_event = on_event
        self.period_s = max(0.1, float(period_s))
        self._stop = False
        self._thread: Optional[threading.Thread] = None
        self._dwell = 0.0
        self._last = None

    def start(self):
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True
        if self._thread:
            self._thread.join(timeout=1.0)

    def _run(self):
        while not self._stop:
            if self._last is None or random.random() < 0.3:
                # change de cellule
                x = random.randint(0, 5)
                y = random.randint(0, 5)
                self._last = (x, y)
                self._dwell = 0.0
            else:
                x, y = self._last
            vol = max(0.0, min(1.0, random.random()))
            self._dwell += self.period_s
            evt = TrackerEvent(x=x, y=y, volume=vol, dwell_s=self._dwell)
            self.on_event(evt)
            time.sleep(self.period_s)
