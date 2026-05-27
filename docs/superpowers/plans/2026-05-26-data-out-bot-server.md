# FH6 Data Out — Bot Server Changes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add token management, a telemetry HTTP API, and database schema updates to the existing Discord bot so the `fh6-relay` exe can authenticate users and submit lap times.

**Architecture:** A new `cogs/telemetry.py` Discord cog issues and refreshes auth tokens stored (SHA-256 hashed) in a new `tokens` table. A new `api_server.py` runs an aiohttp web application on a separate port within the same asyncio loop, exposing `POST /api/lap`, `GET /api/vehicles`, and `GET /api/tracks`. The existing `database.py` and `bot.py` are extended; no existing slash commands change.

**Tech Stack:** Python 3.14, discord.py, aiohttp, SQLite, pytest, pytest-asyncio

---

## File Map

| Action | Path | What changes |
|--------|------|--------------|
| Modify | `database.py` | Schema migration, `add_entry` signature, token functions |
| Modify | `config.py` | Add `API_PORT` |
| Modify | `bot.py` | Load telemetry cog, start/stop API server |
| Modify | `tests/test_database.py` | Token + schema tests |
| Create | `api_server.py` | aiohttp app with all three endpoints |
| Create | `cogs/telemetry.py` | `/dataout-register`, `/dataout-refresh` |
| Create | `tests/test_api_server.py` | API endpoint integration tests |

---

## Task 1: DB Schema Migration + Updated `add_entry`

**Files:**
- Modify: `database.py`
- Test: `tests/test_database.py`

- [ ] **Step 1: Write the failing tests**

Add to the bottom of `tests/test_database.py`:

```python
def test_add_entry_screenshot_is_optional(fresh_db):
    entry_id = database.add_entry("111", "Alice", "Hokubu Circuit", "2024 Toyota GR86", "A", 83456)
    entry = database.get_entry(entry_id)
    assert entry["screenshot_path"] is None


def test_add_entry_default_source_is_manual(fresh_db):
    entry_id = database.add_entry("111", "Alice", "Hokubu Circuit", "2024 Toyota GR86", "A", 83456)
    entry = database.get_entry(entry_id)
    assert entry["source"] == "manual"


def test_add_entry_telemetry_source_and_raw_telemetry(fresh_db):
    entry_id = database.add_entry(
        "111", "Alice", "Hokubu Circuit", "2024 Toyota GR86", "A", 83456,
        source="telemetry", raw_telemetry='{"lap_number": 3}',
    )
    entry = database.get_entry(entry_id)
    assert entry["source"] == "telemetry"
    assert entry["raw_telemetry"] == '{"lap_number": 3}'


def test_init_db_migrates_old_schema(tmp_path, monkeypatch):
    import sqlite3
    db = tmp_path / "legacy.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE time_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT NOT NULL, username TEXT NOT NULL,
            track TEXT NOT NULL, vehicle TEXT NOT NULL, class TEXT NOT NULL,
            lap_time_ms INTEGER NOT NULL, screenshot_path TEXT NOT NULL,
            submitted_at TEXT NOT NULL
        )
    """)
    conn.execute(
        "INSERT INTO time_entries VALUES (1,'1','Alice','T','V','A',1000,'s.png','2026-01-01')"
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(config, "DB_PATH", db)
    database.init_db()

    conn = sqlite3.connect(db)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(time_entries)")}
    rows = conn.execute("SELECT source, raw_telemetry FROM time_entries").fetchall()
    conn.close()

    assert "source" in cols
    assert "raw_telemetry" in cols
    assert rows[0] == ("manual", None)
```

- [ ] **Step 2: Run to confirm failures**

```
pytest tests/test_database.py::test_add_entry_screenshot_is_optional \
       tests/test_database.py::test_add_entry_default_source_is_manual \
       tests/test_database.py::test_add_entry_telemetry_source_and_raw_telemetry \
       tests/test_database.py::test_init_db_migrates_old_schema -v
```

Expected: 4 FAILs (column errors / wrong signature).

- [ ] **Step 3: Update `database.py`**

Add imports at the top of `database.py` (after existing imports):

```python
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
```

Replace the entire `init_db` function and add the migration helper directly after it:

```python
def init_db() -> None:
    conn = _connect()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS time_entries (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id       TEXT    NOT NULL,
                    username         TEXT    NOT NULL,
                    track            TEXT    NOT NULL,
                    vehicle          TEXT    NOT NULL,
                    class            TEXT    NOT NULL,
                    lap_time_ms      INTEGER NOT NULL,
                    screenshot_path  TEXT,
                    submitted_at     TEXT    NOT NULL,
                    source           TEXT    NOT NULL DEFAULT 'manual',
                    raw_telemetry    TEXT
                )
            """)
            _migrate_time_entries_if_needed(conn)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id   TEXT NOT NULL UNIQUE,
                    token_hash   TEXT NOT NULL,
                    expires_at   TEXT NOT NULL
                )
            """)
    finally:
        conn.close()


def _migrate_time_entries_if_needed(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(time_entries)")}
    if "source" in cols:
        return
    conn.execute("DROP TABLE IF EXISTS time_entries_v2")
    conn.execute("""
        CREATE TABLE time_entries_v2 (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id       TEXT    NOT NULL,
            username         TEXT    NOT NULL,
            track            TEXT    NOT NULL,
            vehicle          TEXT    NOT NULL,
            class            TEXT    NOT NULL,
            lap_time_ms      INTEGER NOT NULL,
            screenshot_path  TEXT,
            submitted_at     TEXT    NOT NULL,
            source           TEXT    NOT NULL DEFAULT 'manual',
            raw_telemetry    TEXT
        )
    """)
    conn.execute("""
        INSERT INTO time_entries_v2
            (id, discord_id, username, track, vehicle, class,
             lap_time_ms, screenshot_path, submitted_at)
        SELECT id, discord_id, username, track, vehicle, class,
               lap_time_ms, screenshot_path, submitted_at
        FROM time_entries
    """)
    conn.execute("DROP TABLE time_entries")
    conn.execute("ALTER TABLE time_entries_v2 RENAME TO time_entries")
```

Replace the `add_entry` function signature and body:

```python
def add_entry(
    discord_id: str,
    username: str,
    track: str,
    vehicle: str,
    class_: str,
    lap_time_ms: int,
    screenshot_path: str | None = None,
    source: str = "manual",
    raw_telemetry: str | None = None,
) -> int:
    submitted_at = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    try:
        with conn:
            cur = conn.execute(
                """INSERT INTO time_entries
                   (discord_id, username, track, vehicle, class, lap_time_ms,
                    screenshot_path, submitted_at, source, raw_telemetry)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (discord_id, username, track, vehicle, class_, lap_time_ms,
                 screenshot_path, submitted_at, source, raw_telemetry),
            )
            return cur.lastrowid
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to confirm pass**

```
pytest tests/test_database.py -v
```

Expected: all pass (existing tests still pass because `screenshot_path` is now keyword-optional — the existing calls in `tests/test_database.py` pass it positionally, so verify those still work too).

- [ ] **Step 5: Commit**

```bash
git add database.py tests/test_database.py
git commit -m "feat: migrate time_entries schema, make screenshot optional, add tokens table"
```

---

## Task 2: Token Functions in `database.py`

**Files:**
- Modify: `database.py`
- Test: `tests/test_database.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_database.py`:

```python
def test_create_token_returns_64_char_hex_string(fresh_db):
    token = database.create_token("111")
    assert len(token) == 64
    assert all(c in "0123456789abcdef" for c in token)


def test_create_token_each_call_returns_unique_token(fresh_db):
    assert database.create_token("111") != database.create_token("222")


def test_create_token_overwrites_existing_for_same_user(fresh_db):
    old_token = database.create_token("111")
    _new_token = database.create_token("111")
    assert database.get_token_row(old_token) is None


def test_get_token_row_returns_dict_with_discord_id(fresh_db):
    token = database.create_token("111")
    row = database.get_token_row(token)
    assert row is not None
    assert row["discord_id"] == "111"


def test_get_token_row_unknown_token_returns_none(fresh_db):
    database.create_token("111")
    assert database.get_token_row("notarealtoken") is None


def test_get_token_row_expires_at_is_in_the_future(fresh_db):
    from datetime import datetime, timezone
    token = database.create_token("111")
    row = database.get_token_row(token)
    expires_at = datetime.fromisoformat(row["expires_at"])
    assert expires_at > datetime.now(timezone.utc)
```

- [ ] **Step 2: Run to confirm failures**

```
pytest tests/test_database.py::test_create_token_returns_64_char_hex_string \
       tests/test_database.py::test_get_token_row_returns_dict_with_discord_id -v
```

Expected: FAIL with `AttributeError: module 'database' has no attribute 'create_token'`.

- [ ] **Step 3: Add token functions to `database.py`**

Add after `_migrate_time_entries_if_needed` (before `add_entry`):

```python
_TOKEN_EXPIRY_DAYS = 30


def _hash_token(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()


def create_token(discord_id: str) -> str:
    plain = secrets.token_hex(32)
    token_hash = _hash_token(plain)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=_TOKEN_EXPIRY_DAYS)).isoformat()
    conn = _connect()
    try:
        with conn:
            conn.execute(
                """INSERT INTO tokens (discord_id, token_hash, expires_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(discord_id) DO UPDATE
                   SET token_hash = excluded.token_hash,
                       expires_at = excluded.expires_at""",
                (discord_id, token_hash, expires_at),
            )
    finally:
        conn.close()
    return plain


def get_token_row(plain: str) -> dict | None:
    token_hash = _hash_token(plain)
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT discord_id, token_hash, expires_at FROM tokens WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_database.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add database.py tests/test_database.py
git commit -m "feat: add create_token and get_token_row to database"
```

---

## Task 3: Config + API Server Skeleton (GET endpoints)

**Files:**
- Modify: `config.py`
- Create: `api_server.py`
- Create: `tests/test_api_server.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_api_server.py`:

```python
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
```

- [ ] **Step 2: Run to confirm failures**

```
pytest tests/test_api_server.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'api_server'`.

- [ ] **Step 3: Add `API_PORT` to `config.py`**

Add after the `SCREENSHOTS_DIR` line:

```python
API_PORT: int = int(os.getenv("API_PORT", "8080"))
```

- [ ] **Step 4: Create `api_server.py`**

```python
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


def create_app(bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
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
```

- [ ] **Step 5: Run tests**

```
pytest tests/test_api_server.py::test_get_vehicles_returns_vehicle_list \
       tests/test_api_server.py::test_get_tracks_returns_track_list -v
```

Expected: both PASS.

- [ ] **Step 6: Commit**

```bash
git add config.py api_server.py tests/test_api_server.py
git commit -m "feat: add API_PORT config, api_server skeleton with GET endpoints"
```

---

## Task 4: Implement `POST /api/lap`

**Files:**
- Modify: `api_server.py`
- Test: `tests/test_api_server.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_api_server.py`:

```python
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
    import hashlib, sqlite3
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
```

- [ ] **Step 2: Run to confirm failures**

```
pytest tests/test_api_server.py -v
```

Expected: the new tests FAIL (501 from stub), GET tests still PASS.

- [ ] **Step 3: Implement `_handle_lap` in `api_server.py`**

Replace the stub `_handle_lap` and add the embed helper:

```python
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

    bot = request.app["bot"]
    try:
        user = await bot.fetch_user(int(body["discord_id"]))
        await user.send(embed=_build_lap_embed(
            body["discord_username"], body["track"], body["vehicle_name"],
            class_, body["lap_time_ms"], entry_id,
        ))
    except Exception:
        pass

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
```

- [ ] **Step 4: Run all API tests**

```
pytest tests/test_api_server.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add api_server.py tests/test_api_server.py
git commit -m "feat: implement POST /api/lap with token auth and validation"
```

---

## Task 5: Telemetry Cog (`/dataout-register`, `/dataout-refresh`)

**Files:**
- Create: `cogs/telemetry.py`

(Discord cog slash command tests require a running bot instance; manual verification is the test here.)

- [ ] **Step 1: Create `cogs/telemetry.py`**

```python
import discord
from discord import app_commands
from discord.ext import commands

import database


class TelemetryCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="dataout-register", description="Register for Data Out auto-submit")
    async def dataout_register(self, interaction: discord.Interaction) -> None:
        token = database.create_token(str(interaction.user.id))
        await interaction.response.send_message(
            f"**Your Data Out token:**\n```\n{token}\n```\n"
            "Paste this into the fh6-relay app when prompted on first launch.\n"
            "This token expires in **30 days** — use `/dataout-refresh` to renew it.\n"
            "⚠️ Keep this private — anyone with your token can submit times on your behalf.",
            ephemeral=True,
        )

    @app_commands.command(name="dataout-refresh", description="Refresh your Data Out token (invalidates old one)")
    async def dataout_refresh(self, interaction: discord.Interaction) -> None:
        token = database.create_token(str(interaction.user.id))
        await interaction.response.send_message(
            f"**Your new Data Out token:**\n```\n{token}\n```\n"
            "Your previous token has been invalidated. Update it in fh6-relay via the Settings menu.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TelemetryCog(bot))
```

- [ ] **Step 2: Run existing tests to confirm nothing broken**

```
pytest tests/ -v
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add cogs/telemetry.py
git commit -m "feat: add TelemetryCog with /dataout-register and /dataout-refresh"
```

---

## Task 6: Wire Up in `bot.py`

**Files:**
- Modify: `bot.py`

- [ ] **Step 1: Add `cogs.telemetry` to the COGS list in `bot.py`**

Change:
```python
COGS = [
    "cogs.submission",
    "cogs.query",
    "cogs.admin",
]
```

To:
```python
COGS = [
    "cogs.submission",
    "cogs.query",
    "cogs.admin",
    "cogs.telemetry",
]
```

- [ ] **Step 2: Add `_api_runner` to `TimeAttackBot.__init__`**

Add after `self.http_session: aiohttp.ClientSession | None = None`:

```python
self._api_runner: aiohttp.web.AppRunner | None = None
```

- [ ] **Step 3: Start the API server in `setup_hook`**

Add at the end of `setup_hook`, after the slash command sync block:

```python
        import api_server
        from aiohttp import web as aiohttp_web
        _app = api_server.create_app(self)
        self._api_runner = aiohttp_web.AppRunner(_app)
        await self._api_runner.setup()
        site = aiohttp_web.TCPSite(self._api_runner, "0.0.0.0", config.API_PORT)
        await site.start()
        log.info(f"API server listening on port {config.API_PORT}")
```

- [ ] **Step 4: Clean up the runner in `close`**

Replace the existing `close` method:

```python
    async def close(self) -> None:
        if self._api_runner:
            await self._api_runner.cleanup()
        if self.http_session:
            await self.http_session.close()
        await super().close()
```

- [ ] **Step 5: Run full test suite**

```
pytest tests/ -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add bot.py
git commit -m "feat: start API server alongside Discord bot on API_PORT"
```

---

## Task 7: Update `.env.example`

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Add `API_PORT` to `.env.example`**

Read the current `.env.example` and add:

```
API_PORT=8080
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: add API_PORT to .env.example"
```
