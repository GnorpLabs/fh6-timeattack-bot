import asyncio
import threading
import time

import relay_logger
import token_store
import udp_listener
from gui import App
from packet_parser import PACKET_SIZE, parse_all_fields
from relay_logger import DebugStats
from session_manager import SessionManager

log = relay_logger.log

# Timing fields we watch for immediate change-logging (excludes high-freq fields
# like CurrentLap/CurrentRaceTime which change every packet).
_WATCH_FIELDS = ("BestLap", "LastLap", "LapNumber")

# Snapshot fields included in the periodic 5-second telemetry dump.
_DUMP_FIELDS = (
    "IsRaceOn", "CurrentEngineRpm", "Speed", "Gear", "Fuel",
    "TireTempFL", "TireTempFR", "TireTempRL", "TireTempRR",
    "BestLap", "LastLap", "CurrentLap", "CurrentRaceTime",
    "LapNumber", "RacePosition", "Accel", "Brake",
    "CarOrdinal", "CarClass", "CarPI",
    "Unk_284", "Unk_288", "Unk_292",
)


async def _async_main(app: App, port: int, stats: DebugStats) -> None:
    _telem: dict = {"last_dump": 0.0, "prev": {}}

    def on_raw(data: bytes) -> None:
        size = len(data)
        with stats._lock:
            stats.packets_total += 1
            stats.last_size = size
            first = stats.packets_total == 1
            if size != PACKET_SIZE:
                stats.bad_size_count += 1
                stats.last_bad_size = size
        if first:
            log.info("First UDP packet: %d bytes (expected %d)", size, PACKET_SIZE)
        if size != PACKET_SIZE and (stats.bad_size_count <= 5 or stats.bad_size_count % 1000 == 0):
            log.warning("Unexpected packet size %d (expected %d), dropping", size, PACKET_SIZE)
            return

        fields = parse_all_fields(data)
        if not fields or fields.get("IsRaceOn") != 1:
            return

        # Log immediately when BestLap, LastLap, or LapNumber changes.
        prev = _telem["prev"]
        for key in _WATCH_FIELDS:
            val = fields[key]
            if val != prev.get(key):
                log.info("FIELD %s: %s → %s", key, prev.get(key, "?"),
                         f"{val:.4f}" if isinstance(val, float) else val)
                prev[key] = val

        # Periodic full snapshot every 5 seconds.
        now = time.monotonic()
        if now - _telem["last_dump"] >= 5.0:
            _telem["last_dump"] = now
            parts = []
            for k in _DUMP_FIELDS:
                v = fields[k]
                parts.append(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}")
            log.info("TELEMETRY  %s", "  ".join(parts))

    def on_packet(packet) -> None:
        with stats._lock:
            prev_race_on = stats.is_race_on
            stats.is_race_on = packet.is_race_on
            stats.lap_number = packet.lap_number
            stats.last_lap_s = packet.last_lap
        if prev_race_on != packet.is_race_on:
            log.info("IsRaceOn: %d → %d", prev_race_on, packet.is_race_on)
        lap = app.session.on_packet(packet)
        if lap is not None:
            with stats._lock:
                stats.laps_recorded += 1
            log.info("Lap %d recorded: %.3fs", lap.lap_number, lap.lap_time_ms / 1000)
            app.notify_new_lap(lap)

    log.info("UDP listener starting on 127.0.0.1:%d (expecting %d-byte packets)", port, PACKET_SIZE)
    transport = await udp_listener.start_udp_listener("127.0.0.1", port, on_packet, on_raw)
    try:
        await asyncio.Event().wait()
    finally:
        transport.close()


def main() -> None:
    log.info("fh6-relay starting")
    loop = asyncio.new_event_loop()
    session = SessionManager()
    stats = DebugStats()
    app = App(session, loop, stats)
    port = token_store.get_udp_port()

    def run_loop() -> None:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_async_main(app, port, stats))

    t = threading.Thread(target=run_loop, daemon=True)
    t.start()

    app.run()
    log.info("fh6-relay shutting down")


if __name__ == "__main__":
    main()
