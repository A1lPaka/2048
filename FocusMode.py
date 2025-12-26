from __future__ import annotations
from typing import TYPE_CHECKING, Callable
if TYPE_CHECKING:
    from Game_2048 import MainWindow

from PySide6.QtCore import Qt, QTimer, QRect, QSize


class FocusMode:
    def __init__(self, window: MainWindow):
        self.window = window
        self.focus_mode_enabled: bool = False
        self._normal_rect: QRect | None = None
        self._normal_flags: Qt.WindowFlags | None = None
        self._minimum_size: QSize | None = None
        self._was_fullscreen: bool = False

    def enter_focus_mode(self):
        if self.focus_mode_enabled:
            return
        
        self.window.on_menu_command()
        self.focus_mode_enabled = True

        if not self.window.isFullScreen():
            self._normal_rect = self.window.geometry()
        else:
            self.window.showNormal()
            self._normal_rect = self.window.geometry()
            self._was_fullscreen = True

        self._normal_flags = self.window.windowFlags()
        self._minimum_size = self.window.minimumSize()

        new_flags = self._normal_flags | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        self.window.setWindowFlags(new_flags)

        self.window.controls.mouse_active = False

        self.window.central_wrapper.hide()
        self.window.hud.hide()
        self.window.optional_button.hide()
        self.window.board_holder.hide()

        self.window.game_board.setParent(self.window)
        self.window.game_board.show()

        min_board_size = self.window.game_board.minimumSizeHint()
        self.window.setMinimumSize(min_board_size)

        self.window.show()
        current_size = min(self.window._start_size) if self.window._start_size else min_board_size.width()
        self.window.resize(current_size, current_size)
        self.window.size_grip.setParent(self.window)
        self.window.size_grip.show()
        self.window.size_grip.raise_()
        self.window.size_grip.update()

    def exit_focus_mode(self, after_exit: Callable | None = None):
        if not self.focus_mode_enabled:
            return
        
        self.focus_mode_enabled = False

        self.window.game_board.setParent(self.window.board_holder)
        self.window.game_board.show()

        self.window.size_grip.hide()

        self.window.setWindowFlags(self._normal_flags)

        if self._normal_rect:
            self.window.setGeometry(self._normal_rect)

        self.window.show()

        if self._minimum_size:
            self.window.setMinimumSize(self._minimum_size)
            self._minimum_size = None

        self.window.central_wrapper.show()
        self.window.board_holder.show()
        self.window.hud.show()
        self.window.optional_button.show()

        self.window.controls.mouse_active = True

        QTimer.singleShot(0, lambda: self.window.resize(self.window.width() + 1, self.window.height() + 1))
        QTimer.singleShot(0, lambda: self.window.resize(self.window.width() - 1, self.window.height() - 1))

        if after_exit:
            QTimer.singleShot(0, after_exit)

        if self._was_fullscreen:
            self.window.showFullScreen()
            self._was_fullscreen = False