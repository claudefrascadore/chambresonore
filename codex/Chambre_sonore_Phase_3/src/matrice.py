# -*- coding: utf-8 -*-
"""
matrice.py — gestion de la matrice 6×6: lecture/sauvegarde JSON, structures et helpers.

Chaque cellule contient:
- objet sonore principal (optionnel) + 3 variations mappées à des plages de volume [0..1]
- paramètres d'éclairage (intensité, couleur hex, mode, durée auto/fixe)
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
import json, os, re

GRID_W = 6
GRID_H = 6

VALID_LIGHT_MODES = {"continu", "strobe", "fondu", "fondu_up", "fondu_down"}

def clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

def valid_hex_color(s: str) -> bool:
    return bool(re.fullmatch(r"#?[0-9A-Fa-f]{6}", s or ""))

@dataclass
class Variation:
    min_vol: float = 0.0
    max_vol: float = 1.0
    fichier: str = ""  # chemin du fichier audio pour cette variation

    def normalize(self) -> None:
        self.min_vol = clamp01(float(self.min_vol))
        self.max_vol = clamp01(float(self.max_vol))
        if self.min_vol > self.max_vol:
            self.min_vol, self.max_vol = self.max_vol, self.min_vol

@dataclass
class DureeParam:
    type: str = "auto"   # "auto" ou "fixe"
    valeur: float = 1.5  # utilisé seulement si type == "fixe"

    def normalize(self) -> None:
        self.type = "auto" if self.type not in ("auto", "fixe") else self.type
        self.valeur = max(0.05, float(self.valeur))

@dataclass
class Eclairage:
    intensite: float = 0.75     # 0..1
    couleur: str = "#ffffff"    # hex RGB
    mode: str = "fondu"         # continu|strobe|fondu|fondu_up|fondu_down
    duree: DureeParam = field(default_factory=DureeParam)

    def normalize(self) -> None:
        self.intensite = clamp01(float(self.intensite))
        if not valid_hex_color(self.couleur):
            self.couleur = "#ffffff"
        if not self.couleur.startswith("#"):
            self.couleur = "#" + self.couleur
        self.mode = self.mode if self.mode in VALID_LIGHT_MODES else "fondu"
        self.duree.normalize()

@dataclass
class Cellule:
    x: int = 0
    y: int = 0
    objet: str = ""  # fichier audio principal (optionnel)
    variations: List[Variation] = field(default_factory=lambda: [
        Variation(0.0, 0.33, ""),
        Variation(0.34, 0.66, ""),
        Variation(0.67, 1.0, ""),
    ])
    eclairage: Eclairage = field(default_factory=Eclairage)

    def normalize(self) -> None:
        for v in self.variations:
            v.normalize()
        self.eclairage.normalize()

    def select_variation_by_volume(self, vol: float) -> str:
        vol = clamp01(vol)
        # on parcourt dans l'ordre; si aucune plage stricte, on tombe sur la dernière non vide
        chosen = ""
        for v in self.variations:
            if v.min_vol <= vol <= v.max_vol and v.fichier:
                return v.fichier
            if v.fichier:
                chosen = v.fichier
        return chosen

def cellule_to_dict(c: Cellule) -> Dict[str, Any]:
    return {
        "x": c.x,
        "y": c.y,
        "objet": c.objet,
        "variations": [asdict(v) for v in c.variations],
        "eclairage": {
            "intensite": c.eclairage.intensite,
            "couleur": c.eclairage.couleur,
            "mode": c.eclairage.mode,
            "duree": {
                "type": c.eclairage.duree.type,
                "valeur": c.eclairage.duree.valeur
            }
        }
    }

def dict_to_cellule(d: Dict[str, Any]) -> Cellule:
    variations = [Variation(**v) for v in d.get("variations", [])]
    duree = d.get("eclairage", {}).get("duree", {})
    ecl = Eclairage(
        intensite=d.get("eclairage", {}).get("intensite", 0.75),
        couleur=d.get("eclairage", {}).get("couleur", "#ffffff"),
        mode=d.get("eclairage", {}).get("mode", "fondu"),
        duree=DureeParam(**{
            "type": duree.get("type", "auto"),
            "valeur": duree.get("valeur", 1.5),
        })
    )
    cell = Cellule(
        x=int(d.get("x", 0)),
        y=int(d.get("y", 0)),
        objet=d.get("objet", ""),
        variations=variations if variations else [
            Variation(0.0, 0.33, ""),
            Variation(0.34, 0.66, ""),
            Variation(0.67, 1.0, ""),
        ],
        eclairage=ecl
    )
    cell.normalize()
    return cell

def create_default_matrix() -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "grid_w": GRID_W,
        "grid_h": GRID_H,
        "cells": []
    }
    for y in range(GRID_H):
        for x in range(GRID_W):
            c = Cellule(x=x, y=y)
            data["cells"].append(cellule_to_dict(c))
    return data

def load_config(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return create_default_matrix()
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    # normaliser
    out = {"grid_w": int(d.get("grid_w", GRID_W)), "grid_h": int(d.get("grid_h", GRID_H)), "cells": []}
    for c in d.get("cells", []):
        out["cells"].append(cellule_to_dict(dict_to_cellule(c)))
    return out

def save_config(path: str, data: Dict[str, Any]) -> None:
    # valider + normaliser avant d'écrire
    norm_cells = []
    for c in data.get("cells", []):
        norm_cells.append(cellule_to_dict(dict_to_cellule(c)))
    data = {
        "grid_w": int(data.get("grid_w", GRID_W)),
        "grid_h": int(data.get("grid_h", GRID_H)),
        "cells": norm_cells
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
