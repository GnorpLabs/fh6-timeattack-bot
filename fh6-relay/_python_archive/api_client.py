import asyncio

import aiohttp

from session_manager import LapRecord

_TIMEOUT = aiohttp.ClientTimeout(total=10)


async def submit_lap(
    api_url: str,
    token: str,
    discord_id: str,
    discord_username: str,
    lap: LapRecord,
    track: str,
    vehicle_name: str,
) -> dict:
    payload = {
        "token": token,
        "discord_id": discord_id,
        "discord_username": discord_username,
        "lap_time_ms": lap.lap_time_ms,
        "track": track,
        "vehicle_name": vehicle_name,
        "car_class_int": lap.car_class_int,
        "car_ordinal": lap.car_ordinal,
        "raw_telemetry": lap.raw_telemetry,
    }
    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
            async with session.post(f"{api_url}/api/lap", json=payload) as resp:
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                if resp.status == 200:
                    return data
                raise ValueError(data.get("reason", "unknown_error"))
    except aiohttp.ClientConnectorError:
        raise ValueError("connection_refused")
    except asyncio.TimeoutError:
        raise ValueError("timeout")
