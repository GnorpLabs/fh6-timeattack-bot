# FH6 Time Attack Bot — Design Spec

**Date:** 2026-05-26  
**Status:** Approved

---

## Overview

A Discord bot that lets a friend group record, persist, and query their Forza Horizon 6 time attack lap times. Each submission requires a screenshot, lap time, vehicle, vehicle class, and track. The bot stores entries permanently so history survives FH6's leaderboard resets.

---

## Architecture

**Pattern:** discord.py Cog-based modular bot (Option B), with the database layer behind a clean named-function interface so upgrading to a full service/repository pattern (Option C) requires no cog changes.

**Upgrade path to Option C:** `database.py` → split into `repository.py` + `service.py`. Cogs remain untouched.

### File Structure

```
fh6-timeattack-bot/
├── bot.py                        # Entry point, loads cogs, syncs slash commands
├── config.py                     # Loads env vars, reads TRACKS/CLASSES from constants and vehicles.json
├── database.py                   # All SQL — named functions only, no raw SQL in cogs
├── cogs/
│   ├── submission.py             # /submit command
│   ├── query.py                  # /leaderboard, /my-times, /history
│   └── admin.py                  # /delete (own entries only)
├── data/
│   ├── timeattack.db             # SQLite database (mounted volume)
│   └── vehicles.json             # Full FH6 vehicle roster
├── screenshots/                  # Downloaded screenshot files (mounted volume)
├── Dockerfile
├── docker-compose.yml
└── helm/                         # Helm chart for Kubernetes deployment
    ├── Chart.yaml
    ├── values.yaml
    └── templates/
```

---

## Data Model

Single table. No joins needed for any query.

```sql
CREATE TABLE time_entries (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id       TEXT    NOT NULL,   -- immutable Discord user ID
    username         TEXT    NOT NULL,   -- display name at submission time
    track            TEXT    NOT NULL,   -- value from TRACKS list
    vehicle          TEXT    NOT NULL,   -- name from vehicles.json
    class            TEXT    NOT NULL,   -- value from CLASSES list
    lap_time_ms      INTEGER NOT NULL,   -- lap time in milliseconds (e.g. 1:23.456 → 83456)
    screenshot_path  TEXT    NOT NULL,   -- relative path under screenshots/
    submitted_at     TEXT    NOT NULL    -- ISO 8601 timestamp
);
```

**Key decisions:**
- `lap_time_ms` as integer enables `ORDER BY lap_time_ms ASC` with no parsing at query time
- `discord_id` is the Discord snowflake (survives username changes)
- No separate users table — user info is denormalized per entry, keeping queries simple and Option C migration clean

---

## Configuration

### `config.py`

```python
TRACKS = ["track1", "track2", "track3"]   # replace with actual FH6 track names

CLASSES = ["D", "C", "B", "A", "S1", "S2", "X"]

# Loaded at startup from data/vehicles.json
# vehicles.json schema: [{"name": "...", "manufacturer": "..."}, ...]
VEHICLES: list[dict] = []   # populated in bot.py on startup
```

### `data/vehicles.json`

```json
[
  { "name": "1969 Dodge Charger Daytona", "manufacturer": "Dodge" },
  { "name": "2020 Koenigsegg Jesko",      "manufacturer": "Koenigsegg" },
  { "name": "2018 Porsche 911 GT2 RS",    "manufacturer": "Porsche" }
]
```

Autocomplete filters by both name and manufacturer as the user types. To add new cars, edit the JSON and restart the bot — no code changes required.

---

## Slash Commands

### `/submit`

```
/submit time:<mm:ss.ms> track:<autocomplete> vehicle:<autocomplete> class:<autocomplete>
        + required image attachment (screenshot)
```

- Validates attachment is an image (jpg/png/webp)
- Downloads screenshot to `screenshots/<discord_id>_<timestamp>.<ext>`
- Converts `mm:ss.ms` string to milliseconds and stores
- Replies with a confirmation embed: all fields + screenshot thumbnail

### `/leaderboard`

```
/leaderboard track:<autocomplete> [class:<autocomplete>]
```

- Without class: shows fastest entry per class on the track, grouped by class
- With class: shows top 10 entries (by time, any user) for that track+class combo
- Displays: rank, username, vehicle, time (formatted), date submitted

### `/my-times`

```
/my-times [track:<autocomplete>]
```

- Without track: all your entries across all tracks, sorted by track then lap time
- With track: your personal best + full history on that track

### `/history`

```
/history track:<autocomplete> [class:<autocomplete>]
```

- Full submission history for a track (optionally filtered by class), all users, chronological order
- Useful for reviewing progression over time

### `/delete`

```
/delete entry-id:<int>
```

- Bot verifies `discord_id` matches the entry's owner before deleting
- Bot responds with an ephemeral message containing Confirm / Cancel buttons before executing
- Deletes both the DB row and the screenshot file on disk

---

## Screenshot Storage

- Downloaded to `screenshots/` at submission time
- Filename format: `<discord_id>_<unix_timestamp>.<ext>`
- Path stored in `screenshot_path` column as a relative path
- Volume is mounted externally so screenshots survive container restarts

---

## Deployment

### docker-compose

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

### Environment Variables (`.env`)

| Variable           | Description                                      |
|--------------------|--------------------------------------------------|
| `DISCORD_TOKEN`    | Bot token from Discord Developer Portal          |
| `DISCORD_GUILD_ID` | Server ID for instant slash command sync in dev  |

### Helm (Kubernetes)

- Single `Deployment` with `replicas: 1` (SQLite is single-writer)
- Two `PersistentVolumeClaim` resources: one for `/app/data`, one for `/app/screenshots`
- `Secret` for `DISCORD_TOKEN`
- `values.yaml` exposes: image tag, storage class, PVC sizes

---

## Option C Upgrade Path

When this bot outgrows SQLite or needs horizontal scaling:

1. Rename `database.py` → `repository.py` (interface unchanged)
2. Add `service.py` with business logic extracted from cogs
3. Swap SQLite for PostgreSQL in `repository.py`
4. Update `docker-compose.yml` to add a `db` service
5. Update Helm chart to add a PostgreSQL subchart

No cog files change. The named-function interface in `database.py` acts as the seam.
