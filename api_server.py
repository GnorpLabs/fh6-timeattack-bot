import json
from datetime import datetime, timezone

import discord
from aiohttp import web

import config
import database
from utils import format_lap_time

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
    return web.json_response({"reason": "not_implemented"}, status=501)
