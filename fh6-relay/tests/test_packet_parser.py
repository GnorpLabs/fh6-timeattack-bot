import struct
import packet_parser


def _make_packet(**overrides) -> bytes:
    """Build a minimal valid 324-byte FH6 packet. All fields default to 0."""
    data = bytearray(324)
    fields = {
        "is_race_on": (0, "<i"),
        "car_ordinal": (212, "<i"),
        "car_class": (216, "<i"),
        "best_lap": (296, "<f"),
        "last_lap": (300, "<f"),
        "current_lap": (304, "<f"),
        "current_race_time": (308, "<f"),
        "lap_number": (312, "<H"),
        "race_position": (314, "<B"),
    }
    for name, (offset, fmt) in fields.items():
        value = overrides.get(name, 0)
        struct.pack_into(fmt, data, offset, value)
    return bytes(data)


def test_parse_packet_returns_dataclass_for_valid_packet():
    pkt = _make_packet(is_race_on=1, lap_number=3, last_lap=83.456)
    result = packet_parser.parse_packet(pkt)
    assert result is not None
    assert result.is_race_on == 1
    assert result.lap_number == 3
    assert abs(result.last_lap - 83.456) < 0.001


def test_parse_packet_returns_none_for_wrong_size():
    assert packet_parser.parse_packet(b"\x00" * 100) is None
    assert packet_parser.parse_packet(b"\x00" * 325) is None


def test_parse_packet_car_class_extracted():
    pkt = _make_packet(car_class=3)
    result = packet_parser.parse_packet(pkt)
    assert result.car_class == 3


def test_parse_packet_car_ordinal_extracted():
    pkt = _make_packet(car_ordinal=5678)
    result = packet_parser.parse_packet(pkt)
    assert result.car_ordinal == 5678


def test_parse_packet_race_position_extracted():
    pkt = _make_packet(race_position=2)
    result = packet_parser.parse_packet(pkt)
    assert result.race_position == 2
