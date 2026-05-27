import aiohttp

from session_manager import LapRecord


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
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{api_url}/api/lap", json=payload) as resp:
            data = await resp.json()
            if resp.status == 200:
                return data
            raise ValueError(data.get("reason", "unknown_error"))
