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
