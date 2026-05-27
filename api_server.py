import json
import logging
from datetime import datetime, timezone

import discord
from aiohttp import web

import config
import database
from utils import format_lap_time

log = logging.getLogger(__name__)

CAR_CLASS_MAP: dict[int, str] = {
    0: "D", 1: "C", 2: "B", 3: "A", 4: "S1", 5: "S2", 6: "R", 7: "X",
}

_BOT_KEY: web.AppKey = web.AppKey("bot")


def create_app(bot) -> web.Application:
    app = web.Application()
    app[_BOT_KEY] = bot
    app.router.add_get("/api/vehicles", _handle_vehicles)
    app.router.add_get("/api/tracks", _handle_tracks)
    app.router.add_post("/api/lap", _handle_lap)
    return app


async def _handle_vehicles(request: web.Request) -> web.Response:
    return web.json_response(config.VEHICLES)


async def _handle_tracks(request: web.Request) -> web.Response:
    return web.json_response(config.TRACKS)


async def _handle_lap(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"reason": "invalid_json"}, status=400)

    required = [
        "token", "discord_id", "discord_username",
        "lap_time_ms", "track", "vehicle_name", "car_class_int",
    ]
    for field in required:
        if field not in body:
            return web.json_response({"reason": f"missing_field:{field}"}, status=400)

    token_row = database.get_token_row(body["token"])
    if token_row is None:
        return web.json_response({"reason": "invalid_token"}, status=401)

    if datetime.now(timezone.utc) > datetime.fromisoformat(token_row["expires_at"]):
        return web.json_response({"reason": "token_expired"}, status=401)

    if body["discord_id"] != token_row["discord_id"]:
        return web.json_response({"reason": "discord_id_mismatch"}, status=403)

    if body["track"] not in config.TRACKS:
        return web.json_response({"reason": "invalid_track"}, status=400)

    vehicle_names = [v["name"] for v in config.VEHICLES]
    if vehicle_names and body["vehicle_name"] not in vehicle_names:
        return web.json_response({"reason": "invalid_vehicle"}, status=400)

    class_ = CAR_CLASS_MAP.get(body["car_class_int"])
    if class_ is None:
        return web.json_response({"reason": "invalid_car_class"}, status=400)

    raw_telemetry = json.dumps(body["raw_telemetry"]) if body.get("raw_telemetry") else None

    entry_id = database.add_entry(
        discord_id=body["discord_id"],
        username=body["discord_username"],
        track=body["track"],
        vehicle=body["vehicle_name"],
        class_=class_,
        lap_time_ms=body["lap_time_ms"],
        source="telemetry",
        raw_telemetry=raw_telemetry,
    )

    bot = request.app[_BOT_KEY]
    try:
        user = await bot.fetch_user(int(body["discord_id"]))
        await user.send(embed=_build_lap_embed(
            body["discord_username"], body["track"], body["vehicle_name"],
            class_, body["lap_time_ms"], entry_id,
        ))
    except Exception as exc:
        log.warning("Failed to DM user %s after lap submission: %r", body["discord_id"], exc)

    return web.json_response({"entry_id": entry_id})


def _build_lap_embed(
    username: str, track: str, vehicle: str, class_: str, lap_time_ms: int, entry_id: int
) -> discord.Embed:
    embed = discord.Embed(title="Time Attack Entry Recorded (Data Out)", color=discord.Color.blue())
    embed.add_field(name="Track", value=track, inline=True)
    embed.add_field(name="Class", value=class_, inline=True)
    embed.add_field(name="Vehicle", value=vehicle, inline=True)
    embed.add_field(name="Lap Time", value=format_lap_time(lap_time_ms), inline=True)
    embed.add_field(name="Entry ID", value=str(entry_id), inline=True)
    embed.set_footer(text=f"Auto-submitted via Data Out by {username}")
    return embed
