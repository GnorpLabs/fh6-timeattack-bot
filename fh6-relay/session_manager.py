import threading
from dataclasses import dataclass
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
        self._lock = threading.Lock()
        self.laps: list[LapRecord] = []
        self._prev_last_lap: Optional[float] = None
        self._lap_count: int = 0

    def on_packet(self, packet: FH6Packet) -> Optional[LapRecord]:
        if packet.is_race_on == 0:
            self._prev_last_lap = None
            self._lap_count = 0
            return None

        if self._prev_last_lap is None:
            self._prev_last_lap = packet.last_lap
            return None

        # FH6 time attack mode does not increment LapNumber — detect completion
        # by watching LastLap change to a new non-zero value instead.
        if packet.last_lap > 0 and packet.last_lap != self._prev_last_lap:
            self._lap_count += 1
            lap = LapRecord(
                lap_number=self._lap_count,
                lap_time_ms=round(packet.last_lap * 1000),
                car_class_int=packet.car_class,
                car_ordinal=packet.car_ordinal,
                raw_telemetry=_packet_to_dict(packet),
                captured_at=datetime.now(timezone.utc).isoformat(),
            )
            with self._lock:
                self.laps.append(lap)
            self._prev_last_lap = packet.last_lap
            return lap

        self._prev_last_lap = packet.last_lap
        return None

    def reset(self) -> None:
        with self._lock:
            self.laps.clear()
        self._prev_last_lap = None
        self._lap_count = 0

    def get_laps_snapshot(self) -> list[LapRecord]:
        with self._lock:
            return list(self.laps)


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
