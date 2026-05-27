import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from packet_parser import FH6Packet

log = logging.getLogger("fh6relay")

# FH6 time attack never populates BestLap/LastLap/LapNumber — they stay 0.
# Lap completion is detected when CurrentLap resets to a small value after
# running for a meaningful duration.
_MIN_LAP_SECONDS = 15.0   # ignore resets shorter than this (avoids startup noise)
_RESET_THRESHOLD = 10.0   # current_lap must drop by this much to count as a reset


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
        self._prev_current_lap: Optional[float] = None
        self._lap_count: int = 0

    def on_packet(self, packet: FH6Packet) -> Optional[LapRecord]:
        if packet.is_race_on == 0:
            self._prev_current_lap = None
            self._lap_count = 0
            return None

        if self._prev_current_lap is None:
            self._prev_current_lap = packet.current_lap
            log.debug(
                "SessionMgr: initialized  current_lap=%.4f  best_lap=%.4f  lap_number=%d",
                packet.current_lap, packet.best_lap, packet.lap_number,
            )
            return None

        # Lap completion: CurrentLap drops by more than _RESET_THRESHOLD after
        # running long enough to be a real lap.
        if (
            self._prev_current_lap > _MIN_LAP_SECONDS
            and packet.current_lap < self._prev_current_lap - _RESET_THRESHOLD
        ):
            self._lap_count += 1
            lap_time = self._prev_current_lap
            log.debug(
                "SessionMgr: lap detected  current_lap %.4f → %.4f  lap_time=%.4f",
                self._prev_current_lap, packet.current_lap, lap_time,
            )
            lap = LapRecord(
                lap_number=self._lap_count,
                lap_time_ms=round(lap_time * 1000),
                car_class_int=packet.car_class,
                car_ordinal=packet.car_ordinal,
                raw_telemetry=_packet_to_dict(packet),
                captured_at=datetime.now(timezone.utc).isoformat(),
            )
            with self._lock:
                self.laps.append(lap)
            self._prev_current_lap = packet.current_lap
            return lap

        self._prev_current_lap = packet.current_lap
        return None

    def reset(self) -> None:
        with self._lock:
            self.laps.clear()
        self._prev_current_lap = None
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
