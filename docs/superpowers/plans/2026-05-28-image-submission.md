# Image-Only Submission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `/submit` slash command with an image-only flow that OCRs vehicle, time, class, and global rank from a screenshot, shows an ephemeral confirmation, and falls back to a pre-filled modal when extraction is incomplete.

**Architecture:** A new `image_extractor.py` module handles all OCR logic (preprocessing via OpenCV, Tesseract, and rapidfuzz post-processing) and is fully tested without Discord. `cogs/submission.py` gains a `ConfirmView` (two buttons) and a `SubmissionModal` (four text inputs) to handle the confirmation/edit flow. The existing manual command is renamed `/submit-manual`.

**Tech Stack:** `pytesseract`, `opencv-python-headless`, `rapidfuzz`, `discord.py` UI components, SQLite migration

---

### Task 1: Database — add `global_rank` column

**Files:**
- Modify: `database.py`
- Modify: `tests/test_database.py`

- [ ] **Step 1: Write failing tests**

Add to the bottom of `tests/test_database.py`:

```python
def test_add_entry_stores_global_rank(fresh_db):
    entry_id = database.add_entry(
        "111", "Alice", "Hokubu Circuit", "2024 Toyota GR86", "A", 83456,
        global_rank=42,
    )
    entry = database.get_entry(entry_id)
    assert entry["global_rank"] == 42


def test_add_entry_global_rank_defaults_to_none(fresh_db):
    entry_id = database.add_entry("111", "Alice", "Hokubu Circuit", "2024 Toyota GR86", "A", 83456)
    entry = database.get_entry(entry_id)
    assert entry["global_rank"] is None


def test_init_db_migrates_missing_global_rank(tmp_path, monkeypatch):
    import sqlite3
    db = tmp_path / "no_rank.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE time_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT NOT NULL, username TEXT NOT NULL,
            track TEXT NOT NULL, vehicle TEXT NOT NULL, class TEXT NOT NULL,
            lap_time_ms INTEGER NOT NULL, screenshot_path TEXT,
            submitted_at TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual', raw_telemetry TEXT
        )
    """)
    conn.execute(
        "INSERT INTO time_entries (discord_id, username, track, vehicle, class, "
        "lap_time_ms, submitted_at) VALUES ('1','Alice','T','V','A',1000,'2026-01-01')"
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(config, "DB_PATH", db)
    database.init_db()

    conn = sqlite3.connect(db)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(time_entries)")}
    row = conn.execute("SELECT global_rank FROM time_entries WHERE discord_id='1'").fetchone()
    conn.close()

    assert "global_rank" in cols
    assert row[0] is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/gnorplabs/GnorpLabs/fh6-timeattack-bot
pytest tests/test_database.py::test_add_entry_stores_global_rank \
       tests/test_database.py::test_add_entry_global_rank_defaults_to_none \
       tests/test_database.py::test_init_db_migrates_missing_global_rank -v
```

Expected: FAIL with `TypeError: add_entry() got an unexpected keyword argument 'global_rank'` and similar.

- [ ] **Step 3: Update `_migrate_time_entries_if_needed` in `database.py`**

Replace the entire `_migrate_time_entries_if_needed` function:

```python
def _migrate_time_entries_if_needed(conn: sqlite3.Connection) -> None:
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='time_entries'"
    ).fetchone() is not None

    if not table_exists:
        conn.execute("DROP TABLE IF EXISTS time_entries_v2")
        conn.execute("""
            CREATE TABLE time_entries (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id       TEXT    NOT NULL,
                username         TEXT    NOT NULL,
                track            TEXT    NOT NULL,
                vehicle          TEXT    NOT NULL,
                class            TEXT    NOT NULL,
                lap_time_ms      INTEGER NOT NULL,
                screenshot_path  TEXT,
                submitted_at     TEXT    NOT NULL,
                source           TEXT    NOT NULL DEFAULT 'manual',
                raw_telemetry    TEXT,
                global_rank      INTEGER
            )
        """)
        return

    cols = {row[1] for row in conn.execute("PRAGMA table_info(time_entries)")}

    if "source" not in cols or "raw_telemetry" not in cols:
        conn.execute("DROP TABLE IF EXISTS time_entries_v2")
        conn.execute("""
            CREATE TABLE time_entries_v2 (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id       TEXT    NOT NULL,
                username         TEXT    NOT NULL,
                track            TEXT    NOT NULL,
                vehicle          TEXT    NOT NULL,
                class            TEXT    NOT NULL,
                lap_time_ms      INTEGER NOT NULL,
                screenshot_path  TEXT,
                submitted_at     TEXT    NOT NULL,
                source           TEXT    NOT NULL DEFAULT 'manual',
                raw_telemetry    TEXT,
                global_rank      INTEGER
            )
        """)
        conn.execute("""
            INSERT INTO time_entries_v2
                (id, discord_id, username, track, vehicle, class,
                 lap_time_ms, screenshot_path, submitted_at)
            SELECT id, discord_id, username, track, vehicle, class,
                   lap_time_ms, screenshot_path, submitted_at
            FROM time_entries
        """)
        conn.execute("DROP TABLE time_entries")
        conn.execute("ALTER TABLE time_entries_v2 RENAME TO time_entries")
        return  # global_rank already included in v2 CREATE TABLE

    if "global_rank" not in cols:
        conn.execute("ALTER TABLE time_entries ADD COLUMN global_rank INTEGER")
```

- [ ] **Step 4: Update `add_entry` in `database.py`**

Replace the `add_entry` function signature and body:

```python
def add_entry(
    discord_id: str,
    username: str,
    track: str,
    vehicle: str,
    class_: str,
    lap_time_ms: int,
    screenshot_path: str | None = None,
    source: str = "manual",
    raw_telemetry: str | None = None,
    global_rank: int | None = None,
) -> int:
    submitted_at = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    try:
        with conn:
            cur = conn.execute(
                """INSERT INTO time_entries
                   (discord_id, username, track, vehicle, class, lap_time_ms,
                    screenshot_path, submitted_at, source, raw_telemetry, global_rank)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (discord_id, username, track, vehicle, class_, lap_time_ms,
                 screenshot_path, submitted_at, source, raw_telemetry, global_rank),
            )
            return cur.lastrowid
    finally:
        conn.close()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_database.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git checkout -b feat/image-submission
git add database.py tests/test_database.py
git commit -m "feat(db): add global_rank column with migration"
```

---

### Task 2: Add OCR dependencies

**Files:**
- Modify: `requirements.txt`
- Modify: `Dockerfile`

- [ ] **Step 1: Update `requirements.txt`**

Replace the file contents:

```
discord.py>=2.3.2,<3.0.0
python-dotenv>=1.0.0,<2.0.0
aiohttp>=3.9.0,<4.0.0
pytesseract>=0.3.10,<1.0.0
opencv-python-headless>=4.8.0,<5.0.0
rapidfuzz>=3.0.0,<4.0.0
Pillow>=10.0.0,<12.0.0
pytest>=7.4.0,<8.0.0
pytest-asyncio>=0.23.0,<1.0.0
```

- [ ] **Step 2: Update `Dockerfile` to install `tesseract-ocr` system package**

Replace the file contents:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data /app/screenshots

RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser
CMD ["python", "bot.py"]
```

- [ ] **Step 3: Install dependencies locally**

```bash
pip install pytesseract opencv-python-headless "rapidfuzz>=3.0.0,<4.0.0" "Pillow>=10.0.0,<12.0.0"
```

Expected: packages install without errors. (Tesseract binary itself is only required at runtime — tests will mock it.)

- [ ] **Step 4: Commit**

```bash
git add requirements.txt Dockerfile
git commit -m "chore: add tesseract, opencv, rapidfuzz dependencies"
```

---

### Task 3: `image_extractor.py` — text parsing logic

**Files:**
- Create: `image_extractor.py`
- Create: `tests/test_image_extractor.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_image_extractor.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_image_extractor.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'image_extractor'`.

- [ ] **Step 3: Create `image_extractor.py` with data types and parsing functions**

```python
import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process as fuzz_process

import config

_TIME_RE = re.compile(r'\b(\d{1,2}:\d{2}\.\d{3}|\d{2}\.\d{3})\b')
_RANK_RE = re.compile(r'#\s*(\d[\d,]*)|[Rr]ank\s+(\d[\d,]*)')


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


def _parse_class(text: str) -> str | None:
    for token in re.split(r'\W+', text.upper()):
        if token in config.CLASSES:
            return token
    for token in re.split(r'\W+', text.upper()):
        if not token:
            continue
        result = fuzz_process.extractOne(token, config.CLASSES, score_cutoff=80)
        if result:
            return result[0]
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_image_extractor.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add image_extractor.py tests/test_image_extractor.py
git commit -m "feat: add image_extractor text parsing logic"
```

---

### Task 4: `image_extractor.py` — OCR pipeline

**Files:**
- Modify: `image_extractor.py`
- Modify: `tests/test_image_extractor.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_image_extractor.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_image_extractor.py::test_extract_from_image_delegates_to_parse_fields \
       tests/test_image_extractor.py::test_extract_from_image_returns_all_none_on_ocr_failure -v
```

Expected: FAIL with `ImportError: cannot import name 'extract_from_image'`.

- [ ] **Step 3: Add `_ocr` and `extract_from_image` to `image_extractor.py`**

Append to the bottom of `image_extractor.py` (after the existing functions):

```python
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
```

- [ ] **Step 4: Run all image extractor tests**

```bash
pytest tests/test_image_extractor.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add image_extractor.py tests/test_image_extractor.py
git commit -m "feat: add OCR pipeline to image_extractor"
```

---

### Task 5: Rename `/submit` to `/submit-manual`

**Files:**
- Modify: `cogs/submission.py`

- [ ] **Step 1: Rename the command in `cogs/submission.py`**

In `cogs/submission.py`, change line 18:

```python
# Before
@app_commands.command(name="submit", description="Submit a time attack lap time")

# After
@app_commands.command(name="submit-manual", description="Submit a time attack lap time (manual entry)")
```

Leave all other logic untouched.

- [ ] **Step 2: Run existing tests to confirm nothing is broken**

```bash
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add cogs/submission.py
git commit -m "feat: rename /submit to /submit-manual"
```

---

### Task 6: Add `ConfirmView` and `SubmissionModal` to `cogs/submission.py`

**Files:**
- Modify: `cogs/submission.py`

- [ ] **Step 1: Add imports at the top of `cogs/submission.py`**

Add these imports below the existing imports:

```python
from image_extractor import ExtractionResult
from utils import format_lap_time, parse_lap_time  # already imported — no change needed
```

Ensure `add_entry` is already imported from `database`. (It is — no change needed.)

- [ ] **Step 2: Add `_build_success_embed` helper before the `SubmissionCog` class**

```python
def _build_success_embed(
    *,
    track: str,
    class_: str,
    vehicle: str,
    lap_ms: int,
    entry_id: int,
    rank: int | None,
    screenshot_url: str | None,
    username: str,
) -> discord.Embed:
    embed = discord.Embed(title="Time Attack Entry Recorded", color=discord.Color.green())
    embed.add_field(name="Track", value=track, inline=True)
    embed.add_field(name="Class", value=class_, inline=True)
    embed.add_field(name="Vehicle", value=vehicle, inline=True)
    embed.add_field(name="Lap Time", value=format_lap_time(lap_ms), inline=True)
    embed.add_field(name="Entry ID", value=str(entry_id), inline=True)
    if rank is not None:
        embed.add_field(name="Global Rank", value=f"#{rank:,}", inline=True)
    if screenshot_url:
        embed.set_thumbnail(url=screenshot_url)
    embed.set_footer(text=f"Submitted by {username}")
    return embed
```

- [ ] **Step 3: Add `SubmissionModal` class before `SubmissionCog`**

```python
class SubmissionModal(discord.ui.Modal, title="Submit Time Attack Entry"):
    vehicle_input = discord.ui.TextInput(
        label="Vehicle", max_length=200, required=True
    )
    time_input = discord.ui.TextInput(
        label="Time (e.g. 1:23.456)", max_length=20, required=True
    )
    class_input = discord.ui.TextInput(
        label="Class (D/C/B/A/S1/S2/R/X)", max_length=5, required=True
    )
    rank_input = discord.ui.TextInput(
        label="Global Rank (optional)", required=False, max_length=10
    )

    def __init__(
        self,
        track: str,
        screenshot_path: str,
        screenshot_url: str,
        prefill: ExtractionResult,
    ) -> None:
        super().__init__()
        self._track = track
        self._screenshot_path = screenshot_path
        self._screenshot_url = screenshot_url
        if prefill.vehicle:
            self.vehicle_input.default = prefill.vehicle
        if prefill.time_str:
            self.time_input.default = prefill.time_str
        if prefill.class_:
            self.class_input.default = prefill.class_
        if prefill.global_rank is not None:
            self.rank_input.default = str(prefill.global_rank)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            lap_ms = parse_lap_time(self.time_input.value)
        except ValueError as exc:
            await interaction.response.send_message(f"**Time:** {exc}", ephemeral=True)
            return

        class_val = self.class_input.value.strip().upper()
        if class_val not in config.CLASSES:
            valid = ", ".join(f"`{c}`" for c in config.CLASSES)
            await interaction.response.send_message(
                f"**Class:** `{class_val}` isn't valid — choose from {valid}.",
                ephemeral=True,
            )
            return

        vehicle_val = self.vehicle_input.value.strip()
        vehicle_names = config.get_vehicle_names()
        if vehicle_names and vehicle_val not in vehicle_names:
            await interaction.response.send_message(
                f"**Vehicle:** `{vehicle_val}` isn't in the vehicle list — "
                "check the spelling matches the autocomplete list.",
                ephemeral=True,
            )
            return

        rank: int | None = None
        rank_str = self.rank_input.value.strip()
        if rank_str:
            try:
                rank = int(rank_str.lstrip("#").replace(",", ""))
            except ValueError:
                await interaction.response.send_message(
                    "**Global Rank:** must be a number (e.g. `1234`).",
                    ephemeral=True,
                )
                return

        entry_id = add_entry(
            discord_id=str(interaction.user.id),
            username=interaction.user.name,
            track=self._track,
            vehicle=vehicle_val,
            class_=class_val,
            lap_time_ms=lap_ms,
            screenshot_path=self._screenshot_path or None,
            global_rank=rank,
        )

        embed = _build_success_embed(
            track=self._track,
            class_=class_val,
            vehicle=vehicle_val,
            lap_ms=lap_ms,
            entry_id=entry_id,
            rank=rank,
            screenshot_url=self._screenshot_url or None,
            username=interaction.user.display_name,
        )
        await interaction.response.send_message(embed=embed)
```

- [ ] **Step 4: Add `ConfirmView` class before `SubmissionCog`**

```python
class ConfirmView(discord.ui.View):
    def __init__(
        self,
        track: str,
        screenshot_path: str,
        screenshot_url: str,
        result: ExtractionResult,
    ) -> None:
        super().__init__(timeout=300)
        self._track = track
        self._screenshot_path = screenshot_path
        self._screenshot_url = screenshot_url
        self._result = result
        all_present = all([
            result.vehicle,
            result.time_str,
            result.class_,
            result.global_rank is not None,
        ])
        if not all_present:
            self.remove_item(self.confirm_btn)

    @discord.ui.button(label="Confirm ✓", style=discord.ButtonStyle.green)
    async def confirm_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        lap_ms = parse_lap_time(self._result.time_str)
        entry_id = add_entry(
            discord_id=str(interaction.user.id),
            username=interaction.user.name,
            track=self._track,
            vehicle=self._result.vehicle,
            class_=self._result.class_,
            lap_time_ms=lap_ms,
            screenshot_path=self._screenshot_path or None,
            global_rank=self._result.global_rank,
        )
        embed = _build_success_embed(
            track=self._track,
            class_=self._result.class_,
            vehicle=self._result.vehicle,
            lap_ms=lap_ms,
            entry_id=entry_id,
            rank=self._result.global_rank,
            screenshot_url=self._screenshot_url or None,
            username=interaction.user.display_name,
        )
        self.stop()
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Edit ✏️", style=discord.ButtonStyle.secondary)
    async def edit_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        modal = SubmissionModal(
            track=self._track,
            screenshot_path=self._screenshot_path,
            screenshot_url=self._screenshot_url,
            prefill=self._result,
        )
        await interaction.response.send_modal(modal)
```

- [ ] **Step 5: Run existing tests to confirm nothing is broken**

```bash
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add cogs/submission.py
git commit -m "feat: add ConfirmView and SubmissionModal for image submission"
```

---

### Task 7: New `/submit` command

**Files:**
- Modify: `cogs/submission.py`

- [ ] **Step 1: Add the new `/submit` command to `SubmissionCog`**

Add this method inside `SubmissionCog`, before the existing autocomplete handlers:

```python
@app_commands.command(name="submit", description="Submit a time attack lap time via screenshot")
@app_commands.describe(
    track="Select a track from the list",
    screenshot="Attach a screenshot of your result (.jpg, .png, or .webp)",
)
async def submit(
    self,
    interaction: discord.Interaction,
    track: str,
    screenshot: discord.Attachment,
) -> None:
    if track not in config.TRACKS:
        await interaction.response.send_message(
            f"**Track:** `{track}` isn't recognised — select a track from the autocomplete list.",
            ephemeral=True,
        )
        return

    ext = Path(screenshot.filename).suffix.lower()
    if ext not in _IMAGE_EXTENSIONS:
        await interaction.response.send_message(
            f"**Screenshot:** `{screenshot.filename}` isn't a supported file type — attach a `.jpg`, `.png`, or `.webp` image.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)

    config.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{interaction.user.id}_{int(discord.utils.utcnow().timestamp())}{ext}"
    dest = config.SCREENSHOTS_DIR / filename

    http_session = self.bot.http_session  # type: ignore[attr-defined]
    async with http_session.get(screenshot.url) as resp:
        if resp.status != 200:
            await interaction.followup.send(
                "Failed to download screenshot — please try again.", ephemeral=True
            )
            return
        try:
            image_bytes = await resp.content.read(10 * 1024 * 1024)
            dest.write_bytes(image_bytes)
        except OSError:
            await interaction.followup.send(
                "Failed to save screenshot — please try again.", ephemeral=True
            )
            return

    from image_extractor import extract_from_image
    result = extract_from_image(image_bytes)

    all_present = all([
        result.vehicle,
        result.time_str,
        result.class_,
        result.global_rank is not None,
    ])

    embed = discord.Embed(
        title="Screenshot analysed — please confirm",
        color=discord.Color.blurple(),
    )
    embed.add_field(name="Track", value=track, inline=True)
    embed.add_field(name="Vehicle", value=result.vehicle or "❌ Not detected", inline=True)
    embed.add_field(name="Time", value=result.time_str or "❌ Not detected", inline=True)
    embed.add_field(name="Class", value=result.class_ or "❌ Not detected", inline=True)
    embed.add_field(
        name="Global Rank",
        value=f"#{result.global_rank:,}" if result.global_rank is not None else "❌ Not detected",
        inline=True,
    )
    embed.set_thumbnail(url=screenshot.url)
    if not all_present:
        embed.set_footer(text="Some fields couldn't be read — click Edit to fill them in.")
    else:
        embed.set_footer(text="Does this look right?")

    view = ConfirmView(
        track=track,
        screenshot_path=str(dest),
        screenshot_url=screenshot.url,
        result=result,
    )
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
```

Also add a `track` autocomplete handler for the new `/submit` command. Add after the existing autocomplete handlers:

```python
@submit.autocomplete("track")
async def _submit_track_ac(
    self, interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=t, value=t)
        for t in config.TRACKS
        if current.lower() in t.lower()
    ][:25]
```

- [ ] **Step 2: Run all tests**

```bash
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add cogs/submission.py
git commit -m "feat: add image-only /submit command with OCR extraction"
```

---

### Task 8: Push branch and open PR

- [ ] **Step 1: Push branch**

```bash
git push -u origin feat/image-submission
```

- [ ] **Step 2: Open PR**

```bash
gh pr create \
  --title "feat: image-only /submit with OCR extraction" \
  --body "$(cat <<'EOF'
## Summary
- New \`/submit\` command takes only a track dropdown + screenshot attachment
- OCR pipeline (Tesseract + OpenCV preprocessing + rapidfuzz) extracts vehicle, time, class, and global rank
- Ephemeral confirmation embed with Confirm/Edit buttons; Edit opens a pre-filled modal
- Falls back to Edit-only modal when any field fails to extract
- Old manual \`/submit\` preserved as \`/submit-manual\`
- \`global_rank\` column added to \`time_entries\` with backward-compatible migration

## Test plan
- [ ] Run \`pytest tests/ -v\` — all tests pass
- [ ] Start bot locally, run \`/submit\` with a real FH6 results screenshot — verify fields are extracted
- [ ] Test the Confirm button path — verify entry appears in \`/leaderboard\`
- [ ] Test the Edit path — modify an extracted field, confirm, verify corrected value is stored
- [ ] Test with a blurry/unreadable screenshot — verify Edit-only modal appears with blank fields
- [ ] Run \`/submit-manual\` — verify original flow still works

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
