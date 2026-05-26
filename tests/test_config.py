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
