#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
cell_config.py
Configuration des cellules au sol pour la Chambre Sonore.

- Matrice configurable (rows × cols), carrée ou rectangulaire
- Chaque cellule est un objet indépendant avec :
    - identifiant "r,c"
    - position au sol en mètres (x_min, x_max, y_min, y_max)
    - paramètres sonores (wav, volume)
    - paramètres DMX (universe, address, channels, color)
- Sauvegarde / chargement en JSON
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict, field

@dataclass
class DMXConfig:
    universe: int = 1
    address: int = 1
    channels: int = 3
    color: tuple[int, int, int] = (255, 255, 255)


@dataclass
class CellConfigEntry:
    cell_id: str
    name: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    wav: str = ""
    volume: float = 1.0
    dmx: DMXConfig = field(default_factory=DMXConfig)
    active: bool = True

    def to_dict(self) -> dict:
        data = asdict(self)
        dmx_data = data.pop("dmx")
        data["dmx"] = dmx_data
        return data

    def clone(self):
        return CellConfigEntry(
            cell_id=self.cell_id,
            name=self.name,
            x_min=self.x_min,
            x_max=self.x_max,
            y_min=self.y_min,
            y_max=self.y_max,
            wav=self.wav,
            volume=self.volume,
            dmx=DMXConfig(
                universe=self.dmx.universe,
                address=self.dmx.address,
                channels=self.dmx.channels,
                color=self.dmx.color
            )
        )

    def apply_from(self, other):
        self.name = other.name
        self.wav = other.wav
        self.volume = other.volume
        self.dmx = DMXConfig(
            universe=other.dmx.universe,
            address=other.dmx.address,
            channels=other.dmx.channels,
            color=other.dmx.color
        )


    @staticmethod
    def from_dict(data: dict) -> "CellConfigEntry":
        dmx_data = data.get("dmx", {})
        dmx = DMXConfig(
            universe=dmx_data.get("universe", 1),
            address=dmx_data.get("address", 1),
            channels=dmx_data.get("channels", 3),
            color=tuple(dmx_data.get("color", (255, 255, 255))),
        )
        return CellConfigEntry(
            cell_id=data["cell_id"],
            name=data.get("name", data["cell_id"]),
            x_min=data.get("x_min", 0.0),
            x_max=data.get("x_max", 1.0),
            y_min=data.get("y_min", 0.0),
            y_max=data.get("y_max", 1.0),
            wav=data.get("wav", ""),
            volume=data.get("volume", 1.0),
            dmx=dmx,
            active=data.get("active", True),
        )

class CellConfig:
    """
    Gère la configuration de la matrice de cellules au sol.

    La matrice est définie par :
      - room_width_m, room_depth_m (dimensions de la pièce)
      - rows, cols (nombre de cellules)
    Les positions (x_min/x_max/y_min/y_max) sont calculées automatiquement.
    """

    def __init__(
        self,
        room_width_m: float = 6.0,
        room_depth_m: float = 6.0,
        rows: int = 6,
        cols: int = 6,
        json_path: Path | None = None,
    ):
        self.room_width_m = float(room_width_m)
        self.room_depth_m = float(room_depth_m)
        self.rows = int(rows)
        self.cols = int(cols)

        if json_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            config_dir = base_dir / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            self.json_path = config_dir / "cells.json"
        else:
            self.json_path = Path(json_path)

        self.cells: dict[str, CellConfigEntry] = {}
        self._load_or_init()

    # ------------------------------------------------------------------

    def _load_or_init(self) -> None:
        if self.json_path.exists():
            try:
                self._load()
                return
            except Exception as exc:
                print("Erreur chargement cells.json, réinitialisation :", exc)

        self._build_default_grid()
        self.save()

    # ------------------------------------------------------------------

    def _build_default_grid(self) -> None:
        """Construit une grille par défaut selon les dimensions pièce + matrice."""
        self.cells.clear()

        if self.cols <= 0 or self.rows <= 0:
            return

        cell_w = self.room_width_m / float(self.cols)
        cell_h = self.room_depth_m / float(self.rows)

        for r in range(self.rows):
            for c in range(self.cols):
                cell_id = f"{r},{c}"
                x_min = c * cell_w
                x_max = (c + 1) * cell_w
                y_min = r * cell_h
                y_max = (r + 1) * cell_h

                entry = CellConfigEntry(
                    cell_id=cell_id,
                    name=f"cell_{cell_id}",
                    x_min=x_min,
                    x_max=x_max,
                    y_min=y_min,
                    y_max=y_max,
                )
                self.cells[cell_id] = entry

    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Charge la configuration depuis le JSON, en respectant rows/cols actuels."""
        raw = json.loads(self.json_path.read_text(encoding="utf-8"))

        self.room_width_m = float(raw.get("room_width_m", self.room_width_m))
        self.room_depth_m = float(raw.get("room_depth_m", self.room_depth_m))
        self.rows = int(raw.get("rows", self.rows))
        self.cols = int(raw.get("cols", self.cols))

        cells_raw = raw.get("cells", {})
        self.cells.clear()
        for cell_id, data in cells_raw.items():
            entry = CellConfigEntry.from_dict(data)
            self.cells[cell_id] = entry

        expected_count = self.rows * self.cols
        if len(self.cells) != expected_count:
            print("Nombre de cellules incohérent avec rows/cols, reconstruction.")
            self._build_default_grid()

    # ------------------------------------------------------------------

    def save(self) -> None:
        data = {
            "room_width_m": self.room_width_m,
            "room_depth_m": self.room_depth_m,
            "rows": self.rows,
            "cols": self.cols,
            "cells": {cid: entry.to_dict() for cid, entry in self.cells.items()},
        }
        self.json_path.write_text(
            json.dumps(data, indent=4),
            encoding="utf-8"
        )

    # ------------------------------------------------------------------

    def rebuild_grid(
        self,
        room_width_m: float,
        room_depth_m: float,
        rows: int,
        cols: int,
        keep_existing: bool = True,
    ) -> None:
        """
        Recalcule les positions des cellules pour une nouvelle matrice.

        keep_existing=True :
          conserve les infos wav/dmx existantes quand c'est possible.
        """
        old_cells = self.cells.copy() if keep_existing else {}
        self.room_width_m = float(room_width_m)
        self.room_depth_m = float(room_depth_m)
        self.rows = int(rows)
        self.cols = int(cols)

        self.cells.clear()

        if self.cols <= 0 or self.rows <= 0:
            return

        cell_w = self.room_width_m / float(self.cols)
        cell_h = self.room_depth_m / float(self.rows)

        for r in range(self.rows):
            for c in range(self.cols):
                cell_id = f"{r},{c}"
                x_min = c * cell_w
                x_max = (c + 1) * cell_w
                y_min = r * cell_h
                y_max = (r + 1) * cell_h

                if keep_existing and cell_id in old_cells:
                    old = old_cells[cell_id]
                    entry = CellConfigEntry(
                        cell_id=cell_id,
                        name=old.name,
                        x_min=x_min,
                        x_max=x_max,
                        y_min=y_min,
                        y_max=y_max,
                        wav=old.wav,
                        volume=old.volume,
                        dmx=old.dmx,
                        active=old.active,
                    )
                else:
                    entry = CellConfigEntry(
                        cell_id=cell_id,
                        name=f"cell_{cell_id}",
                        x_min=x_min,
                        x_max=x_max,
                        y_min=y_min,
                        y_max=y_max,
                    )

                self.cells[cell_id] = entry

        self.save()

    # ------------------------------------------------------------------

    def get_cell(self, row: int, col: int) -> CellConfigEntry | None:
        cell_id = f"{row},{col}"
        cell_info = self.cells.get(cell_id)
        # print("CELL INFO:", row, col, cell_info.wav if cell_info else None)
        return cell_info

    def set_cell(self, entry: CellConfigEntry) -> None:
        self.cells[entry.cell_id] = entry
        self.save()

    # ------------------------------------------------------------------

    def all_cells(self) -> list[CellConfigEntry]:
        return list(self.cells.values())

