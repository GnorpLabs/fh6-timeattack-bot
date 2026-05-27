# FH6 Time Attack Bot — Test Plan

## Prerequisites

- Bot is running and slash commands are visible in Discord
- You have at least one test image saved (any `.jpg`, `.png`, or `.webp` — a screenshot from the game or any image works)
- Optionally: a second Discord account to test cross-user permission checks

---

## Test Data

### Tracks
```
Legend Island
Hokubu Circuit
Soni Circuit
Sekibe Circuit
```

### Test Vehicles & Classes

Use these exact names when submitting — they match `data/vehicles.json`.

| # | Vehicle | Class | Notes |
|---|---------|-------|-------|
| V1 | `1984 Honda Civic CRX Mugen` | D | Slow baseline |
| V2 | `2013 Subaru BRZ` | C | |
| V3 | `1988 BMW M3` | B | |
| V4 | `1969 Ford Mustang Boss 302` | A | |
| V5 | `2020 Formula Drift #151 Toyota GR Supra` | S1 | |
| V6 | `2017 Nissan GT-R (R35)` | S1 | Used for tie test |
| V7 | `1987 Porsche 959` | S2 | |
| V8 | `2022 Lamborghini Aventador LP 780-4 Ultimae` | S2 | |
| V9 | `1962 Ferrari 250 GT Berlinetta Lusso` | R | |
| V10 | `2024 Ford Mustang Dark Horse` | X | |

### Test Lap Times

| ID | Time | Milliseconds | Notes |
|----|------|-------------|-------|
| T1 | `1:23.456` | 83456 | Valid — standard format |
| T2 | `0:58.100` | 58100 | Valid — sub-minute |
| T3 | `2:01.999` | 121999 | Valid — over 2 mins |
| T4 | `1:23.457` | 83457 | T1 + 1ms — for tie-breaking test |
| T5 | `1:23.456` | 83456 | Exact same as T1 — tie test |
| T6 | `1:20.000` | 80000 | Faster than T1 — leaderboard ordering |
| BAD1 | `83.456` | — | Invalid — missing colon/minutes |
| BAD2 | `1:23` | — | Invalid — no milliseconds |
| BAD3 | `1:60.000` | — | Invalid — seconds over 59 |
| BAD4 | `abc` | — | Invalid — not a time |

---

## Test Cases

### TC-01 — Submit: Happy Path

**Goal:** Confirm a valid submission is accepted and returns a correct embed.

| Step | Input | Expected |
|------|-------|----------|
| 1 | `/submit time:1:23.456 track:Legend Island vehicle:1984 Honda Civic CRX Mugen class:D screenshot:<any image>` | Embed with title "Time Attack Entry Recorded", showing correct track, class, vehicle, time (`1:23.456`), and an Entry ID |
| 2 | Note the **Entry ID** from the embed | Needed for TC-12 (delete) |
| 3 | `/submit time:0:58.100 track:Hokubu Circuit vehicle:2013 Subaru BRZ class:C screenshot:<any image>` | Separate embed for second entry |
| 4 | `/submit time:2:01.999 track:Legend Island vehicle:1987 Porsche 959 class:S2 screenshot:<any image>` | Third entry — same track as step 1, different class |

---

### TC-02 — Submit: Time Format Validation

**Goal:** Confirm the time parser rejects bad inputs before touching Discord or the DB.

| Step | Input | Expected |
|------|-------|----------|
| 1 | `/submit time:83.456 track:Legend Island vehicle:1984 Honda Civic CRX Mugen class:D screenshot:<any image>` | Ephemeral error message, no DB entry |
| 2 | `/submit time:1:23 track:Legend Island vehicle:1984 Honda Civic CRX Mugen class:D screenshot:<any image>` | Ephemeral error, no DB entry |
| 3 | `/submit time:1:60.000 track:Legend Island vehicle:1984 Honda Civic CRX Mugen class:D screenshot:<any image>` | Ephemeral error — seconds out of range |
| 4 | `/submit time:abc track:Legend Island vehicle:1984 Honda Civic CRX Mugen class:D screenshot:<any image>` | Ephemeral error |

---

### TC-03 — Submit: Track Validation

**Goal:** Confirm unknown track names are rejected even if autocomplete is bypassed.

| Step | Input | Expected |
|------|-------|----------|
| 1 | `/submit time:1:23.456 track:FakeTrack vehicle:1984 Honda Civic CRX Mugen class:D screenshot:<any image>` | Ephemeral: "Unknown track. Use the autocomplete list." |

> To bypass autocomplete: type a custom value in the track field by typing quickly before the suggestions appear, or use a bot testing tool.

---

### TC-04 — Submit: Class Validation

| Step | Input | Expected |
|------|-------|----------|
| 1 | `/submit time:1:23.456 track:Legend Island vehicle:1984 Honda Civic CRX Mugen class:Z screenshot:<any image>` | Ephemeral: "Unknown class. Use the autocomplete list." |

---

### TC-05 — Submit: Vehicle Validation

| Step | Input | Expected |
|------|-------|----------|
| 1 | `/submit time:1:23.456 track:Legend Island vehicle:Fake Car 9000 class:D screenshot:<any image>` | Ephemeral: "Unknown vehicle. Use the autocomplete list." |

---

### TC-06 — Submit: Screenshot Validation

| Step | Input | Expected |
|------|-------|----------|
| 1 | Attach a `.txt` or `.pdf` file instead of an image | Ephemeral: "Screenshot must be a jpg, png, or webp image." |

---

### TC-07 — Leaderboard: Single Class

**Goal:** Verify ordering and per-class display. Requires TC-01 to have run first.

| Step | Action | Expected |
|------|--------|----------|
| 1 | Submit 3 entries on `Legend Island` in class `D`: times `1:23.456`, `1:20.000`, `2:01.999` (using V1, or re-submit as the same user) | All accepted |
| 2 | `/leaderboard track:Legend Island class:D` | Shows fastest first: `1:20.000`, then `1:23.456`, then `2:01.999`. Only 1 entry per user (personal best). |
| 3 | `/leaderboard track:Sekibe Circuit class:A` | "No times recorded for **Sekibe Circuit** (A)." (ephemeral) |

---

### TC-08 — Leaderboard: All Classes

**Goal:** Verify the all-classes view groups results by class with one best entry per class.

| Step | Action | Expected |
|------|--------|----------|
| 1 | Ensure `Legend Island` has entries in at least 2 different classes (D from TC-01 step 1 and S2 from TC-01 step 3) | — |
| 2 | `/leaderboard track:Legend Island` (no class) | Embed with a separate field per class, each showing the class best |

---

### TC-09 — Leaderboard: Tie Handling

**Goal:** Verify that two users with the same time both appear on the leaderboard.

| Step | Action | Expected |
|------|--------|----------|
| 1 | User A submits `1:23.456` on `Soni Circuit` class `S1` with V5 | Accepted |
| 2 | User B (second Discord account) submits `1:23.456` on `Soni Circuit` class `S1` with V6 | Accepted |
| 3 | `/leaderboard track:Soni Circuit class:S1` | Both users appear at position 1 with the same time |

---

### TC-10 — My Times

**Goal:** Confirm users see only their own entries.

| Step | Action | Expected |
|------|--------|----------|
| 1 | `/my-times` (after TC-01) | Lists all your entries across all tracks |
| 2 | `/my-times track:Legend Island` | Only entries on Legend Island |
| 3 | `/my-times track:Sekibe Circuit` (no entries there) | "You have no times recorded on **Sekibe Circuit**." (ephemeral) |

---

### TC-11 — History

**Goal:** Confirm all submissions for a track appear in chronological order.

| Step | Action | Expected |
|------|--------|----------|
| 1 | `/history track:Legend Island` | All Legend Island entries, oldest first, showing username, class, time, and vehicle |
| 2 | `/history track:Legend Island class:D` | Only class D entries on Legend Island |
| 3 | `/history track:Sekibe Circuit` | "No history for **Sekibe Circuit**." |

---

### TC-12 — Delete: Own Entry

**Goal:** Confirm the confirmation flow works and the entry is removed.

| Step | Action | Expected |
|------|--------|----------|
| 1 | `/delete entry_id:<ID from TC-01 step 2>` | Ephemeral embed showing the entry details with "Confirm Delete" and "Cancel" buttons |
| 2 | Click **Confirm Delete** | Message updates to "Entry #X deleted." |
| 3 | Run `/my-times` | Deleted entry no longer appears |
| 4 | Run `/delete entry_id:<same ID>` again | "Entry #X not found." |

---

### TC-13 — Delete: Cancel Flow

| Step | Action | Expected |
|------|--------|----------|
| 1 | Submit a new entry, note the Entry ID | — |
| 2 | `/delete entry_id:<new ID>` | Confirmation embed appears |
| 3 | Click **Cancel** | Message updates to "Deletion cancelled." Entry still exists |
| 4 | `/my-times` | Entry is still present |

---

### TC-14 — Delete: Timeout

**Goal:** Confirm buttons are disabled after 30 seconds of inactivity.

| Step | Action | Expected |
|------|--------|----------|
| 1 | Submit a new entry, note the ID | — |
| 2 | `/delete entry_id:<ID>` | Confirmation embed appears |
| 3 | Wait 35 seconds without clicking | Both buttons become greyed out / disabled |
| 4 | Try clicking a button | Nothing happens (buttons are disabled) |
| 5 | Re-run `/delete entry_id:<ID>` | Confirmation prompt appears fresh — entry was not deleted |

---

### TC-15 — Delete: Cross-User Permission

**Goal:** Confirm a user cannot delete another user's entry.

| Step | Action | Expected |
|------|--------|----------|
| 1 | User A submits an entry, notes the Entry ID | — |
| 2 | User B runs `/delete entry_id:<User A's ID>` | Ephemeral: "You can only delete your own entries." |

---

### TC-16 — Autocomplete Smoke Test

**Goal:** Confirm autocomplete returns relevant suggestions and caps at 25.

| Step | Action | Expected |
|------|--------|----------|
| 1 | Type `/submit`, focus the `track` field, type `H` | Autocomplete shows `Hokubu Circuit` |
| 2 | Focus the `class` field, type `S` | Shows `S1`, `S2` |
| 3 | Focus the `vehicle` field, type `Toyota` | Shows Toyota vehicles (by manufacturer), max 25 results |
| 4 | Focus the `vehicle` field, type `Supra` | Shows Supra entries |

---

## Pass/Fail Summary

| TC | Feature | Pass | Fail | Notes |
|----|---------|------|------|-------|
| TC-01 | Submit happy path |x| | |
| TC-02 | Time format validation |x| | |
| TC-03 | Track validation |x| | |
| TC-04 | Class validation |x| | |
| TC-05 | Vehicle validation |x| | |
| TC-06 | Screenshot validation |x| | |
| TC-07 | Leaderboard single class |x| | |
| TC-08 | Leaderboard all classes |x| | |
| TC-09 | Leaderboard ties |x| | |
| TC-10 | My Times |x| | |
| TC-11 | History |x| | |
| TC-12 | Delete own entry |x| | |
| TC-13 | Delete cancel |x| | |
| TC-14 | Delete timeout |x| | |
| TC-15 | Delete cross-user |x| | |
| TC-16 | Autocomplete |x| | |
