# FH6 Relay — Replay Viewer Design Spec

**Date:** 2026-05-29
**Status:** Approved

---

## Overview

Rewrite the `fh6-relay` Windows application from Python/tkinter to Electron + TypeScript, and add a full telemetry replay feature. The new app is a persistent dashboard with three tabs — Live, Session, and Replay — that gives drivers a real-time cockpit view while driving and a full frame-by-frame replay with animated track map and data charts after each run.

The bot server and submission flow are unchanged. Replay data stays entirely local.

---

## Architecture

### Process Model

```
┌─────────────────────────────────────────────────────────┐
│  Electron Main Process (Node.js / TypeScript)           │
│                                                         │
│  UDP listener → packet parser → session manager        │
│  replay file I/O · API client · system tray            │
└────────────────────┬────────────────────────────────────┘
                     │ IPC (ipcMain / ipcRenderer)
┌────────────────────▼────────────────────────────────────┐
│  Renderer Process (TypeScript + HTML/CSS)               │
│                                                         │
│  Live tab · Session tab · Replay tab                   │
│  Chart.js (time-series) · Canvas 2D (track map)        │
└─────────────────────────────────────────────────────────┘
```

**Main process** owns all backend work: UDP socket on `127.0.0.1:20440`, binary packet parsing via Node's `Buffer` API, lap detection state machine, replay file I/O, system tray icon, and the HTTPS POST to the bot API. It runs continuously regardless of window visibility.

**Renderer process** is a single persistent window with three tabs. No frontend framework — vanilla TypeScript with Chart.js for time-series visualization and Canvas 2D for the track map.

**IPC bridge:** Main emits parsed packet data to the renderer at the full ~120 Hz packet rate for the Live tab. For replay, the renderer requests a lap's frame series via IPC and main returns it from in-memory storage (falling back to disk if the session was restarted).

### System Tray

The app minimizes to tray on window close rather than exiting. Tray icon states: idle (grey), active/receiving packets (green), error (red). Right-click menu: Show, Settings, Quit.

### Project Structure

```
fh6-relay/
  src/
    main/
      index.ts            # Electron main entry, tray setup
      udpListener.ts      # dgram UDP server on 127.0.0.1:20440
      packetParser.ts     # Buffer.readFloatLE / readInt32LE parsing
      sessionManager.ts   # Lap detection state machine + frame buffering
      replayStore.ts      # In-memory replay storage + disk I/O
      apiClient.ts        # HTTPS POST to bot API
      tokenStore.ts       # %APPDATA%\FH6BotRelay\config.json
      ipcHandlers.ts      # All ipcMain.handle / ipcMain.on registrations
    renderer/
      index.html
      tabs/
        live.ts           # Live telemetry tab
        session.ts        # Session review tab
        replay.ts         # Replay viewer tab
      charts/
        trackMap.ts       # Canvas 2D track map (shared by Live + Replay)
        inputTraces.ts    # Throttle/brake/steering Chart.js charts
        telemetryCharts.ts # Speed, RPM, gear, tire, suspension charts
      styles/
        main.css
  package.json
  tsconfig.json
  electron-builder.json   # Windows x64 NSIS installer config
```

---

## Data Capture

### Frame Type

Every incoming packet is parsed into a `Frame` object. Only the fields needed for visualization are retained:

```typescript
interface Frame {
  t: number;              // currentLap in seconds (timeline reference)

  // Position
  posX: number;
  posY: number;           // elevation
  posZ: number;

  // Motion
  speed: number;          // m/s
  rpm: number;
  gear: number;

  // Driver inputs
  throttle: number;       // 0–255
  brake: number;
  clutch: number;
  handbrake: number;
  steer: number;          // -127 to 127

  // Tire temperatures
  tireTempFL: number;
  tireTempFR: number;
  tireTempRL: number;
  tireTempRR: number;

  // Tire combined slip (0=full grip, >1=loss of grip)
  tireSlipFL: number;
  tireSlipFR: number;
  tireSlipRL: number;
  tireSlipRR: number;

  // Suspension travel (meters)
  suspFL: number;
  suspFR: number;
  suspRL: number;
  suspRR: number;

  // Misc
  boost: number;
  distanceTraveled: number;
}
```

### Buffering Strategy

The session manager maintains a `currentLapFrames: Frame[]` array. Every packet where `IsRaceOn === 1` appends a frame. On lap completion:

1. `currentLapFrames` is converted to columnar format (one typed array per field) and stored in `replayStore` keyed by lap number.
2. The columnar record is written to disk as a `.fh6replay` file.
3. `currentLapFrames` is reset for the next lap.

All laps from the current session remain in memory so the Replay tab loads instantly without disk reads.

### Columnar Storage Format

Rather than row-per-frame JSON, each replay file stores one array per field. This halves file size and maps directly to Chart.js dataset arrays:

```json
{
  "version": 1,
  "lapNumber": 1,
  "lapTimeMs": 83456,
  "carOrdinal": 1234,
  "carClass": 3,
  "capturedAt": "2026-05-29T14:00:00Z",
  "frameCount": 7200,
  "fields": {
    "t":        [0.000, 0.008, 0.017, ...],
    "posX":     [...],
    "posY":     [...],
    "posZ":     [...],
    "speed":    [...],
    "rpm":      [...],
    "gear":     [...],
    "throttle": [...],
    "brake":    [...],
    "steer":    [...],
    ...
  }
}
```

At ~120 Hz, a 60-second lap produces ~7,200 frames. Estimated file size: 2–3 MB per lap.

### Replay File Location and Retention

Files are saved to `%APPDATA%\FH6BotRelay\replays\YYYY-MM-DD_HH-MM-SS_lap<N>.fh6replay`.

On app start, files older than the configured retention period are deleted. Default retention: 30 days. Configurable in Settings with a minimum of 1 day and no enforced maximum. Submitted lap times in the bot's database are unaffected by retention.

---

## The Three Tabs

### Live Tab

Displays real-time telemetry while driving. Main process emits parsed frames to the renderer; the renderer throttles rendering to ~60 fps via `requestAnimationFrame`.

**Layout:**
- **Center:** Canvas 2D track map. The driven line accumulates as position data arrives. A dot marks the current position. Resets when `IsRaceOn` transitions from 0 → 1.
- **Top row:** Speed (km/h), current RPM with a bar relative to max RPM, gear indicator.
- **Right column:** Vertical throttle, brake, and clutch bars (0–100%). Steering bar (-100% to +100%).
- **Bottom left:** 2×2 tire grid. Each corner shows current temp (°C) and combined slip ratio. Color-coded: green (nominal), yellow (warm/moderate slip), red (overheating/high slip).
- **Bottom right:** Boost (PSI), fuel level bar.

When `IsRaceOn === 0`, the tab shows an "Waiting for session…" overlay and all displays hold their last values.

### Session Tab

Replaces the current Python Session Review window.

**Layout:**
- **Top:** Track dropdown and Vehicle dropdown, populated from `GET /api/tracks` and `GET /api/vehicles` on startup (same bot API endpoints as today).
- **Middle:** Lap table with columns: Lap #, Lap Time, and two action buttons — "Replay" and "Submit". Best lap row is highlighted. A "View Full Race Replay" button above the table covers all laps as one continuous recording.
- **Bottom:** Status area showing submission result or errors.

Submission flow is identical to today: selecting a lap and clicking Submit sends an HTTPS POST to the bot API with lap time, car/class, track, and vehicle name. Replay data is not included.

### Replay Tab

Populated when the user clicks "Replay" for a lap or "View Full Race Replay" from the Session tab. Displays a static analysis panel and animated playback controls.

**Lap selector:** Dropdown at the top to switch between individual laps or "Full Race" within the same view. In Full Race mode, each lap's frames are concatenated and the `t` values of subsequent laps are offset by the cumulative elapsed time of all prior laps, producing a single continuous timeline across the entire session.

**Static analysis panel (scrollable):**

All charts rendered immediately across the full lap time range, sharing the same horizontal time axis. Charts from top to bottom:

1. Track map (Canvas 2D) — full driven line with start/finish markers
2. Elevation — `posY` over time
3. Speed — m/s converted to km/h
4. Inputs — throttle, brake, clutch, handbrake, and steering overlaid on one chart
5. Gear + RPM — dual-axis chart (gear left, RPM right)
6. Boost — PSI over time (flat line for NA cars)
7. Tire temps — four lines (FL, FR, RL, RR)
8. Tire combined slip — four lines
9. Suspension travel — four lines

**Playback controls (fixed at bottom):**

Timeline scrubber spanning the full lap duration. Play/Pause button. Speed selector: 0.25×, 0.5×, 1×, 2×, 4×. Current time readout (MM:SS.mmm).

**Playhead behavior:**

A vertical line moves across all charts simultaneously as the animation plays or the user scrubs. The track map dot moves along the driven line to the corresponding position. A readout above the scrubber shows live values at the playhead: speed, gear, throttle %, brake %, steer angle.

---

## Settings

A Settings panel (accessible from tray right-click menu) exposes:

- UDP port (default: 20440)
- Bot API URL
- Replay retention period (days)
- Token display and re-entry (shows masked token, button to re-enter)

Settings are persisted to `%APPDATA%\FH6BotRelay\config.json` (same file as today's token store, extended with new keys).

---

## Build & Distribution

Electron Builder targeting Windows x64, producing an NSIS installer (`.exe`). Distributed as a GitHub release asset, replacing the PyInstaller `.exe`. Auto-update via `electron-updater` is out of scope for this iteration.

---

## Bot Server Changes

None. The submission payload and bot API are unchanged. The new Electron app replicates the same HTTPS POST behavior as the Python relay.

---

## Out of Scope

- Sending telemetry series to the bot server (deferred — bot receives lap time only)
- macOS / Linux builds
- Auto-update
- Lap comparison (overlay two laps on the same charts)
- Sector timing
