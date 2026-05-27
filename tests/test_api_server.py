import pytest
from aiohttp.test_utils import TestClient, TestServer
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

import config
import database
import api_server


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    user_mock = MagicMock()
    user_mock.send = AsyncMock()
    bot.fetch_user = AsyncMock(return_value=user_mock)
    return bot


@pytest.fixture
async def client(fresh_db, mock_bot, monkeypatch):
    monkeypatch.setattr(config, "TRACKS", ["Hokubu Circuit", "Soni Circuit"])
    monkeypatch.setattr(config, "VEHICLES", [
        {"name": "2024 Toyota GR86", "manufacturer": "Toyota"},
        {"name": "2022 Acura NSX Type S", "manufacturer": "Acura"},
    ])
    app = api_server.create_app(mock_bot)
    async with TestClient(TestServer(app)) as c:
        yield c


async def test_get_vehicles_returns_vehicle_list(client):
    resp = await client.get("/api/vehicles")
    assert resp.status == 200
    data = await resp.json()
    assert {"name": "2024 Toyota GR86", "manufacturer": "Toyota"} in data


async def test_get_tracks_returns_track_list(client):
    resp = await client.get("/api/tracks")
    assert resp.status == 200
    data = await resp.json()
    assert "Hokubu Circuit" in data
