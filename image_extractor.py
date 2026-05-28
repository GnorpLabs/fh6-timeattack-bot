import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process as fuzz_process

import config

_TIME_RE = re.compile(r'\b(\d{1,2}:\d{2}\.\d{3}|\d{2}\.\d{3})\b')
_RANK_RE = re.compile(r'#\s*(\d[\d,]*)|rank\s+(\d[\d,]*)', re.IGNORECASE)


@dataclass
class ExtractionResult:
    vehicle: str | None
    time_str: str | None
    class_: str | None
    global_rank: int | None


def _parse_time(text: str) -> str | None:
    m = _TIME_RE.search(text)
    return m.group(1) if m else None


def _parse_rank(text: str) -> int | None:
    m = _RANK_RE.search(text)
    if not m:
        return None
    raw = (m.group(1) or m.group(2)).replace(",", "")
    try:
        return int(raw)
    except ValueError:
        return None


_CLASS_ALIASES: dict[str, str] = {
    "51": "S1",
    "52": "S2",
    "SI": "S1",
    "S!": "S1",
}


def _parse_class(text: str) -> str | None:
    for token in re.split(r'\W+', text.upper()):
        if token in config.CLASSES:
            return token
    for token in re.split(r'\W+', text.upper()):
        if token in _CLASS_ALIASES:
            return _CLASS_ALIASES[token]
    return None


def _parse_vehicle(text: str, vehicle_names: list[str]) -> str | None:
    if not vehicle_names:
        return None
    result = fuzz_process.extractOne(
        text, vehicle_names, scorer=fuzz.partial_ratio, score_cutoff=75
    )
    return result[0] if result else None


def _parse_fields(raw_text: str, vehicle_names: list[str]) -> ExtractionResult:
    return ExtractionResult(
        vehicle=_parse_vehicle(raw_text, vehicle_names),
        time_str=_parse_time(raw_text),
        class_=_parse_class(raw_text),
        global_rank=_parse_rank(raw_text),
    )


def _ocr(image_bytes: bytes) -> str:
    import cv2
    import numpy as np
    import pytesseract

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return pytesseract.image_to_string(thresh, config="--psm 6")


def extract_from_image(
    image_bytes: bytes,
    vehicle_names: list[str] | None = None,
) -> ExtractionResult:
    if vehicle_names is None:
        vehicle_names = config.get_vehicle_names()
    try:
        raw_text = _ocr(image_bytes)
    except Exception:
        raw_text = ""
    return _parse_fields(raw_text, vehicle_names)
