import re


def parse_lap_time(time_str: str) -> int:
    m = re.fullmatch(r"(?:(\d+):)?(\d{2})\.(\d{3})", time_str.strip())
    if not m:
        raise ValueError(
            f"`{time_str.strip()}` isn't a valid time — use `mm:ss.ms` (e.g. `1:23.456`) or `ss.ms` for sub-minute laps (e.g. `58.120`)"
        )
    minutes = int(m.group(1)) if m.group(1) is not None else 0
    seconds, millis = int(m.group(2)), int(m.group(3))
    if seconds >= 60:
        raise ValueError(f"`{seconds}` seconds is out of range — seconds must be between 0 and 59")
    return minutes * 60_000 + seconds * 1_000 + millis


def format_lap_time(ms: int) -> str:
    minutes, remainder = divmod(ms, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{minutes}:{seconds:02d}.{millis:03d}"
