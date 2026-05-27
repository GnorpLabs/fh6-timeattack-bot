import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
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
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='time_entries'"
    ).fetchone() is not None

    if not table_exists:
        conn.execute("DROP TABLE IF EXISTS time_entries_v2")
        conn.execute("""
            CREATE TABLE time_entries (
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
        return

    cols = {row[1] for row in conn.execute("PRAGMA table_info(time_entries)")}
    if "source" in cols and "raw_telemetry" in cols:
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
                """SELECT discord_id, username, vehicle, class, lap_time_ms
                   FROM (
                       SELECT discord_id, username, vehicle, class,
                              MIN(lap_time_ms) AS lap_time_ms,
                              ROW_NUMBER() OVER (
                                  PARTITION BY class ORDER BY MIN(lap_time_ms) ASC
                              ) AS rn
                       FROM time_entries
                       WHERE track = ?
                       GROUP BY discord_id, class
                   )
                   WHERE rn <= 5
                   ORDER BY class, lap_time_ms ASC""",
                (track,),
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
