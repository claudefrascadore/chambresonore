# -*- coding: utf-8 -*-
"""
main.py — Pipeline hors Qt + Interface Qt
"""

import sys
from PyQt6.QtWidgets import QApplication
from src.dmx_controller import DMXController
from src.orbbec_depth_pipeline import PipelineOrbbec
from src.grid_ui import GridUI


def main():

    # 1) Pipeline créé AVANT Qt
    pipeline = PipelineOrbbec()

    # 2) Qt ensuite
    app = QApplication(sys.argv)
    dmx = DMXController(universe=0)
    ui = GridUI(pipeline=pipeline)
#    ui.resize(900,1500)
    ui.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

