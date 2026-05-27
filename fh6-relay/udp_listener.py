import asyncio
from typing import Callable

from packet_parser import FH6Packet, parse_packet


class _FH6Protocol(asyncio.DatagramProtocol):
    def __init__(self, on_packet: Callable[[FH6Packet], None]) -> None:
        self._on_packet = on_packet

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        packet = parse_packet(data)
        if packet is not None:
            self._on_packet(packet)

    def error_received(self, exc: Exception) -> None:
        pass

    def connection_lost(self, exc: Exception | None) -> None:
        pass


async def start_udp_listener(
    host: str, port: int, on_packet: Callable[[FH6Packet], None]
) -> asyncio.BaseTransport:
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: _FH6Protocol(on_packet),
        local_addr=(host, port),
    )
    return transport
