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


def _valid_lap_body(token: str, discord_id: str = "111") -> dict:
    return {
        "token": token,
        "discord_id": discord_id,
        "discord_username": "alice",
        "lap_time_ms": 83456,
        "track": "Hokubu Circuit",
        "vehicle_name": "2024 Toyota GR86",
        "car_class_int": 3,
        "car_ordinal": 1234,
    }


async def test_post_lap_valid_returns_entry_id(client):
    token = database.create_token("111")
    resp = await client.post("/api/lap", json=_valid_lap_body(token))
    assert resp.status == 200
    data = await resp.json()
    assert isinstance(data["entry_id"], int)


async def test_post_lap_invalid_token_returns_401(client):
    resp = await client.post("/api/lap", json=_valid_lap_body("badtoken"))
    assert resp.status == 401
    assert (await resp.json())["reason"] == "invalid_token"


async def test_post_lap_expired_token_returns_401(client):
    import hashlib
    import sqlite3
    from datetime import timedelta
    token = database.create_token("111")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("UPDATE tokens SET expires_at = ? WHERE token_hash = ?", (past, token_hash))
    conn.commit()
    conn.close()
    resp = await client.post("/api/lap", json=_valid_lap_body(token))
    assert resp.status == 401
    assert (await resp.json())["reason"] == "token_expired"


async def test_post_lap_discord_id_mismatch_returns_403(client):
    token = database.create_token("111")
    body = _valid_lap_body(token, discord_id="999")
    resp = await client.post("/api/lap", json=body)
    assert resp.status == 403
    assert (await resp.json())["reason"] == "discord_id_mismatch"


async def test_post_lap_invalid_track_returns_400(client):
    token = database.create_token("111")
    body = _valid_lap_body(token)
    body["track"] = "Fake Track"
    resp = await client.post("/api/lap", json=body)
    assert resp.status == 400
    assert (await resp.json())["reason"] == "invalid_track"


async def test_post_lap_invalid_vehicle_returns_400(client):
    token = database.create_token("111")
    body = _valid_lap_body(token)
    body["vehicle_name"] = "1985 Fake Car"
    resp = await client.post("/api/lap", json=body)
    assert resp.status == 400
    assert (await resp.json())["reason"] == "invalid_vehicle"


async def test_post_lap_invalid_car_class_returns_400(client):
    token = database.create_token("111")
    body = _valid_lap_body(token)
    body["car_class_int"] = 99
    resp = await client.post("/api/lap", json=body)
    assert resp.status == 400
    assert (await resp.json())["reason"] == "invalid_car_class"


async def test_post_lap_missing_field_returns_400(client):
    resp = await client.post("/api/lap", json={"token": "x"})
    assert resp.status == 400


async def test_post_lap_dms_user_on_success(client, mock_bot):
    token = database.create_token("111")
    await client.post("/api/lap", json=_valid_lap_body(token))
    mock_bot.fetch_user.assert_awaited_once_with(111)
    mock_bot.fetch_user.return_value.send.assert_awaited_once()
