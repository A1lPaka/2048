import sys
from PySide6.QtCore import Qt, QTimer, QSettings, QRect, QPoint, QSize
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QSizeGrip
from PySide6.QtGui import QIcon, QFont, QFontDatabase

from BoardHolder import BoardHolder
from Overlays import MenuOverlay
from HUD import HUD
from ControlsPanel import OptionalButton, ControlButton
from FocusMode import FocusMode
from controls import Controls
from engine import GameEngine
from utils import load_stylesheet, res_path
from sounds import SoundsEffects
from save_load import save_game, load_game
import resources_rc

class MainWindow(QMainWindow):
    def __init__(self, settings: QSettings | None = None):
        super().__init__()
        self.setWindowTitle("2048")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.settings = settings
        self.central_wrapper = QWidget(self)
        self.central_wrapper.setAttribute(Qt.WA_StyledBackground, True)
        self.central_wrapper.setObjectName("CentralWidget")
        self.setCentralWidget(self.central_wrapper)

        self.size_grip = QSizeGrip(self)
        self.size_grip.hide()

        self._drag_active = False
        self._drag_offset: QPoint | None = None

        self.menu_opened = False
        self.game_won_shown = False
        self.game_over_shown = False
        self.game_area_rect = QRect()
        self._start_size = None

        self.sfx = SoundsEffects()
        self.sfx.prestart()    

        self.board_size = self.settings.value("board_size", 4, type=int) if self.settings else 4
        self.prev_game = self.settings.value(f"prev_game_{self.board_size}x{self.board_size}", None) if self.settings else None
        self.volume = self.settings.value("volume", 50, type=int) if self.settings else 50
        self.best_score = self.settings.value(f"best_score_{self.board_size}x{self.board_size}", 0, type=int) if self.settings else 0
        self.sfx.set_volume(self.volume / 100.0)

        self.engine = GameEngine(self.board_size)

        self.focus_mode = FocusMode(self)

        self.controls = None
        self._add_controls()

        self.board_holder = None
        self.game_board = None
        self._add_board_holder()

        self.hud = None
        self._add_hud()        
        
        self.optional_button = None
        self._add_optional_button()

        self.menu_overlay = None
        self._add_menu_overlay()

        self.game_won_overlay = None
        self._add_game_won_overlay()

        self.game_over_overlay = None
        self._add_game_over_overlay()

        self.setStyleSheet(load_stylesheet(":/assets/style_2048.qss"))

        QTimer.singleShot(0, lambda: self.load_game(self.prev_game))

        self.setMinimumSize(340, 480)
        self._window_resize()
        
    def _add_controls(self):
        self.controls = Controls(self)
        self.controls.move.connect(self.on_move_command)
        self.controls.restart.connect(self.on_restart_command)
        self.controls.menu.connect(self.on_menu_command)
        self.controls.undo.connect(self.on_undo_command)
        self.controls.fullscreen.connect(self.on_fullscreen_command)        

    def _add_board_holder(self):
        self.board_holder = BoardHolder(self, size=self.board_size, sfx=self.sfx)
        self.game_board = self.board_holder.game_board
        self._arrow_button_command(self.board_holder.up_button, "u")
        self._arrow_button_command(self.board_holder.down_button, "d")
        self._arrow_button_command(self.board_holder.left_button, "l")
        self._arrow_button_command(self.board_holder.right_button, "r")
        self.board_holder.show()

    def _arrow_button_command(self, button: ControlButton, direction: str):
        button.clicked.connect(lambda: self.on_move_command(direction))

    def _update_board_holder_geometry(self):
        w = self.width()
        h = round(self.height() * 0.7)
        y = round(self.height() * 0.15)
        self.board_holder.setGeometry(0, y, w, h)

    def _clear_board_holder(self):
        self.board_holder.setParent(None)
        self.board_holder.deleteLater()
        self.board_holder = None

    def _add_hud(self):
        self.hud = HUD(self, settings=self.settings)
        self.hud.update_score(self.engine.state.score, best_score=self.best_score)

    def _add_optional_button(self):
        self.optional_button = OptionalButton(self, sfx=self.sfx)
        self.optional_button.undo_button.clicked.connect(self.on_undo_command)
        self.optional_button.restart_button.clicked.connect(self.on_restart_command)
        self.optional_button.menu_button.clicked.connect(self.on_menu_command)

    def _add_menu_overlay(self):
        self.menu_overlay = MenuOverlay(main_window=self, variant="Menu", board_size=self.board_size, volume=self.volume, sfx=self.sfx)
        self.menu_overlay.menu_content.continue_button.clicked.connect(self.on_menu_command)
        self.menu_overlay.menu_content.new_game_button.clicked.connect(lambda: (self.on_restart_command(), self.on_menu_command()))
        self.menu_overlay.menu_content.focus_mode_button.clicked.connect(self.focus_mode.enter_focus_mode)
        self.menu_overlay.menu_content.change_size_button.min_button.clicked.connect(lambda: self.change_board_size(-1))
        self.menu_overlay.menu_content.change_size_button.max_button.clicked.connect(lambda: self.change_board_size(1))
        self.menu_overlay.menu_content.change_volume_button.min_button.clicked.connect(lambda: self.change_volume(-1))
        self.menu_overlay.menu_content.change_volume_button.max_button.clicked.connect(lambda: self.change_volume(1))
        self.menu_overlay.menu_content.exit_button.clicked.connect(self.close)
        self.menu_overlay.side_key1.connect(self.change_board_size)
        self.menu_overlay.side_key2.connect(self.change_volume)

    def _add_game_won_overlay(self):
        self.game_won_overlay = MenuOverlay(main_window=self, variant="GameWon", sfx=self.sfx)
        self.game_won_overlay.game_won_content.buttons[0].clicked.connect(self.on_menu_command)
        self.game_won_overlay.game_won_content.buttons[1].clicked.connect(lambda: (self.on_restart_command(), self.on_menu_command()))

    def _add_game_over_overlay(self):
        self.game_over_overlay = MenuOverlay(main_window=self, variant="GameOver", sfx=self.sfx)
        self.game_over_overlay.game_over_content.buttons[0].clicked.connect(lambda: (self.on_restart_command(), self.on_menu_command()))
        self.game_over_overlay.game_over_content.buttons[1].clicked.connect(self.close)

    def on_move_command(self, direction: str):
        if self.game_board.is_animating():
            self.game_board.snap_current_step()

        new_state, moved, delta = self.engine.move(direction)

        if moved:
            def on_animation_complete():
                self._game_area_rect_in_window()

                if self.engine.state.game_over and not self.game_over_shown:
                    self.game_over_shown = True
                    self.game_over_overlay.show_menu([self.game_area_rect, self.hud.geometry(), self.optional_button.geometry()])
                    self.controls.disable_all_shortcuts()

                if self.engine.state.game_won and not self.game_won_shown:
                    self.game_won_shown = True
                    self.game_won_overlay.show_menu([self.game_area_rect, self.hud.geometry(), self.optional_button.geometry()])
                    self.controls.disable_all_shortcuts()

            animated = True
            self.game_board.play_step(
                delta=delta,
                new_board=new_state.board,
                new_id_board=new_state.id_board,
                animated=animated,
                on_complete=on_animation_complete,
                variant="move"
            )

        score = self.engine.state.score
        if score > self.best_score:
            self.best_score = score
            self.settings.setValue(f"best_score_{self.board_size}x{self.board_size}", self.best_score)
        self.hud.update_score(self.engine.state.score, best_score=self.best_score)

    def on_restart_command(self):   
        self.game_won_shown = False
        self.game_over_shown = False     
        self.engine.new_game(self.engine.size if self.engine.size else self.board_size)
        self._sync_full_redraw()

        self.hud.update_score(self.engine.state.score, best_score=self.best_score)

    def on_menu_command(self):
        if self.focus_mode.focus_mode_enabled:
            def after_exit():
                self._game_area_rect_in_window()
                self.menu_overlay.show_menu([self.game_area_rect, self.hud.geometry(), self.optional_button.geometry()])
                self.controls.disable_all_shortcuts()
                self.menu_opened = True
            self.focus_mode.exit_focus_mode(after_exit=after_exit)
            return
        if self.game_over_overlay.isVisible() or self.game_won_overlay.isVisible():
            self.game_over_overlay.hide_menu()
            self.game_won_overlay.hide_menu()
            self.controls.enable_all_shortcuts()
            return
        elif self.menu_opened:
            self.menu_overlay.hide_menu()
            self.controls.enable_all_shortcuts()
            self.menu_opened = False
        else:
            self._game_area_rect_in_window()
            self.menu_overlay.show_menu([self.game_area_rect, self.hud.geometry(), self.optional_button.geometry()])
            self.controls.disable_all_shortcuts()
            self.menu_opened = True     

    def on_fullscreen_command(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def on_undo_command(self):
        if self.game_over_shown or self.game_won_shown:
            self.game_won_shown = False
            self.game_over_shown = False 
        if self.game_board.is_animating():
            self.game_board.snap_current_step()

        prev_state, undone, delta = self.engine.undo()

        if undone:
            animated = True
            self.game_board.play_step(
                delta=delta,
                new_board=prev_state.board,
                new_id_board=prev_state.id_board,
                animated=animated,
                variant="undo"
            )

        self.hud.update_score(prev_state.score, best_score=self.best_score)

    def change_board_size(self, delta: int = 0):
        prev_game = save_game(self.engine.state, self.engine.history, self.engine.delta_history)
        self.settings.setValue(f"prev_game_{self.board_size}x{self.board_size}", prev_game)
        new_size = self.menu_overlay.menu_content.change_size_button.change_value(delta)
        new_game = self.settings.value(f"prev_game_{new_size}x{new_size}", None)
        if new_size != self.board_size:
            self.board_size = new_size
            self.settings.setValue("board_size", self.board_size)
            self.engine.new_game(self.board_size)
            self._clear_board_holder()
            self._add_board_holder()
            self._update_board_holder_geometry()
            self.best_score = self.settings.value(f"best_score_{self.board_size}x{self.board_size}", 0, type=int)
            self.hud.update_score(self.engine.state.score, best_score=self.best_score)
            QTimer.singleShot(0, lambda: (self.load_game(new_game), self.menu_overlay.restart_menu()))

    def change_volume(self, delta: int = 0):
        new_volume = self.menu_overlay.menu_content.change_volume_button.change_value(delta)
        if new_volume != self.volume:
            self.volume = new_volume
            self.settings.setValue("volume", self.volume)
            self.sfx.set_volume(self.volume / 100.0)
            self.sfx.play_pop()

    def _sync_full_redraw(self):
        state = self.engine.state
        self.game_board.clear_tiles()
        self.game_board.set_full_state(state.board, state.id_board)

    def _game_area_rect_in_window(self):
        local = self.board_holder.current_game_area

        if not local or local.isNull():
            return QRect()

        top_left = self.board_holder.mapTo(self, local.topLeft())
        self.game_area_rect = QRect(top_left, local.size())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        h = self.height()
        if not self.focus_mode.focus_mode_enabled:
            holder_h = round(h * 0.7)
            frame_side = min(w, holder_h)
            board_side = round((frame_side - 4) / 1.25)
        
            if self.hud:
                hud_h = round(board_side / 8)
                hud_y = round(0.075 * h - hud_h / 2)
                hud_x = round(w - board_side - hud_h / 2)

                self.hud.setGeometry(hud_x, hud_y, board_side, hud_h)
                self.hud.update_font_size(hud_h)

            if self.board_holder:
                holder_y = round(h * 0.15)

                self.board_holder.setGeometry(0, holder_y, w, holder_h)

            if self.optional_button:
                btn_h = round(board_side / 6)
                btn_w = round(btn_h * 3.5)
                btn_x = round((w - btn_w) / 2)
                btn_y = round(0.925 * h - btn_h / 2)

                self.optional_button.setGeometry(btn_x, btn_y, btn_w, btn_h)

            if self.controls:
                self.controls.update_swipe_threshold(round(board_side * 0.4))
        else:
            w = self.width()
            h = self.height()
            side = min(w, h)
            
            if abs(w - h) > 2:
                self.resize(side, side)
                return
            
            board_x = (w - side) // 2
            board_y = (h - side) // 2
            self.game_board.setGeometry(board_x, board_y, side, side)

            if self.size_grip:
                grip_size = side // 20
                self.size_grip.setGeometry(w - grip_size * 1.1, h - grip_size * 1.1, grip_size, grip_size)

        if self.menu_opened:
            self.menu_overlay.setGeometry(self.rect())
            self.menu_overlay.veil.setGeometry(self.menu_overlay.rect())
            self._game_area_rect_in_window()
            self.menu_overlay.update_targets([self.game_area_rect, self.hud.geometry(), self.optional_button.geometry()])
            self.menu_overlay.update()

        if self.engine.state.game_over or self.engine.state.game_won:
            overlay = self.game_over_overlay if self.engine.state.game_over else self.game_won_overlay
            overlay.setGeometry(self.rect())
            overlay.veil.setGeometry(overlay.rect())
            self._game_area_rect_in_window()
            overlay.update_targets([self.game_area_rect, self.hud.geometry(), self.optional_button.geometry()])
            overlay.update()

    def mousePressEvent(self, event):
        if self.focus_mode.focus_mode_enabled and event.button() in (Qt.LeftButton, Qt.RightButton):
            self._drag_active = True
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.focus_mode.focus_mode_enabled and self._drag_active and self._drag_offset:
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            self.move(new_pos)
            
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if self.focus_mode.focus_mode_enabled and event.button() in (Qt.LeftButton, Qt.RightButton):
            self._drag_active = False
            self._drag_offset = None
            
        super().mouseReleaseEvent(event)

    def load_game(self, prev_game: dict | None):
        if prev_game:
            try:
                state, history, delta_history = load_game(prev_game)
                self.engine.state = state
                self.engine.history = history
                self.engine.delta_history = delta_history
                self._sync_full_redraw()
                self.hud.update_score(self.engine.state.score, best_score=self.best_score)
            except (KeyError, ValueError, TypeError, IndexError) as e:
                print(f"Failed to load saved game: {e}. Starting new game.")
                self.engine.new_game(self.board_size)
                self._sync_full_redraw()
                self.hud.update_score(self.engine.state.score, best_score=self.best_score)
        else:
            self._sync_full_redraw()

    def closeEvent(self, event):
        prev_game = save_game(self.engine.state, self.engine.history, self.engine.delta_history)
        self.settings.setValue(f"prev_game_{self.board_size}x{self.board_size}", prev_game)
        self.settings.setValue("board_size", self.board_size)
        self.settings.setValue("volume", self.volume)
        return super().closeEvent(event)
    
    def _window_resize(self):
        screen = QApplication.primaryScreen().availableGeometry()

        target_w = max(round(screen.width() * 0.25), 340)
        target_h = max(round(screen.height() * 0.65), 480)

        self._start_size = (target_w, target_h)

        self.resize(target_w, target_h)
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(res_path("assets/app_icon.ico")))
    
    font_id = QFontDatabase.addApplicationFont(res_path("assets/JetBrainsMono-Bold.ttf"))
    font_2048 = QFontDatabase.applicationFontFamilies(font_id)[0]
    bold_font_id = QFontDatabase.addApplicationFont(res_path("assets/JetBrainsMono-ExtraBold.ttf"))
    font_2048_bold = QFontDatabase.applicationFontFamilies(bold_font_id)[0]
    tile_font_id = QFontDatabase.addApplicationFont(res_path("assets/Montserrat-Bold.ttf"))
    tile_font = QFontDatabase.applicationFontFamilies(tile_font_id)[0]
    
    app.setFont(QFont(font_2048, 10))
    settings = QSettings("Cute_Alpaca_Club", "2048_Game")
    window = MainWindow(settings=settings)
    window.show()
    sys.exit(app.exec())