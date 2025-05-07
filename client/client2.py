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
