from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional

from dataclasses import dataclass, replace
import random

DeltaEvent = Dict[str, Any]

@dataclass
class GameState:
    board: List[List[int]]
    id_board: List[List[int]] # матрица с id тайлов для отслеживания анимаций
    score: int = 0
    game_over: bool = False
    game_won: bool = False
    next_id: int = 1 # счетчик для присвоения уникальных id новым тайлам

class GameEngine:
    def __init__(self, size: int, random_seed: int | None = None):
        self.size = size
        self.random_seed = random_seed
        self.rng = random.Random(random_seed)
        self.state: GameState = self.new_game(size)
        self.history: List[GameState] = []
        self.delta_history: List[List[DeltaEvent]] = []

    def new_game(self, size: int) -> GameState:
        board = [[0 for _ in range(size)] for _ in range(size)]
        id_board = [[0 for _ in range(size)] for _ in range(size)]

        self.size = size

        state = GameState(board=board, id_board=id_board, score=0, game_over=False, game_won=False, next_id=1)

        self.rng = random.Random(self.random_seed)

        state = self._spawn_tile(state)
        state = self._spawn_tile(state)
        self.history = []
        self.delta_history = []
        self.state = state

        return state
    
    def move(self, direction: str) -> Tuple[GameState, bool, List[DeltaEvent]]:
        new_board, new_id_board, score_gain, moved, delta = self._move(self.state.board, self.state.id_board, direction)
        if not moved:
            return self.state, False, []
        
        new_state = replace(
            self.state,
            board=new_board,
            id_board=new_id_board,
            score=self.state.score + score_gain,
        )

        if any(2048 in row for row in new_board):
            new_state.game_won = True

        new_state, spawn_event = self._spawn_tile(new_state, return_event=True)
        if spawn_event:
            delta.append(spawn_event)

        new_state.game_over = self._check_game_over(new_state.board)

        self.history.append(self.state)
        self.delta_history.append(delta)
        self.state = new_state

        if len(self.history) > 10:
            self.history.pop(0)
            self.delta_history.pop(0)

        return new_state, True, delta
    
    def undo(self):
        if not self.history:
            return self.state, False, []
        
        prev_state = self.history.pop()
        delta = self.delta_history.pop()
        inverted_delta: List[DeltaEvent] = []
        for event in delta:
            if event["type"] == "spawn":
                inverted_delta.append({
                    "type": "despawn",
                    "id": event["id"],
                    "at": event["at"],
                })
            elif event["type"] == "move":
                inverted_delta.append({
                    "type": "reverse",
                    "id": event["id"],
                    "from": event["to"],
                    "to": event["from"],
                })
            elif event["type"] == "merge":
                inverted_delta.append({
                    "type": "split",
                    "from_ids": event["from_ids"],
                    "new_id": event["new_id"],
                    "at": event["at"],
                    "value": event["value"],
                })
        self.state = prev_state
        return prev_state, True, inverted_delta
    
    def _spawn_tile(self, state: GameState, *, return_event: bool = False) -> Tuple[GameState, Optional[DeltaEvent]] | GameState:
        empties = []
        for r in range(self.size):
            for c in range(self.size):
                if state.board[r][c] == 0:
                    empties.append((r, c))
        if not empties:
            return (state, None) if return_event else state
        
        r, c = self.rng.choice(empties)
        value = 2 if self.rng.random() < 0.9 else 4
        new_id = state.next_id

        new_board = [row[:] for row in state.board]
        new_id_board = [row[:] for row in state.id_board]

        new_board[r][c] = value
        new_id_board[r][c] = new_id

        event = {"type": "spawn", "id": new_id, "at": (r, c)}
        new_state = replace(state, board=new_board, id_board=new_id_board, next_id=state.next_id + 1)

        return (new_state, event) if return_event else new_state
    
    def _move(self, vals_board: List[List[int]], ids_board: List[List[int]], direction: str) -> Tuple[List[List[int]], List[List[int]], int, bool, List[DeltaEvent]]:
        n = self.size
        delta: List[DeltaEvent] = []

        original_vals_board = [row[:] for row in vals_board]
        work_vals_board = [row[:] for row in vals_board]

        original_ids_board = [row[:] for row in ids_board]
        work_ids_board = [row[:] for row in ids_board]

        if direction in ("d", "u"):
            work_vals_board = [list(row) for row in zip(*work_vals_board)] # Транспонируем текущую доску. Теперь движение вверх/вниз - это движение влево/вправо по транспонированной доске.
            work_ids_board = [list(row) for row in zip(*work_ids_board)]

        new_vals_board = []
        new_ids_board = []
        total_score_gain = 0

        for row in range(n):
            vals = work_vals_board[row][:]
            ids = work_ids_board[row][:]
            if direction in ("r", "d"):
                vals = vals[::-1] # Разворачиваем строку при направлении вправо/вниз, чтобы всегда двигаться влево(выполнять одни и теже действия с доской).
                ids = ids[::-1]

            new_vals, new_ids, score_gain, row_delta = self._compress_line(vals, ids)
            total_score_gain += score_gain

            if direction in ("r", "d"):
                new_vals = new_vals[::-1]
                new_ids = new_ids[::-1]
                for event in row_delta:
                    if event["type"] == "move":
                        event["from_idx"] = n - 1 - event["from_idx"]
                        event["to_idx"] = n - 1 - event["to_idx"]
                    elif event["type"] == "merge":
                        event["at_idx"] = n - 1 - event["at_idx"]

            for event in row_delta:
                if event["type"] == "move":
                    cur_row, cur_from, cur_to = row, event["from_idx"], event["to_idx"] 
                    if direction in ("d", "u"):
                        delta.append({
                            "type": "move",
                            "id": event["id"],
                            "from": (cur_from, cur_row),
                            "to": (cur_to, cur_row),
                        })
                    else:
                        delta.append({
                            "type": "move",
                            "id": event["id"],
                            "from": (cur_row, cur_from),
                            "to": (cur_row, cur_to),
                        })
                elif event["type"] == "merge":
                    cur_row, cur_at = row, event["at_idx"]
                    if direction in ("d", "u"):
                        delta.append({
                            "type": "merge",
                            "from_ids": event["from_ids"],
                            "new_id": event["new_id"],
                            "at": (cur_at, cur_row),
                            "value": event["value"],
                        })
                    else:
                        delta.append({
                            "type": "merge",
                            "from_ids": event["from_ids"],
                            "new_id": event["new_id"],
                            "at": (cur_row, cur_at),
                            "value": event["value"],
                        })

            new_vals_board.append(new_vals)
            new_ids_board.append(new_ids)

        if direction in ("d","u"):
            new_vals_board = [list(row) for row in zip(*new_vals_board)]
            new_ids_board = [list(row) for row in zip(*new_ids_board)]


        return new_vals_board, new_ids_board, total_score_gain, (original_vals_board != new_vals_board), delta
    
    def _compress_line(self, vals_row: List[int], ids_row: List[int]) -> Tuple[List[int], List[int], int, List[DeltaEvent]]:
        n = len(vals_row)
        tiles = [(vals_row[i], ids_row[i], i) for i in range(n) if vals_row[i] != 0] # (value, id, index)

        new_vals = []
        new_ids = []
        event = []
        write_idx = 0
        score_gain = 0

        i = 0
        while i < len(tiles):
            val_tile, id_tile, idx_tile = tiles[i]

            if i + 1 < len(tiles) and tiles[i][0] == tiles[i + 1][0]:
                val_tile2, id_tile2, idx_tile2 = tiles[i + 1]
                new_val = val_tile * 2
                new_id = id_tile # сохраняем id первого тайла при слиянии

                if idx_tile != write_idx:
                    event.append({
                        "type": "move",
                        "id": id_tile,
                        "from_idx": idx_tile,
                        "to_idx": write_idx,
                    })
                if idx_tile2 != write_idx:
                    event.append({
                        "type": "move",
                        "id": id_tile2,
                        "from_idx": idx_tile2,
                        "to_idx": write_idx,
                    })

                event.append({
                    "type": "merge",
                    "from_ids": [id_tile, id_tile2],
                    "new_id": new_id,
                    "at_idx": write_idx,
                    "value" : new_val,
                })
                new_vals.append(new_val)
                new_ids.append(new_id)
                score_gain += new_val
                write_idx += 1
                i += 2
            else:
                if idx_tile != write_idx:
                    event.append({
                        "type": "move",
                        "id": id_tile,
                        "from_idx": idx_tile,
                        "to_idx": write_idx,
                    })
                new_vals.append(val_tile)
                new_ids.append(id_tile)
                write_idx += 1
                i += 1

        new_vals += [0] * (n - len(new_vals))
        new_ids += [0] * (n - len(new_ids))

        return new_vals, new_ids, score_gain, event

    def _check_game_over(self, board: List[List[int]]) -> bool:
        for i in range(self.size):
            for j in range(self.size):
                if board[i][j] == 0:
                    return False
                if j + 1 < self.size and board[i][j] == board[i][j + 1]:
                    return False
                if i + 1 < self.size and board[i][j] == board[i + 1][j]:
                    return False
        return True

