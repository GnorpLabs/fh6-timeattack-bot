import pytest
from utils import parse_lap_time, format_lap_time


def test_parse_standard_time():
    assert parse_lap_time("1:23.456") == 83456


def test_parse_zero_minutes():
    assert parse_lap_time("0:45.123") == 45123


def test_parse_strips_whitespace():
    assert parse_lap_time("  1:23.456  ") == 83456


def test_parse_sub_minute_no_minutes():
    assert parse_lap_time("58.120") == 58120


def test_parse_sub_minute_with_zero_minutes():
    assert parse_lap_time("0:58.120") == 58120


def test_parse_invalid_format_raises_value_error():
    with pytest.raises(ValueError, match="isn't a valid time"):
        parse_lap_time("123.456")


def test_parse_colon_ms_separator_raises_value_error():
    with pytest.raises(ValueError, match="isn't a valid time"):
        parse_lap_time("0:58:120")


def test_parse_missing_milliseconds_raises_value_error():
    with pytest.raises(ValueError, match="isn't a valid time"):
        parse_lap_time("1:23")


def test_parse_seconds_over_59_raises_value_error():
    with pytest.raises(ValueError, match="out of range"):
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
