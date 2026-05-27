import packet_parser
import session_manager

# Thresholds from session_manager — tests must stay in sync.
_MIN = session_manager._MIN_LAP_SECONDS   # 15.0
_GAP = session_manager._RESET_THRESHOLD  # 10.0

# A realistic lap time that clears both thresholds.
_LAP = _MIN + _GAP + 5.0   # e.g. 30.0 s


def _make_packet(
    is_race_on=1,
    current_lap=0.0,
    car_class=3,
    car_ordinal=100,
) -> packet_parser.FH6Packet:
    return packet_parser.FH6Packet(
        is_race_on=is_race_on,
        car_ordinal=car_ordinal,
        car_class=car_class,
        best_lap=0.0,
        last_lap=0.0,
        current_lap=current_lap,
        current_race_time=0.0,
        lap_number=0,
        race_position=1,
    )


def test_first_packet_does_not_trigger_lap():
    sm = session_manager.SessionManager()
    result = sm.on_packet(_make_packet(current_lap=0.0))
    assert result is None
    assert sm.laps == []


def test_no_trigger_while_lap_time_increasing():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(current_lap=0.0))
    result = sm.on_packet(_make_packet(current_lap=_LAP / 2))
    assert result is None


def test_current_lap_reset_triggers_lap_record():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(current_lap=0.0))
    sm.on_packet(_make_packet(current_lap=_LAP))
    result = sm.on_packet(_make_packet(current_lap=1.0))  # reset after crossing line
    assert result is not None
    assert result.lap_time_ms == round(_LAP * 1000)


def test_lap_time_converted_to_milliseconds():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(current_lap=0.0))
    sm.on_packet(_make_packet(current_lap=_LAP))
    result = sm.on_packet(_make_packet(current_lap=1.0))
    assert result.lap_time_ms == round(_LAP * 1000)


def test_lap_number_increments_each_lap():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(current_lap=0.0))
    sm.on_packet(_make_packet(current_lap=_LAP))
    r1 = sm.on_packet(_make_packet(current_lap=1.0))
    sm.on_packet(_make_packet(current_lap=_LAP))
    r2 = sm.on_packet(_make_packet(current_lap=1.0))
    assert r1.lap_number == 1
    assert r2.lap_number == 2


def test_multiple_laps_appended():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(current_lap=0.0))
    sm.on_packet(_make_packet(current_lap=_LAP))
    sm.on_packet(_make_packet(current_lap=1.0))
    sm.on_packet(_make_packet(current_lap=_LAP))
    sm.on_packet(_make_packet(current_lap=1.0))
    assert len(sm.laps) == 2


def test_short_lap_does_not_trigger():
    """CurrentLap below _MIN_LAP_SECONDS must not count as a lap."""
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(current_lap=0.0))
    sm.on_packet(_make_packet(current_lap=_MIN - 1.0))  # below threshold
    result = sm.on_packet(_make_packet(current_lap=1.0))
    assert result is None


def test_small_drop_does_not_trigger():
    """A drop smaller than _RESET_THRESHOLD must not be treated as a lap."""
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(current_lap=0.0))
    sm.on_packet(_make_packet(current_lap=_LAP))
    result = sm.on_packet(_make_packet(current_lap=_LAP - _GAP + 1.0))  # small dip
    assert result is None


def test_is_race_on_zero_resets_state():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(current_lap=0.0))
    sm.on_packet(_make_packet(is_race_on=0))
    result = sm.on_packet(_make_packet(is_race_on=1, current_lap=_LAP))
    assert result is None  # re-initialised, not a lap trigger


def test_lap_after_race_restart_detected():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(current_lap=0.0))
    sm.on_packet(_make_packet(is_race_on=0))
    sm.on_packet(_make_packet(is_race_on=1, current_lap=0.0))   # initialises
    sm.on_packet(_make_packet(is_race_on=1, current_lap=_LAP))  # lap running
    result = sm.on_packet(_make_packet(is_race_on=1, current_lap=1.0))  # reset
    assert result is not None
    assert result.lap_time_ms == round(_LAP * 1000)


def test_lap_count_resets_after_race_restart():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(current_lap=0.0))
    sm.on_packet(_make_packet(current_lap=_LAP))
    sm.on_packet(_make_packet(current_lap=1.0))   # lap 1
    sm.on_packet(_make_packet(is_race_on=0))
    sm.on_packet(_make_packet(is_race_on=1, current_lap=0.0))
    sm.on_packet(_make_packet(is_race_on=1, current_lap=_LAP))
    result = sm.on_packet(_make_packet(is_race_on=1, current_lap=1.0))
    assert result.lap_number == 1


def test_lap_record_contains_car_fields():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(current_lap=0.0, car_class=4, car_ordinal=999))
    sm.on_packet(_make_packet(current_lap=_LAP, car_class=4, car_ordinal=999))
    result = sm.on_packet(_make_packet(current_lap=1.0, car_class=4, car_ordinal=999))
    assert result.car_class_int == 4
    assert result.car_ordinal == 999


def test_lap_record_raw_telemetry_is_dict():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(current_lap=0.0))
    sm.on_packet(_make_packet(current_lap=_LAP))
    result = sm.on_packet(_make_packet(current_lap=1.0))
    assert isinstance(result.raw_telemetry, dict)


def test_reset_clears_laps_and_state():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(current_lap=0.0))
    sm.on_packet(_make_packet(current_lap=_LAP))
    sm.on_packet(_make_packet(current_lap=1.0))
    sm.reset()
    assert sm.laps == []
    result = sm.on_packet(_make_packet(current_lap=_LAP))
    assert result is None  # re-initialised after reset


def test_get_laps_snapshot_returns_copy():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(current_lap=0.0))
    sm.on_packet(_make_packet(current_lap=_LAP))
    sm.on_packet(_make_packet(current_lap=1.0))
    snapshot = sm.get_laps_snapshot()
    assert len(snapshot) == 1
    sm.reset()
    assert len(snapshot) == 1  # snapshot is independent of internal list
