# Image-Only Submission Design

**Date:** 2026-05-28
**Status:** Approved

## Overview

Replace the current `/submit` command (which requires the user to type all fields manually) with an image-only flow: the user selects a track from a dropdown and attaches a screenshot. The bot extracts vehicle name, time, class, and global rank from the screenshot using OCR, then presents the extracted data for confirmation before saving.

The existing manual submission code is preserved under `/submit-manual` as a fallback.

## Components

### `image_extractor.py` (new)

Standalone module containing the entire OCR pipeline. Has no Discord dependency — takes image bytes, returns an `ExtractionResult` dataclass.

```python
@dataclass
class ExtractionResult:
    vehicle: str | None
    time_str: str | None
    class_: str | None
    global_rank: int | None
```

Any field that cannot be extracted with sufficient confidence is `None`. The cog uses the presence of `None` fields to decide the UX branch.

**Pipeline:**

1. **Preprocess** — convert to grayscale, apply CLAHE for local contrast normalisation, threshold to binary. Handles FH6's dynamic/varied backgrounds without a fixed threshold.
2. **OCR** — run Tesseract with `--psm 6` (uniform text block) on the preprocessed image. Produces a flat string of all detected text.
3. **Field extraction** from the raw text string:
   - **Time** — regex match for `M:SS.mmm` or `SS.mmm` (e.g. `1:23.456`, `58.120`)
   - **Class** — fuzzy match against `config.CLASSES` (the 8 known values) using `rapidfuzz`; minimum score 80. Handles common OCR errors like `S1` → `51`.
   - **Global rank** — regex for a plain integer, stripping any `#` prefix or comma separators
   - **Vehicle** — fuzzy match against all names in `vehicles.json` using `rapidfuzz`; minimum score 75 (lower than class because vehicle names are longer and partial matches are more useful)

**New dependencies:**
- `pytesseract` — Python wrapper for Tesseract
- `opencv-python-headless` — image preprocessing (no GUI required)
- `rapidfuzz` — fuzzy string matching
- `tesseract-ocr` binary added to the Dockerfile

---

### `cogs/submission.py` (modified)

**`/submit` command** — new signature: `track` (autocomplete, required) + `screenshot` (attachment, required).

After downloading the screenshot and running `image_extractor.extract_from_image()`, the command always responds with an ephemeral `ConfirmView` embed. The embed content varies based on extraction outcome:

- **All fields present** → embed shows all four extracted values with **Confirm** and **Edit** buttons
  - **Confirm** → saves entry, edits the ephemeral message to show a success confirmation, posts public embed
  - **Edit** → opens `SubmissionModal` pre-filled with extracted values

- **Any field is `None`** → embed shows extracted values and explicitly flags missing fields; **Edit / Enter Details** button only (no Confirm until all fields are known)
  - **Edit / Enter Details** → opens `SubmissionModal` with whatever was extracted pre-filled; blank inputs for missing fields

This two-step design (ephemeral embed → button → modal) is required by Discord's API: modals can only be sent in direct response to a component interaction, not after a deferred slash command response. Since image download and OCR require a `defer()`, the modal must always be triggered by a button click.

**`SubmissionModal`** — four `discord.ui.TextInput` fields: Vehicle, Time, Class, Global Rank. On submit, validates all four (time parse, class in list, vehicle in list), returns inline ephemeral errors on failure, on success writes entry and posts public embed.

**`/submit-manual`** — the existing `/submit` code unchanged except for a one-character rename of the `name=` argument in the decorator. Kept as a fallback; not prominently advertised.

---

### `database.py` (modified)

- `add_entry` gains `global_rank: int | None = None` parameter
- `time_entries` table gets a new nullable column: `global_rank INTEGER`
- `_migrate_time_entries_if_needed` gains an additional column-presence check: if `global_rank` is absent, runs `ALTER TABLE time_entries ADD COLUMN global_rank INTEGER`. Existing rows receive `NULL`.

## UX Flow

```
/submit (track dropdown + screenshot attachment)
    │
    ▼ defer()
Download image → image_extractor.extract_from_image()
    │
    ▼
ephemeral ConfirmView embed (always shown)
    │
    ├─ all 4 fields found ──► Confirm button + Edit button
    │                              │
    │                         Confirm ──► add_entry → public embed
    │                         Edit    ──► SubmissionModal (pre-filled) → add_entry → public embed
    │
    └─ any field None ──► "Enter Details" button only (lists missing fields)
                               │
                          SubmissionModal (partially pre-filled) → add_entry → public embed
```

## Error Handling

- **Image download failure** — ephemeral error, no entry created
- **Tesseract failure / exception** — treat as all fields `None`; fall through to modal so the user can still submit manually
- **Modal validation failure** — inline ephemeral error listing which field failed; modal stays open (Discord handles this via `interaction.response.send_message(ephemeral=True)`)
- **Unsupported file type** — same validation as current `/submit` (jpg, png, webp only)

## Out of Scope

- Spatial/region-of-interest OCR (full-image Tesseract is sufficient for a first pass; can be added later if accuracy is poor)
- Any changes to `/leaderboard`, `/my-times`, `/history`, or `/delete`
- The relay auto-submit path is unaffected
