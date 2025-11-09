# -*- coding: utf-8 -*-
"""
gui.py — interface PyQt6 pour éditer la matrice 6×6 et tester audio/DMX.
"""
from __future__ import annotations
from PyQt6 import QtWidgets, QtGui, QtCore
from typing import Dict, Any, Callable
from matrice import GRID_W, GRID_H, load_config, save_config, dict_to_cellule, cellule_to_dict, VALID_LIGHT_MODES

class CellEditorDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, cell_data: Dict[str, Any] | None = None, on_test: Callable[[Dict[str, Any]], None] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Édition cellule")
        self.on_test = on_test
        self._data = cell_data or {}

        # Coordonnées et numéro
        self.x = self._data.get("x", 0)
        self.y = self._data.get("y", 0)
        self.numero = self.y * 6 + self.x + 1  # calcul du numéro 01–36

        layout = QtWidgets.QFormLayout(self)
        lbl_num = QtWidgets.QLabel(f"Cellule {self.numero:02d}  (x={self.x}, y={self.y})")
        font = lbl_num.font()
        font.setBold(True)
        lbl_num.setFont(font)
        layout.addRow(lbl_num)

        # Objet principal
        self.ed_objet = QtWidgets.QLineEdit(self._data.get("objet", ""))
        layout.addRow("Objet sonore (principal):", self.ed_objet)

        # Variations (3)
        self.var_edits = []
        for i in range(3):
            row = QtWidgets.QHBoxLayout()
            v = self._data.get("variations", [{}]*3)[i]
            ed_min = QtWidgets.QDoubleSpinBox()
            ed_min.setRange(0.0, 1.0); ed_min.setSingleStep(0.01); ed_min.setDecimals(2)
            ed_min.setValue(float(v.get("min_vol", [0.0,0.34,0.67][i])))
            ed_max = QtWidgets.QDoubleSpinBox()
            ed_max.setRange(0.0, 1.0); ed_max.setSingleStep(0.01); ed_max.setDecimals(2)
            ed_max.setValue(float(v.get("max_vol", [0.33,0.66,1.0][i])))
            ed_file = QtWidgets.QLineEdit(v.get("fichier", ""))
            row.addWidget(QtWidgets.QLabel(f"Var {i+1} min:")); row.addWidget(ed_min)
            row.addWidget(QtWidgets.QLabel("max:")); row.addWidget(ed_max)
            row.addWidget(QtWidgets.QLabel("fichier:")); row.addWidget(ed_file)
            layout.addRow(row)
            self.var_edits.append((ed_min, ed_max, ed_file))

        # Éclairage
        ecl = self._data.get("eclairage", {})
        self.sb_int = QtWidgets.QDoubleSpinBox(); self.sb_int.setRange(0.0,1.0); self.sb_int.setSingleStep(0.01); self.sb_int.setDecimals(2)
        self.sb_int.setValue(float(ecl.get("intensite", 0.75)))
        self.ed_col = QtWidgets.QLineEdit(ecl.get("couleur", "#ffffff"))
        self.cmb_mode = QtWidgets.QComboBox(); self.cmb_mode.addItems(sorted(list(VALID_LIGHT_MODES)))
        mode = ecl.get("mode", "fondu")
        idx = self.cmb_mode.findText(mode)
        if idx >= 0: self.cmb_mode.setCurrentIndex(idx)

        layout.addRow("Intensité:", self.sb_int)
        layout.addRow("Couleur hex (#rrggbb):", self.ed_col)
        layout.addRow("Mode:", self.cmb_mode)

        # Durée
        duree = ecl.get("duree", {})
        self.chk_auto = QtWidgets.QCheckBox("Durée automatique (temps de présence)")
        self.chk_auto.setChecked(duree.get("type", "auto") == "auto")
        self.sb_fix = QtWidgets.QDoubleSpinBox(); self.sb_fix.setRange(0.05, 60.0); self.sb_fix.setSingleStep(0.05); self.sb_fix.setDecimals(2)
        self.sb_fix.setValue(float(duree.get("valeur", 1.5)))
        self.sb_fix.setEnabled(not self.chk_auto.isChecked())
        self.chk_auto.toggled.connect(lambda s: self.sb_fix.setEnabled(not s))
        layout.addRow(self.chk_auto)
        layout.addRow("Durée fixe (s):", self.sb_fix)

        # Boutons
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btn_test = QtWidgets.QPushButton("Tester son+lumière")
        btns.addButton(btn_test, QtWidgets.QDialogButtonBox.ButtonRole.ActionRole)
        btn_test.clicked.connect(self._emit_test)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def _collect(self) -> Dict[str, Any]:
        vars_out = []
        for (ed_min, ed_max, ed_file) in self.var_edits:
            vars_out.append({
                "min_vol": float(ed_min.value()),
                "max_vol": float(ed_max.value()),
                "fichier": ed_file.text().strip()
            })
        return {
            "x": self.x,
            "y": self.y,
            "objet": self.ed_objet.text().strip(),
            "variations": vars_out,
            "eclairage": {
                "intensite": float(self.sb_int.value()),
                "couleur": self.ed_col.text().strip(),
                "mode": self.cmb_mode.currentText(),
                "duree": {
                    "type": "auto" if self.chk_auto.isChecked() else "fixe",
                    "valeur": float(self.sb_fix.value())
                }
            }
        }

    def _emit_test(self):
        if self.on_test:
            self.on_test(self._collect())

    def get_data(self) -> Dict[str, Any]:
        return self._collect()

class MainWindow(QtWidgets.QMainWindow):
    request_test = QtCore.pyqtSignal(dict)     # payload cellule pour test
    request_save = QtCore.pyqtSignal()         # sauver config
    request_reload = QtCore.pyqtSignal()       # recharger config

    def __init__(self, config_path: str):
        super().__init__()
        self.setWindowTitle("Chambre Sonore — Grille 6×6")
        self._config_path = config_path
        self._data = load_config(config_path)

        central = QtWidgets.QWidget(self)
        lay = QtWidgets.QGridLayout(central)
        self.setCentralWidget(central)

        self.buttons = {}
        num = 1
        for y in range(self._data["grid_h"]):
            for x in range(self._data["grid_w"]):
                label = f"{num:02d}"
                btn = QtWidgets.QPushButton(label)
                btn.setFixedSize(80, 40)  # boutons rectangulaires
                btn.clicked.connect(lambda _, xx=x, yy=y: self.edit_cell(xx, yy))
                lay.addWidget(btn, y, x)
                self.buttons[(x, y)] = btn
                num += 1

        # barre d'outils
        tb = self.addToolBar("Fichier")
        act_save = QtGui.QAction("Sauvegarder", self)
        act_save.triggered.connect(self._on_save)
        act_reload = QtGui.QAction("Recharger", self)
        act_reload.triggered.connect(self._on_reload)
        tb.addAction(act_save)
        tb.addAction(act_reload)

        self.statusBar().showMessage(self._config_path)

    def _find_cell(self, x: int, y: int) -> Dict[str, Any]:
        for c in self._data["cells"]:
            if c["x"] == x and c["y"] == y:
                return c
        raise KeyError(f"Cellule {x},{y} introuvable")

    def edit_cell(self, x: int, y: int):
        c = self._find_cell(x, y)

        def on_test(payload):
            self.request_test.emit(payload)

        dlg = CellEditorDialog(self, c, on_test=on_test)
        if dlg.exec():
            updated = dlg.get_data()
            c.update(updated)
            self.statusBar().showMessage(f"Cellule {x},{y} (#{y*6+x+1:02d}) mise à jour")

    def _on_save(self):
        save_config(self._config_path, self._data)
        self.statusBar().showMessage("Configuration sauvegardée")
        self.request_save.emit()

    def _on_reload(self):
        self._data = load_config(self._config_path)
        self.statusBar().showMessage("Configuration rechargée")
        self.request_reload.emit()

    def get_data(self) -> Dict[str, Any]:
        return self._data
