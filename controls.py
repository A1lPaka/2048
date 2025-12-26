from PySide6.QtCore import QObject, Signal, QPoint, QEvent, Qt
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QWidget

UP = 'u' # U / ↑ / num8 / slide up 
DOWN = 'd' # D / ↓ / num2 / slide down
LEFT = 'l' # L / ← / num4 / slide left
RIGHT = 'r' # R / → / num6 / slide right

class Controls(QObject):
    move = Signal(str) # 'u', 'd', 'l', 'r'
    undo = Signal() # ctrl + z
    restart = Signal() # ctrl + n
    menu = Signal() # Escape
    fullscreen = Signal() # F11 / alt + Enter

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.parentt = parent
        self.swipe_threshold = 100
        self.all_shortcuts: list[QShortcut] = []
        self.mouse_active = True

        self.all_shortcuts_enabled = True
        self._press_pos: QPoint | None = None

        self.parentt.installEventFilter(self)
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        for seq in ("Up", "W", "Num8"):
            shortcut = QShortcut(QKeySequence(seq), self.parentt, activated=lambda: self._emit_move(UP))
            self.all_shortcuts.append(shortcut)
        for seq in ("Down", "S", "Num2"):
            shortcut = QShortcut(QKeySequence(seq), self.parentt, activated=lambda: self._emit_move(DOWN))
            self.all_shortcuts.append(shortcut)
        for seq in ("Left", "A", "Num4"):
            shortcut = QShortcut(QKeySequence(seq), self.parentt, activated=lambda: self._emit_move(LEFT))
            self.all_shortcuts.append(shortcut)
        for seq in ("Right", "D", "Num6"):
            shortcut = QShortcut(QKeySequence(seq), self.parentt, activated=lambda: self._emit_move(RIGHT))
            self.all_shortcuts.append(shortcut)

        for seq in ("Ctrl+N", "Ctrl+R"):
            shortcut = QShortcut(QKeySequence(seq), self.parentt, activated=lambda: self._emit_restart())
            self.all_shortcuts.append(shortcut)

        shortcut = QShortcut(QKeySequence("Ctrl+Z"), self.parentt, activated=lambda: self._emit_undo())
        self.all_shortcuts.append(shortcut)

    def _emit_move(self, direction: str):
        self.move.emit(direction)

    def _emit_undo(self):
        self.undo.emit()

    def _emit_restart(self):
        self.restart.emit()

    def _emit_menu(self):
        self.menu.emit()

    def update_swipe_threshold(self, threshold: int):
        self.swipe_threshold = threshold

    def eventFilter(self, watched, event):
        et = event.type()

        if et == QEvent.MouseButtonPress:
            if self.all_shortcuts_enabled:
                self._press_pos = event.position().toPoint()
                return False
        
        if et == QEvent.MouseButtonRelease and self._press_pos is not None:
            if self.all_shortcuts_enabled and self.mouse_active:
                release_pos = event.position().toPoint()
                delta = release_pos - self._press_pos
                self._press_pos = None

                dx = delta.x()
                dy = delta.y()

                if abs(dx) < self.swipe_threshold and abs(dy) < self.swipe_threshold:
                    return False
                
                if abs(dx) > abs(dy):
                    self.move.emit(RIGHT if dx > 0 else LEFT)
                else:
                    self.move.emit(DOWN if dy > 0 else UP)
                return True
        
        if et == QEvent.KeyRelease:
            if event.key() == Qt.Key_Escape:
                if event.isAutoRepeat():
                    return False
                self.menu.emit()
                return True
            
            alt_mod = bool(Qt.AltModifier & event.modifiers())
            ctrl_mod = bool(Qt.ControlModifier & event.modifiers())
            switch_mod = bool(Qt.GroupSwitchModifier & event.modifiers())

            if event.key() == Qt.Key_Space and not alt_mod and not ctrl_mod and not switch_mod:
                if event.isAutoRepeat():
                    return False
                if self.all_shortcuts_enabled:
                    self.menu.emit()
                    return True
                return True
            
            if self.mouse_active:

                if event.key() == Qt.Key_F11 and not alt_mod and not ctrl_mod and not switch_mod:
                    if event.isAutoRepeat():
                        return False
                    self.fullscreen.emit()
                    return True
                
                if event.key() in (Qt.Key_Enter, Qt.Key_Return) and alt_mod and not switch_mod:
                    if event.isAutoRepeat():
                        return False
                    self.fullscreen.emit()
                    return True
                
                if event.key() in (Qt.Key_Enter, Qt.Key_Return) and alt_mod and ctrl_mod:
                    if event.isAutoRepeat():
                        return False
                    self.fullscreen.emit()
                    return True
        
        return False
    
    def enable_all_shortcuts(self):
        self.all_shortcuts_enabled = True
        for sc in self.all_shortcuts:
            sc.setEnabled(True)

    def disable_all_shortcuts(self):
        self.all_shortcuts_enabled = False
        for sc in self.all_shortcuts:
            sc.setEnabled(False)