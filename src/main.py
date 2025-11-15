# -*- coding: utf-8 -*-
"""
main.py — point d'entrée
"""

import sys
from PyQt6.QtWidgets import QApplication

from src.orbbec_input import OrbbecStream
from src.tracker import Tracker
from src.calibration import GridCalibrator
from src.grid_ui import GridUI


def main():
    stream = OrbbecStream()
    calibrator = GridCalibrator(grid_rows=6, grid_cols=6, config_path="calibration.json")
    tracker = Tracker(stream=stream, calibrator=calibrator)

    app = QApplication(sys.argv)
    ui = GridUI(tracker=tracker, calibrator=calibrator) 
    ui.setWindowTitle("Chambre sonore — Vue portrait")
    ui.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

