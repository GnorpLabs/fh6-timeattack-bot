import asyncio
import threading

import token_store
import udp_listener
from gui import App
from session_manager import SessionManager


async def _async_main(app: App, port: int) -> None:
    def on_packet(packet):
        lap = app.session.on_packet(packet)
        if lap is not None:
            app.notify_new_lap(lap)

    transport = await udp_listener.start_udp_listener("127.0.0.1", port, on_packet)
    try:
        await asyncio.Event().wait()
    finally:
        transport.close()


def main() -> None:
    loop = asyncio.new_event_loop()
    session = SessionManager()
    app = App(session, loop)
    port = token_store.get_udp_port()

    def run_loop() -> None:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_async_main(app, port))

    t = threading.Thread(target=run_loop, daemon=True)
    t.start()

    app.run()  # blocks on main thread until quit


if __name__ == "__main__":
    main()
