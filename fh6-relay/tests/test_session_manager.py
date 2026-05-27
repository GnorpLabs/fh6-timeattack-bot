import packet_parser
import session_manager


def _make_packet(is_race_on=1, lap_number=1, last_lap=83.456, car_class=3, car_ordinal=100) -> packet_parser.FH6Packet:
    return packet_parser.FH6Packet(
        is_race_on=is_race_on,
        car_ordinal=car_ordinal,
        car_class=car_class,
        best_lap=last_lap,
        last_lap=last_lap,
        current_lap=0.0,
        current_race_time=0.0,
        lap_number=lap_number,
        race_position=1,
    )


def test_first_packet_does_not_trigger_lap():
    sm = session_manager.SessionManager()
    result = sm.on_packet(_make_packet(lap_number=1))
    assert result is None
    assert sm.laps == []


def test_same_lap_number_does_not_trigger_lap():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(lap_number=1))
    result = sm.on_packet(_make_packet(lap_number=1))
    assert result is None
    assert sm.laps == []


def test_lap_number_increment_triggers_lap_record():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(lap_number=1))
    result = sm.on_packet(_make_packet(lap_number=2, last_lap=83.456))
    assert result is not None
    assert result.lap_number == 2
    assert result.lap_time_ms == 83456


def test_lap_time_converted_to_milliseconds():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(lap_number=1))
    result = sm.on_packet(_make_packet(lap_number=2, last_lap=1.001))
    assert result.lap_time_ms == 1001


def test_lap_appended_to_session_laps():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(lap_number=1))
    sm.on_packet(_make_packet(lap_number=2))
    sm.on_packet(_make_packet(lap_number=3))
    assert len(sm.laps) == 2


def test_is_race_on_zero_resets_prev_lap_number():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(lap_number=5))
    sm.on_packet(_make_packet(is_race_on=0, lap_number=5))
    # After race off, first new packet should not trigger a lap
    result = sm.on_packet(_make_packet(is_race_on=1, lap_number=1))
    assert result is None


def test_lap_record_contains_car_fields():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(lap_number=1, car_class=4, car_ordinal=999))
    result = sm.on_packet(_make_packet(lap_number=2, car_class=4, car_ordinal=999))
    assert result.car_class_int == 4
    assert result.car_ordinal == 999


def test_lap_record_raw_telemetry_is_dict():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(lap_number=1))
    result = sm.on_packet(_make_packet(lap_number=2))
    assert isinstance(result.raw_telemetry, dict)


def test_reset_clears_laps_and_state():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(lap_number=1))
    sm.on_packet(_make_packet(lap_number=2))
    sm.reset()
    assert sm.laps == []
    # After reset, first packet should not trigger a lap
    result = sm.on_packet(_make_packet(lap_number=3))
    assert result is None


def test_zero_last_lap_is_ignored():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(lap_number=1))
    result = sm.on_packet(_make_packet(lap_number=2, last_lap=0.0))
    assert result is None
    assert sm.laps == []


def test_get_laps_snapshot_returns_copy():
    sm = session_manager.SessionManager()
    sm.on_packet(_make_packet(lap_number=1))
    sm.on_packet(_make_packet(lap_number=2))
    snapshot = sm.get_laps_snapshot()
    assert len(snapshot) == 1
    sm.reset()
    assert len(snapshot) == 1  # snapshot is independent of internal list
