import pytest
from image_extractor import _parse_fields, ExtractionResult


_VEHICLES = ["2024 Toyota GR86", "2023 Honda Civic Type R", "2022 Subaru WRX STI"]


def test_parse_time_minutes_seconds_millis():
    result = _parse_fields("Result 1:23.456 Class A #1234", _VEHICLES)
    assert result.time_str == "1:23.456"


def test_parse_time_seconds_millis_only():
    result = _parse_fields("Result 58.120 Class A #1234", _VEHICLES)
    assert result.time_str == "58.120"


def test_parse_time_ocr_space_after_colon():
    # OCR sometimes inserts a space after ":" — e.g. "00: 34.502". Normalise it.
    result = _parse_fields("00: 34.502 B Class Leaderboard #1288", _VEHICLES)
    assert result.time_str == "00:34.502"


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


def test_parse_class_context_class_colon():
    result = _parse_fields("Class: S1 1:23.456", _VEHICLES)
    assert result.class_ == "S1"


def test_parse_class_context_label_before():
    result = _parse_fields("S1 Class 1:23.456", _VEHICLES)
    assert result.class_ == "S1"


def test_parse_class_leaderboard_anchor():
    result = _parse_fields("1:23.456 S1 Class Leaderboard #100", _VEHICLES)
    assert result.class_ == "S1"


def test_parse_class_leaderboard_single_letter():
    result = _parse_fields("1:23.456 A Class Leaderboard #100", _VEHICLES)
    assert result.class_ == "A"


def test_parse_class_leaderboard_anchor_beats_earlier_noise():
    # Letters "A" and "C" appear elsewhere in the text; "B Class Leaderboard" is the true class
    result = _parse_fields("A C 1:23.456 B Class Leaderboard #100", _VEHICLES)
    assert result.class_ == "B"


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
    assert result.rank_top_pct is None


def test_parse_rank_top_pct_integer():
    result = _parse_fields("1:23.456 Class A Top 3%", _VEHICLES)
    assert result.global_rank is None
    assert result.rank_top_pct == 3.0


def test_parse_rank_top_pct_decimal():
    result = _parse_fields("1:23.456 Class A Top 12.5%", _VEHICLES)
    assert result.global_rank is None
    assert result.rank_top_pct == 12.5


def test_parse_rank_top_pct_case_insensitive():
    result = _parse_fields("1:23.456 Class A TOP 1%", _VEHICLES)
    assert result.rank_top_pct == 1.0


def test_parse_rank_top_pct_takes_priority_over_hash():
    # "Top X%" should win even if a bare # appears elsewhere in text
    result = _parse_fields("Top 5% Player #99 1:23.456", _VEHICLES)
    assert result.rank_top_pct == 5.0
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


def test_parse_rank_ordinal_th():
    result = _parse_fields("1:23.456 Class A 3,597th", _VEHICLES)
    assert result.global_rank == 3597
    assert result.rank_top_pct is None


def test_parse_rank_ordinal_small_th():
    result = _parse_fields("1:23.456 Class A 4,078th", _VEHICLES)
    assert result.global_rank == 4078


def test_parse_rank_ordinal_st():
    result = _parse_fields("1:23.456 Class A 1st", _VEHICLES)
    assert result.global_rank == 1


def test_parse_rank_ordinal_nd():
    result = _parse_fields("1:23.456 Class A 2nd", _VEHICLES)
    assert result.global_rank == 2


def test_parse_rank_ordinal_rd():
    result = _parse_fields("1:23.456 Class A 3rd", _VEHICLES)
    assert result.global_rank == 3


def test_parse_rank_top_pct_beats_ordinal():
    # "Top X%" should still win even when an ordinal also appears
    result = _parse_fields("Top 3% Player 1st 1:23.456", _VEHICLES)
    assert result.rank_top_pct == 3.0
    assert result.global_rank is None


def test_parse_rank_ordinal_beats_hash_noise():
    # Ordinal format must win over a noise "#N" that appears earlier in the text
    result = _parse_fields("1:23.456 Class A noise #5 junk 4,078th", _VEHICLES)
    assert result.global_rank == 4078


def test_normalize_dollar_s2():
    # "$2 Class Leaderboard" (Tesseract S→$) should resolve to S2
    result = _parse_fields("$2 Class Leaderboard 1:23.456 #100", _VEHICLES)
    assert result.class_ == "S2"


def test_normalize_section_s2():
    # "§2 Class Leaderboard" (Tesseract S→§) should resolve to S2
    result = _parse_fields("§2 Class Leaderboard 1:23.456 #100", _VEHICLES)
    assert result.class_ == "S2"


_TA_VEHICLES = ["1986 MG Metro 6R4", "2001 Honda #33 Integra WTAC", "2015 Radical RXC Turbo"]

# Simulated OCR text for each test image, based on the visual content.
_TA1_OCR = "A Class Leaderboard\nWhiteAmigo6608\n01:06.101\n3,597th\nMG METRO 6R4\nsirkinkington"
_TA2_OCR = "$2 Class Leaderboard\nWhiteAmigo6608\n00:54.492\n4,078th\n#33 H. INTEGRA"
_TATOP_OCR = "S2 Class Leaderboard\nWhiteAmigo6608\n00:41.602\nTop 3%\nRADICAL RXC"


def test_ta1_time():
    assert _parse_fields(_TA1_OCR, _TA_VEHICLES).time_str == "01:06.101"


def test_ta1_class():
    assert _parse_fields(_TA1_OCR, _TA_VEHICLES).class_ == "A"


def test_ta1_rank():
    assert _parse_fields(_TA1_OCR, _TA_VEHICLES).global_rank == 3597


def test_ta1_vehicle():
    assert _parse_fields(_TA1_OCR, _TA_VEHICLES).vehicle == "1986 MG Metro 6R4"


def test_ta2_time():
    assert _parse_fields(_TA2_OCR, _TA_VEHICLES).time_str == "00:54.492"


def test_ta2_class():
    assert _parse_fields(_TA2_OCR, _TA_VEHICLES).class_ == "S2"


def test_ta2_rank():
    assert _parse_fields(_TA2_OCR, _TA_VEHICLES).global_rank == 4078


def test_ta2_vehicle():
    assert _parse_fields(_TA2_OCR, _TA_VEHICLES).vehicle == "2001 Honda #33 Integra WTAC"


def test_tatop_rank_top_pct():
    r = _parse_fields(_TATOP_OCR, _TA_VEHICLES)
    assert r.global_rank is None
    assert r.rank_top_pct == 3.0


def test_tatop_vehicle():
    assert _parse_fields(_TATOP_OCR, _TA_VEHICLES).vehicle == "2015 Radical RXC Turbo"


from image_extractor import extract_from_image


def test_parse_time_comma_as_colon():
    # Tesseract sometimes reads "00:34.502" as "00,34.502"
    result = _parse_fields("00,34.502 R Class Leaderboard #1288", _VEHICLES)
    assert result.time_str == "00:34.502"


def test_normalize_strips_leading_pipe_noise():
    # "| A Class Leaderboard" — pipe and space before class token
    result = _parse_fields("| A Class Leaderboard\n1:23.456\n#1234", _VEHICLES)
    assert result.class_ == "A"
    assert result.time_str == "1:23.456"
    assert result.global_rank == 1234


def test_normalize_strips_leading_quote_noise():
    # "' 00:34.502" — leading apostrophe on a time line (seen in ta-6 OCR)
    result = _parse_fields("R Class Leaderboard\n' 00:34.502\n#1288", _VEHICLES)
    assert result.time_str == "00:34.502"


def test_parse_class_leaderboard_noise_before_class():
    # ta-4: "a 'Class Leaderboard" — apostrophe between class token and keyword
    result = _parse_fields("a 'Class Leaderboard 56.023 #2432", _VEHICLES)
    assert result.class_ == "A"


def test_parse_class_leaderboard_noise_prefix_and_punctuation():
    # ta-6: "| dR. Class Leaderboard" — noise word 'd' prefix, period separator
    result = _parse_fields("| dR. Class Leaderboard 00:34.502 #1288", _VEHICLES)
    assert result.class_ == "R"


def test_normalize_asterisk_is_x_class():
    # ta-7: "| * Class Leaderboard" — asterisk is OCR's read of the X-class icon
    result = _parse_fields("| * Class Leaderboard\n00:37.643\nTop 8%\n#32 SKYLINE", _VEHICLES)
    assert result.class_ == "X"
    assert result.time_str == "00:37.643"
    assert result.rank_top_pct == 8.0


def test_normalize_ciass_to_class():
    # ta-11: "GBM ciass Leaderboard" — "class" misread as "ciass" in billboard font
    result = _parse_fields("B ciass Leaderboard\n1:23.456\n#100", _VEHICLES)
    assert result.class_ == "B"


def test_normalize_ciess_to_class():
    # ta-10/13: "ciess" variant of the same misread
    result = _parse_fields("R ciess Leaderboard\n1:23.456\n#100", _VEHICLES)
    assert result.class_ == "R"


def test_normalize_leaderbgard_to_leaderboard():
    # ta-20: "Leaderbgard" — transposed letter
    result = _parse_fields("| || Class Leaderbgard\n01:06.171\n5,043rd", _VEHICLES)
    assert result.time_str == "01:06.171"
    assert result.global_rank == 5043


def test_parse_rank_ordinal_requires_word_boundary():
    # ta-20: "6B O43rd" — OCR noise before the digits; must not extract 43 as rank
    result = _parse_fields("A Class Leaderboard\n01:06.171\n6B O43rd\nVOLVO 242", _VEHICLES)
    assert result.global_rank is None


def test_parse_time_minutes_on_preceding_line():
    # ta-4: Tesseract sometimes splits "00:56.023" as "00," on one line, "56.023" later
    result = _parse_fields("A Class Leaderboard\n00,\nnoise\n56.023\n#2432", _VEHICLES)
    assert result.time_str == "00:56.023"


def test_no_false_s1_from_si_in_username():
    # ta-13: "Si" in a username ("Serenagnyent\nSi") must not trigger S1 detection
    result = _parse_fields("FRB ciess Leaderboard\nSerenagnyent\nSi\n00:52.396\n#8484", _VEHICLES)
    assert result.class_ is None  # class letter is garbled; no false positive


# Simulated OCR strings for newer training images (reflect actual Tesseract output)
_TA7_OCR = "| * Class Leaderboard\nResets in 1p 12H 31M\nVWS SoHo\n00:37.643\nTop 8%\n#32 SKYLINE WTAC"
_TA8_OCR = "B Class Leaderboard\ngosets in 6D 16H 43m\nWhiteAmigo6608\n00:56.516\n4,120th\nHONDA S2000"
_TA9_OCR = "X Class L\neaderboard\n0:40.205\n8,740th\nJJM SUPRA WTAC"
_TA14_OCR = "R Class Leaderboard\nResets in 5b Oh 2eny\nWhiteAmigo6608\n00:39.077\n4,406th\nTACOMA FE"
_TA15_OCR = "S2 Class Leaderboard\nResets in 6D 16H 25M\nWhiteAmigo6608\n00:45.648\nTop 43%\nARIEL ATOM"

_TA_VEHICLES2 = [
    "1986 MG Metro 6R4", "2001 Honda #33 Integra WTAC", "2015 Radical RXC Turbo",
    "#32 Nissan Skyline WTAC", "Honda S2000", "JJM Toyota Supra WTAC",
    "Toyota Tacoma FE", "Ariel Atom",
]


def test_ta7_class():
    assert _parse_fields(_TA7_OCR, _TA_VEHICLES2).class_ == "X"


def test_ta7_time():
    assert _parse_fields(_TA7_OCR, _TA_VEHICLES2).time_str == "00:37.643"


def test_ta7_rank():
    assert _parse_fields(_TA7_OCR, _TA_VEHICLES2).rank_top_pct == 8.0


def test_ta8_class():
    assert _parse_fields(_TA8_OCR, _TA_VEHICLES2).class_ == "B"


def test_ta8_time():
    assert _parse_fields(_TA8_OCR, _TA_VEHICLES2).time_str == "00:56.516"


def test_ta8_rank():
    assert _parse_fields(_TA8_OCR, _TA_VEHICLES2).global_rank == 4120


def test_ta9_class():
    assert _parse_fields(_TA9_OCR, _TA_VEHICLES2).class_ == "X"


def test_ta9_time():
    assert _parse_fields(_TA9_OCR, _TA_VEHICLES2).time_str == "0:40.205"


def test_ta9_rank():
    assert _parse_fields(_TA9_OCR, _TA_VEHICLES2).global_rank == 8740


def test_ta14_class():
    assert _parse_fields(_TA14_OCR, _TA_VEHICLES2).class_ == "R"


def test_ta14_time():
    assert _parse_fields(_TA14_OCR, _TA_VEHICLES2).time_str == "00:39.077"


def test_ta14_rank():
    assert _parse_fields(_TA14_OCR, _TA_VEHICLES2).global_rank == 4406


def test_ta15_class():
    assert _parse_fields(_TA15_OCR, _TA_VEHICLES2).class_ == "S2"


def test_ta15_time():
    assert _parse_fields(_TA15_OCR, _TA_VEHICLES2).time_str == "00:45.648"


def test_ta15_rank():
    assert _parse_fields(_TA15_OCR, _TA_VEHICLES2).rank_top_pct == 43.0


def test_extract_from_image_delegates_to_parse_fields(monkeypatch):
    monkeypatch.setattr(
        "image_extractor._ocr",
        lambda data, names: "2024 Toyota GR86 A Class Leaderboard 1:23.456 #1234",
    )
    result = extract_from_image(b"fake", ["2024 Toyota GR86"])
    assert result.time_str == "1:23.456"
    assert result.class_ == "A"
    assert result.global_rank == 1234
    assert result.vehicle == "2024 Toyota GR86"


def test_extract_from_image_returns_all_none_on_ocr_failure(monkeypatch):
    def bad_ocr(_data, _names):
        raise RuntimeError("tesseract not found")

    monkeypatch.setattr("image_extractor._ocr", bad_ocr)
    result = extract_from_image(b"fake", [])
    assert result.time_str is None
    assert result.class_ is None
    assert result.global_rank is None
    assert result.vehicle is None
