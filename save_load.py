from engine import GameState, DeltaEvent

def save_game(state: GameState, history: list[GameState], delta_history: list[list[DeltaEvent]]) -> dict:
    def unpack_state(state: GameState) -> dict:    
        return {
            "board": state.board,
            "id_board": state.id_board,
            "score": state.score,
            "game_over": state.game_over,
            "game_won": state.game_won,
            "next_id": state.next_id,
        }
    cur_state_dict = unpack_state(state)
    history_state_dict: list[dict] = []
    for state in history:
        history_state_dict.append(unpack_state(state))

    return {
        "state": cur_state_dict,
        "history": history_state_dict,
        "delta_history": delta_history,
    }

def load_game(data: dict) -> tuple[GameState, list[GameState], list[list[DeltaEvent]]]:
    def pack_state(state_dict: dict) -> GameState:
        return GameState(
            board=state_dict["board"],
            id_board=state_dict["id_board"],
            score=state_dict["score"],
            game_over=state_dict["game_over"],
            game_won=state_dict["game_won"],
            next_id=state_dict["next_id"],
        )
    state = pack_state(data["state"])
    history: list[GameState] = []
    for state_dict in data["history"]:
        history.append(pack_state(state_dict))
    delta_history: list[list[DeltaEvent]] = data["delta_history"]

    return state, history, delta_history