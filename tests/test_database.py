import pytest
import config
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


def test_get_leaderboard_no_class_top_5_per_class(fresh_db):
    for i in range(7):
        database.add_entry(str(i), f"User{i}", "Horizon Circuit", "Car", "S1", 80000 + i * 1000, "s/x.png")
    entries = database.get_leaderboard("Horizon Circuit")
    s1_entries = [e for e in entries if e["class"] == "S1"]
    assert len(s1_entries) == 5
    times = [e["lap_time_ms"] for e in s1_entries]
    assert times == sorted(times)
    assert times[0] == 80000


def test_get_leaderboard_no_class_best_per_user(fresh_db):
    database.add_entry("111", "Alice", "Horizon Circuit", "Car", "S1", 85000, "s/a.png")
    database.add_entry("111", "Alice", "Horizon Circuit", "Car", "S1", 80000, "s/b.png")
    database.add_entry("222", "Bob", "Horizon Circuit", "Car", "S1", 82000, "s/c.png")
    entries = database.get_leaderboard("Horizon Circuit")
    s1_entries = [e for e in entries if e["class"] == "S1"]
    assert len(s1_entries) == 2
    assert s1_entries[0]["discord_id"] == "111"
    assert s1_entries[0]["lap_time_ms"] == 80000


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
    assert "global_rank" in cols
    assert rows[0] == ("manual", None)

    # screenshot_path should be nullable after migration
    conn = sqlite3.connect(db)
    # Insert a row with NULL screenshot_path to verify nullable
    conn.execute(
        "INSERT INTO time_entries (discord_id, username, track, vehicle, class, lap_time_ms, submitted_at, source) "
        "VALUES ('2', 'Bob', 'T', 'V', 'A', 2000, '2026-01-02', 'manual')"
    )
    conn.commit()
    row = conn.execute("SELECT screenshot_path FROM time_entries WHERE discord_id='2'").fetchone()
    conn.close()
    assert row[0] is None


def test_init_db_is_idempotent(fresh_db):
    # fresh_db already called init_db() once
    entry_id = database.add_entry("111", "Alice", "Hokubu Circuit", "2024 Toyota GR86", "A", 83456)
    database.init_db()  # call again
    entry = database.get_entry(entry_id)
    assert entry is not None
    assert entry["discord_id"] == "111"


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


def test_add_entry_stores_global_rank(fresh_db):
    entry_id = database.add_entry(
        "111", "Alice", "Hokubu Circuit", "2024 Toyota GR86", "A", 83456,
        global_rank=42,
    )
    entry = database.get_entry(entry_id)
    assert entry["global_rank"] == 42


def test_add_entry_global_rank_defaults_to_none(fresh_db):
    entry_id = database.add_entry("111", "Alice", "Hokubu Circuit", "2024 Toyota GR86", "A", 83456)
    entry = database.get_entry(entry_id)
    assert entry["global_rank"] is None


def test_init_db_migrates_missing_global_rank(tmp_path, monkeypatch):
    import sqlite3
    db = tmp_path / "no_rank.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE time_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT NOT NULL, username TEXT NOT NULL,
            track TEXT NOT NULL, vehicle TEXT NOT NULL, class TEXT NOT NULL,
            lap_time_ms INTEGER NOT NULL, screenshot_path TEXT,
            submitted_at TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual', raw_telemetry TEXT
        )
    """)
    conn.execute(
        "INSERT INTO time_entries (discord_id, username, track, vehicle, class, "
        "lap_time_ms, submitted_at) VALUES ('1','Alice','T','V','A',1000,'2026-01-01')"
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(config, "DB_PATH", db)
    database.init_db()

    conn = sqlite3.connect(db)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(time_entries)")}
    row = conn.execute("SELECT global_rank FROM time_entries WHERE discord_id='1'").fetchone()
    conn.close()

    assert "global_rank" in cols
    assert row[0] is None
