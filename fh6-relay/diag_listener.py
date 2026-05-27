"""Standalone diagnostic listener — no GUI, no token store.

Binds on 0.0.0.0:PORT so packets can arrive from another machine on the LAN.
Logs all 89 FH6 telemetry fields to stdout every 5 seconds while racing, and
immediately logs any change to discrete-value fields.

Usage:
    python diag_listener.py [--port 20440]

In Forza Horizon 6 Data Out settings:
    IP:   <this machine's LAN IP>
    Port: 20440 (or whatever --port you pass)
"""

import argparse
import asyncio
import logging
import sys
import time

from packet_parser import PACKET_SIZE, parse_all_fields

HOST = "0.0.0.0"

_TELEM_GROUPS: list[tuple[str, tuple[str, ...]]] = [
    ("sled/motion", (
        "IsRaceOn", "TimestampMS",
        "AccelX", "AccelY", "AccelZ",
        "VelocityX", "VelocityY", "VelocityZ",
        "AngularVelX", "AngularVelY", "AngularVelZ",
        "Yaw", "Pitch", "Roll",
    )),
    ("sled/suspension", (
        "SuspNormFL", "SuspNormFR", "SuspNormRL", "SuspNormRR",
        "SuspTravelMetersFL", "SuspTravelMetersFR", "SuspTravelMetersRL", "SuspTravelMetersRR",
    )),
    ("sled/tires", (
        "TireSlipRatioFL", "TireSlipRatioFR", "TireSlipRatioRL", "TireSlipRatioRR",
        "TireSlipAngleFL", "TireSlipAngleFR", "TireSlipAngleRL", "TireSlipAngleRR",
        "TireCombinedSlipFL", "TireCombinedSlipFR", "TireCombinedSlipRL", "TireCombinedSlipRR",
        "WheelRotSpeedFL", "WheelRotSpeedFR", "WheelRotSpeedRL", "WheelRotSpeedRR",
        "WheelOnRumbleFL", "WheelOnRumbleFR", "WheelOnRumbleRL", "WheelOnRumbleRR",
        "PuddleDepthFL", "PuddleDepthFR", "PuddleDepthRL", "PuddleDepthRR",
        "SurfaceRumbleFL", "SurfaceRumbleFR", "SurfaceRumbleRL", "SurfaceRumbleRR",
    )),
    ("sled/engine", (
        "EngineMaxRpm", "EngineIdleRpm", "CurrentEngineRpm",
        "DrivetrainType", "NumCylinders",
        "CarOrdinal", "CarClass", "CarPI",
    )),
    ("dash/position", (
        "PositionX", "PositionY", "PositionZ",
    )),
    ("dash/performance", (
        "Speed", "Power", "Torque", "Boost", "Fuel", "DistanceTraveled",
    )),
    ("dash/tires", (
        "TireTempFL", "TireTempFR", "TireTempRL", "TireTempRR",
    )),
    ("dash/timing", (
        "BestLap", "LastLap", "CurrentLap", "CurrentRaceTime",
        "LapNumber", "RacePosition",
    )),
    ("dash/driver", (
        "Accel", "Brake", "Clutch", "HandBrake", "Gear", "Steer",
        "NormDrivingLine", "NormAIBrakeDiff",
    )),
    ("dash/unknown", (
        "Unk_284", "Unk_288", "Unk_292", "Unk_323",
    )),
]

_WATCH_FIELDS = (
    "BestLap", "LastLap", "LapNumber", "RacePosition",
    "CarOrdinal", "CarClass", "CarPI", "DrivetrainType", "NumCylinders",
    "Gear",
)


def _setup_log() -> logging.Logger:
    logger = logging.getLogger("fh6diag")
    logger.setLevel(logging.DEBUG)
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s"))
    logger.addHandler(h)
    return logger


log = _setup_log()


class _DiagProtocol(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self._packets = 0
        self._bad = 0
        self._last_dump = 0.0
        self._prev: dict = {}
        self._race_was_on = False

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        size = len(data)
        self._packets += 1

        if self._packets == 1:
            log.info("First packet from %s:%d — %d bytes (expected %d)", addr[0], addr[1], size, PACKET_SIZE)

        if size != PACKET_SIZE:
            self._bad += 1
            if self._bad <= 5 or self._bad % 500 == 0:
                log.warning("Unexpected size %d (expected %d) — packet #%d", size, PACKET_SIZE, self._packets)
            return

        fields = parse_all_fields(data)
        race_on = fields.get("IsRaceOn") == 1

        if race_on != self._race_was_on:
            log.info("IsRaceOn: %d → %d", int(self._race_was_on), int(race_on))
            self._race_was_on = race_on
            if not race_on:
                self._prev.clear()

        if not race_on:
            return

        # Immediate log on discrete-field changes.
        for key in _WATCH_FIELDS:
            val = fields[key]
            if val != self._prev.get(key):
                prev_str = f"{self._prev[key]:.4f}" if isinstance(self._prev.get(key), float) else str(self._prev.get(key, "?"))
                val_str = f"{val:.4f}" if isinstance(val, float) else str(val)
                log.info("FIELD %-20s %s → %s", key + ":", prev_str, val_str)
                self._prev[key] = val

        # Full dump every 5 seconds.
        now = time.monotonic()
        if now - self._last_dump >= 5.0:
            self._last_dump = now
            for group, keys in _TELEM_GROUPS:
                parts = [
                    f"{k}={fields[k]:.3f}" if isinstance(fields[k], float) else f"{k}={fields[k]}"
                    for k in keys
                ]
                log.info("TELEMETRY[%-16s]  %s", group, "  ".join(parts))

    def error_received(self, exc: Exception) -> None:
        log.error("UDP error: %s", exc)

    def connection_lost(self, exc: Exception | None) -> None:
        log.info("UDP connection closed")


async def _run(port: int) -> None:
    loop = asyncio.get_running_loop()
    log.info("Listening on %s:%d  (expecting %d-byte FH6 packets)", HOST, port, PACKET_SIZE)
    log.info("In FH6 Data Out settings → IP: <this machine's LAN IP>  Port: %d", port)
    transport, _ = await loop.create_datagram_endpoint(
        _DiagProtocol,
        local_addr=(HOST, port),
    )
    try:
        await asyncio.Event().wait()
    finally:
        transport.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="FH6 diagnostic UDP listener")
    parser.add_argument("--port", type=int, default=20440)
    args = parser.parse_args()
    try:
        asyncio.run(_run(args.port))
    except KeyboardInterrupt:
        log.info("Stopped.")


if __name__ == "__main__":
    main()
