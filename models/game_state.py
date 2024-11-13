# src/models/game_state.py


class GameState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.hand_state = []
        self.active_pokemon = []
        self.bench_pokemon = {
            0: None,  # Left bench slot
            1: None,  # Middle bench slot
            2: None,  # Right bench slot
        }
        self.number_of_cards = None
        self.is_first_turn = True
        self.first_turn_done = False
        self.go_first = False
        self.played_trainer_cards = 0
        self.failed_cards = []
