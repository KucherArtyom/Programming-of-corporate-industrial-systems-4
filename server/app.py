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