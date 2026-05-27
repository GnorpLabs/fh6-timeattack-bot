# FH6 Data Out Auto-Submit — Design Spec

**Date:** 2026-05-26  
**Status:** Approved  

---

## Overview

Add support for Forza Horizon 6's "Data Out" UDP telemetry feature so players can automatically capture lap times without manually typing them into Discord. The feature consists of two components:

1. **`fh6-relay`** — a new Windows `.exe` (separate Python project) that runs on the player's PC, listens for FH6's UDP stream, records lap completions, and lets the player review and submit a chosen lap via a system tray GUI.
2. **Bot server additions** — a token-auth HTTP API endpoint, a new Discord cog for token management, and minor database schema changes to the existing `fh6-timeattack-bot`.

The existing `/submit` slash command and all other bot functionality are unchanged.

---

## Architecture

```
┌──────────────────────────────────┐        HTTPS POST        ┌──────────────────────────────┐
│  fh6-relay  (Windows .exe)       │ ───────────────────────► │  fh6-timeattack-bot (server)  │
│                                  │                           │                               │
│  UDP ◄── FH6 Game (127.0.0.1)   │                           │  Discord bot  +  HTTP API     │
└──────────────────────────────────┘                           └──────────────────────────────┘
```

- FH6 sends UDP to `127.0.0.1:20440` (same machine — no NAT issues).
- The exe processes all packets locally, only sending one small HTTPS POST per submitted lap.
- The bot's HTTP server runs on a new port (default `8080`) alongside the Discord bot in the same asyncio event loop.

---

## FH6 UDP Packet Format

Single 324-byte little-endian UDP packet per game frame (~120–140 Hz).

Key fields used by this feature:

| Offset | Field | Type | Notes |
|--------|-------|------|-------|
| 0 | `IsRaceOn` | s32 | 1 = in session, 0 = menus |
| 212 | `CarOrdinal` | s32 | Game-internal car ID |
| 216 | `CarClass` | s32 | 0=D 1=C 2=B 3=A 4=S1 5=S2 6=R 7=X *(mapping to be verified against live FH6 data during implementation)* |
| 296 | `BestLap` | f32 | Session best lap in seconds |
| 300 | `LastLap` | f32 | Most recently completed lap in seconds |
| 304 | `CurrentLap` | f32 | Current ongoing lap in seconds |
| 312 | `LapNumber` | u16 | Increments on each lap completion |
| 314 | `RacePosition` | u8 | Race position |

The packet does **not** contain a track name or human-readable vehicle name. Track is supplied by the user in the review window; vehicle is selected from the 616-car dropdown (same list as `/submit`).

---

## Component 1: `fh6-relay` exe

### Project Structure

```
fh6-relay/
  main.py            # Entry point, asyncio event loop
  udp_listener.py    # asyncio UDP server on 127.0.0.1:20440
  packet_parser.py   # struct.unpack of the 324-byte packet
  session_manager.py # Lap detection state machine
  token_store.py     # Read/write %APPDATA%\FH6BotRelay\config.json
  api_client.py      # Single aiohttp HTTPS POST to bot API
  gui.py             # pystray tray icon + tkinter Session Review window
  build.spec         # PyInstaller spec for producing the .exe
```

### Lap Detection Logic

```python
# session_manager.py (pseudocode)
prev_lap_number = None

def on_packet(p):
    if p.IsRaceOn == 0:
        return
    if prev_lap_number is None:
        prev_lap_number = p.LapNumber
        return
    if p.LapNumber > prev_lap_number:
        lap = {
            "lap_time_ms": int(p.LastLap * 1000),
            "car_class_int": p.CarClass,
            "car_ordinal": p.CarOrdinal,
            "raw_telemetry": serialize_packet(p),
            "captured_at": utcnow(),
        }
        session.laps.append(lap)
        prev_lap_number = p.LapNumber
```

`raw_telemetry` stores the full packet snapshot as a JSON blob, enabling future anti-cheat validation without re-engineering the submission flow.

### Session Review Window (tkinter)

Fields:
- **Track** — dropdown populated from `GET /api/tracks` on the bot (same list as `/submit`)
- **Vehicle** — searchable dropdown from `GET /api/vehicles`
- **Laps table** — all laps captured this session, showing lap number and time; user selects one row
- **Submit** button — sends the selected lap

Track and vehicle selections persist in memory for the session (user sets them once, drives many laps, submits chosen lap).

### System Tray (pystray)

- Icon shows idle / active / error state
- Right-click menu: `Open Session Review`, `Settings`, `Quit`
- `Settings` allows changing the UDP port and API URL (for self-hosters)

### Token Store

File: `%APPDATA%\FH6BotRelay\config.json`

```json
{
  "token": "abc123...",
  "api_url": "https://your-bot-host.example.com",
  "udp_port": 20440
}
```

On first launch, if either `token` or `api_url` is absent, a setup modal prompts the user for both:
- **Server address** — IP address or FQDN of the bot server (e.g. `192.168.1.1` or `bot.example.com`). The exe constructs the full URL as `https://<input>`.
- **Token** — pasted from the `/dataout-register` Discord response.

Both are saved to `config.json` and not requested again. If the API subsequently returns `401`, only the token prompt is shown (the server address stays unchanged).

### Build

PyInstaller one-file build targeting Windows x64. The `.exe` is distributed as a GitHub release asset.

---

## Component 2: Bot Server Changes

### Database Schema

**`time_entries` — three changes:**

```sql
-- SQLite does not support ALTER COLUMN, so making screenshot_path nullable
-- requires the standard recreate-table migration:
--   1. CREATE new table with nullable screenshot_path
--   2. INSERT INTO new SELECT * FROM old
--   3. DROP TABLE old
--   4. ALTER TABLE new RENAME TO time_entries
-- This is handled in database.init_db() at startup using a schema version flag.

-- New columns (ADD COLUMN is supported by SQLite):
ALTER TABLE time_entries ADD COLUMN source TEXT NOT NULL DEFAULT 'manual';
-- 'manual' | 'telemetry'

ALTER TABLE time_entries ADD COLUMN raw_telemetry TEXT;
-- JSON snapshot, NULL for manual submissions
```

**New `tokens` table:**

```sql
CREATE TABLE IF NOT EXISTS tokens (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id   TEXT NOT NULL UNIQUE,
    token_hash   TEXT NOT NULL,   -- SHA-256 hex of the plain token
    expires_at   TEXT NOT NULL    -- ISO-8601 UTC
);
```

Tokens are never stored in plaintext. The bot generates a 32-byte secure random token, returns it ephemerally to the user once, and stores only its SHA-256 hash.

### New File: `cogs/telemetry.py`

Two slash commands:

**`/dataout-register`**
1. Generates `secrets.token_hex(32)` → plain token
2. Hashes it → stores in `tokens` table with `expires_at = now + 30 days`
3. Responds ephemerally with the plain token and setup instructions
4. If a token already exists for this user, overwrites it (re-registration)

**`/dataout-refresh`**
1. Same as register — regenerates token, invalidates the old one immediately
2. Responds ephemerally with the new token

### New File: `api_server.py`

`aiohttp.web.Application` started inside `bot.py`'s `setup_hook` on port `8080`.

**`POST /api/lap`**

Request body (JSON):
```json
{
  "token": "abc123...",
  "lap_time_ms": 83456,
  "track": "Hokubu Circuit",
  "vehicle_name": "2024 Toyota GR86",
  "car_class_int": 3,
  "car_ordinal": 1234,
  "raw_telemetry": { ... }
}
```

Logic:
1. SHA-256 hash the incoming token, look up in `tokens` table
2. Return `401 {"reason": "invalid_token"}` if not found
3. Return `401 {"reason": "token_expired"}` if `expires_at` is past
4. Validate `track` is in `config.TRACKS`, `vehicle_name` is in `config.VEHICLES`
5. Map `car_class_int` → class string (`{0:"D", 1:"C", 2:"B", 3:"A", 4:"S1", 5:"S2", 6:"R", 7:"X"}`)
6. Resolve username: `user = await bot.fetch_user(int(discord_id))` → `username = user.name`
7. Call `add_entry(discord_id, username, track, vehicle_name, class_, lap_time_ms, screenshot_path=None, source='telemetry', raw_telemetry=json_blob)`
8. DM the Discord user a confirmation embed (same format as `/submit` response)
9. Return `200 {"entry_id": 42}`

**`GET /api/vehicles`**

Returns `config.VEHICLES` as JSON. Allows the exe to sync the vehicle list on startup without bundling a stale copy.

**`GET /api/tracks`**

Returns `config.TRACKS` as JSON.

### Changes to `bot.py`

- Import and start `api_server.py` in `setup_hook` using `aiohttp.web.AppRunner`
- Add `API_PORT` to `config.py` (default `8080`, env-var overridable)

### Changes to `database.py`

- `add_entry()` gains two optional kwargs: `source='manual'`, `raw_telemetry=None`, `screenshot_path` becomes optional (defaults to `None`)
- `init_db()` runs the schema migrations for the new columns and `tokens` table

---

## Token Lifecycle

```
User runs /dataout-register
  → bot generates token, stores hash, returns plain token ephemerally

User pastes token into exe on first launch
  → exe saves to %APPDATA%\FH6BotRelay\config.json

Every API call
  → exe sends token in POST body
  → bot hashes it, checks expiry

Token expires (30 days)
  → bot returns 401 token_expired
  → exe modal prompts user to get a new token via /dataout-refresh
```

---

## End-to-End Data Flow

```
1. FH6 configured: Data Out → 127.0.0.1:20440
2. Player launches fh6-relay.exe (sits in system tray)
3. Player drives — exe collects lap completions silently
4. Player clicks tray icon → Session Review window
5. Player selects: track, vehicle, lap row → Submit
6. exe → HTTPS POST /api/lap → bot server
7. bot validates token → add_entry() → SQLite
8. bot DMs player confirmation embed
9. exe shows success toast
```

---

## Out of Scope (this iteration)

- Anti-cheat / lap validation using `raw_telemetry` — data is captured now, logic added later
- Auto-submission without user review — deferred until validation is in place
- macOS / Linux exe — Windows only via PyInstaller for now
- Screenshot capture from telemetry sessions
