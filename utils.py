from PySide6.QtCore import QFile, QTextStream
import os, sys

def res_path(relative_path: str) -> str:
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def load_stylesheet(path: str = ":/assets/style_2048.qss"):
    file = QFile(path)
    if not file.open(QFile.ReadOnly | QFile.Text):
        return ""
    stream = QTextStream(file)
    css = stream.readAll()
    file.close()
    return css
