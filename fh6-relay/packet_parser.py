import struct
from dataclasses import dataclass

# Byte offsets match the FH6 "car dash" sled telemetry format.
# Reference: docs/superpowers/specs/2026-05-26-data-out-design.md
PACKET_SIZE = 324


@dataclass
class FH6Packet:
    is_race_on: int
    car_ordinal: int
    car_class: int
    best_lap: float
    last_lap: float
    current_lap: float
    current_race_time: float
    lap_number: int
    race_position: int


def parse_packet(data: bytes) -> FH6Packet | None:
    if len(data) != PACKET_SIZE:
        return None
    return FH6Packet(
        is_race_on=struct.unpack_from("<i", data, 0)[0],
        car_ordinal=struct.unpack_from("<i", data, 212)[0],
        car_class=struct.unpack_from("<i", data, 216)[0],
        best_lap=struct.unpack_from("<f", data, 296)[0],
        last_lap=struct.unpack_from("<f", data, 300)[0],
        current_lap=struct.unpack_from("<f", data, 304)[0],
        current_race_time=struct.unpack_from("<f", data, 308)[0],
        lap_number=struct.unpack_from("<H", data, 312)[0],
        race_position=struct.unpack_from("<B", data, 314)[0],
    )
