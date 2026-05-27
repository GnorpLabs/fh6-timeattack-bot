import asyncio

import aiohttp
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import api_client
from session_manager import LapRecord


def _make_lap() -> LapRecord:
    return LapRecord(
        lap_number=2,
        lap_time_ms=83456,
        car_class_int=3,
        car_ordinal=1234,
        raw_telemetry={"lap_number": 2},
        captured_at="2026-05-26T12:00:00+00:00",
    )


async def test_submit_lap_returns_entry_id_on_success():
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={"entry_id": 42})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("api_client.aiohttp.ClientSession", return_value=mock_session):
        result = await api_client.submit_lap(
            api_url="https://bot.example.com",
            token="tok",
            discord_id="111",
            discord_username="alice",
            lap=_make_lap(),
            track="Hokubu Circuit",
            vehicle_name="2024 Toyota GR86",
        )
    assert result == {"entry_id": 42}


async def test_submit_lap_raises_value_error_on_401():
    mock_resp = AsyncMock()
    mock_resp.status = 401
    mock_resp.json = AsyncMock(return_value={"reason": "token_expired"})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("api_client.aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(ValueError, match="token_expired"):
            await api_client.submit_lap(
                api_url="https://bot.example.com",
                token="tok",
                discord_id="111",
                discord_username="alice",
                lap=_make_lap(),
                track="Hokubu Circuit",
                vehicle_name="2024 Toyota GR86",
            )


async def test_submit_lap_sends_correct_payload():
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={"entry_id": 1})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("api_client.aiohttp.ClientSession", return_value=mock_session):
        await api_client.submit_lap(
            api_url="https://bot.example.com",
            token="tok",
            discord_id="111",
            discord_username="alice",
            lap=_make_lap(),
            track="Hokubu Circuit",
            vehicle_name="2024 Toyota GR86",
        )

    call_kwargs = mock_session.post.call_args
    assert call_kwargs[0][0] == "https://bot.example.com/api/lap"
    payload = call_kwargs[1]["json"]
    assert payload["token"] == "tok"
    assert payload["discord_id"] == "111"
    assert payload["lap_time_ms"] == 83456
    assert payload["track"] == "Hokubu Circuit"
    assert payload["vehicle_name"] == "2024 Toyota GR86"
    assert payload["car_class_int"] == 3


async def test_submit_lap_raises_value_error_on_connection_refused():
    with patch("api_client.aiohttp.ClientSession") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(
            side_effect=aiohttp.ClientConnectorError(
                connection_key=None, os_error=OSError("refused")
            )
        )
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
        with pytest.raises(ValueError, match="connection_refused"):
            await api_client.submit_lap(
                api_url="https://bot.example.com",
                token="tok",
                discord_id="111",
                discord_username="alice",
                lap=_make_lap(),
                track="Hokubu Circuit",
                vehicle_name="2024 Toyota GR86",
            )


async def test_submit_lap_raises_value_error_on_timeout():
    with patch("api_client.aiohttp.ClientSession") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(
            side_effect=asyncio.TimeoutError()
        )
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
        with pytest.raises(ValueError, match="timeout"):
            await api_client.submit_lap(
                api_url="https://bot.example.com",
                token="tok",
                discord_id="111",
                discord_username="alice",
                lap=_make_lap(),
                track="Hokubu Circuit",
                vehicle_name="2024 Toyota GR86",
            )
