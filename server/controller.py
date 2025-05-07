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