from PySide6.QtCore import Qt, QPointF, QEvent
from PySide6.QtWidgets import QWidget, QAbstractButton, QPushButton
from PySide6.QtGui import QPainter, QColor, QPen, QPolygonF, QPainterPath, QFont

from sounds import SoundsEffects

class ControlButton(QAbstractButton):
    def __init__(self, direction: str = "up", parent: QWidget | None = None, sfx: SoundsEffects | None = None):
        super().__init__(parent)
        self.direction = direction
        self.setMouseTracking(True)
        self.is_hovered = False

        self.sfx = sfx

        self.setFocusPolicy(Qt.NoFocus)

    def enterEvent(self, event):        
        self.is_hovered = True
        self.update()
    
    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()

    def mouseReleaseEvent(self, e):
        return super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        path, triangle_height = self._create_triangle_path()

        if self.isDown():
            bg_color = QColor(170, 161, 148)
        elif self.is_hovered:
            bg_color = QColor(187, 177, 164)
        else:
            bg_color = QColor(205, 193, 180)

        border_color = QColor(187, 173, 160)

        painter.setBrush(bg_color)

        border_size = max(2, int(triangle_height / 7.5))

        pen = QPen(border_color, border_size)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)

        painter.drawPath(path)

    def hitButton(self, pos):
        path, _ = self._create_triangle_path()
        return path.contains(pos)
    
    def mouseMoveEvent(self, e):
        path, _ = self._create_triangle_path()
        hovered_now = path.contains(e.position())
        if hovered_now != self.is_hovered:
            self.is_hovered = hovered_now
            self.update()

        return super().mouseMoveEvent(e)
    
    def _create_triangle_path(self) -> QPainterPath:
        w = self.width()
        h = self.height()

        triangle_base = max(w, h) * 0.95
        triangle_height = (triangle_base / 4.0) * 0.85

        cx = w / 2.0
        cy = h / 2.0

        if self.direction == "up":
            base_y = cy + triangle_height / 2.0
            top_y = base_y - triangle_height   

            p1 = QPointF(cx, top_y)
            p2 = QPointF(cx - triangle_base / 2.0, base_y)
            p3 = QPointF(cx + triangle_base / 2.0, base_y)

        elif self.direction == "down":
            base_y = cy - triangle_height / 2.0
            top_y = base_y + triangle_height   

            p1 = QPointF(cx, top_y)
            p2 = QPointF(cx - triangle_base / 2.0, base_y)
            p3 = QPointF(cx + triangle_base / 2.0, base_y)

        elif self.direction == "left":
            base_x = cx + triangle_height / 2.0
            top_x = base_x - triangle_height   

            p1 = QPointF(top_x, cy)
            p2 = QPointF(base_x, cy - triangle_base / 2.0)
            p3 = QPointF(base_x, cy + triangle_base / 2.0)

        elif self.direction == "right":
            base_x = cx - triangle_height / 2.0
            top_x = base_x + triangle_height   

            p1 = QPointF(top_x, cy)
            p2 = QPointF(base_x, cy - triangle_base / 2.0)
            p3 = QPointF(base_x, cy + triangle_base / 2.0)

        poly = QPolygonF([p1, p2, p3])
        path = QPainterPath()
        path.addPolygon(poly)
        path.closeSubpath()
        return path, triangle_height
    
class OptionalButton(QWidget):
    def __init__(self, parent: QWidget | None = None, sfx: SoundsEffects | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.sfx = sfx

        self.undo_button = QPushButton("⮌", self)
        self.restart_button = QPushButton("⭯", self) 
        self.menu_button = QPushButton("☰", self) 

        for btn in (self.undo_button, self.restart_button, self.menu_button):
            btn.setObjectName("OptionalControlButton")
            btn.setFocusPolicy(Qt.NoFocus)

            if self.sfx:
                btn.pressed.connect(self.sfx.play_click_in)
                btn.released.connect(self.sfx.play_click_out)

            btn.installEventFilter(self)

        self.setMinimumSize(147, 42)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Enter:
            if self.sfx:
                self.sfx.play_short_pop()
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        w = self.width()
        font = QFont()

        btn_size = round(w / 3.5)
        btn_x2 = round(w * 0.357)
        btn_x3 = round(w * 0.714)
        font.setPixelSize(round(btn_size * 0.6))

        self.undo_button.setGeometry(0, 0, btn_size, btn_size)
        self.undo_button.setFont(font)
        self.restart_button.setGeometry(btn_x2, 0, btn_size, btn_size)
        self.restart_button.setFont(font)
        self.menu_button.setGeometry(btn_x3, 0, btn_size, btn_size)
        self.menu_button.setFont(font)