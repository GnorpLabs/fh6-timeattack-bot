import sqlite3
from datetime import datetime, timezone
from typing import Optional

import config


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
                    screenshot_path  TEXT    NOT NULL,
                    submitted_at     TEXT    NOT NULL
                )
            """)
    finally:
        conn.close()


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
    conn = _connect()
    try:
        with conn:
            cur = conn.execute(
                """INSERT INTO time_entries
                   (discord_id, username, track, vehicle, class, lap_time_ms, screenshot_path, submitted_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (discord_id, username, track, vehicle, class_, lap_time_ms, screenshot_path, submitted_at),
            )
            return cur.lastrowid
    finally:
        conn.close()


def get_entry(entry_id: int) -> Optional[dict]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM time_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_leaderboard(track: str, class_: Optional[str] = None) -> list[dict]:
    conn = _connect()
    try:
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
    finally:
        conn.close()


def get_user_times(discord_id: str, track: Optional[str] = None) -> list[dict]:
    conn = _connect()
    try:
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
    finally:
        conn.close()


def get_history(track: str, class_: Optional[str] = None) -> list[dict]:
    conn = _connect()
    try:
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
    finally:
        conn.close()


def delete_entry(entry_id: int, discord_id: str) -> bool:
    conn = _connect()
    try:
        with conn:
            cur = conn.execute(
                "DELETE FROM time_entries WHERE id = ? AND discord_id = ?",
                (entry_id, discord_id),
            )
            return cur.rowcount > 0
    finally:
        conn.close()
