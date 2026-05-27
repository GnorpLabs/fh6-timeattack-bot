# FH6 Data Out — Relay Exe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `fh6-relay`, a self-contained Windows `.exe` that listens for FH6's UDP telemetry on localhost, records lap completions during a session, and lets the user review and submit a chosen lap to the Discord bot's HTTP API via a system tray GUI.

**Architecture:** An asyncio event loop (background thread) runs the UDP listener and API client. The main thread runs `pystray` (system tray). tkinter windows are spawned in short-lived daemon threads when the user opens them. `session_manager` holds all in-memory state. On first launch, a tkinter setup dialog collects server address, Discord user ID, username, and token — saved to `%APPDATA%\FH6BotRelay\config.json`.

**Tech Stack:** Python 3.11+ (target for PyInstaller compatibility), asyncio, aiohttp, pystray, Pillow, tkinter (stdlib), PyInstaller

---

## File Map

All files live under `fh6-relay/` in the repo root.

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `fh6-relay/packet_parser.py` | Unpack 324-byte FH6 UDP packet into dataclass |
| Create | `fh6-relay/session_manager.py` | Lap detection state machine, in-memory lap store |
| Create | `fh6-relay/token_store.py` | Read/write `%APPDATA%\FH6BotRelay\config.json` |
| Create | `fh6-relay/api_client.py` | Single `aiohttp` HTTPS POST to `/api/lap` |
| Create | `fh6-relay/udp_listener.py` | asyncio `DatagramProtocol` on `127.0.0.1:PORT` |
| Create | `fh6-relay/gui.py` | pystray tray icon + tkinter windows |
| Create | `fh6-relay/main.py` | Entry point — wires asyncio loop + GUI |
| Create | `fh6-relay/requirements.txt` | Python dependencies |
| Create | `fh6-relay/build.spec` | PyInstaller one-file spec |
| Create | `fh6-relay/tests/conftest.py` | pytest sys.path setup |
| Create | `fh6-relay/tests/test_packet_parser.py` | Parser unit tests |
| Create | `fh6-relay/tests/test_session_manager.py` | Lap detection unit tests |
| Create | `fh6-relay/tests/test_token_store.py` | Config read/write tests |
| Create | `fh6-relay/tests/test_api_client.py` | API client tests (aiohttp mock) |

---

## Task 1: Project Scaffold

**Files:**
- Create: `fh6-relay/requirements.txt`
- Create: `fh6-relay/tests/conftest.py`

- [ ] **Step 1: Create `fh6-relay/requirements.txt`**

```
aiohttp>=3.9.0,<4.0.0
pystray>=0.19.0,<1.0.0
Pillow>=10.0.0,<11.0.0
pytest>=7.4.0,<8.0.0
pytest-asyncio>=0.23.0,<1.0.0
```

- [ ] **Step 2: Create `fh6-relay/tests/conftest.py`**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
```

- [ ] **Step 3: Create `fh6-relay/pytest.ini`**

```ini
[pytest]
testpaths = tests
asyncio_mode = auto
```

- [ ] **Step 4: Install dependencies and confirm pytest runs**

```bash
cd fh6-relay
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
pytest
```

Expected: `no tests ran` (0 collected).

- [ ] **Step 5: Commit**

```bash
git add fh6-relay/
git commit -m "chore: scaffold fh6-relay project"
```

---

## Task 2: Packet Parser

**Files:**
- Create: `fh6-relay/packet_parser.py`
- Create: `fh6-relay/tests/test_packet_parser.py`

- [ ] **Step 1: Write the failing tests**

Create `fh6-relay/tests/test_packet_parser.py`:

```python
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
```

- [ ] **Step 2: Run to confirm failures**

```bash
cd fh6-relay
pytest tests/test_packet_parser.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'packet_parser'`.

- [ ] **Step 3: Create `fh6-relay/packet_parser.py`**

```python
import struct
from dataclasses import dataclass

PACKET_SIZE = 324


@dataclass
class FH6Packet:
    is_race_on: int
    car_ordinal: int
    car_class: int
    best_lap: float
    last_lap: float
    current_lap: float
    current_race_time: float
    lap_number: int
    race_position: int


def parse_packet(data: bytes) -> FH6Packet | None:
    if len(data) != PACKET_SIZE:
        return None
    return FH6Packet(
        is_race_on=struct.unpack_from("<i", data, 0)[0],
        car_ordinal=struct.unpack_from("<i", data, 212)[0],
        car_class=struct.unpack_from("<i", data, 216)[0],
        best_lap=struct.unpack_from("<f", data, 296)[0],
        last_lap=struct.unpack_from("<f", data, 300)[0],
        current_lap=struct.unpack_from("<f", data, 304)[0],
        current_race_time=struct.unpack_from("<f", data, 308)[0],
        lap_number=struct.unpack_from("<H", data, 312)[0],
        race_position=struct.unpack_from("<B", data, 314)[0],
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_packet_parser.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add fh6-relay/packet_parser.py fh6-relay/tests/test_packet_parser.py
git commit -m "feat(relay): packet parser for 324-byte FH6 UDP packet"
```

---

## Task 3: Session Manager

**Files:**
- Create: `fh6-relay/session_manager.py`
- Create: `fh6-relay/tests/test_session_manager.py`

- [ ] **Step 1: Write the failing tests**

Create `fh6-relay/tests/test_session_manager.py`:

```python
import struct
from dataclasses import asdict
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
```

- [ ] **Step 2: Run to confirm failures**

```bash
pytest tests/test_session_manager.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'session_manager'`.

- [ ] **Step 3: Create `fh6-relay/session_manager.py`**

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from packet_parser import FH6Packet


@dataclass
class LapRecord:
    lap_number: int
    lap_time_ms: int
    car_class_int: int
    car_ordinal: int
    raw_telemetry: dict
    captured_at: str


class SessionManager:
    def __init__(self) -> None:
        self.laps: list[LapRecord] = []
        self._prev_lap_number: Optional[int] = None

    def on_packet(self, packet: FH6Packet) -> Optional[LapRecord]:
        if packet.is_race_on == 0:
            self._prev_lap_number = None
            return None

        if self._prev_lap_number is None:
            self._prev_lap_number = packet.lap_number
            return None

        if packet.lap_number > self._prev_lap_number:
            lap = LapRecord(
                lap_number=packet.lap_number,
                lap_time_ms=int(packet.last_lap * 1000),
                car_class_int=packet.car_class,
                car_ordinal=packet.car_ordinal,
                raw_telemetry=_packet_to_dict(packet),
                captured_at=datetime.now(timezone.utc).isoformat(),
            )
            self.laps.append(lap)
            self._prev_lap_number = packet.lap_number
            return lap

        self._prev_lap_number = packet.lap_number
        return None

    def reset(self) -> None:
        self.laps.clear()
        self._prev_lap_number = None


def _packet_to_dict(packet: FH6Packet) -> dict:
    return {
        "is_race_on": packet.is_race_on,
        "car_ordinal": packet.car_ordinal,
        "car_class": packet.car_class,
        "best_lap": packet.best_lap,
        "last_lap": packet.last_lap,
        "current_lap": packet.current_lap,
        "current_race_time": packet.current_race_time,
        "lap_number": packet.lap_number,
        "race_position": packet.race_position,
    }
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_session_manager.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add fh6-relay/session_manager.py fh6-relay/tests/test_session_manager.py
git commit -m "feat(relay): session manager with lap detection state machine"
```

---

## Task 4: Token Store

**Files:**
- Create: `fh6-relay/token_store.py`
- Create: `fh6-relay/tests/test_token_store.py`

- [ ] **Step 1: Write the failing tests**

Create `fh6-relay/tests/test_token_store.py`:

```python
import pytest
import token_store


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setattr(token_store, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(token_store, "CONFIG_DIR", tmp_path)


def test_load_config_returns_empty_dict_when_no_file():
    assert token_store.load_config() == {}


def test_is_setup_complete_false_when_no_file():
    assert token_store.is_setup_complete() is False


def test_save_setup_persists_all_fields():
    token_store.save_setup(
        api_url="https://bot.example.com",
        discord_id="123",
        discord_username="alice",
        token="abc123",
    )
    cfg = token_store.load_config()
    assert cfg["api_url"] == "https://bot.example.com"
    assert cfg["discord_id"] == "123"
    assert cfg["discord_username"] == "alice"
    assert cfg["token"] == "abc123"


def test_is_setup_complete_true_after_save():
    token_store.save_setup("https://x.com", "1", "alice", "tok")
    assert token_store.is_setup_complete() is True


def test_get_udp_port_defaults_to_20440():
    assert token_store.get_udp_port() == 20440


def test_get_udp_port_reads_from_config():
    token_store.save_setup("https://x.com", "1", "alice", "tok")
    cfg = token_store.load_config()
    cfg["udp_port"] = 9999
    token_store._save_raw(cfg)
    assert token_store.get_udp_port() == 9999


def test_update_token_replaces_only_token():
    token_store.save_setup("https://x.com", "1", "alice", "old")
    token_store.update_token("newtoken")
    cfg = token_store.load_config()
    assert cfg["token"] == "newtoken"
    assert cfg["discord_id"] == "1"
```

- [ ] **Step 2: Run to confirm failures**

```bash
pytest tests/test_token_store.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create `fh6-relay/token_store.py`**

```python
import json
import os
from pathlib import Path

CONFIG_DIR: Path = Path(os.environ.get("APPDATA", Path.home())) / "FH6BotRelay"
CONFIG_FILE: Path = CONFIG_DIR / "config.json"

_REQUIRED_KEYS = ("token", "api_url", "discord_id", "discord_username")


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def _save_raw(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def save_setup(api_url: str, discord_id: str, discord_username: str, token: str) -> None:
    cfg = load_config()
    cfg.update({
        "api_url": api_url,
        "discord_id": discord_id,
        "discord_username": discord_username,
        "token": token,
    })
    _save_raw(cfg)


def update_token(token: str) -> None:
    cfg = load_config()
    cfg["token"] = token
    _save_raw(cfg)


def is_setup_complete() -> bool:
    cfg = load_config()
    return all(k in cfg and cfg[k] for k in _REQUIRED_KEYS)


def get_udp_port() -> int:
    return load_config().get("udp_port", 20440)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_token_store.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add fh6-relay/token_store.py fh6-relay/tests/test_token_store.py
git commit -m "feat(relay): token store for AppData config persistence"
```

---

## Task 5: API Client

**Files:**
- Create: `fh6-relay/api_client.py`
- Create: `fh6-relay/tests/test_api_client.py`

- [ ] **Step 1: Write the failing tests**

Create `fh6-relay/tests/test_api_client.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import api_client
from session_manager import LapRecord


def _make_lap() -> LapRecord:
    return LapRecord(
        lap_number=2,
        lap_time_ms=83456,
        car_class_int=3,
        car_ordinal=1234,
        raw_telemetry={"lap_number": 2},
        captured_at="2026-05-26T12:00:00+00:00",
    )


async def test_submit_lap_returns_entry_id_on_success():
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={"entry_id": 42})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("api_client.aiohttp.ClientSession", return_value=mock_session):
        result = await api_client.submit_lap(
            api_url="https://bot.example.com",
            token="tok",
            discord_id="111",
            discord_username="alice",
            lap=_make_lap(),
            track="Hokubu Circuit",
            vehicle_name="2024 Toyota GR86",
        )
    assert result == {"entry_id": 42}


async def test_submit_lap_raises_value_error_on_401():
    mock_resp = AsyncMock()
    mock_resp.status = 401
    mock_resp.json = AsyncMock(return_value={"reason": "token_expired"})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("api_client.aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(ValueError, match="token_expired"):
            await api_client.submit_lap(
                api_url="https://bot.example.com",
                token="tok",
                discord_id="111",
                discord_username="alice",
                lap=_make_lap(),
                track="Hokubu Circuit",
                vehicle_name="2024 Toyota GR86",
            )


async def test_submit_lap_sends_correct_payload():
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={"entry_id": 1})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("api_client.aiohttp.ClientSession", return_value=mock_session):
        await api_client.submit_lap(
            api_url="https://bot.example.com",
            token="tok",
            discord_id="111",
            discord_username="alice",
            lap=_make_lap(),
            track="Hokubu Circuit",
            vehicle_name="2024 Toyota GR86",
        )

    call_kwargs = mock_session.post.call_args
    assert call_kwargs[0][0] == "https://bot.example.com/api/lap"
    payload = call_kwargs[1]["json"]
    assert payload["token"] == "tok"
    assert payload["discord_id"] == "111"
    assert payload["lap_time_ms"] == 83456
    assert payload["track"] == "Hokubu Circuit"
    assert payload["vehicle_name"] == "2024 Toyota GR86"
    assert payload["car_class_int"] == 3
```

- [ ] **Step 2: Run to confirm failures**

```bash
pytest tests/test_api_client.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create `fh6-relay/api_client.py`**

```python
import aiohttp

from session_manager import LapRecord


async def submit_lap(
    api_url: str,
    token: str,
    discord_id: str,
    discord_username: str,
    lap: LapRecord,
    track: str,
    vehicle_name: str,
) -> dict:
    payload = {
        "token": token,
        "discord_id": discord_id,
        "discord_username": discord_username,
        "lap_time_ms": lap.lap_time_ms,
        "track": track,
        "vehicle_name": vehicle_name,
        "car_class_int": lap.car_class_int,
        "car_ordinal": lap.car_ordinal,
        "raw_telemetry": lap.raw_telemetry,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{api_url}/api/lap", json=payload) as resp:
            data = await resp.json()
            if resp.status == 200:
                return data
            raise ValueError(data.get("reason", "unknown_error"))
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_api_client.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add fh6-relay/api_client.py fh6-relay/tests/test_api_client.py
git commit -m "feat(relay): API client for submitting laps to bot server"
```

---

## Task 6: UDP Listener

**Files:**
- Create: `fh6-relay/udp_listener.py`

(Network I/O is tested via integration; unit-tested implicitly through session_manager tests.)

- [ ] **Step 1: Create `fh6-relay/udp_listener.py`**

```python
import asyncio
from typing import Callable

from packet_parser import FH6Packet, parse_packet


class _FH6Protocol(asyncio.DatagramProtocol):
    def __init__(self, on_packet: Callable[[FH6Packet], None]) -> None:
        self._on_packet = on_packet

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        packet = parse_packet(data)
        if packet is not None:
            self._on_packet(packet)

    def error_received(self, exc: Exception) -> None:
        pass

    def connection_lost(self, exc: Exception | None) -> None:
        pass


async def start_udp_listener(
    host: str, port: int, on_packet: Callable[[FH6Packet], None]
) -> asyncio.BaseTransport:
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: _FH6Protocol(on_packet),
        local_addr=(host, port),
    )
    return transport
```

- [ ] **Step 2: Run all relay tests to confirm nothing broken**

```bash
pytest -v
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add fh6-relay/udp_listener.py
git commit -m "feat(relay): asyncio UDP listener for FH6 Data Out packets"
```

---

## Task 7: GUI (`gui.py`)

**Files:**
- Create: `fh6-relay/gui.py`

GUI code is not unit tested. Verify manually by running `python main.py` after Task 8.

- [ ] **Step 1: Create `fh6-relay/gui.py`**

```python
import asyncio
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

import pystray
from PIL import Image, ImageDraw

import api_client
import token_store

if TYPE_CHECKING:
    from session_manager import LapRecord, SessionManager


class App:
    def __init__(self, session: "SessionManager", loop: asyncio.AbstractEventLoop) -> None:
        self.session = session
        self.loop = loop
        self._icon: pystray.Icon | None = None

    def run(self) -> None:
        """Start the system tray. Blocks until quit. Must be called from main thread."""
        if not token_store.is_setup_complete():
            _show_setup_dialog()
        self._icon = pystray.Icon(
            "FH6 Relay",
            _make_tray_image(),
            "FH6 Relay",
            pystray.Menu(
                pystray.MenuItem("Session Review", self._on_open_review),
                pystray.MenuItem("Settings", self._on_open_settings),
                pystray.MenuItem("Quit", self._on_quit),
            ),
        )
        self._icon.run()

    def notify_new_lap(self, lap: "LapRecord") -> None:
        ms = lap.lap_time_ms
        m, rest = divmod(ms, 60_000)
        s, ms_part = divmod(rest, 1_000)
        time_str = f"{m}:{s:02d}.{ms_part:03d}" if m else f"{s}.{ms_part:03d}"
        if self._icon:
            self._icon.notify(f"Lap {lap.lap_number} recorded: {time_str}", "FH6 Relay")

    def _on_open_review(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        threading.Thread(target=self._show_review_window, daemon=True).start()

    def _on_open_settings(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        threading.Thread(target=_show_settings_dialog, daemon=True).start()

    def _on_quit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        icon.stop()
        self.loop.call_soon_threadsafe(self.loop.stop)

    def _show_review_window(self) -> None:
        cfg = token_store.load_config()

        root = tk.Tk()
        root.title("FH6 Relay — Session Review")
        root.geometry("620x420")

        # Track / vehicle selectors
        frame_top = tk.Frame(root)
        frame_top.pack(fill="x", padx=10, pady=6)

        tk.Label(frame_top, text="Track:").pack(side="left")
        track_var = tk.StringVar()
        track_combo = ttk.Combobox(frame_top, textvariable=track_var, width=28)
        track_combo.pack(side="left", padx=(4, 12))

        tk.Label(frame_top, text="Vehicle:").pack(side="left")
        vehicle_var = tk.StringVar()
        vehicle_combo = ttk.Combobox(frame_top, textvariable=vehicle_var, width=30)
        vehicle_combo.pack(side="left", padx=4)

        # Laps table
        tree = ttk.Treeview(root, columns=("lap", "time"), show="headings", selectmode="browse")
        tree.heading("lap", text="Lap #")
        tree.heading("time", text="Time")
        tree.column("lap", width=80, anchor="center")
        tree.column("time", width=160, anchor="center")
        tree.pack(fill="both", expand=True, padx=10, pady=4)

        for lap in self.session.laps:
            ms = lap.lap_time_ms
            m, rest = divmod(ms, 60_000)
            s, ms_part = divmod(rest, 1_000)
            time_str = f"{m}:{s:02d}.{ms_part:03d}" if m else f"{s}.{ms_part:03d}"
            tree.insert("", "end", iid=str(lap.lap_number), values=(lap.lap_number, time_str))

        status_var = tk.StringVar(value="Select a lap and fill in track + vehicle, then submit.")
        tk.Label(root, textvariable=status_var, anchor="w").pack(fill="x", padx=10)

        def on_submit() -> None:
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("No Lap", "Select a lap row first.", parent=root)
                return
            if not track_var.get().strip():
                messagebox.showwarning("No Track", "Select or type a track name.", parent=root)
                return
            if not vehicle_var.get().strip():
                messagebox.showwarning("No Vehicle", "Select or type a vehicle name.", parent=root)
                return

            lap_num = int(sel[0])
            lap = next(l for l in self.session.laps if l.lap_number == lap_num)
            status_var.set("Submitting…")
            root.update()

            future = asyncio.run_coroutine_threadsafe(
                api_client.submit_lap(
                    api_url=cfg["api_url"],
                    token=cfg["token"],
                    discord_id=cfg["discord_id"],
                    discord_username=cfg["discord_username"],
                    lap=lap,
                    track=track_var.get().strip(),
                    vehicle_name=vehicle_var.get().strip(),
                ),
                self.loop,
            )
            try:
                result = future.result(timeout=10)
                status_var.set(f"Submitted! Entry #{result['entry_id']} — check Discord for confirmation.")
            except ValueError as exc:
                reason = str(exc)
                if "token_expired" in reason:
                    messagebox.showerror(
                        "Token Expired",
                        "Your token has expired.\nRun /dataout-refresh in Discord, then update it via Settings.",
                        parent=root,
                    )
                else:
                    messagebox.showerror("Submission Failed", f"Server error: {reason}", parent=root)
                status_var.set("Submission failed.")
            except Exception as exc:
                messagebox.showerror("Network Error", str(exc), parent=root)
                status_var.set("Submission failed.")

        def on_clear() -> None:
            self.session.reset()
            for item in tree.get_children():
                tree.delete(item)
            status_var.set("Session cleared.")

        btn_frame = tk.Frame(root)
        btn_frame.pack(fill="x", padx=10, pady=6)
        tk.Button(btn_frame, text="Submit Selected Lap", command=on_submit).pack(side="right")
        tk.Button(btn_frame, text="Clear Session", command=on_clear).pack(side="right", padx=6)

        # Fetch tracks + vehicles from bot API in background
        if cfg.get("api_url"):
            import aiohttp

            async def _fetch() -> tuple[list, list]:
                async with aiohttp.ClientSession() as sess:
                    async with sess.get(f"{cfg['api_url']}/api/tracks") as r:
                        tracks = await r.json()
                    async with sess.get(f"{cfg['api_url']}/api/vehicles") as r:
                        vehicles_raw = await r.json()
                return tracks, [v["name"] for v in vehicles_raw]

            fetch_future = asyncio.run_coroutine_threadsafe(_fetch(), self.loop)
            try:
                tracks, vehicle_names = fetch_future.result(timeout=5)
                track_combo["values"] = tracks
                vehicle_combo["values"] = vehicle_names
            except Exception:
                pass  # offline — user can type values manually

        root.mainloop()


def _show_setup_dialog() -> None:
    root = tk.Tk()
    root.title("FH6 Relay — First Time Setup")
    root.resizable(False, False)

    cfg = token_store.load_config()
    rows = [
        ("api_url", "Server IP or FQDN", "e.g. 192.168.1.1 or bot.example.com"),
        ("discord_id", "Discord User ID", "Developer Mode → right-click profile → Copy User ID"),
        ("discord_username", "Discord Username", "e.g. alice"),
        ("token", "Token", "From /dataout-register in Discord"),
    ]
    entries: dict[str, tk.Entry] = {}
    for i, (key, label, hint) in enumerate(rows):
        tk.Label(root, text=label, anchor="w", font=("", 10, "bold")).grid(
            row=i * 2, column=0, columnspan=2, padx=12, pady=(8, 0), sticky="w"
        )
        tk.Label(root, text=hint, anchor="w", fg="gray").grid(
            row=i * 2, column=0, columnspan=2, padx=12, sticky="w"
        )
        entry = tk.Entry(root, width=52)
        entry.insert(0, cfg.get(key, ""))
        entry.grid(row=i * 2 + 1, column=0, columnspan=2, padx=12, pady=(2, 0), sticky="ew")
        entries[key] = entry

    def on_save() -> None:
        values = {k: e.get().strip() for k, e in entries.items()}
        if not all(values.values()):
            messagebox.showerror("Required", "All fields are required.", parent=root)
            return
        api_url = values["api_url"]
        if not api_url.startswith("http"):
            api_url = f"https://{api_url}"
        token_store.save_setup(
            api_url=api_url,
            discord_id=values["discord_id"],
            discord_username=values["discord_username"],
            token=values["token"],
        )
        root.destroy()

    tk.Button(root, text="Save & Continue", command=on_save, width=20).grid(
        row=len(rows) * 2, column=0, columnspan=2, pady=14
    )
    root.mainloop()


def _show_settings_dialog() -> None:
    _show_setup_dialog()


def _make_tray_image() -> Image.Image:
    img = Image.new("RGB", (64, 64), color=(20, 20, 20))
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 56, 56], fill=(0, 180, 80))
    return img
```

- [ ] **Step 2: Run all relay tests**

```bash
pytest -v
```

Expected: all pass (gui.py has no unit tests).

- [ ] **Step 3: Commit**

```bash
git add fh6-relay/gui.py
git commit -m "feat(relay): system tray GUI with session review and first-launch setup"
```

---

## Task 8: `main.py` + PyInstaller Build

**Files:**
- Create: `fh6-relay/main.py`
- Create: `fh6-relay/build.spec`

- [ ] **Step 1: Create `fh6-relay/main.py`**

```python
import asyncio
import threading

import token_store
import udp_listener
from gui import App
from session_manager import SessionManager


async def _async_main(app: App, port: int) -> None:
    def on_packet(packet):
        lap = app.session.on_packet(packet)
        if lap is not None:
            app.notify_new_lap(lap)

    transport = await udp_listener.start_udp_listener("127.0.0.1", port, on_packet)
    try:
        await asyncio.Event().wait()
    finally:
        transport.close()


def main() -> None:
    loop = asyncio.new_event_loop()
    session = SessionManager()
    app = App(session, loop)
    port = token_store.get_udp_port()

    def run_loop() -> None:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_async_main(app, port))

    t = threading.Thread(target=run_loop, daemon=True)
    t.start()

    app.run()  # blocks on main thread until quit


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test — run from source**

```bash
cd fh6-relay
python main.py
```

Expected: tray icon appears. If `%APPDATA%\FH6BotRelay\config.json` doesn't exist, the setup dialog appears. No crashes.

- [ ] **Step 3: Commit `main.py`**

```bash
git add fh6-relay/main.py
git commit -m "feat(relay): main entry point wiring asyncio loop and tray GUI"
```

- [ ] **Step 4: Install PyInstaller and create `build.spec`**

```bash
pip install pyinstaller
```

Create `fh6-relay/build.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=["pystray._win32"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="fh6-relay",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
```

- [ ] **Step 5: Build the exe**

```bash
cd fh6-relay
pyinstaller build.spec
```

Expected: `dist/fh6-relay.exe` is created.

- [ ] **Step 6: Test the built exe**

Run `dist/fh6-relay.exe`. Tray icon should appear. Setup dialog should show on first run. No console window.

- [ ] **Step 7: Commit**

```bash
git add fh6-relay/main.py fh6-relay/build.spec
git commit -m "feat(relay): PyInstaller build spec for fh6-relay.exe"
```
