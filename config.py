import string
from pathlib import Path

# Конфигурация игры
GAME_CONFIG = {
    "CODE_LENGTH": 4,
    "MAX_ATTEMPTS": 10,
    "MAX_PLAYERS": 4,
    "MIN_PLAYERS": 2,
    "ALLOWED_SYMBOLS": string.ascii_uppercase + string.digits,
    "HOST": "localhost",
    "PORT": 8888,
    "RESULTS_DIR": Path("results"),
    "ROUND_TIME_LIMIT": 300,
}
