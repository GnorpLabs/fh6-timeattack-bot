from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from packet_parser import FH6Packet


@dataclass
class LapRecord:
    lap_number: int
    lap_time_ms: int
    car_class_int: int
    car_ordinal: int
    raw_telemetry: dict
    captured_at: str


class SessionManager:
    def __init__(self) -> None:
        self.laps: list[LapRecord] = []
        self._prev_lap_number: Optional[int] = None

    def on_packet(self, packet: FH6Packet) -> Optional[LapRecord]:
        if packet.is_race_on == 0:
            self._prev_lap_number = None
            return None

        if self._prev_lap_number is None:
            self._prev_lap_number = packet.lap_number
            return None

        if packet.lap_number > self._prev_lap_number:
            lap = LapRecord(
                lap_number=packet.lap_number,
                lap_time_ms=round(packet.last_lap * 1000),
                car_class_int=packet.car_class,
                car_ordinal=packet.car_ordinal,
                raw_telemetry=_packet_to_dict(packet),
                captured_at=datetime.now(timezone.utc).isoformat(),
            )
            self.laps.append(lap)
            self._prev_lap_number = packet.lap_number
            return lap

        self._prev_lap_number = packet.lap_number
        return None

    def reset(self) -> None:
        self.laps.clear()
        self._prev_lap_number = None


def _packet_to_dict(packet: FH6Packet) -> dict:
    return {
        "is_race_on": packet.is_race_on,
        "car_ordinal": packet.car_ordinal,
        "car_class": packet.car_class,
        "best_lap": packet.best_lap,
        "last_lap": packet.last_lap,
        "current_lap": packet.current_lap,
        "current_race_time": packet.current_race_time,
        "lap_number": packet.lap_number,
        "race_position": packet.race_position,
    }
