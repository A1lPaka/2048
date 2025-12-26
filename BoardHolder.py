from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtWidgets import QWidget

from GameBoard import GameBoard
from ControlsPanel import ControlButton
from sounds import SoundsEffects

class BoardHolder(QWidget):
    def __init__(self, parent: QWidget | None = None, size: int = 4, sfx: SoundsEffects | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.game_board = GameBoard(self, size=size, sfx=sfx)
        self.current_game_area = 0

        self.up_button = ControlButton(direction="up", parent=self, sfx=sfx)
        self.down_button = ControlButton(direction="down",  parent=self, sfx=sfx)
        self.left_button = ControlButton(direction="left", parent=self, sfx=sfx)
        self.right_button = ControlButton(direction="right", parent=self, sfx=sfx)

        self.setMinimumSize(322, 322)

    def resizeEvent(self, event):
        w = self.width()
        h = self.height()

        frame_side = min(w, h)
        frame_x = (w - frame_side) // 2
        frame_y = (h - frame_side) // 2

        gap = 2

        board_side = round((frame_side - 2 * gap) / 1.25)

        btn_big_side = board_side // 2
        btn_small_side = board_side // 8

        space_for_buttons = gap + btn_small_side

        board_x = frame_x + space_for_buttons
        board_y = frame_y + space_for_buttons

        self.game_board.setGeometry(board_x, board_y, board_side, board_side)

        upbtn_x = frame_x + (frame_side - btn_big_side) // 2
        upbtn_y = frame_y

        btmbtn_x = upbtn_x
        btmbtn_y = frame_y + frame_side - btn_small_side

        lftbtn_x = frame_x
        lftbtn_y = frame_y + (frame_side - btn_big_side) // 2

        rgtbtn_x = frame_x + frame_side - btn_small_side
        rgtbtn_y = frame_y + (frame_side - btn_big_side) // 2
        
        self.up_button.setGeometry(upbtn_x, upbtn_y, btn_big_side, btn_small_side)
        self.down_button.setGeometry(btmbtn_x, btmbtn_y, btn_big_side, btn_small_side)
        self.left_button.setGeometry(lftbtn_x, lftbtn_y, btn_small_side, btn_big_side)
        self.right_button.setGeometry(rgtbtn_x, rgtbtn_y, btn_small_side, btn_big_side)

        self.current_game_area = QRect(board_x - space_for_buttons, board_y - space_for_buttons, board_side + 2 * space_for_buttons, board_side + 2 * space_for_buttons)

        super().resizeEvent(event)

    def minimumSizeHint(self):
        gb_min_size = self.game_board.minimumSizeHint()
        w = gb_min_size.width() + gb_min_size.width() // 4 + 40
        h = gb_min_size.height() + gb_min_size.height() // 4 + 40
        return QSize(w, h)