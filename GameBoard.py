from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional, Dict, List, Tuple

from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QRect, QUrl
from PySide6.QtWidgets import QWidget, QGridLayout, QFrame
from PySide6.QtGui import QFont, QPainter, QColor
from PySide6.QtMultimedia import QSoundEffect

from sounds import SoundsEffects 

color_map = {
    2: "#eee4da",
    4: "#ede0c8",
    8: "#f2b179",
    16: "#f59563",
    32: "#f67c5f",
    64: "#f65e3b",
    128: "#edcf72",
    256: "#edcc61",
    512: "#edc850",
    1024: "#edc53f",
    2048: "#edc22e",
    -1: "#3c3a32"
}
font_color_map = {
    "dark": "#2f2f2f",
    "light": "#ffffff"
}

@dataclass
class StepState:
    final_board: List[List[int]]
    final_id_board: List[List[int]]
    move_events: List[Dict]
    merge_events: List[Dict]
    spawn_events: List[Dict]
    despawn_events: List[Dict]
    split_tile_events: List[Dict]
    reverse_events: List[Dict]
    on_complete: Optional[Callable] = None
    running_animations: int = 0
    token: int = 0

class GameBoard(QWidget):
    def __init__(self, parent=None, size=4, sfx: SoundsEffects | None = None):
        super().__init__(parent)
        self.board_size = size

        self.setObjectName("GameBoard") 
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.main_layout = QGridLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.cells: List[List[EmptyTile]] = [[None for _ in range(size)] for _ in range(size)]
        self.tile_by_id: Dict[int, Tile] = {}
        self.id_to_pos: Dict[int, Tuple[int, int]] = {}

        self.active_animations: List[QPropertyAnimation] = []
        self.animation_token: int = 0
        self.current_step: Optional[StepState] = None

        self.sfx = sfx

        self._make_board_table()
        self.setMinimumSize(250, 250)

    def _make_board_table(self):
        for row in range(self.board_size):
            for col in range(self.board_size):
                tile = EmptyTile(self)
                self.main_layout.addWidget(tile, row, col)
                self.cells[row][col] = tile

    def sizeHint(self):
        return QSize(480, 480)
    
    def minimumSizeHint(self):
        return QSize(250, 250)
    
    def resizeEvent(self, event): 
        super().resizeEvent(event)

        w = self.width()
        h = self.height()

        side = min(w, h)

        border = max(4, side // 50)

        self.main_layout.setContentsMargins(border, border, border, border)
        self.main_layout.setSpacing(border)
        self.main_layout.activate()

        self._update_tiles_geometry()

    def set_full_state(self, board: List[List[int]], id_board: List[List[int]]):
        self.clear_tiles()
        for r in range(self.board_size):
            for c in range(self.board_size):
                value = board[r][c]
                tile_id = id_board[r][c]
                if value != 0 and tile_id != 0:
                    self._add_tile(tile_id, value, r, c)

        self._update_tiles_geometry()

    def play_step(
            self, 
            delta: List[Dict], 
            new_board: List[List[int]], 
            new_id_board: List[List[int]], 
            animated: bool = True, 
            on_complete: Optional[Callable] = None,
            variant: str = "move"
            ):
        
        if not delta or not animated:
            self.set_full_state(new_board, new_id_board)
            if on_complete:
                on_complete()
            return
        
        move_events, merge_events, spawn_events, despawn_events, split_tile_events, reverse_events = self._split_events(delta)

        if variant == "move":
            if not move_events and not merge_events and not spawn_events:
                self.set_full_state(new_board, new_id_board)
                if on_complete:
                    on_complete()
                return
        elif variant == "undo":
            if not despawn_events and not reverse_events and not split_tile_events:
                self.set_full_state(new_board, new_id_board)
                if on_complete:
                    on_complete()
                return
        
        self.animation_token += 1
        token = self.animation_token

        step = StepState(
            final_board=new_board,
            final_id_board=new_id_board,
            move_events=move_events,
            merge_events=merge_events,
            spawn_events=spawn_events,
            despawn_events=despawn_events,
            split_tile_events=split_tile_events,
            reverse_events=reverse_events,
            on_complete=on_complete,
            running_animations=0,
            token=token
        )

        self.current_step = step
        if variant == "move":
            self._play_moves(step)
        elif variant == "undo":
            self._play_despawns(step) 

    def snap_current_step(self):
        if self.current_step is None:
            return

        step = self.current_step

        for anim in self.active_animations:
            anim.stop()
        self.active_animations.clear()

        self.animation_token += 1

        self.set_full_state(step.final_board, step.final_id_board)

        if step.on_complete:
            step.on_complete()

        self.current_step = None

    def is_animating(self) -> bool:
        return self.current_step is not None
    
    def clear_tiles(self):
        for anim in self.active_animations:
            anim.stop()
        self.active_animations.clear()

        for tile in list(self.tile_by_id.values()):
            tile.setParent(None)
            tile.deleteLater()

        self.tile_by_id.clear()
        self.id_to_pos.clear()
        self.current_step = None

    def _add_tile(self, tile_id, value: int, row: int, col: int):
        tile = Tile(self, value=value)
        cell_rect = self._get_cell_rect(row, col)
        tile.setGeometry(cell_rect)
        tile.show()

        self.tile_by_id[tile_id] = tile
        self.id_to_pos[tile_id] = (row, col)

    def _remove_tile(self, tile_id):
        tile = self.tile_by_id.pop(tile_id, None)
        self.id_to_pos.pop(tile_id, None)
        if tile is not None:
            tile.setParent(None)
            tile.deleteLater()

    def _update_tiles_geometry(self):
        for tile_id, tile in self.tile_by_id.items():
            pos = self.id_to_pos.get(tile_id, None)
            if pos is not None:
                r, c = pos
                cell_rect = self._get_cell_rect(r, c)
                tile.setGeometry(cell_rect)

    def _get_cell_rect(self, row: int, col: int):
        return self.main_layout.cellRect(row, col)
    
    def _split_events(self, delta: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        move_events: List[Dict] = []
        merge_events: List[Dict] = []
        spawn_events: List[Dict] = []
        reverse_events: List[Dict] = []
        despawn_events: List[Dict] = []
        split_tile_events: List[Dict] = []

        for event in delta:
            t = event.get("type", "")
            if t == "move":
                move_events.append(event)
            elif t == "merge":
                merge_events.append(event)
            elif t == "spawn":
                spawn_events.append(event)
            elif t == "despawn":
                despawn_events.append(event)
            elif t == "split":
                split_tile_events.append(event)
            elif t == "reverse":
                reverse_events.append(event)

        return move_events, merge_events, spawn_events, despawn_events, split_tile_events, reverse_events
    
    def _play_moves(self, step: StepState):
        if self.current_step is not step or step.token != self.animation_token:
            return
        
        if not step.move_events:
            self._play_effects(step)
            return
        
        self.sfx.play_swipe()
        
        for event in step.move_events:
            tile_id = event.get("id", None)
            if tile_id is None:
                continue

            tile = self.tile_by_id.get(tile_id, None)
            if tile is None:
                continue

            from_row, from_col = event["from"]
            to_row, to_col = event["to"]

            start_rect = self._get_cell_rect(from_row, from_col)
            end_rect = self._get_cell_rect(to_row, to_col)

            self.id_to_pos[tile_id] = (to_row, to_col)

            self._animate_geometry(
                tile=tile, 
                start_rect=start_rect.topLeft(), 
                end_rect=end_rect.topLeft(), 
                step=step, 
                variant=b"pos", 
                duration=140, 
                easing=QEasingCurve.OutQuart, 
                on_all_finished=lambda s=step: self._play_effects(s)
            )

        if step.running_animations == 0:
            self._play_effects(step)

    def _play_merges(self, step: StepState, on_all_finished: Optional[Callable] = None):
        if self.current_step is not step or step.token != self.animation_token:
            return

        if not step.merge_events:
            return

        for event in step.merge_events:
            from_ids = event.get("from_ids", (None, None))
            new_id = event.get("new_id", None)
            if None in from_ids or new_id is None:
                continue

            tile_winner = self.tile_by_id.get(new_id, None)
            if tile_winner is None:
                continue

            tile_id1, tile_id2 = from_ids
            loser_id = tile_id1 if tile_id1 != new_id else tile_id2

            if loser_id is not None:
                self._remove_tile(loser_id)

            row, col = event["at"]
            cell_rect = self._get_cell_rect(row, col)

            new_value = event.get("value", tile_winner.value * 2)
            tile_winner.switch_tile_value(new_value)

            self.id_to_pos[new_id] = (row, col)

            dw = round(cell_rect.width() * 0.03)
            dh = round(cell_rect.height() * 0.03)
            start_rect = cell_rect.adjusted(-dw, -dh, dw, dh)

            self._animate_geometry(
                tile=tile_winner, 
                start_rect=start_rect, 
                end_rect=cell_rect, 
                step=step, 
                variant=b"geometry", 
                duration=80, 
                easing=QEasingCurve.InQuad, 
                on_all_finished=on_all_finished
            )

    def _play_spawns(self, step: StepState, on_all_finished: Optional[Callable] = None):
        if self.current_step is not step or step.token != self.animation_token:
            return

        if not step.spawn_events:
            return

        for event in step.spawn_events:
            tile_id = event.get("id", None)
            if tile_id is None:
                 continue
            
            row, col = event["at"]
            value = step.final_board[row][col]

            tile = self.tile_by_id.get(tile_id, None)
            if tile is None:
                self._add_tile(tile_id, value, row, col)
                tile = self.tile_by_id[tile_id]
            else:
                tile.switch_tile_value(value)

            self.id_to_pos[tile_id] = (row, col)

            cell_rect = self._get_cell_rect(row, col)

            dw = round(cell_rect.width() * 0.2)
            dh = round(cell_rect.height() * 0.2)
            start_rect = cell_rect.adjusted(dw, dh, -dw, -dh)

            tile.setGeometry(start_rect)

            self._animate_geometry(
                tile=tile, 
                start_rect=start_rect, 
                end_rect=cell_rect, 
                step=step, 
                variant=b"geometry",
                duration=80, 
                easing=QEasingCurve.OutQuad, 
                on_all_finished=on_all_finished
            )

    def _play_despawns(self, step: StepState):
        if self.current_step is not step or step.token != self.animation_token:
            return

        if not step.despawn_events:
            self._play_reverses(step)
            return
        
        self.sfx.play_anti_pop()
        
        for event in step.despawn_events:
            tile_id = event.get("id", None)
            if tile_id is None:
                continue

            row, col = event["at"]
            
            tile = self.tile_by_id.get(tile_id, None)
            if tile is None:
                continue

            self.id_to_pos.pop(tile_id, None)

            cell_rect = self._get_cell_rect(row, col)

            dw = round(cell_rect.width() * 0.2)
            dh = round(cell_rect.height() * 0.2)
            end_rect = cell_rect.adjusted(dw, dh, -dw, -dh)

            def on_finished(tid=tile_id, s=step):
                self._remove_tile(tid)
                if s.running_animations == 0:
                    self._play_reverses(s)

            self._animate_geometry(
                tile=tile, 
                start_rect=cell_rect, 
                end_rect=end_rect, 
                step=step, 
                variant=b"geometry", 
                duration=80, 
                easing=QEasingCurve.InQuad, 
                on_all_finished=on_finished
            )

    def _play_tile_splits(self, step: StepState):
        if self.current_step is not step or step.token != self.animation_token:
            return

        if not step.split_tile_events:
            return

        for event in step.split_tile_events:
            from_id = event.get("new_id", None)
            prev_ids = event.get("from_ids", (None, None))
            if from_id is None or None in prev_ids:
                continue

            tile_parent = self.tile_by_id.get(from_id, None)
            if tile_parent is None:
                continue

            prev_tile_id1, prev_tile_id2 = prev_ids
            child_id = prev_tile_id1 if prev_tile_id1 != from_id else prev_tile_id2

            row, col = event["at"]
            value = event.get("value", tile_parent.value)
            value = value // 2

            if child_id is not None:
                self._add_tile(child_id, value, row, col)
                tile_parent.switch_tile_value(value)

    def _play_reverses(self, step: StepState):
        if self.current_step is not step or step.token != self.animation_token:
            return
        
        self._play_tile_splits(step)

        if not step.reverse_events:
            self._finish_step(step)
            return
        
        self.sfx.play_short_swipe()
        
        for event in step.reverse_events:
            tile_id = event.get("id", None)
            if tile_id is None:
                continue

            tile = self.tile_by_id.get(tile_id, None)
            if tile is None:
                continue

            from_row, from_col = event["from"]
            to_row, to_col = event["to"]

            start_rect = self._get_cell_rect(from_row, from_col)
            end_rect = self._get_cell_rect(to_row, to_col)

            self.id_to_pos[tile_id] = (to_row, to_col)

            self._animate_geometry(
                tile=tile, 
                start_rect=start_rect.topLeft(), 
                end_rect=end_rect.topLeft(), 
                step=step, 
                variant=b"pos", 
                duration=120, 
                easing=QEasingCurve.OutQuart, 
                on_all_finished=lambda s=step: self._finish_step(s)
            )

        if step.running_animations == 0:
            self._finish_step(step)

    def _play_effects(self, step: StepState):
        if self.current_step is not step or step.token != self.animation_token:
            return
        
        if not step.spawn_events and not step.merge_events:
            self._finish_step(step)
            return
        
        def on_all_finished():
            self._finish_step(step)

        self.sfx.play_pop()

        self._play_merges(step, on_all_finished=on_all_finished)
        self._play_spawns(step, on_all_finished=on_all_finished)

    def _finish_step(self, step: StepState):
        if self.current_step is not step or step.token != self.animation_token:
            return

        self._update_tiles_geometry()

        if step.on_complete:
            step.on_complete()

        self.current_step = None

    def _animate_geometry(
            self, 
            tile: Tile, 
            start_rect: QRect, 
            end_rect: QRect, 
            step: StepState, 
            variant: bytes, 
            duration: int, 
            easing: QEasingCurve.Type, 
            on_all_finished: Optional[Callable] = None
            ):
        
        if self.current_step is not step or step.token != self.animation_token:
            return
        
        anim = QPropertyAnimation(tile, variant)
        anim.setDuration(duration)
        anim.setStartValue(start_rect)
        anim.setEndValue(end_rect)
        anim.setEasingCurve(easing)

        self.active_animations.append(anim)
        step.running_animations += 1
        current_token = self.animation_token

        def handle_finished():
            if self.animation_token != current_token:
                return

            if self.current_step is not step:
                return
            
            if anim in self.active_animations:
                self.active_animations.remove(anim)

            if step.running_animations > 0:
                step.running_animations -= 1

            if step.running_animations == 0 and on_all_finished is not None:
                on_all_finished()

        anim.finished.connect(handle_finished)
        anim.start()

class EmptyTile(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("GameSquare")

    def sizeHint(self):
        return QSize(100, 100)

class Tile(QWidget):
    def __init__(self, parent = None, value: int = 2):
        super().__init__(parent)
        self.value = value
        self.short_value = self._short_value(value)
        self.main_font = QFont("Montserrat")

        self.background_color = color_map.get(value, "#3c3a32")
        self.font_color = font_color_map["dark"] if value <= 4 else font_color_map["light"]

    def _short_value(self, value: int) -> str:
        if value < 10000:
            return str(value)
        units = ["", "K", "M", "B", "T", "Q", "Qi"]
        count = 0

        while value >= 1000 and count < len(units) - 1:
            value /= 1000.0
            count += 1

        short_value = f"{value:.1f}"
        if len(short_value) > 4:
            short_value = f"{int(value)}"

        return f"{short_value}{units[count]}"
    
    def switch_tile_value(self, new_value: int):
        self.value = new_value
        self.short_value = self._short_value(new_value)
        self.background_color = color_map.get(new_value, "#3c3a32")
        self.font_color = font_color_map["dark"] if new_value <= 4 else font_color_map["light"]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect()
        side = min(rect.width(), rect.height())
        font_size = max(3, round(side / 3.2))

        painter.setBrush(QColor(self.background_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 12, 12)

        font = QFont(self.main_font)
        font.setPixelSize(font_size)
        painter.setFont(font)

        painter.setPen(QColor(self.font_color))
        painter.drawText(rect, Qt.AlignCenter, self.short_value)

        return super().paintEvent(event)
        