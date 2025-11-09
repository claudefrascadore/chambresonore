from PyQt6.QtWidgets import QWidget, QGridLayout, QPushButton

class GridWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chambre sonore – Grille 6×6")
        layout = QGridLayout()
        for row in range(6):
            for col in range(6):
                cell = QPushButton(f"{row*6+col+1:02}")
                layout.addWidget(cell, row, col)
        self.setLayout(layout)
