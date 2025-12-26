from PySide6.QtCore import Qt, QRect, QEvent, Signal, QTimer
from PySide6.QtGui import QPainter, QPixmap, QShortcut, QKeySequence, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton

from sounds import SoundsEffects

class MenuOverlay(QWidget):
    side_key1 = Signal(int)
    side_key2 = Signal(int)
    def __init__(self, main_window: QWidget, variant: str = "Menu", board_size: int = 4, volume: int = 50, sfx: SoundsEffects | None = None):
        super().__init__(main_window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)

        self.main_window = main_window
        self.blur_targets = []
        self.variant = variant
        self.blur_cache: dict[QRect, QPixmap] = {}
        self.cur_widget = None

        self.sfx = sfx

        self.veil = QWidget(self)
        self.veil.setAttribute(Qt.WA_StyledBackground, True)
        self.veil.setObjectName("veil")
        self.veil.setFocusPolicy(Qt.NoFocus)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        if variant == "Menu":

            self.menu_content = MenuContent(self, board_size=board_size, volume=volume)
            self.widget_for_focus = [self.menu_content.continue_button, self.menu_content.new_game_button,
                                     self.menu_content.focus_mode_button, self.menu_content.change_size_button, 
                                     self.menu_content.change_volume_button, self.menu_content.exit_button]
            self.idx_focus = None

        elif variant == "GameOver":

            self.game_over_content = EndGameContent(self)
            self.game_over_content.set_name_text("Game\u2009Over")
            self.game_over_content.set_button(count_buttons=2, text=["Restart", "Exit"])
            self.widget_for_focus = [self.game_over_content.buttons[0], self.game_over_content.buttons[1]]
            self.idx_focus = None

        elif variant == "GameWon":

            self.game_won_content = EndGameContent(self)
            self.game_won_content.set_name_text("You\u2009Win!")
            self.game_won_content.set_button(count_buttons=2, text=["Continue", "Restart"])
            self.widget_for_focus = [self.game_won_content.buttons[0], self.game_won_content.buttons[1]]
            self.idx_focus = None

        for widget in self.widget_for_focus:
            widget.installEventFilter(self)
        
        self.shortcuts = [
            QShortcut(QKeySequence(seq), self, activated=lambda: self._focus_widget(1)) for seq in ("Down", "S", "Num2", "Tab")] + [
            QShortcut(QKeySequence(seq), self, activated=lambda: self._focus_widget(-1)) for seq in ("Up", "W", "Num8", "Backtab")] + [
            QShortcut(QKeySequence(seq), self, activated=lambda: self._emit_key(-1)) for seq in ("Left", "A", "Num4")] + [
            QShortcut(QKeySequence(seq), self, activated=lambda: self._emit_key(1)) for seq in ("Right", "D", "Num6")
        ]

        for skt in self.shortcuts:
            skt.setEnabled(False)

        self.hide()

    # ====== Показ меню ======

    def show_menu(self, blur_targets: list[QRect]):
        self.setGeometry(self.main_window.rect())
        self.veil.setGeometry(self.rect())

        self.blur_targets = blur_targets

        self._prepare_blur()

        self.raise_()
        self.show()
        for skt in self.shortcuts:
            skt.setEnabled(True)

        for widget in self.widget_for_focus:
            if widget.underMouse():
                self.idx_focus = self.widget_for_focus.index(widget)
                widget.setFocus()
                break
        else:
            self.setFocus()
            self.idx_focus = None

    def hide_menu(self):
        self.blur_cache.clear()
        self.blur_targets = []
        for skt in self.shortcuts:
            skt.setEnabled(False)
        self.hide()

    def restart_menu(self):
        cur_idx = self.idx_focus
        for skt in self.shortcuts:
            skt.setEnabled(False)
        self.hide()
        self.show_menu(self.blur_targets)
        self.idx_focus = cur_idx
        if self.idx_focus is not None:
            widget = self.widget_for_focus[self.idx_focus]
            widget.setFocus()

    # ====== Отрисовка Меню ======

    def _prepare_blur(self):
        self.blur_cache.clear()
        
        for target in self.blur_targets:
            if not isinstance(target, QRect) or target.isNull():
                continue

            expended = target.adjusted(-10, -10, 10, 10)

            screen = self.main_window.grab(expended)

            if screen.isNull():
                continue

            blurred = self._blur_screen(screen)

            self.blur_cache[target] = blurred

    def _blur_screen(self, screen: QPixmap) -> QPixmap:
        orig_size = screen.size()
        small_w = max(1, int(orig_size.width() * 0.333))
        small_h = max(1, int(orig_size.height() * 0.333))

        blurred = screen

        for _ in range(5):
            small = blurred.scaled(int(small_w), int(small_h), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            blurred = small.scaled(orig_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        return blurred
    
    def update_targets(self, blur_targets: list[QRect]):
        new_blur_cache: dict[QRect, QPixmap] = {}
        for target, (old_target, pixmap) in zip(blur_targets, self.blur_cache.items()):
            new_blur_cache[target] = pixmap

        self.blur_targets = blur_targets
        self.blur_cache = new_blur_cache

    def paintEvent(self, event):
        if not self.blur_cache:
            return super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        for target, blurred in self.blur_cache.items():
            expended = target.adjusted(-10, -10, 10, 10)

            painter.drawPixmap(expended, blurred)

        painter.end()

    def resizeEvent(self, event):
        w = self.width()
        w = w - (w % 2)
        h = self.height()
        h = h - (h % 2)
        center_x = w // 2
        center_y = h // 2

        gap = 30

        menu_h = round(max(h * 0.8, h - 2 * gap))
        menu_w = round(menu_h * 0.8)

        if menu_w > w - 2 * gap:
            menu_w = w - 2 * gap
            menu_h = round(menu_w / 0.8)

        menu_x = center_x - menu_w // 2
        menu_y = center_y - menu_h // 2

        if self.variant == "Menu":
            self.menu_content.setGeometry(menu_x, menu_y, menu_w, menu_h)
        elif self.variant == "GameOver":
            self.game_over_content.setGeometry(menu_x, menu_y, menu_w, menu_h)
        elif self.variant == "GameWon":
            self.game_won_content.setGeometry(menu_x, menu_y, menu_w, menu_h)

        super().resizeEvent(event)

    # ====== Работа с кнопками ======

    def _focus_widget(self, delta: int = 1):
        if self.idx_focus is None:
            self.idx_focus = 0 
            widget = self.widget_for_focus[self.idx_focus]
            widget.setFocus()
        else:
            self.idx_focus = (self.idx_focus + delta) % len(self.widget_for_focus)
            widget = self.widget_for_focus[self.idx_focus]
            widget.setFocus()
            
    def _emit_key(self, delta: int):
        if self.variant == "Menu":
            if self.menu_content.change_size_button.hasFocus():
                self.idx_focus = 3
                self.side_key1.emit(delta)
            elif self.menu_content.change_volume_button.hasFocus():
                self.idx_focus = 4
                self.side_key2.emit(delta)

    def eventFilter(self, watched: QWidget | QPushButton, event: QEvent):
        et = event.type()
        if et == QEvent.Enter:
            if watched in self.widget_for_focus:
                self.idx_focus = self.widget_for_focus.index(watched)
                watched.setFocus()
            return True
        if et == QEvent.Leave:
            if watched in self.widget_for_focus:
                if self.idx_focus == self.widget_for_focus.index(watched):
                    self.idx_focus = None
                    watched.clearFocus()
            return True
        
        if et == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
                if event.isAutoRepeat():
                    return True
                if isinstance(watched, QPushButton) and watched in self.widget_for_focus:
                    watched.setDown(True)
                    self.sfx.play_click_in()
                    self.cur_widget = watched
                    return True
        if et == QEvent.KeyRelease:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
                if event.isAutoRepeat():
                    return True
                if isinstance(watched, QPushButton) and watched in self.widget_for_focus:
                    watched.setDown(False)
                    if self.cur_widget == watched:
                        self.sfx.play_click_out()
                        watched.click()
                        self.cur_widget = None
                    return True
                
        if et == QEvent.FocusIn:
            if watched in self.widget_for_focus:
                self.sfx.play_short_pop()
            return False
        if et == QEvent.FocusOut:
            self.cur_widget = None
            return False
        
        if et == QEvent.MouseButtonPress:
            if isinstance(watched, QPushButton) and watched in self.widget_for_focus:
                watched.setDown(True)
                self.cur_widget = watched
                self.idx_focus = self.widget_for_focus.index(watched)
                self.sfx.play_click_in()
            return False
        if et == QEvent.MouseButtonRelease:
            if isinstance(watched, QPushButton) and watched in self.widget_for_focus:
                watched.setDown(False)
                if self.cur_widget == watched and watched.underMouse():
                    self.sfx.play_click_out()
                    watched.click()
                    self.cur_widget = None
            return False
        
        return super().eventFilter(watched, event)
            
class MenuContent(QWidget):
    def __init__(self, parent: QWidget = None, board_size: int = 4, volume: int = 50):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setObjectName("menuContent")

        self.main_label = QLabel(self)
        self.main_label.setText("2O48")
        self.main_label.setObjectName("mainLabel")
        self.main_label.setFocusPolicy(Qt.NoFocus)
        self.main_label.setAlignment(Qt.AlignCenter)

        self.continue_button = QPushButton(self)
        self.continue_button.setText("Continue")
        self.continue_button.setObjectName("menuButton")

        self.new_game_button = QPushButton(self)
        self.new_game_button.setText("New\u2009Game")
        self.new_game_button.setObjectName("menuButton")

        self.focus_mode_button = QPushButton(self)
        self.focus_mode_button.setText("Focus\u2009Mode")
        self.focus_mode_button.setObjectName("menuButton")

        self.change_size_button = MenuSpinButton(self, board_size, delta=1)
        self.change_size_button.set_name_text("Board\u2009Size:")
        self.change_size_button.set_range(3, 8)
        self.change_size_button.set_value_format("{value}x{value}")

        self.change_volume_button = MenuSpinButton(self, volume, delta=10)
        self.change_volume_button.set_name_text("Volume:")
        self.change_volume_button.set_range(0, 100)
        self.change_volume_button.set_value_format("{value}")

        self.exit_button = QPushButton(self)
        self.exit_button.setText("Exit")
        self.exit_button.setObjectName("menuButton")

        self.buttons: list[QPushButton | MenuSpinButton] = [
                        self.continue_button, 
                        self.new_game_button,
                        self.focus_mode_button,
                        self.change_size_button, 
                        self.change_volume_button,
                        self.exit_button
                        ]

    def resizeEvent(self, event):
        w = self.width()
        h = self.height()
        center_x = w // 2
        font = QFont()

        button_h = round(h * 0.1)
        button_hgap = round(h * 0.08)
        button_w = round(w - 2 * button_hgap)
        button_font_px = round(h * 0.04)
        name_label_y = round(h * 0.02)
        name_label_h = round(h * 0.22)
        button_x = center_x - button_w // 2

        button_block_y = round(h * 0.285)

        for i, button in enumerate(self.buttons):
            button_y = button_block_y + i * 0.115 * h
            button.setGeometry(button_x, button_y, button_w, button_h)
            
            if isinstance(button, QPushButton):
                font.setPixelSize(button_font_px)
                button.setFont(font)
            elif isinstance(button, MenuSpinButton):
                button.update_font_size(button_font_px)

        self.main_label.setGeometry(0, name_label_y, w, name_label_h)
        font = QFont("JetBrains Mono ExtraBold")
        font.setPixelSize(int(name_label_h*1.1))
        self.main_label.setFont(font)

        return super().resizeEvent(event)

class MenuSpinButton(QWidget):
    def __init__(self, parent: QWidget = None, start_value: int = 4, delta: int = 1):
        super().__init__(parent)
        self.start_value = start_value
        self.delta = delta
        self.min_size = 3
        self.max_size = 8
        self.value_format = ""
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setObjectName("MenuSpinButton")

        self.name_label = QLabel(self)
        self.name_label.setObjectName("MenuSpinButton_NameLabel")
        self.name_label.setAlignment(Qt.AlignCenter)

        self.min_button = QPushButton(self)
        self.min_button.setObjectName("MenuSpinButton_MinButton")
        self.min_button.setText("◀")
        self.min_button.setFocusPolicy(Qt.NoFocus)

        self.value_label = QLabel(self)
        self.value_label.setObjectName("MenuSpinButton_ValueLabel")
        self.value_label.setAlignment(Qt.AlignCenter)

        self.max_button = QPushButton(self)
        self.max_button.setObjectName("MenuSpinButton_MaxButton")
        self.max_button.setText("▶")
        self.max_button.setFocusPolicy(Qt.NoFocus)

    def update_font_size(self, board_size: int):
        font = QFont()
        font.setPixelSize(board_size)
        self.name_label.setFont(font)
        self.value_label.setFont(font)
        font.setPixelSize((board_size - 4) if board_size > 6 else board_size)
        self.min_button.setFont(font)
        self.max_button.setFont(font)

    def resizeEvent(self, event):
        w = self.width()
        h = self.height()
        center_y = h // 2

        button_h = round(h * 0.5)
        button_y = center_y - button_h // 2

        value_w = round(h * 1.5)

        min_button_x = round(w * 0.75 - 1.25 * h)
        value_label_x = round(w * 0.75 - 0.75 * h)
        max_button_x = round(w * 0.75 + 0.75 * h)

        self.min_button.setGeometry(min_button_x, button_y, button_h, button_h)
        self.value_label.setGeometry(value_label_x, button_y, value_w, button_h)
        self.max_button.setGeometry(max_button_x, button_y, button_h, button_h)

        name_label_w = round(h * 3)
        name_label_x = round(w * 0.25 - 1.25 * h)

        self.name_label.setGeometry(name_label_x, button_y, name_label_w, button_h)

        return super().resizeEvent(event)

    def set_value(self, value: int):
        self.start_value = value
        if self.value_format:
            self.value_label.setText(self.value_format.format(value=value))
        else:
            self.value_label.setText(f"{value}")

    def set_value_format(self, form: str = "{value}"):
        self.value_format = form
        self.set_value(self.start_value)

    def set_range(self, min_size: int, max_size: int):
        self.min_size = min_size
        self.max_size = max_size

    def set_delta(self, delta: int):
        self.delta = delta

    def set_name_text(self, text: str):
        self.name_label.setText(text)

    def change_value(self, delta: int) -> int:
        new_value = self.start_value + self.delta * delta
        if self.min_size <= new_value <= self.max_size:
            self.set_value(new_value)
            return new_value
        return self.start_value

class EndGameContent(QWidget):
    def __init__(self, parent: QWidget = None, label_text: str = "Game Over"):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setObjectName("EndGameContent")

        self.main_label = QLabel(self)
        self.main_label.setText(label_text)
        self.main_label.setObjectName("EndGameContent_mainLabel")
        self.main_label.setFocusPolicy(Qt.NoFocus)
        self.main_label.setAlignment(Qt.AlignCenter)

        self.buttons: list[QPushButton] = []

    def set_name_text(self, text: str):
        self.main_label.setText(text)

    def set_button(self, count_buttons: int, text: list[str]):
        self.buttons = [None for _ in range(count_buttons)]
        for i in range(count_buttons):
            button = QPushButton(self)
            button.setText(text[i])
            button.setObjectName("EndGameContent_Button")
            self.buttons[i] = button

    def resizeEvent(self, event):
        w = self.width()
        h = self.height()
        center_x = w // 2
        font = QFont()

        button_h = round(h * 0.1)
        button_hgap = round(h * 0.1)
        button_w = round(w - 2 * button_hgap)
        button_font_px = round(h * 0.04)
        name_label_h = round(h * 0.22)
        name_label_y = round(h * 0.19)
        button_x = center_x - button_w // 2

        n_buttons = len(self.buttons)
        button_block_y = round(h*0.71 - 0.06*h*n_buttons)

        for i, button in enumerate(self.buttons):
            button_y = button_block_y + i * 0.12 * h
            button.setGeometry(button_x, button_y, button_w, button_h)
            font.setPixelSize(button_font_px)
            button.setFont(font)

        self.main_label.setGeometry(0, name_label_y, w, name_label_h)
        font = QFont("JetBrains Mono ExtraBold")
        font.setPixelSize(int(name_label_h*0.7))
        self.main_label.setFont(font)

        return super().resizeEvent(event)