import re


def parse_lap_time(time_str: str) -> int:
    m = re.fullmatch(r"(\d+):(\d{2})\.(\d{3})", time_str.strip())
    if not m:
        raise ValueError(
            f"Invalid time format '{time_str.strip()}'. Use mm:ss.ms (e.g. 1:23.456)"
        )
    minutes, seconds, millis = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if seconds >= 60:
        raise ValueError(f"Seconds must be 0-59, got {seconds}")
    return minutes * 60_000 + seconds * 1_000 + millis


def format_lap_time(ms: int) -> str:
    minutes, remainder = divmod(ms, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{minutes}:{seconds:02d}.{millis:03d}"
