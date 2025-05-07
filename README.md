# Programming-of-corporate-industrial-systems-4
## Кучер Артем Сергеевич ЭФМО-02-24
### Практика 4
### Сетевая многопользовательская игра "Код-Мастер"

### Код программы
#### app.py
```
import asyncio
from config import GAME_CONFIG
from controller import GameController

async def main():
    controller = GameController()
    server = await asyncio.start_server(
        controller.handle_connection,
        GAME_CONFIG["HOST"],
        GAME_CONFIG["PORT"]
    )

    addr = server.sockets[0].getsockname()
    print(f"Сервер запущен на {addr}")

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
```

#### controller.py
```
import asyncio
from typing import Dict, Any, Optional
from config import GAME_CONFIG
from game import CodeMasterGame
from serializer import GameResultSerializer
from datetime import datetime


class GameController:
    def __init__(self):
        self.game = CodeMasterGame()
        self.serializer = GameResultSerializer()
        self.player_sockets = {}

    async def handle_connection(self, reader, writer):
        addr = writer.get_extra_info("peername")
        print(f"Новое подключение от {addr}")

        try:
            player_id = await self._register_player(reader, writer)
            if not player_id:
                return

            while True:
                if not self.game.round_active and self.game.is_ready_to_start():
                    self.game.start_new_round()
                    await self._broadcast(f"Новый раунд начался! Код длиной {GAME_CONFIG['CODE_LENGTH']} символов.")

                if self.game.round_active and self.game.players[self.game.current_player_idx] == player_id:
                    await self._handle_player_turn(reader, writer, player_id)
                else:
                    await asyncio.sleep(1)

        except (ConnectionResetError, asyncio.CancelledError):
            print(f"Игрок {player_id} отключился")
        finally:
            self._cleanup_player(player_id, writer)

    async def _register_player(self, reader, writer) -> Optional[str]:
        writer.write(b"Enter your player ID: ")
        await writer.drain()

        data = await reader.read(100)
        player_id = data.decode().strip()

        if not player_id:
            return None

        if not self.game.add_player(player_id):
            writer.write(b"Maximum number of players reached.\n")
            await writer.drain()
            return None

        self.player_sockets[player_id] = writer
        await self._send_message(writer, f"You are registered as {player_id}. Waiting for other players...")
        return player_id

    async def _handle_player_turn(self, reader, writer, player_id):
        game_state = self.game.get_game_state(player_id)

        attempts_left = GAME_CONFIG["MAX_ATTEMPTS"] - len(game_state["attempts"])
        await self._send_message(writer, f"\nВаш ход! Попыток осталось: {attempts_left}")
        await self._send_message(writer, "Введите ваш вариант кода: ")

        data = await reader.read(100)
        guess = data.decode().strip().upper()

        try:
            black, white, guessed = self.game.make_guess(player_id, guess)
            response = f"Результат: {black} черных, {white} белых маркеров."
            await self._send_message(writer, response)

            if guessed:
                await self._broadcast(f"Игрок {player_id} угадал код и выиграл раунд!")
                self._save_round_results()
        except ValueError as e:
            await self._send_message(writer, f"Ошибка: {str(e)}")

    async def _send_message(self, writer, message: str):
        writer.write(f"{message}\n".encode())
        await writer.drain()

    async def _broadcast(self, message: str):
        for player_id, writer in self.player_sockets.items():
            await self._send_message(writer, message)

    def _save_round_results(self):
        game_data = {
            "code": self.game.code,
            "attempts": self.game.attempts,
            "start_time": self.game.start_time,
            "end_time": self.game.end_time or datetime.now(),
            "winner": self.game.winner,
        }
        filename = self.serializer.serialize(game_data)
        print(f"Результаты раунда сохранены в {filename}")

    def _cleanup_player(self, player_id: str, writer):
        if player_id in self.player_sockets:
            del self.player_sockets[player_id]

        if player_id in self.game.players:
            self.game.players.remove(player_id)

        writer.close()
```

#### game.py
```
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
```

#### serializer.py
```
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from config import GAME_CONFIG


class GameResultSerializer:
    def __init__(self):
        self.results_dir = GAME_CONFIG["RESULTS_DIR"]
        self.results_dir.mkdir(exist_ok=True)

    def serialize(self, game_data: Dict[str, Any]) -> str:
        root = ET.Element("CodeMasterRound")

        # Основная информация
        ET.SubElement(root, "StartTime").text = game_data["start_time"].isoformat()
        ET.SubElement(root, "EndTime").text = game_data["end_time"].isoformat()
        ET.SubElement(root, "SecretCode").text = game_data["code"]
        ET.SubElement(root, "Winner").text = game_data["winner"] or "None"

        players_elem = ET.SubElement(root, "Players")
        for player, attempts in game_data["attempts"].items():
            player_elem = ET.SubElement(players_elem, "Player", name=player)
            player_elem.set("attempts", str(len(attempts)))

            for i, (guess, black, white) in enumerate(attempts, 1):
                attempt_elem = ET.SubElement(player_elem, "Attempt", number=str(i))
                ET.SubElement(attempt_elem, "Guess").text = guess
                ET.SubElement(attempt_elem, "BlackMarkers").text = str(black)
                ET.SubElement(attempt_elem, "WhiteMarkers").text = str(white)

        timestamp = game_data["start_time"].strftime("%Y%m%d_%H%M%S")
        filename = self.results_dir / f"round_{timestamp}.xml"

        tree = ET.ElementTree(root)
        tree.write(filename, encoding="utf-8", xml_declaration=True)

        return str(filename)
```

#### config.py
```
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

```

#### client.py
```
import asyncio
import tkinter as tk
from tkinter import scrolledtext, messagebox
from config import GAME_CONFIG


class CodeMasterClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Code Master Game")

        self.reader = None
        self.writer = None
        self.player_id = ""
        self.game_active = False

        self.setup_ui()

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self.connect())
        self.update_loop()

    def setup_ui(self):
        self.id_frame = tk.Frame(self.root)
        self.id_frame.pack(pady=10)

        tk.Label(self.id_frame, text="Player ID:").pack(side=tk.LEFT)
        self.id_entry = tk.Entry(self.id_frame, width=20)
        self.id_entry.pack(side=tk.LEFT, padx=5)
        self.id_entry.bind("<Return>", lambda e: self.send_player_id())

        self.connect_button = tk.Button(self.id_frame, text="Connect", command=self.send_player_id)
        self.connect_button.pack(side=tk.LEFT)

        self.chat_area = scrolledtext.ScrolledText(self.root, width=60, height=20, state='disabled')
        self.chat_area.pack(pady=10)

        self.guess_frame = tk.Frame(self.root)
        self.guess_frame.pack(pady=5)

        tk.Label(self.guess_frame, text="Your guess:").pack(side=tk.LEFT)
        self.guess_entry = tk.Entry(self.guess_frame, width=20, state='disabled')
        self.guess_entry.pack(side=tk.LEFT, padx=5)
        self.guess_entry.bind("<Return>", lambda e: self.send_guess())

        self.guess_button = tk.Button(self.guess_frame, text="Send", command=self.send_guess, state='disabled')
        self.guess_button.pack(side=tk.LEFT)

        self.status_var = tk.StringVar()
        self.status_var.set("Not connected")
        self.status_label = tk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_label.pack(fill=tk.X, pady=5)

    def update_loop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.loop.run_forever()
        self.root.after(100, self.update_loop)

    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(
                GAME_CONFIG["HOST"],
                GAME_CONFIG["PORT"]
            )

            data = await self.reader.read(1024)
            self.display_message(data.decode())

            self.root.after(0, self.enable_id_input)

            while True:
                data = await self.reader.read(1024)
                if not data:
                    break

                message = data.decode()
                self.display_message(message)

                if "Введите ваш вариант кода:" in message:
                    self.root.after(0, self.enable_guess_input)
                elif "раунд начался!" in message:
                    self.root.after(0, self.game_started)
                elif "угадал код" in message:
                    self.root.after(0, self.game_ended)

        except (ConnectionRefusedError, ConnectionResetError) as e:
            self.root.after(0, lambda: messagebox.showerror("Connection Error", f"Ошибка подключения: {e}"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Произошла ошибка: {e}"))
        finally:
            self.root.after(0, self.connection_closed)

    def send_player_id(self):
        """Отправляет ID игрока на сервер"""
        self.player_id = self.id_entry.get().strip()
        if not self.player_id:
            messagebox.showwarning("Input Error", "Player ID cannot be empty")
            return

        if self.writer:
            self.writer.write(self.player_id.encode())
            self.loop.create_task(self.writer.drain())

            self.id_entry.config(state='disabled')
            self.connect_button.config(state='disabled')
            self.status_var.set(f"Connected as {self.player_id}")

    def send_guess(self):
        guess = self.guess_entry.get().strip().upper()
        if not guess:
            messagebox.showwarning("Input Error", "Guess cannot be empty")
            return

        if self.writer:
            self.writer.write(guess.encode())
            self.loop.create_task(self.writer.drain())

            self.guess_entry.delete(0, tk.END)
            self.guess_entry.config(state='disabled')
            self.guess_button.config(state='disabled')

    def display_message(self, message):
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, message)
        self.chat_area.see(tk.END)
        self.chat_area.config(state='disabled')

    def enable_id_input(self):
        self.id_entry.config(state='normal')
        self.connect_button.config(state='normal')

    def enable_guess_input(self):
        self.guess_entry.config(state='normal')
        self.guess_button.config(state='normal')
        self.guess_entry.focus()

    def game_started(self):
        self.game_active = True
        self.status_var.set(f"Game started - waiting for your turn")

    def game_ended(self):
        self.game_active = False
        self.guess_entry.config(state='disabled')
        self.guess_button.config(state='disabled')

    def connection_closed(self):
        self.status_var.set("Connection closed")
        self.id_entry.config(state='disabled')
        self.connect_button.config(state='disabled')
        self.guess_entry.config(state='disabled')
        self.guess_button.config(state='disabled')

        if self.writer:
            self.writer.close()
            self.loop.create_task(self.writer.wait_closed())

    def on_closing(self):
        self.loop.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    client = CodeMasterClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", client.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()

```
