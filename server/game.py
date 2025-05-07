import random
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from config import GAME_CONFIG

class CodeMasterGame:
    def __init__(self):
        self.code = ""
        self.players = []
        self.attempts = {}
        self.start_time = None
        self.end_time = None
        self.winner = None
        self.current_player_idx = 0
        self.round_active = False

    def start_new_round(self):
        self.code = self._generate_code()
        self.attempts = {player: [] for player in self.players}
        self.start_time = datetime.now()
        self.end_time = None
        self.winner = None
        self.current_player_idx = 0
        self.round_active = True

    def _generate_code(self) -> str:
        symbols = GAME_CONFIG["ALLOWED_SYMBOLS"]
        return "".join(random.choice(symbols) for _ in range(GAME_CONFIG["CODE_LENGTH"]))

    def add_player(self, player_id: str) -> bool:
        if len(self.players) >= GAME_CONFIG["MAX_PLAYERS"]:
            return False
        if player_id not in self.players:
            self.players.append(player_id)
            self.attempts[player_id] = []
            return True
        return False

    def is_ready_to_start(self) -> bool:
        return len(self.players) >= GAME_CONFIG["MIN_PLAYERS"]

    def make_guess(self, player_id: str, guess: str) -> Tuple[int, int, bool]:
        if not self.round_active or player_id != self.players[self.current_player_idx]:
            raise ValueError("Не ваш ход или раунд не активен")

        if len(guess) != GAME_CONFIG["CODE_LENGTH"]:
            raise ValueError(f"Код должен быть длиной {GAME_CONFIG['CODE_LENGTH']} символов")

        black, white = self._calculate_markers(guess)
        self.attempts[player_id].append((guess, black, white))

        guessed = black == GAME_CONFIG["CODE_LENGTH"]
        if guessed:
            self.winner = player_id
            self.end_time = datetime.now()
            self.round_active = False

        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)

        return black, white, guessed

    def _calculate_markers(self, guess: str) -> Tuple[int, int]:
        black = sum(g == c for g, c in zip(guess, self.code))
        white = 0

        code_counter = {}
        guess_counter = {}

        for g, c in zip(guess, self.code):
            if g != c:
                code_counter[c] = code_counter.get(c, 0) + 1
                guess_counter[g] = guess_counter.get(g, 0) + 1

        for symbol in guess_counter:
            white += min(guess_counter[symbol], code_counter.get(symbol, 0))

        return black, white

    def get_game_state(self, player_id: str) -> Dict:
        return {
            "code_length": GAME_CONFIG["CODE_LENGTH"],
            "attempts": self.attempts.get(player_id, []),
            "max_attempts": GAME_CONFIG["MAX_ATTEMPTS"],
            "current_player": self.players[self.current_player_idx],
            "round_active": self.round_active,
            "winner": self.winner,
            "players": self.players,
            "start_time": self.start_time,
        }