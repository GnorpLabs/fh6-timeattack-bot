import pytest
from image_extractor import _parse_fields, ExtractionResult


_VEHICLES = ["2024 Toyota GR86", "2023 Honda Civic Type R", "2022 Subaru WRX STI"]


def test_parse_time_minutes_seconds_millis():
    result = _parse_fields("Result 1:23.456 Class A #1234", _VEHICLES)
    assert result.time_str == "1:23.456"


def test_parse_time_seconds_millis_only():
    result = _parse_fields("Result 58.120 Class A #1234", _VEHICLES)
    assert result.time_str == "58.120"


def test_parse_time_missing_returns_none():
    result = _parse_fields("No time here Class A #1234", _VEHICLES)
    assert result.time_str is None


def test_parse_class_exact_single_letter():
    result = _parse_fields("Class A 1:23.456", _VEHICLES)
    assert result.class_ == "A"


def test_parse_class_s1():
    result = _parse_fields("Class S1 1:23.456", _VEHICLES)
    assert result.class_ == "S1"


def test_parse_class_fuzzy_ocr_error_51_reads_as_s1():
    result = _parse_fields("Class 51 1:23.456", _VEHICLES)
    assert result.class_ == "S1"


def test_parse_class_missing_returns_none():
    result = _parse_fields("1:23.456 no class here", _VEHICLES)
    assert result.class_ is None


def test_parse_class_d1_is_not_a_class():
    result = _parse_fields("1:23.456 D1 #100", _VEHICLES)
    assert result.class_ is None


def test_parse_class_b1_is_not_a_class():
    result = _parse_fields("1:23.456 B1 #100", _VEHICLES)
    assert result.class_ is None


def test_parse_class_r1_is_not_a_class():
    result = _parse_fields("1:23.456 R1 #100", _VEHICLES)
    assert result.class_ is None


def test_parse_rank_with_hash():
    result = _parse_fields("1:23.456 Class A #1,234", _VEHICLES)
    assert result.global_rank == 1234


def test_parse_rank_without_hash():
    result = _parse_fields("1:23.456 Class A Rank 5678", _VEHICLES)
    assert result.global_rank == 5678


def test_parse_rank_missing_returns_none():
    result = _parse_fields("1:23.456 Class A no rank", _VEHICLES)
    assert result.global_rank is None


def test_parse_vehicle_exact_match():
    result = _parse_fields("2024 Toyota GR86 Class A 1:23.456 #100", _VEHICLES)
    assert result.vehicle == "2024 Toyota GR86"


def test_parse_vehicle_ocr_error_one_char_off():
    result = _parse_fields("2024 Toyota GR8B Class A 1:23.456 #100", _VEHICLES)
    assert result.vehicle == "2024 Toyota GR86"


def test_parse_vehicle_below_threshold_returns_none():
    result = _parse_fields("Class A 1:23.456 #100", _VEHICLES)
    assert result.vehicle is None


def test_parse_vehicle_empty_list_returns_none():
    result = _parse_fields("2024 Toyota GR86 Class A 1:23.456 #100", [])
    assert result.vehicle is None


def test_parse_fields_returns_extraction_result_dataclass():
    result = _parse_fields("2024 Toyota GR86 Class A 1:23.456 #100", _VEHICLES)
    assert isinstance(result, ExtractionResult)


from image_extractor import extract_from_image


def test_extract_from_image_delegates_to_parse_fields(monkeypatch):
    monkeypatch.setattr(
        "image_extractor._ocr",
        lambda data: "2024 Toyota GR86 A 1:23.456 #1234",
    )
    result = extract_from_image(b"fake", ["2024 Toyota GR86"])
    assert result.time_str == "1:23.456"
    assert result.class_ == "A"
    assert result.global_rank == 1234
    assert result.vehicle == "2024 Toyota GR86"


def test_extract_from_image_returns_all_none_on_ocr_failure(monkeypatch):
    def bad_ocr(_data):
        raise RuntimeError("tesseract not found")

    monkeypatch.setattr("image_extractor._ocr", bad_ocr)
    result = extract_from_image(b"fake", [])
    assert result.time_str is None
    assert result.class_ is None
    assert result.global_rank is None
    assert result.vehicle is None
