from PySide6.QtCore import Qt, QSettings, QSize
from PySide6.QtWidgets import QWidget,  QFrame, QLabel,  QHBoxLayout
from PySide6.QtGui import QFont

class HUD(QWidget):
    def __init__(self, parent: QWidget | None = None, settings: QSettings | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.settings = settings

        self.score_layout = QHBoxLayout(self)
        self.score_layout.setContentsMargins(0, 0, 0, 0)
        self.score_layout.setSpacing(12)

        self.score_frame = QFrame(self)
        self.score_frame.setObjectName("ScoreFrame")

        self.score_frame_layout = QHBoxLayout(self.score_frame)
        self.score_frame_layout.setContentsMargins(4, 4, 4, 4) 
        self.score_frame_layout.setSpacing(0)

        self.score_label = QLabel(self.score_frame)
        self.score_label.setObjectName("ScoreLabel")
        self.score_frame_layout.addWidget(self.score_label)

        self.best_score_frame = QFrame(self)
        self.best_score_frame.setObjectName("ScoreFrame")

        self.best_score_frame_layout = QHBoxLayout(self.best_score_frame)
        self.best_score_frame_layout.setContentsMargins(4, 4, 4, 4)
        self.best_score_frame_layout.setSpacing(0)

        self.best_score_label = QLabel(self.best_score_frame)
        self.best_score_label.setObjectName("ScoreLabel")
        self.best_score_frame_layout.addWidget(self.best_score_label)

        self.score_layout.addWidget(self.score_frame)
        self.score_layout.addWidget(self.best_score_frame)

        self.setMinimumSize(250, 32)

    def update_score(self, new_score: int, best_score: int | None = None):
        self.score_label.setText(f"Score:\u2009{new_score}")
            
        self.best_score_label.setText(f"Best:\u2009{best_score}")

    def update_font_size(self, size: int):
        font = QFont()
        font.setPixelSize(round(size / 2.5))
        self.score_label.setFont(font)
        self.best_score_label.setFont(font)

    def sizeHint(self):
        return QSize(340, 50)