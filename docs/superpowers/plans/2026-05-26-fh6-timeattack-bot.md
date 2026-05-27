# FH6 Time Attack Bot — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Discord bot that lets a friend group record, persist, and query Forza Horizon 6 time attack lap times with required screenshot proof.

**Architecture:** Cog-based discord.py bot (Option B) with a clean `database.py` interface behind named functions — designed so upgrading to a full service/repository layer (Option C) requires no cog changes. SQLite on a mounted volume stores all entries; screenshots are downloaded to a second mounted volume.

**Tech Stack:** Python 3.11, discord.py 2.x, SQLite3, aiohttp, python-dotenv, pytest, Docker, Helm

---

## File Map

| File | Responsibility |
|------|---------------|
| `bot.py` | Entry point: loads vehicles.json into `config.VEHICLES`, calls `init_db()`, loads cogs, syncs slash commands |
| `config.py` | Env vars, `TRACKS`, `CLASSES`, `DB_PATH`, `SCREENSHOTS_DIR`, `VEHICLES` list, `get_vehicle_names()` |
| `utils.py` | `parse_lap_time(str) -> int` and `format_lap_time(int) -> str` |
| `database.py` | All SQL — named functions only, imports `config.DB_PATH` |
| `cogs/__init__.py` | Empty, makes `cogs/` a package |
| `cogs/submission.py` | `/submit` slash command + autocomplete + screenshot download |
| `cogs/query.py` | `/leaderboard`, `/my-times`, `/history` |
| `cogs/admin.py` | `/delete` with Confirm/Cancel button view |
| `data/vehicles.json` | Full vehicle roster `[{"name": "...", "manufacturer": "..."}]` |
| `tests/conftest.py` | Shared `fresh_db` pytest fixture |
| `tests/test_utils.py` | Tests for `parse_lap_time` and `format_lap_time` |
| `tests/test_database.py` | Tests for all database functions |
| `tests/test_config.py` | Tests for static config values |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Ignores `.env`, `data/`, `screenshots/`, `__pycache__/` |
| `.env.example` | Template env file |
| `pytest.ini` | pytest config |
| `Dockerfile` | Python 3.11-slim image |
| `docker-compose.yml` | Bot service with two mounted volumes |
| `helm/Chart.yaml` | Helm chart metadata |
| `helm/values.yaml` | Image, storage class, PVC sizes, Discord credentials |
| `helm/templates/secret.yaml` | k8s Secret for `DISCORD_TOKEN` and `DISCORD_GUILD_ID` |
| `helm/templates/pvc.yaml` | Two PVCs: data and screenshots |
| `helm/templates/deployment.yaml` | Bot Deployment, single replica |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `pytest.ini`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `cogs/__init__.py`
- Create: `data/.gitkeep`
- Create: `screenshots/.gitkeep`

- [ ] **Step 1: Create `requirements.txt`**

```
discord.py>=2.3.2
python-dotenv>=1.0.0
aiohttp>=3.9.0
pytest>=7.4.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 2: Create `.gitignore`**

```
.env
data/timeattack.db
screenshots/
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
```

- [ ] **Step 3: Create `.env.example`**

```
DISCORD_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=your_guild_id_here
DB_PATH=data/timeattack.db
SCREENSHOTS_DIR=screenshots
```

- [ ] **Step 4: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
```

- [ ] **Step 5: Create `Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data /app/screenshots

CMD ["python", "bot.py"]
```

- [ ] **Step 6: Create `docker-compose.yml`**

```yaml
services:
  bot:
    build: .
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./screenshots:/app/screenshots
    restart: unless-stopped
```

- [ ] **Step 7: Create empty `cogs/__init__.py` and placeholder volume dirs**

```bash
touch cogs/__init__.py data/.gitkeep screenshots/.gitkeep
```

- [ ] **Step 8: Commit**

```bash
git init
git add requirements.txt .gitignore .env.example pytest.ini Dockerfile docker-compose.yml cogs/__init__.py data/.gitkeep screenshots/.gitkeep
git commit -m "chore: project scaffolding"
```

---

## Task 2: Lap Time Utilities (TDD)

**Files:**
- Create: `utils.py`
- Create: `tests/test_utils.py`

- [ ] **Step 1: Create `tests/test_utils.py` with failing tests**

```python
import pytest
from utils import parse_lap_time, format_lap_time


def test_parse_standard_time():
    assert parse_lap_time("1:23.456") == 83456


def test_parse_zero_minutes():
    assert parse_lap_time("0:45.123") == 45123


def test_parse_strips_whitespace():
    assert parse_lap_time("  1:23.456  ") == 83456


def test_parse_invalid_format_raises_value_error():
    with pytest.raises(ValueError, match="Invalid time format"):
        parse_lap_time("123.456")


def test_parse_missing_milliseconds_raises_value_error():
    with pytest.raises(ValueError, match="Invalid time format"):
        parse_lap_time("1:23")


def test_parse_seconds_over_59_raises_value_error():
    with pytest.raises(ValueError, match="Seconds must be 0-59"):
        parse_lap_time("1:60.000")


def test_format_basic():
    assert format_lap_time(83456) == "1:23.456"


def test_format_zero_minutes():
    assert format_lap_time(45123) == "0:45.123"


def test_format_pads_seconds():
    assert format_lap_time(5123) == "0:05.123"


def test_format_pads_millis():
    assert format_lap_time(60010) == "1:00.010"


def test_roundtrip():
    assert parse_lap_time(format_lap_time(83456)) == 83456
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_utils.py -v
```

Expected: `ModuleNotFoundError: No module named 'utils'`

- [ ] **Step 3: Create `utils.py`**

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_utils.py -v
```

Expected: all 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add utils.py tests/test_utils.py
git commit -m "feat: lap time parse/format utilities"
```

---

## Task 3: Vehicle Roster

**Files:**
- Create: `data/vehicles.json`

- [ ] **Step 1: Create `data/vehicles.json`**

```json
[
  { "name": "2020 Dodge Challenger SRT Super Stock", "manufacturer": "Dodge" },
  { "name": "2017 Dodge Viper ACR", "manufacturer": "Dodge" },
  { "name": "2017 Ford GT", "manufacturer": "Ford" },
  { "name": "2013 Ford Mustang Shelby GT500", "manufacturer": "Ford" },
  { "name": "2016 Ford Focus RS", "manufacturer": "Ford" },
  { "name": "2019 Chevrolet Corvette ZR1", "manufacturer": "Chevrolet" },
  { "name": "2018 Chevrolet Camaro ZL1 1LE", "manufacturer": "Chevrolet" },
  { "name": "2018 Ferrari 812 Superfast", "manufacturer": "Ferrari" },
  { "name": "2015 Ferrari 488 GTB", "manufacturer": "Ferrari" },
  { "name": "2013 Ferrari LaFerrari", "manufacturer": "Ferrari" },
  { "name": "2017 Lamborghini Huracán Performante", "manufacturer": "Lamborghini" },
  { "name": "2020 Lamborghini Sián FKP 37", "manufacturer": "Lamborghini" },
  { "name": "2018 Lamborghini Urus", "manufacturer": "Lamborghini" },
  { "name": "2018 Porsche 911 GT2 RS", "manufacturer": "Porsche" },
  { "name": "2014 Porsche 918 Spyder", "manufacturer": "Porsche" },
  { "name": "2020 Porsche Taycan Turbo S", "manufacturer": "Porsche" },
  { "name": "2018 McLaren Senna", "manufacturer": "McLaren" },
  { "name": "2014 McLaren P1", "manufacturer": "McLaren" },
  { "name": "2017 McLaren 720S", "manufacturer": "McLaren" },
  { "name": "2018 Bugatti Chiron", "manufacturer": "Bugatti" },
  { "name": "2017 Koenigsegg Agera RS", "manufacturer": "Koenigsegg" },
  { "name": "2020 Koenigsegg Jesko", "manufacturer": "Koenigsegg" },
  { "name": "2021 BMW M3 Competition", "manufacturer": "BMW" },
  { "name": "2017 Mercedes-AMG GT R", "manufacturer": "Mercedes-AMG" },
  { "name": "2016 Audi R8 V10 Plus", "manufacturer": "Audi" },
  { "name": "2020 Toyota GR Supra", "manufacturer": "Toyota" },
  { "name": "2020 Toyota GR Yaris", "manufacturer": "Toyota" },
  { "name": "2017 Nissan GT-R NISMO", "manufacturer": "Nissan" },
  { "name": "2021 Honda Civic Type R", "manufacturer": "Honda" },
  { "name": "2016 Mazda MX-5 Miata", "manufacturer": "Mazda" },
  { "name": "1997 Mazda RX-7", "manufacturer": "Mazda" },
  { "name": "2016 Subaru WRX STI", "manufacturer": "Subaru" },
  { "name": "2016 Alfa Romeo Giulia Quadrifoglio", "manufacturer": "Alfa Romeo" },
  { "name": "2016 Pagani Huayra BC", "manufacturer": "Pagani" },
  { "name": "2009 Pagani Zonda Cinque Roadster", "manufacturer": "Pagani" }
]
```

> **Note:** Replace these with the actual FH6 vehicle roster. To add new cars, edit this file and restart the bot — no code changes required.

- [ ] **Step 2: Commit**

```bash
git add data/vehicles.json
git commit -m "feat: seed FH6 vehicle roster"
```

---

## Task 4: Configuration (TDD)

**Files:**
- Create: `config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Create `tests/test_config.py` with failing tests**

```python
from config import TRACKS, CLASSES, VEHICLES, get_vehicle_names


def test_tracks_is_nonempty_list():
    assert isinstance(TRACKS, list)
    assert len(TRACKS) > 0


def test_tracks_are_strings():
    assert all(isinstance(t, str) for t in TRACKS)


def test_classes_contains_expected_values():
    assert set(CLASSES) == {"D", "C", "B", "A", "S1", "S2", "X"}


def test_vehicles_starts_as_empty_list():
    assert isinstance(VEHICLES, list)


def test_get_vehicle_names_returns_empty_when_vehicles_empty():
    assert get_vehicle_names() == []
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Create `config.py`**

```python
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
DISCORD_GUILD_ID: str = os.getenv("DISCORD_GUILD_ID", "")

DB_PATH: Path = Path(os.getenv("DB_PATH", "data/timeattack.db"))
SCREENSHOTS_DIR: Path = Path(os.getenv("SCREENSHOTS_DIR", "screenshots"))

TRACKS: list[str] = [
    # Replace with actual FH6 time attack track names
    "Horizon Circuit",
    "Goliath",
    "Colossus",
    "Gauntlet",
    "Marathon",
]

CLASSES: list[str] = ["D", "C", "B", "A", "S1", "S2", "X"]

VEHICLES: list[dict] = []


def get_vehicle_names() -> list[str]:
    return [v["name"] for v in VEHICLES]
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: configuration module"
```

---

## Task 5: Database Layer (TDD)

**Files:**
- Create: `database.py`
- Create: `tests/conftest.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Create `tests/conftest.py`**

```python
import pytest
import config
import database


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    database.init_db()
```

- [ ] **Step 2: Create `tests/test_database.py` with failing tests**

```python
import pytest
import database


def test_add_entry_returns_integer_id(fresh_db):
    entry_id = database.add_entry("111", "Alice", "Horizon Circuit", "2018 Porsche 911 GT2 RS", "S1", 83456, "screenshots/a.png")
    assert isinstance(entry_id, int)
    assert entry_id >= 1


def test_get_entry_returns_correct_fields(fresh_db):
    entry_id = database.add_entry("111", "Alice", "Horizon Circuit", "2018 Porsche 911 GT2 RS", "S1", 83456, "screenshots/a.png")
    entry = database.get_entry(entry_id)
    assert entry["discord_id"] == "111"
    assert entry["username"] == "Alice"
    assert entry["track"] == "Horizon Circuit"
    assert entry["vehicle"] == "2018 Porsche 911 GT2 RS"
    assert entry["class"] == "S1"
    assert entry["lap_time_ms"] == 83456
    assert entry["screenshot_path"] == "screenshots/a.png"


def test_get_entry_nonexistent_returns_none(fresh_db):
    assert database.get_entry(9999) is None


def test_delete_entry_own_entry_succeeds(fresh_db):
    entry_id = database.add_entry("111", "Alice", "Horizon Circuit", "2018 Porsche 911 GT2 RS", "S1", 83456, "screenshots/a.png")
    assert database.delete_entry(entry_id, "111") is True
    assert database.get_entry(entry_id) is None


def test_delete_entry_wrong_owner_fails(fresh_db):
    entry_id = database.add_entry("111", "Alice", "Horizon Circuit", "2018 Porsche 911 GT2 RS", "S1", 83456, "screenshots/a.png")
    assert database.delete_entry(entry_id, "999") is False
    assert database.get_entry(entry_id) is not None


def test_delete_nonexistent_entry_returns_false(fresh_db):
    assert database.delete_entry(9999, "111") is False


def test_get_leaderboard_with_class_returns_fastest_first(fresh_db):
    database.add_entry("111", "Alice", "Horizon Circuit", "Porsche GT2", "S1", 83456, "s/a.png")
    database.add_entry("222", "Bob", "Horizon Circuit", "Ferrari 488", "S1", 80000, "s/b.png")
    database.add_entry("333", "Carol", "Horizon Circuit", "McLaren 720S", "S2", 75000, "s/c.png")
    entries = database.get_leaderboard("Horizon Circuit", "S1")
    assert len(entries) == 2
    assert entries[0]["username"] == "Bob"
    assert entries[1]["username"] == "Alice"


def test_get_leaderboard_with_class_shows_best_per_user(fresh_db):
    database.add_entry("111", "Alice", "Horizon Circuit", "Porsche GT2", "S1", 83456, "s/a.png")
    database.add_entry("111", "Alice", "Horizon Circuit", "Porsche GT2", "S1", 85000, "s/b.png")
    entries = database.get_leaderboard("Horizon Circuit", "S1")
    assert len(entries) == 1
    assert entries[0]["lap_time_ms"] == 83456


def test_get_leaderboard_with_class_limited_to_10(fresh_db):
    for i in range(15):
        database.add_entry(str(i), f"User{i}", "Horizon Circuit", "Car", "S1", 80000 + i * 100, f"s/{i}.png")
    entries = database.get_leaderboard("Horizon Circuit", "S1")
    assert len(entries) == 10


def test_get_leaderboard_no_class_groups_by_class(fresh_db):
    database.add_entry("111", "Alice", "Horizon Circuit", "Porsche GT2", "S1", 83456, "s/a.png")
    database.add_entry("222", "Bob", "Horizon Circuit", "BMW M3", "A", 90000, "s/b.png")
    entries = database.get_leaderboard("Horizon Circuit")
    classes = [e["class"] for e in entries]
    assert "S1" in classes
    assert "A" in classes


def test_get_leaderboard_empty_track_returns_empty(fresh_db):
    assert database.get_leaderboard("No Such Track") == []


def test_get_user_times_returns_all_entries_for_user(fresh_db):
    database.add_entry("123", "Alice", "Horizon Circuit", "Porsche GT2", "S1", 83456, "s/a.png")
    database.add_entry("123", "Alice", "Goliath", "Porsche GT2", "S1", 90000, "s/b.png")
    database.add_entry("456", "Bob", "Horizon Circuit", "Ferrari 488", "S1", 80000, "s/c.png")
    entries = database.get_user_times("123")
    assert len(entries) == 2
    assert all(e["discord_id"] == "123" for e in entries)


def test_get_user_times_filtered_by_track(fresh_db):
    database.add_entry("123", "Alice", "Horizon Circuit", "Porsche GT2", "S1", 83456, "s/a.png")
    database.add_entry("123", "Alice", "Goliath", "Porsche GT2", "S1", 90000, "s/b.png")
    entries = database.get_user_times("123", "Horizon Circuit")
    assert len(entries) == 1
    assert entries[0]["track"] == "Horizon Circuit"


def test_get_user_times_no_entries_returns_empty(fresh_db):
    assert database.get_user_times("999") == []


def test_get_history_is_chronological(fresh_db):
    database.add_entry("111", "Alice", "Horizon Circuit", "Porsche GT2", "S1", 83456, "s/a.png")
    database.add_entry("222", "Bob", "Horizon Circuit", "Ferrari 488", "S1", 80000, "s/b.png")
    entries = database.get_history("Horizon Circuit")
    assert len(entries) == 2
    assert entries[0]["submitted_at"] <= entries[1]["submitted_at"]


def test_get_history_filtered_by_class(fresh_db):
    database.add_entry("111", "Alice", "Horizon Circuit", "Porsche GT2", "S1", 83456, "s/a.png")
    database.add_entry("222", "Bob", "Horizon Circuit", "BMW M3", "A", 90000, "s/b.png")
    entries = database.get_history("Horizon Circuit", "S1")
    assert len(entries) == 1
    assert entries[0]["class"] == "S1"
```

- [ ] **Step 3: Run tests — verify they fail**

```bash
pytest tests/test_database.py -v
```

Expected: `ModuleNotFoundError: No module named 'database'`

- [ ] **Step 4: Create `database.py`**

```python
import sqlite3
from datetime import datetime, timezone
from typing import Optional

import config


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS time_entries (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id       TEXT    NOT NULL,
                username         TEXT    NOT NULL,
                track            TEXT    NOT NULL,
                vehicle          TEXT    NOT NULL,
                class            TEXT    NOT NULL,
                lap_time_ms      INTEGER NOT NULL,
                screenshot_path  TEXT    NOT NULL,
                submitted_at     TEXT    NOT NULL
            )
        """)


def add_entry(
    discord_id: str,
    username: str,
    track: str,
    vehicle: str,
    class_: str,
    lap_time_ms: int,
    screenshot_path: str,
) -> int:
    submitted_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO time_entries
               (discord_id, username, track, vehicle, class, lap_time_ms, screenshot_path, submitted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (discord_id, username, track, vehicle, class_, lap_time_ms, screenshot_path, submitted_at),
        )
        return cur.lastrowid


def get_entry(entry_id: int) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM time_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return dict(row) if row else None


def get_leaderboard(track: str, class_: Optional[str] = None) -> list[dict]:
    with _connect() as conn:
        if class_:
            rows = conn.execute(
                """SELECT discord_id, username, vehicle, class,
                          MIN(lap_time_ms) AS lap_time_ms, screenshot_path, submitted_at
                   FROM time_entries
                   WHERE track = ? AND class = ?
                   GROUP BY discord_id
                   ORDER BY lap_time_ms ASC
                   LIMIT 10""",
                (track, class_),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT e.discord_id, e.username, e.vehicle, e.class,
                          e.lap_time_ms, e.screenshot_path, e.submitted_at
                   FROM time_entries e
                   INNER JOIN (
                       SELECT class, MIN(lap_time_ms) AS min_time
                       FROM time_entries WHERE track = ?
                       GROUP BY class
                   ) best ON e.class = best.class
                             AND e.lap_time_ms = best.min_time
                             AND e.track = ?
                   ORDER BY e.class, e.lap_time_ms ASC""",
                (track, track),
            ).fetchall()
        return [dict(r) for r in rows]


def get_user_times(discord_id: str, track: Optional[str] = None) -> list[dict]:
    with _connect() as conn:
        if track:
            rows = conn.execute(
                """SELECT * FROM time_entries
                   WHERE discord_id = ? AND track = ?
                   ORDER BY track, lap_time_ms ASC""",
                (discord_id, track),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM time_entries
                   WHERE discord_id = ?
                   ORDER BY track, lap_time_ms ASC""",
                (discord_id,),
            ).fetchall()
        return [dict(r) for r in rows]


def get_history(track: str, class_: Optional[str] = None) -> list[dict]:
    with _connect() as conn:
        if class_:
            rows = conn.execute(
                """SELECT * FROM time_entries
                   WHERE track = ? AND class = ?
                   ORDER BY submitted_at ASC""",
                (track, class_),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM time_entries
                   WHERE track = ?
                   ORDER BY submitted_at ASC""",
                (track,),
            ).fetchall()
        return [dict(r) for r in rows]


def delete_entry(entry_id: int, discord_id: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM time_entries WHERE id = ? AND discord_id = ?",
            (entry_id, discord_id),
        )
        return cur.rowcount > 0
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
pytest tests/test_database.py -v
```

Expected: all 17 tests PASS

- [ ] **Step 6: Run full test suite**

```bash
pytest -v
```

Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add database.py tests/conftest.py tests/test_database.py
git commit -m "feat: database layer with SQLite"
```

---

## Task 6: Bot Entry Point

**Files:**
- Create: `bot.py`

- [ ] **Step 1: Create `bot.py`**

```python
import asyncio
import json
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

import config
from database import init_db

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

COGS = [
    "cogs.submission",
    "cogs.query",
    "cogs.admin",
]


async def main() -> None:
    vehicles_path = Path("data/vehicles.json")
    if vehicles_path.exists():
        with open(vehicles_path) as f:
            config.VEHICLES = json.load(f)
        log.info(f"Loaded {len(config.VEHICLES)} vehicles from {vehicles_path}")
    else:
        log.warning("data/vehicles.json not found — vehicle autocomplete will be empty")

    config.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    init_db()
    log.info("Database initialised")

    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready() -> None:
        log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
        guild_id = config.DISCORD_GUILD_ID
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            log.info(f"Slash commands synced to guild {guild_id}")
        else:
            await bot.tree.sync()
            log.info("Slash commands synced globally")

    for cog in COGS:
        await bot.load_extension(cog)
        log.info(f"Loaded cog: {cog}")

    await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Verify import chain is clean**

```bash
python -c "import bot" 2>&1 | head -5
```

Expected: no errors (may warn about missing `.env` — that is fine)

- [ ] **Step 3: Commit**

```bash
git add bot.py
git commit -m "feat: bot entry point"
```

---

## Task 7: Submission Cog

**Files:**
- Create: `cogs/submission.py`

- [ ] **Step 1: Create `cogs/submission.py`**

```python
from pathlib import Path

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

import config
from database import add_entry
from utils import format_lap_time, parse_lap_time

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class SubmissionCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="submit", description="Submit a time attack lap time")
    @app_commands.describe(
        time="Lap time in mm:ss.ms format (e.g. 1:23.456)",
        track="Time attack track",
        vehicle="Vehicle used",
        class_="Vehicle class",
        screenshot="Screenshot of your finish time",
    )
    @app_commands.rename(class_="class")
    async def submit(
        self,
        interaction: discord.Interaction,
        time: str,
        track: str,
        vehicle: str,
        class_: str,
        screenshot: discord.Attachment,
    ) -> None:
        try:
            lap_ms = parse_lap_time(time)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        ext = Path(screenshot.filename).suffix.lower()
        if ext not in _IMAGE_EXTENSIONS:
            await interaction.response.send_message(
                "Screenshot must be a jpg, png, or webp image.", ephemeral=True
            )
            return

        await interaction.response.defer()

        config.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{interaction.user.id}_{int(discord.utils.utcnow().timestamp())}{ext}"
        dest = config.SCREENSHOTS_DIR / filename

        async with aiohttp.ClientSession() as session:
            async with session.get(screenshot.url) as resp:
                if resp.status != 200:
                    await interaction.followup.send(
                        "Failed to download screenshot — please try again.", ephemeral=True
                    )
                    return
                dest.write_bytes(await resp.read())

        entry_id = add_entry(
            discord_id=str(interaction.user.id),
            username=interaction.user.display_name,
            track=track,
            vehicle=vehicle,
            class_=class_,
            lap_time_ms=lap_ms,
            screenshot_path=str(dest),
        )

        embed = discord.Embed(title="Time Attack Entry Recorded", color=discord.Color.green())
        embed.add_field(name="Track", value=track, inline=True)
        embed.add_field(name="Class", value=class_, inline=True)
        embed.add_field(name="Vehicle", value=vehicle, inline=True)
        embed.add_field(name="Lap Time", value=format_lap_time(lap_ms), inline=True)
        embed.add_field(name="Entry ID", value=str(entry_id), inline=True)
        embed.set_thumbnail(url=screenshot.url)
        embed.set_footer(text=f"Submitted by {interaction.user.display_name}")

        await interaction.followup.send(embed=embed)

    @submit.autocomplete("track")
    async def _track_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=t, value=t)
            for t in config.TRACKS
            if current.lower() in t.lower()
        ][:25]

    @submit.autocomplete("class_")
    async def _class_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=c, value=c)
            for c in config.CLASSES
            if current.lower() in c.lower()
        ][:25]

    @submit.autocomplete("vehicle")
    async def _vehicle_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=v["name"], value=v["name"])
            for v in config.VEHICLES
            if current.lower() in v["name"].lower() or current.lower() in v["manufacturer"].lower()
        ][:25]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SubmissionCog(bot))
```

- [ ] **Step 2: Verify import is clean**

```bash
python -c "from cogs.submission import SubmissionCog; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add cogs/submission.py
git commit -m "feat: /submit command with autocomplete and screenshot download"
```

---

## Task 8: Query Cog

**Files:**
- Create: `cogs/query.py`

- [ ] **Step 1: Create `cogs/query.py`**

```python
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
from database import get_history, get_leaderboard, get_user_times
from utils import format_lap_time


class QueryCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="leaderboard", description="View fastest times on a track")
    @app_commands.describe(track="The track", class_="Filter by vehicle class (optional)")
    @app_commands.rename(class_="class")
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        track: str,
        class_: Optional[str] = None,
    ) -> None:
        entries = get_leaderboard(track, class_)
        if not entries:
            label = f"**{track}**" + (f" ({class_})" if class_ else "")
            await interaction.response.send_message(
                f"No times recorded for {label}.", ephemeral=True
            )
            return

        title = f"Leaderboard — {track}" + (f" [{class_}]" if class_ else "")
        embed = discord.Embed(title=title, color=discord.Color.gold())

        if class_:
            lines = [
                f"{i}. **{e['username']}** — {format_lap_time(e['lap_time_ms'])} | {e['vehicle']}"
                for i, e in enumerate(entries, 1)
            ]
            embed.description = "\n".join(lines)
        else:
            by_class: dict[str, list[dict]] = {}
            for e in entries:
                by_class.setdefault(e["class"], []).append(e)
            for cls, cls_entries in by_class.items():
                lines = [
                    f"{i}. **{e['username']}** — {format_lap_time(e['lap_time_ms'])} | {e['vehicle']}"
                    for i, e in enumerate(cls_entries, 1)
                ]
                embed.add_field(name=f"Class {cls}", value="\n".join(lines), inline=False)

        await interaction.response.send_message(embed=embed)

    @leaderboard.autocomplete("track")
    async def _lb_track_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=t, value=t)
            for t in config.TRACKS if current.lower() in t.lower()
        ][:25]

    @leaderboard.autocomplete("class_")
    async def _lb_class_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=c, value=c)
            for c in config.CLASSES if current.lower() in c.lower()
        ][:25]

    @app_commands.command(name="my-times", description="View your personal lap times")
    @app_commands.describe(track="Filter to a specific track (optional)")
    async def my_times(
        self,
        interaction: discord.Interaction,
        track: Optional[str] = None,
    ) -> None:
        entries = get_user_times(str(interaction.user.id), track)
        if not entries:
            suffix = f" on **{track}**" if track else ""
            await interaction.response.send_message(
                f"You have no times recorded{suffix}.", ephemeral=True
            )
            return

        title = "Your Times" + (f" — {track}" if track else "")
        embed = discord.Embed(title=title, color=discord.Color.blue())
        lines = [
            f"**{e['track']}** [{e['class']}] — {format_lap_time(e['lap_time_ms'])} | {e['vehicle']} *(ID: {e['id']})*"
            for e in entries
        ]
        desc = "\n".join(lines)
        embed.description = desc[:4000] + ("\n..." if len(desc) > 4000 else "")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @my_times.autocomplete("track")
    async def _mt_track_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=t, value=t)
            for t in config.TRACKS if current.lower() in t.lower()
        ][:25]

    @app_commands.command(name="history", description="View full submission history for a track")
    @app_commands.describe(track="The track", class_="Filter by class (optional)")
    @app_commands.rename(class_="class")
    async def history(
        self,
        interaction: discord.Interaction,
        track: str,
        class_: Optional[str] = None,
    ) -> None:
        entries = get_history(track, class_)
        if not entries:
            label = f"**{track}**" + (f" ({class_})" if class_ else "")
            await interaction.response.send_message(
                f"No history for {label}.", ephemeral=True
            )
            return

        title = f"History — {track}" + (f" [{class_}]" if class_ else "")
        embed = discord.Embed(title=title, color=discord.Color.purple())
        lines = [
            f"`{e['submitted_at'][:10]}` **{e['username']}** [{e['class']}] — {format_lap_time(e['lap_time_ms'])} | {e['vehicle']}"
            for e in entries
        ]
        desc = "\n".join(lines)
        embed.description = desc[:4000] + ("\n..." if len(desc) > 4000 else "")
        await interaction.response.send_message(embed=embed)

    @history.autocomplete("track")
    async def _hist_track_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=t, value=t)
            for t in config.TRACKS if current.lower() in t.lower()
        ][:25]

    @history.autocomplete("class_")
    async def _hist_class_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=c, value=c)
            for c in config.CLASSES if current.lower() in c.lower()
        ][:25]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(QueryCog(bot))
```

- [ ] **Step 2: Verify import is clean**

```bash
python -c "from cogs.query import QueryCog; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add cogs/query.py
git commit -m "feat: /leaderboard, /my-times, /history commands"
```

---

## Task 9: Admin Cog

**Files:**
- Create: `cogs/admin.py`

- [ ] **Step 1: Create `cogs/admin.py`**

```python
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from database import delete_entry, get_entry
from utils import format_lap_time


class _ConfirmDeleteView(discord.ui.View):
    def __init__(self, entry: dict) -> None:
        super().__init__(timeout=30)
        self.entry = entry

    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        deleted = delete_entry(self.entry["id"], str(interaction.user.id))
        if deleted:
            screenshot = Path(self.entry["screenshot_path"])
            if screenshot.exists():
                screenshot.unlink()
            await interaction.response.edit_message(
                content=f"Entry #{self.entry['id']} deleted.", embed=None, view=None
            )
        else:
            await interaction.response.edit_message(
                content="Could not delete entry — it may have already been removed.",
                embed=None,
                view=None,
            )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        await interaction.response.edit_message(
            content="Deletion cancelled.", embed=None, view=None
        )

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="delete", description="Delete one of your own time entries")
    @app_commands.describe(entry_id="Entry ID to delete — find it with /my-times")
    async def delete(self, interaction: discord.Interaction, entry_id: int) -> None:
        entry = get_entry(entry_id)

        if entry is None:
            await interaction.response.send_message(
                f"Entry #{entry_id} not found.", ephemeral=True
            )
            return

        if entry["discord_id"] != str(interaction.user.id):
            await interaction.response.send_message(
                "You can only delete your own entries.", ephemeral=True
            )
            return

        embed = discord.Embed(title=f"Delete Entry #{entry_id}?", color=discord.Color.red())
        embed.add_field(name="Track", value=entry["track"], inline=True)
        embed.add_field(name="Class", value=entry["class"], inline=True)
        embed.add_field(name="Vehicle", value=entry["vehicle"], inline=True)
        embed.add_field(name="Lap Time", value=format_lap_time(entry["lap_time_ms"]), inline=True)
        embed.set_footer(text="This action cannot be undone.")

        await interaction.response.send_message(
            embed=embed, view=_ConfirmDeleteView(entry), ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
```

- [ ] **Step 2: Verify import is clean**

```bash
python -c "from cogs.admin import AdminCog; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Run full test suite one final time**

```bash
pytest -v
```

Expected: all tests PASS

- [ ] **Step 4: Commit**

```bash
git add cogs/admin.py
git commit -m "feat: /delete command with confirm/cancel button"
```

---

## Task 10: Helm Chart

**Files:**
- Create: `helm/Chart.yaml`
- Create: `helm/values.yaml`
- Create: `helm/templates/secret.yaml`
- Create: `helm/templates/pvc.yaml`
- Create: `helm/templates/deployment.yaml`

- [ ] **Step 1: Create `helm/Chart.yaml`**

```yaml
apiVersion: v2
name: fh6-timeattack-bot
description: FH6 Time Attack Discord Bot
type: application
version: 0.1.0
appVersion: "1.0.0"
```

- [ ] **Step 2: Create `helm/values.yaml`**

```yaml
image:
  repository: fh6-timeattack-bot
  tag: latest
  pullPolicy: IfNotPresent

discord:
  token: ""
  guildId: ""

storage:
  storageClass: ""
  data:
    size: 1Gi
  screenshots:
    size: 5Gi
```

- [ ] **Step 3: Create `helm/templates/secret.yaml`**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: fh6-timeattack-bot-secret
type: Opaque
stringData:
  DISCORD_TOKEN: {{ .Values.discord.token | quote }}
  DISCORD_GUILD_ID: {{ .Values.discord.guildId | quote }}
```

- [ ] **Step 4: Create `helm/templates/pvc.yaml`**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: fh6-timeattack-bot-data
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: {{ .Values.storage.storageClass | quote }}
  resources:
    requests:
      storage: {{ .Values.storage.data.size }}
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: fh6-timeattack-bot-screenshots
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: {{ .Values.storage.storageClass | quote }}
  resources:
    requests:
      storage: {{ .Values.storage.screenshots.size }}
```

- [ ] **Step 5: Create `helm/templates/deployment.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fh6-timeattack-bot
  labels:
    app: fh6-timeattack-bot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fh6-timeattack-bot
  template:
    metadata:
      labels:
        app: fh6-timeattack-bot
    spec:
      containers:
        - name: bot
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          envFrom:
            - secretRef:
                name: fh6-timeattack-bot-secret
          volumeMounts:
            - name: data
              mountPath: /app/data
            - name: screenshots
              mountPath: /app/screenshots
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: fh6-timeattack-bot-data
        - name: screenshots
          persistentVolumeClaim:
            claimName: fh6-timeattack-bot-screenshots
```

- [ ] **Step 6: Commit**

```bash
git add helm/
git commit -m "feat: Helm chart for Kubernetes deployment"
```

---

## Post-Setup: Running Locally

```bash
# 1. Copy and fill env file
cp .env.example .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the bot
python bot.py
```

## Post-Setup: Docker Compose

```bash
docker compose up --build -d
docker compose logs -f
```

## Post-Setup: Updating TRACKS

Edit `config.py` and update the `TRACKS` list, then restart the bot. No migration required — track values are stored as plain strings.
