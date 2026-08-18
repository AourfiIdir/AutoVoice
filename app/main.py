import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor, QPalette
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    app.setStyle("Fusion")

    CR = QPalette.ColorRole
    palette = app.palette()
    palette.setColor(CR.Window, QColor("#1e1e2e"))
    palette.setColor(CR.WindowText, QColor("#cdd6f4"))
    palette.setColor(CR.Base, QColor("#313244"))
    palette.setColor(CR.AlternateBase, QColor("#45475a"))
    palette.setColor(CR.Text, QColor("#cdd6f4"))
    palette.setColor(CR.Button, QColor("#45475a"))
    palette.setColor(CR.ButtonText, QColor("#cdd6f4"))
    palette.setColor(CR.Highlight, QColor("#2563eb"))
    palette.setColor(CR.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
