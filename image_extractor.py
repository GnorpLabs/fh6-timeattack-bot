import logging
import re
import tempfile
from dataclasses import dataclass

import numpy as np
from rapidfuzz import fuzz, process as fuzz_process

import config

_log = logging.getLogger(__name__)

_user_words_path: str | None = None


def _get_user_words_path(vehicle_names: list[str]) -> str | None:
    """Write unique words from vehicle names to a temp file for Tesseract --user-words.
    Cached for the process lifetime — vehicle list doesn't change at runtime."""
    global _user_words_path
    if not vehicle_names:
        return None
    if _user_words_path is None:
        words = sorted({
            word
            for name in vehicle_names
            for word in name.split()
            if len(word) >= 2
        } | set(config.CLASSES))
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        tmp.write("\n".join(words))
        tmp.close()
        _user_words_path = tmp.name
        _log.info("Wrote %d vehicle words to Tesseract user-words file: %s", len(words), _user_words_path)
    return _user_words_path


_TIME_RE = re.compile(r'\b(\d{1,2} *: *\d{2}\.\d{3}|\d{2}\.\d{3})\b')
_RANK_ORDINAL_RE = re.compile(r'\b(\d[\d,]*)(?:st|nd|rd|th)\b', re.IGNORECASE)
_SPLIT_MINS_RE = re.compile(r'\b(\d{1,2}),\s*$', re.MULTILINE)
_RANK_HASH_RE = re.compile(r'#\s*(\d[\d,]*)', re.IGNORECASE)
_RANK_WORD_RE = re.compile(r'rank\s+(\d[\d,]*)', re.IGNORECASE)
_TOP_PCT_RE = re.compile(r'top\s+(\d+(?:\.\d+)?)\s*%', re.IGNORECASE)

_OCR_S_FIX_RE = re.compile(r'[§$]([12])', re.IGNORECASE)

# Billboard background colour ranges per class, in OpenCV HSV (H:0-179, S:0-255, V:0-255).
# Each entry is a list of (lower, upper) pairs to handle hues that wrap (red).
# D and S2 share similar hues but are separated by brightness (V):
#   D (light blue): V ≥ 150   S2 (dark blue): V ≤ 130
# Ranges calibrated from class-icons-colors.png reference image (icon median H values):
#   X≈58  D≈97  C≈21  B≈10  A≈174  S1≈140  S2≈112
_CLASS_COLOR_HSV: dict[str, list[tuple[tuple, tuple]]] = {
    "D":  [((80,  30,  150), (118, 200, 255))],   # bright light blue / cyan (H median≈97)
    "C":  [((13,  80,  150), (35,  255, 255))],   # yellow (H median≈21)
    "B":  [((4,   130, 100), (22,  255, 255))],   # orange (H median≈10)
    "A":  [((0,   100, 60),  (8,   255, 255)),    # red – lower hue
           ((162, 100, 60),  (179, 255, 255))],   # red – upper hue (H median≈174)
    "S1": [((128, 40,  50),  (158, 255, 220))],   # purple (H median≈140)
    "S2": [((85,  50,  15),  (125, 200, 130))],   # dark blue (low V, H median≈112)
    "R":  [((148, 20,  100), (175, 160, 255))],   # pink
    "X":  [((43,  70,  40),  (72,  255, 220))],   # green (H median≈58)
}


@dataclass
class ExtractionResult:
    vehicle: str | None
    time_str: str | None
    class_: str | None
    global_rank: int | None
    rank_top_pct: float | None = None  # e.g. 3.0 for "Top 3%", set when rank > 10k


_COMMA_COLON_RE = re.compile(r'\b(\d{1,2}),(\d{2}\.\d{3})\b')


def _normalize_ocr_text(text: str) -> str:
    """Fix recurring Tesseract misreads before field parsing."""
    text = text.replace("§", "S")
    text = _OCR_S_FIX_RE.sub(r'S\1', text)  # $2 → S2, $1 → S1
    # "| * Class Leaderboard" — asterisk is OCR's reading of the X-class star icon.
    text = re.sub(r'\*(\s+class\s+leaderboard)', r'X\1', text, flags=re.IGNORECASE)
    # "ciass" / "ciess" — Tesseract reads "cl" as "ci" in the billboard font.
    text = re.sub(r'\bci[ae]ss\b', 'class', text, flags=re.IGNORECASE)
    # "Leaderbgard" — common transposition of "Leaderboard".
    text = re.sub(r'\bleaderbgard\b', 'leaderboard', text, flags=re.IGNORECASE)
    # Strip leading non-content characters from each line (pipe, quotes, dashes…).
    # Meaningful tokens start with a letter, digit, or '#'; everything before is noise.
    text = '\n'.join(re.sub(r'^[^a-zA-Z0-9#]+', '', line) for line in text.split('\n'))
    # Tesseract sometimes reads a time colon as a comma: "00,34.502" → "00:34.502".
    text = _COMMA_COLON_RE.sub(r'\1:\2', text)
    return text


def _parse_time(text: str) -> str | None:
    m = _TIME_RE.search(text)
    if not m:
        return None
    t = m.group(1).replace(' ', '')
    # If only the SS.mmm part was captured (no colon), look for a "MM," fragment on an
    # earlier line — Tesseract sometimes splits "00:56.023" as "00," then "56.023".
    if ':' not in t:
        mins_m = _SPLIT_MINS_RE.search(text[:m.start()])
        if mins_m:
            t = f"{mins_m.group(1)}:{t}"
    return t


def _parse_rank(text: str) -> tuple[int | None, float | None]:
    """Returns (global_rank, rank_top_pct). Exactly one will be non-None if rank was found."""
    m = _TOP_PCT_RE.search(text)
    if m:
        return None, float(m.group(1))
    # Try ordinal first (e.g. "3,597th") — more distinctive than a bare "#N".
    for pattern in (_RANK_ORDINAL_RE, _RANK_HASH_RE, _RANK_WORD_RE):
        m = pattern.search(text)
        if m:
            raw = m.group(1).replace(",", "")
            try:
                return int(raw), None
            except ValueError:
                pass
    return None, None


_CLASS_ALIASES: dict[str, str] = {
    "51": "S1",
    "52": "S2",
    # "SI" / "S!" removed — too noisy, fires on common words and usernames
}


_CLASS_LEADERBOARD_RE = re.compile(
    r'\b[a-z]?(D|C|B|A|S1|52|51|S2|R|X)\W+class\s+leaderboard\b',
    re.IGNORECASE,
)
_CLASS_LABEL_RE = re.compile(
    r'\bclass\s*[:\-]?\s*(D|C|B|A|S1|52|51|S2|R|X)\b'  # "Class: A", "Class 51"
    r'|\b(D|C|B|A|S1|52|51|S2|R|X)\s+class\b',          # "A Class", "51 Class"
    re.IGNORECASE,
)


def _resolve_class_token(token: str) -> str | None:
    t = token.upper()
    if t in config.CLASSES:
        return t
    return _CLASS_ALIASES.get(t)


def _parse_class(text: str) -> str | None:
    # 1. "S2 Class Leaderboard" — the definitive FH6 UI anchor, always present.
    m = _CLASS_LEADERBOARD_RE.search(text)
    if m:
        return _resolve_class_token(m.group(1))

    # 2. Other explicit label forms ("Class: A", "A Class") as a fallback.
    m = _CLASS_LABEL_RE.search(text)
    if m:
        return _resolve_class_token(m.group(1) or m.group(2))

    # 3. Last resort: standalone multi-char class token (S1, S2 only).
    # Single-letter classes are too common in OCR noise.
    # Digit aliases (51→S1, 52→S2) are intentionally excluded here — they
    # fire on lap-time digits like "00:52.396"; those aliases are handled
    # by _CLASS_LEADERBOARD_RE and _CLASS_LABEL_RE where context is enforced.
    for token in re.split(r'\W+', text.upper()):
        if len(token) >= 2 and token in config.CLASSES:
            return token
    return None


def _parse_vehicle(text: str, vehicle_names: list[str]) -> str | None:
    if not vehicle_names:
        return None
    best_name: str | None = None
    best_score: float = 75.0
    for line in re.split(r'\n+', text):
        line = line.strip()
        if len(line) < 8:  # skip short noise; real vehicle fragments are at least 8 chars
            continue
        result = fuzz_process.extractOne(
            line, vehicle_names, scorer=fuzz.token_set_ratio,
            score_cutoff=best_score, processor=str.casefold,
        )
        if result and result[1] > best_score:
            best_name, best_score = result[0], result[1]
    return best_name


def _parse_fields(raw_text: str, vehicle_names: list[str]) -> ExtractionResult:
    text = _normalize_ocr_text(raw_text)
    global_rank, rank_top_pct = _parse_rank(text)
    return ExtractionResult(
        vehicle=_parse_vehicle(text, vehicle_names),
        time_str=_parse_time(text),
        class_=_parse_class(text),
        global_rank=global_rank,
        rank_top_pct=rank_top_pct,
    )


def _detect_class_from_color(img_bgr: np.ndarray) -> str | None:
    """Detect class from billboard background colour when OCR text parsing fails.

    Each FH6 class has a distinct background colour. We count only vivid,
    non-dark pixels (S > 60, V > 100) so that desaturated vegetation and dark
    backgrounds don't interfere.  The winner must also be ≥ 1.5× the second-best
    count — close-up billboard shots have a dominant colour; complex scenes with
    small billboards don't and should return None rather than guess wrong.
    """
    import cv2
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    vivid = (hsv[:, :, 1] > 60) & (hsv[:, :, 2] > 100)
    vivid_count = int(np.sum(vivid))
    if vivid_count == 0:
        return None

    all_counts: list[int] = []
    best_class: str | None = None
    best_count = 0
    for cls, ranges in _CLASS_COLOR_HSV.items():
        mask = np.zeros(hsv.shape[:2], dtype=bool)
        for lower, upper in ranges:
            m = cv2.inRange(hsv, np.array(lower, dtype=np.uint8), np.array(upper, dtype=np.uint8))
            mask |= m.astype(bool)
        count = int(np.sum(mask & vivid))
        all_counts.append(count)
        if count > best_count:
            best_count = count
            best_class = cls

    if best_count < vivid_count * 0.05:
        return None
    # Require the dominant class to be ≥ 1.5× the second-best; complex game
    # scenes (vegetation, taillights) produce several competing colours — the
    # billboard background is only decisive in close-up shots.
    second_best = sorted(all_counts)[-2] if len(all_counts) > 1 else 0
    if second_best > 0 and best_count < second_best * 1.5:
        return None
    return best_class


def _bright_bg_text_mask(img_bgr: np.ndarray, scale: int = 3) -> np.ndarray:
    """Build a black-text-on-white image for bright-background billboards.

    Instead of Otsu (which fails when text and background are both bright),
    we isolate white and yellow text by colour, then invert so Tesseract
    sees dark text on a white field.
    """
    import cv2
    img = cv2.resize(img_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    b, g, r = cv2.split(img.astype(np.int16))

    # White / near-white text: all channels high and colour-balanced
    white = (r > 200) & (g > 200) & (b > 200) & (np.abs(r - b) < 70)
    # Orange / warm text (lap-time display): R dominates B regardless of absolute B level.
    # D-class billboards use cream-orange text with B≈158, so "b < 120" is too strict.
    yellow = (r > 160) & (g > 100) & (r - b > 60)

    text_pixels = (white | yellow).astype(np.uint8)
    # text → 0 (black for Tesseract), background → 255 (white)
    result = np.where(text_pixels, np.uint8(0), np.uint8(255))

    # Slight erosion to thicken thin strokes
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    return cv2.erode(result, kernel, iterations=1)


def _ocr(image_bytes: bytes, vehicle_names: list[str]) -> str:
    import cv2
    import pytesseract

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(
            f"cv2.imdecode failed — image data may be truncated or corrupt "
            f"({len(image_bytes)} bytes received)"
        )

    # Grayscale BEFORE resize: interpolating in grayscale avoids colour-channel
    # interactions that can flip ambiguous digits (e.g. "1" → "7").
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if float(np.mean(gray)) > 110:
        # Bright-background billboard (D/C/B/R/X classes): white and yellow text
        # on a coloured background.  Otsu fails here; use colour separation instead.
        thresh = _bright_bg_text_mask(img, scale=3)
    else:
        # Dark-background billboard: standard Otsu + adaptive polarity correction.
        # CLAHE removed — it amplifies background noise in game screenshots.
        gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Invert when result is dark-dominant (white text on black → flip for Tesseract).
        if float(cv2.mean(thresh)[0]) < 128:
            thresh = cv2.bitwise_not(thresh)

    tess_config = "--psm 11"
    user_words = _get_user_words_path(vehicle_names)
    if user_words:
        tess_config += f" --user-words {user_words}"
    return pytesseract.image_to_string(thresh, config=tess_config)


def extract_from_image(
    image_bytes: bytes,
    vehicle_names: list[str] | None = None,
) -> ExtractionResult:
    if vehicle_names is None:
        vehicle_names = config.get_vehicle_names()
    try:
        raw_text = _ocr(image_bytes, vehicle_names)
        _log.info("OCR raw text: %r", raw_text)
    except Exception as exc:
        _log.warning("OCR failed: %s", exc)
        raw_text = ""

    result = _parse_fields(raw_text, vehicle_names)

    # Class fallback: if OCR couldn't read the class text, detect it from the
    # billboard's background colour (each FH6 class has a distinct colour).
    if result.class_ is None:
        import cv2
        try:
            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                detected = _detect_class_from_color(img)
                if detected:
                    _log.info("Class detected from colour: %s", detected)
                    result = ExtractionResult(
                        vehicle=result.vehicle,
                        time_str=result.time_str,
                        class_=detected,
                        global_rank=result.global_rank,
                        rank_top_pct=result.rank_top_pct,
                    )
        except Exception as exc:
            _log.warning("Colour-based class detection failed: %s", exc)

    return result
