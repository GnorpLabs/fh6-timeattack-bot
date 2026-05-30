# Electron Relay — Core App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `fh6-relay` from Python/tkinter to an Electron + TypeScript desktop app with a persistent three-tab window, producing a fully working relay replacement with Live and Session tabs (Replay tab is Plan 2).

**Architecture:** Electron main process owns all backend work (UDP, packet parsing, session management, file I/O, API calls); renderer process is a vanilla TypeScript UI communicating via IPC. The Python `fh6-relay/` directory is replaced in-place — old `.py` files are archived then removed.

**Tech Stack:** Electron 32, TypeScript 5, Chart.js 4 (Live tab gauges), Canvas 2D (track map), Jest + ts-jest (unit tests on main-process modules), electron-builder (NSIS Windows installer).

---

## File Map

| Path | Role |
|------|------|
| `fh6-relay/src/shared/types.ts` | `Frame`, `LapRecord`, `Config`, IPC channel constants |
| `fh6-relay/src/main/index.ts` | Electron entry — app lifecycle, BrowserWindow, tray |
| `fh6-relay/src/main/preload.ts` | `contextBridge` — exposes safe IPC surface to renderer |
| `fh6-relay/src/main/packetParser.ts` | `Buffer` → `Frame` (324-byte FH6 packet) |
| `fh6-relay/src/main/sessionManager.ts` | Lap detection state machine + per-lap frame buffer |
| `fh6-relay/src/main/replayStore.ts` | In-memory columnar lap storage + `.fh6replay` disk I/O |
| `fh6-relay/src/main/udpListener.ts` | `dgram` UDP socket → packetParser → sessionManager |
| `fh6-relay/src/main/tokenStore.ts` | Read/write `%APPDATA%\FH6BotRelay\config.json` |
| `fh6-relay/src/main/apiClient.ts` | `POST /api/lap`, `GET /api/tracks`, `GET /api/vehicles` |
| `fh6-relay/src/main/ipcHandlers.ts` | All `ipcMain.handle` registrations |
| `fh6-relay/src/renderer/index.html` | Shell HTML — tab bar + three tab panes |
| `fh6-relay/src/renderer/main.ts` | Tab switching, IPC listener setup |
| `fh6-relay/src/renderer/tabs/live.ts` | Live tab — gauges, inputs, tire grid, track map |
| `fh6-relay/src/renderer/tabs/session.ts` | Session tab — lap table, dropdowns, submit |
| `fh6-relay/src/renderer/charts/trackMap.ts` | Canvas 2D track map (used by Live tab; extended in Plan 2) |
| `fh6-relay/src/renderer/styles/main.css` | App-wide layout + dark theme |
| `fh6-relay/tests/packetParser.test.ts` | Unit tests for packet parser |
| `fh6-relay/tests/sessionManager.test.ts` | Unit tests for session manager |
| `fh6-relay/tests/replayStore.test.ts` | Unit tests for replay store |
| `fh6-relay/tests/tokenStore.test.ts` | Unit tests for token store |
| `fh6-relay/tests/apiClient.test.ts` | Unit tests for API client (mocked fetch) |
| `fh6-relay/package.json` | Project deps + scripts |
| `fh6-relay/tsconfig.json` | Renderer TypeScript config |
| `fh6-relay/tsconfig.main.json` | Main process TypeScript config (CommonJS target) |
| `fh6-relay/jest.config.js` | Jest + ts-jest config |
| `fh6-relay/electron-builder.json` | Windows x64 NSIS installer config |

---

## Task 1: Archive Python Files and Initialize Project

**Files:**
- Archive: `fh6-relay/` (all `.py` files)
- Create: `fh6-relay/package.json`
- Create: `fh6-relay/tsconfig.json`
- Create: `fh6-relay/tsconfig.main.json`
- Create: `fh6-relay/jest.config.js`
- Create: `fh6-relay/electron-builder.json`

- [ ] **Step 1: Archive Python source**

```bash
cd fh6-relay
mkdir -p _python_archive
mv *.py pytest.ini requirements.txt relay_logger.py _python_archive/
mv tests _python_archive/tests_python
```

- [ ] **Step 2: Create `package.json`**

```json
{
  "name": "fh6-relay",
  "version": "2.0.0",
  "description": "FH6 telemetry relay — Electron desktop app",
  "main": "dist/main/index.js",
  "scripts": {
    "build": "tsc -p tsconfig.main.json && tsc -p tsconfig.json",
    "start": "npm run build && electron .",
    "test": "jest",
    "pack": "npm run build && electron-builder --win --dir",
    "dist": "npm run build && electron-builder --win"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "electron": "^32.0.0",
    "electron-builder": "^25.0.0",
    "jest": "^29.7.0",
    "ts-jest": "^29.2.0",
    "typescript": "^5.4.0",
    "@types/jest": "^29.5.0"
  },
  "dependencies": {
    "chart.js": "^4.4.0"
  }
}
```

- [ ] **Step 3: Create `tsconfig.main.json`** (main process — Node.js/CommonJS)

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "moduleResolution": "node",
    "outDir": "dist/main",
    "rootDir": "src/main",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src/main/**/*", "src/shared/**/*"]
}
```

- [ ] **Step 4: Create `tsconfig.json`** (renderer — ESM)

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "bundler",
    "outDir": "dist/renderer",
    "rootDir": "src/renderer",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src/renderer/**/*", "src/shared/**/*"]
}
```

- [ ] **Step 5: Create `jest.config.js`**

```js
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/tests'],
  moduleNameMapper: {
    '^../src/shared/(.*)$': '<rootDir>/src/shared/$1',
    '^../src/main/(.*)$': '<rootDir>/src/main/$1',
  },
};
```

- [ ] **Step 6: Create `electron-builder.json`**

```json
{
  "appId": "com.gnorplabs.fh6relay",
  "productName": "FH6 Relay",
  "directories": { "output": "release" },
  "files": ["dist/**/*", "src/renderer/index.html", "src/renderer/styles/**"],
  "win": {
    "target": "nsis",
    "arch": ["x64"]
  },
  "nsis": {
    "oneClick": false,
    "allowToChangeInstallationDirectory": true
  }
}
```

- [ ] **Step 7: Install dependencies**

```bash
npm install
```

Expected: `node_modules/` created, no errors.

- [ ] **Step 8: Create directory structure**

```bash
mkdir -p src/main src/shared src/renderer/tabs src/renderer/charts src/renderer/styles tests
```

- [ ] **Step 9: Commit**

```bash
git add fh6-relay/
git commit -m "chore: init Electron+TypeScript project, archive Python relay"
```

---

## Task 2: Shared Types

**Files:**
- Create: `fh6-relay/src/shared/types.ts`

- [ ] **Step 1: Create `src/shared/types.ts`**

```typescript
export interface Frame {
  t: number;           // currentLap seconds — timeline reference
  posX: number;
  posY: number;        // elevation
  posZ: number;
  speed: number;       // m/s
  rpm: number;
  gear: number;
  throttle: number;    // 0–255
  brake: number;       // 0–255
  clutch: number;      // 0–255
  handbrake: number;   // 0–255
  steer: number;       // -127 to 127
  tireTempFL: number;
  tireTempFR: number;
  tireTempRL: number;
  tireTempRR: number;
  tireSlipFL: number;
  tireSlipFR: number;
  tireSlipRL: number;
  tireSlipRR: number;
  suspFL: number;
  suspFR: number;
  suspRL: number;
  suspRR: number;
  boost: number;
  distanceTraveled: number;
  carOrdinal: number;  // static per session, repeated each frame
  carClass: number;    // 0=D 1=C 2=B 3=A 4=S1 5=S2 6=R 7=X
}

export interface ColumnarLap {
  version: 1;
  lapNumber: number;
  lapTimeMs: number;
  carOrdinal: number;
  carClass: number;
  capturedAt: string;
  frameCount: number;
  fields: { [K in keyof Frame]: number[] };
}

export interface LapRecord {
  lapNumber: number;
  lapTimeMs: number;
  carOrdinal: number;
  carClass: number;
  capturedAt: string;
}

export interface Config {
  token: string;
  apiUrl: string;
  discordId: string;
  discordUsername: string;
  udpPort: number;
  retentionDays: number;
}

export const IPC = {
  // Main → Renderer (webContents.send)
  FRAME: 'telemetry:frame',
  LAP_COMPLETE: 'telemetry:lapComplete',
  RACE_OFF: 'telemetry:raceOff',
  // Renderer → Main (ipcMain.handle)
  GET_LAP: 'replay:getLap',
  GET_FULL_RACE: 'replay:getFullRace',
  SUBMIT_LAP: 'submit:lap',
  GET_VEHICLES: 'api:getVehicles',
  GET_TRACKS: 'api:getTracks',
  CONFIG_GET: 'config:get',
  CONFIG_SET: 'config:set',
} as const;
```

- [ ] **Step 2: Commit**

```bash
git add fh6-relay/src/shared/types.ts
git commit -m "feat(relay): add shared types and IPC channel constants"
```

---

## Task 3: Packet Parser

**Files:**
- Create: `fh6-relay/src/main/packetParser.ts`
- Create: `fh6-relay/tests/packetParser.test.ts`

All byte offsets are from `docs/fh6-telemetry-spec.md` and `fh6-relay/_python_archive/packet_parser.py`.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/packetParser.test.ts
import { parsePacket } from '../src/main/packetParser';

function makePacket(overrides: Record<number, { value: number; type: 'f32' | 'i32' | 'u32' | 'u16' | 'u8' | 'i8' }>): Buffer {
  const buf = Buffer.alloc(324, 0);
  for (const [offsetStr, { value, type }] of Object.entries(overrides)) {
    const offset = Number(offsetStr);
    switch (type) {
      case 'f32': buf.writeFloatLE(value, offset); break;
      case 'i32': buf.writeInt32LE(value, offset); break;
      case 'u32': buf.writeUInt32LE(value, offset); break;
      case 'u16': buf.writeUInt16LE(value, offset); break;
      case 'u8':  buf.writeUInt8(value, offset); break;
      case 'i8':  buf.writeInt8(value, offset); break;
    }
  }
  return buf;
}

describe('parsePacket', () => {
  it('returns null for wrong packet size', () => {
    expect(parsePacket(Buffer.alloc(100))).toBeNull();
  });

  it('returns null when IsRaceOn is 0', () => {
    const buf = makePacket({ 0: { value: 0, type: 'i32' } });
    expect(parsePacket(buf)).toBeNull();
  });

  it('parses all Frame fields from a valid packet', () => {
    const buf = makePacket({
      0:   { value: 1,      type: 'i32' },  // IsRaceOn
      232: { value: 10.5,   type: 'f32' },  // PositionX
      236: { value: 5.0,    type: 'f32' },  // PositionY (elevation)
      240: { value: -20.3,  type: 'f32' },  // PositionZ
      244: { value: 30.0,   type: 'f32' },  // Speed (m/s)
      16:  { value: 4500.0, type: 'f32' },  // CurrentEngineRpm
      319: { value: 3,      type: 'u8'  },  // Gear
      315: { value: 200,    type: 'u8'  },  // Accel
      316: { value: 0,      type: 'u8'  },  // Brake
      317: { value: 0,      type: 'u8'  },  // Clutch
      318: { value: 0,      type: 'u8'  },  // HandBrake
      320: { value: 64,     type: 'i8'  },  // Steer
      256: { value: 80.0,   type: 'f32' },  // TireTempFL
      260: { value: 81.0,   type: 'f32' },  // TireTempFR
      264: { value: 79.0,   type: 'f32' },  // TireTempRL
      268: { value: 82.0,   type: 'f32' },  // TireTempRR
      180: { value: 0.1,    type: 'f32' },  // TireCombinedSlipFL
      184: { value: 0.1,    type: 'f32' },  // TireCombinedSlipFR
      188: { value: 0.2,    type: 'f32' },  // TireCombinedSlipRL
      192: { value: 0.2,    type: 'f32' },  // TireCombinedSlipRR
      196: { value: 0.05,   type: 'f32' },  // SuspTravelFL
      200: { value: 0.05,   type: 'f32' },  // SuspTravelFR
      204: { value: 0.06,   type: 'f32' },  // SuspTravelRL
      208: { value: 0.06,   type: 'f32' },  // SuspTravelRR
      272: { value: 5.0,    type: 'f32' },  // Boost
      280: { value: 1500.0, type: 'f32' },  // DistanceTraveled
      304: { value: 45.2,   type: 'f32' },  // CurrentLap
    });

    const frame = parsePacket(buf);
    expect(frame).not.toBeNull();
    expect(frame!.posX).toBeCloseTo(10.5, 3);
    expect(frame!.posY).toBeCloseTo(5.0, 3);
    expect(frame!.posZ).toBeCloseTo(-20.3, 3);
    expect(frame!.speed).toBeCloseTo(30.0, 3);
    expect(frame!.rpm).toBeCloseTo(4500.0, 0);
    expect(frame!.gear).toBe(3);
    expect(frame!.throttle).toBe(200);
    expect(frame!.steer).toBe(64);
    expect(frame!.tireTempFL).toBeCloseTo(80.0, 3);
    expect(frame!.tireSlipFL).toBeCloseTo(0.1, 3);
    expect(frame!.suspFL).toBeCloseTo(0.05, 3);
    expect(frame!.boost).toBeCloseTo(5.0, 3);
    expect(frame!.t).toBeCloseTo(45.2, 3);
  });
});
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd fh6-relay && npx jest tests/packetParser.test.ts
```

Expected: FAIL — `Cannot find module '../src/main/packetParser'`

- [ ] **Step 3: Implement `src/main/packetParser.ts`**

```typescript
import { Frame } from '../shared/types';

export const PACKET_SIZE = 324;

export function parsePacket(data: Buffer): Frame | null {
  if (data.length !== PACKET_SIZE) return null;
  if (data.readInt32LE(0) === 0) return null; // IsRaceOn === 0

  return {
    t:              data.readFloatLE(304),  // CurrentLap
    posX:           data.readFloatLE(232),
    posY:           data.readFloatLE(236),
    posZ:           data.readFloatLE(240),
    speed:          data.readFloatLE(244),
    rpm:            data.readFloatLE(16),   // CurrentEngineRpm
    gear:           data.readUInt8(319),
    throttle:       data.readUInt8(315),
    brake:          data.readUInt8(316),
    clutch:         data.readUInt8(317),
    handbrake:      data.readUInt8(318),
    steer:          data.readInt8(320),
    tireTempFL:     data.readFloatLE(256),
    tireTempFR:     data.readFloatLE(260),
    tireTempRL:     data.readFloatLE(264),
    tireTempRR:     data.readFloatLE(268),
    tireSlipFL:     data.readFloatLE(180),
    tireSlipFR:     data.readFloatLE(184),
    tireSlipRL:     data.readFloatLE(188),
    tireSlipRR:     data.readFloatLE(192),
    suspFL:         data.readFloatLE(196),
    suspFR:         data.readFloatLE(200),
    suspRL:         data.readFloatLE(204),
    suspRR:         data.readFloatLE(208),
    boost:          data.readFloatLE(272),
    distanceTraveled: data.readFloatLE(280),
    carOrdinal:     data.readInt32LE(212),
    carClass:       data.readInt32LE(216),
  };
}
```

- [ ] **Step 4: Run test — verify it passes**

```bash
npx jest tests/packetParser.test.ts
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add fh6-relay/src/main/packetParser.ts fh6-relay/tests/packetParser.test.ts
git commit -m "feat(relay): add TypeScript packet parser with tests"
```

---

## Task 4: Session Manager

**Files:**
- Create: `fh6-relay/src/main/sessionManager.ts`
- Create: `fh6-relay/tests/sessionManager.test.ts`

The lap detection logic mirrors the Python version: CurrentLap drops by `>10s` after running `>15s` = lap complete.

- [ ] **Step 1: Write the failing test**

```typescript
// tests/sessionManager.test.ts
import { SessionManager } from '../src/main/sessionManager';
import { Frame } from '../src/shared/types';

function frame(t: number): Frame {
  return {
    t, posX: 0, posY: 0, posZ: 0, speed: 20, rpm: 3000, gear: 3,
    throttle: 200, brake: 0, clutch: 0, handbrake: 0, steer: 0,
    tireTempFL: 80, tireTempFR: 80, tireTempRL: 80, tireTempRR: 80,
    tireSlipFL: 0.1, tireSlipFR: 0.1, tireSlipRL: 0.1, tireSlipRR: 0.1,
    suspFL: 0.05, suspFR: 0.05, suspRL: 0.05, suspRR: 0.05,
    boost: 0, distanceTraveled: 1000,
  };
}

describe('SessionManager', () => {
  it('buffers frames and detects a lap when CurrentLap resets', () => {
    const sm = new SessionManager();
    const lapCompleted = jest.fn();
    sm.on('lapComplete', lapCompleted);

    // Simulate driving for 60s
    for (let t = 0; t <= 60; t += 0.1) sm.onFrame(frame(t));

    // Lap reset: t drops from ~60 back to ~0
    sm.onFrame(frame(0.5));

    expect(lapCompleted).toHaveBeenCalledTimes(1);
    const { lapRecord, frames } = lapCompleted.mock.calls[0][0];
    expect(lapRecord.lapTimeMs).toBeCloseTo(60000, -2);
    expect(frames.length).toBeGreaterThan(500);
  });

  it('ignores resets shorter than MIN_LAP_SECONDS', () => {
    const sm = new SessionManager();
    const lapCompleted = jest.fn();
    sm.on('lapComplete', lapCompleted);

    // Only 5s of driving — below the 15s minimum
    for (let t = 0; t <= 5; t += 0.1) sm.onFrame(frame(t));
    sm.onFrame(frame(0.1));

    expect(lapCompleted).not.toHaveBeenCalled();
  });

  it('resets internal state on reset()', () => {
    const sm = new SessionManager();
    for (let t = 0; t <= 60; t += 0.1) sm.onFrame(frame(t));
    sm.reset();
    expect(sm.getLapCount()).toBe(0);
  });
});
```

- [ ] **Step 2: Run test — verify it fails**

```bash
npx jest tests/sessionManager.test.ts
```

Expected: FAIL — `Cannot find module '../src/main/sessionManager'`

- [ ] **Step 3: Implement `src/main/sessionManager.ts`**

```typescript
import { EventEmitter } from 'events';
import { Frame, LapRecord } from '../shared/types';

const MIN_LAP_SECONDS = 15;
const RESET_THRESHOLD = 10;

export interface LapCompletePayload {
  lapRecord: LapRecord;
  frames: Frame[];
}

export class SessionManager extends EventEmitter {
  private prevT: number | null = null;
  private currentFrames: Frame[] = [];
  private lapCount = 0;

  onFrame(frame: Frame): void {
    if (this.prevT === null) {
      this.prevT = frame.t;
      this.currentFrames.push(frame);
      return;
    }

    if (
      this.prevT > MIN_LAP_SECONDS &&
      frame.t < this.prevT - RESET_THRESHOLD
    ) {
      this.lapCount++;
      const lapTimeMs = Math.round(this.prevT * 1000);
      const frames = [...this.currentFrames];
      const lastFrame = this.currentFrames[this.currentFrames.length - 1];
      const lapRecord: LapRecord = {
        lapNumber: this.lapCount,
        lapTimeMs,
        carOrdinal: lastFrame.carOrdinal,
        carClass: lastFrame.carClass,
        capturedAt: new Date().toISOString(),
      };
      this.emit('lapComplete', { lapRecord, frames } satisfies LapCompletePayload);
      this.currentFrames = [];
    }

    this.currentFrames.push(frame);
    this.prevT = frame.t;
  }

  reset(): void {
    this.prevT = null;
    this.currentFrames = [];
    this.lapCount = 0;
  }

  getLapCount(): number {
    return this.lapCount;
  }
}
```

- [ ] **Step 4: Run test — verify it passes**

```bash
npx jest tests/sessionManager.test.ts
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add fh6-relay/src/main/sessionManager.ts fh6-relay/tests/sessionManager.test.ts
git commit -m "feat(relay): add session manager with lap detection and tests"
```

---

## Task 5: Replay Store

**Files:**
- Create: `fh6-relay/src/main/replayStore.ts`
- Create: `fh6-relay/tests/replayStore.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// tests/replayStore.test.ts
import * as os from 'os';
import * as path from 'path';
import * as fs from 'fs';
import { ReplayStore } from '../src/main/replayStore';
import { Frame, LapRecord } from '../src/shared/types';

function makeFrames(count: number): Frame[] {
  return Array.from({ length: count }, (_, i) => ({
    t: i * 0.008,
    posX: i * 0.1, posY: 0, posZ: 0, speed: 20, rpm: 3000, gear: 3,
    throttle: 200, brake: 0, clutch: 0, handbrake: 0, steer: 0,
    tireTempFL: 80, tireTempFR: 80, tireTempRL: 80, tireTempRR: 80,
    tireSlipFL: 0.1, tireSlipFR: 0.1, tireSlipRL: 0.1, tireSlipRR: 0.1,
    suspFL: 0.05, suspFR: 0.05, suspRL: 0.05, suspRR: 0.05,
    boost: 0, distanceTraveled: i * 0.5,
  }));
}

const lapRecord: LapRecord = {
  lapNumber: 1, lapTimeMs: 60000, carOrdinal: 1234,
  carClass: 3, capturedAt: new Date().toISOString(),
};

describe('ReplayStore', () => {
  let store: ReplayStore;
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'fh6relay-test-'));
    store = new ReplayStore(tmpDir, 30);
  });

  afterEach(() => fs.rmSync(tmpDir, { recursive: true }));

  it('stores a lap in memory and retrieves it', () => {
    const frames = makeFrames(100);
    store.storeLap(lapRecord, frames);

    const columnar = store.getLap(1);
    expect(columnar).not.toBeNull();
    expect(columnar!.lapNumber).toBe(1);
    expect(columnar!.frameCount).toBe(100);
    expect(columnar!.fields.posX[0]).toBeCloseTo(0, 3);
    expect(columnar!.fields.posX[1]).toBeCloseTo(0.1, 3);
  });

  it('writes a .fh6replay file to disk', () => {
    store.storeLap(lapRecord, makeFrames(50));
    const files = fs.readdirSync(tmpDir);
    expect(files.some(f => f.endsWith('.fh6replay'))).toBe(true);
  });

  it('deletes files older than retentionDays on cleanup', () => {
    store.storeLap(lapRecord, makeFrames(10));

    // Backdate the file
    const files = fs.readdirSync(tmpDir).map(f => path.join(tmpDir, f));
    const old = Date.now() - 31 * 24 * 60 * 60 * 1000;
    fs.utimesSync(files[0], old / 1000, old / 1000);

    store.runRetentionCleanup();
    expect(fs.readdirSync(tmpDir).length).toBe(0);
  });
});
```

- [ ] **Step 2: Run test — verify it fails**

```bash
npx jest tests/replayStore.test.ts
```

Expected: FAIL — `Cannot find module '../src/main/replayStore'`

- [ ] **Step 3: Implement `src/main/replayStore.ts`**

```typescript
import * as fs from 'fs';
import * as path from 'path';
import { Frame, ColumnarLap, LapRecord } from '../shared/types';

function toColumnar(record: LapRecord, frames: Frame[]): ColumnarLap {
  const keys = Object.keys(frames[0]) as (keyof Frame)[];
  const fields = {} as ColumnarLap['fields'];
  for (const key of keys) {
    fields[key] = frames.map(f => f[key]);
  }
  return {
    version: 1,
    lapNumber: record.lapNumber,
    lapTimeMs: record.lapTimeMs,
    carOrdinal: record.carOrdinal,
    carClass: record.carClass,
    capturedAt: record.capturedAt,
    frameCount: frames.length,
    fields,
  };
}

export class ReplayStore {
  private laps = new Map<number, ColumnarLap>();

  constructor(
    private readonly replayDir: string,
    private readonly retentionDays: number,
  ) {
    fs.mkdirSync(replayDir, { recursive: true });
  }

  storeLap(record: LapRecord, frames: Frame[]): void {
    const columnar = toColumnar(record, frames);
    this.laps.set(record.lapNumber, columnar);

    const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const filename = `${ts}_lap${record.lapNumber}.fh6replay`;
    fs.writeFileSync(
      path.join(this.replayDir, filename),
      JSON.stringify(columnar),
    );
  }

  getLap(lapNumber: number): ColumnarLap | null {
    return this.laps.get(lapNumber) ?? null;
  }

  getFullRace(): ColumnarLap | null {
    const laps = [...this.laps.values()].sort((a, b) => a.lapNumber - b.lapNumber);
    if (laps.length === 0) return null;

    // Stitch laps: offset each lap's t values by cumulative time
    let timeOffset = 0;
    const allFields = { ...laps[0].fields } as ColumnarLap['fields'];
    const keys = Object.keys(allFields) as (keyof Frame)[];

    for (const key of keys) allFields[key] = [];

    for (const lap of laps) {
      for (const key of keys) {
        const arr = lap.fields[key].map(v => key === 't' ? v + timeOffset : v);
        allFields[key].push(...arr);
      }
      timeOffset += lap.lapTimeMs / 1000;
    }

    return {
      version: 1,
      lapNumber: -1,
      lapTimeMs: timeOffset * 1000,
      carOrdinal: laps[0].carOrdinal,
      carClass: laps[0].carClass,
      capturedAt: laps[0].capturedAt,
      frameCount: allFields.t.length,
      fields: allFields,
    };
  }

  runRetentionCleanup(): void {
    const cutoff = Date.now() - this.retentionDays * 24 * 60 * 60 * 1000;
    for (const file of fs.readdirSync(this.replayDir)) {
      const full = path.join(this.replayDir, file);
      const { mtimeMs } = fs.statSync(full);
      if (mtimeMs < cutoff) fs.unlinkSync(full);
    }
  }
}
```

- [ ] **Step 4: Run test — verify it passes**

```bash
npx jest tests/replayStore.test.ts
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add fh6-relay/src/main/replayStore.ts fh6-relay/tests/replayStore.test.ts
git commit -m "feat(relay): add replay store with columnar storage, disk I/O, retention"
```

---

## Task 6: Token Store

**Files:**
- Create: `fh6-relay/src/main/tokenStore.ts`
- Create: `fh6-relay/tests/tokenStore.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// tests/tokenStore.test.ts
import * as os from 'os';
import * as path from 'path';
import * as fs from 'fs';
import { TokenStore } from '../src/main/tokenStore';

describe('TokenStore', () => {
  let tmpDir: string;
  let store: TokenStore;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'fh6relay-cfg-'));
    store = new TokenStore(path.join(tmpDir, 'config.json'));
  });

  afterEach(() => fs.rmSync(tmpDir, { recursive: true }));

  it('returns defaults when no config file exists', () => {
    const cfg = store.load();
    expect(cfg.udpPort).toBe(20440);
    expect(cfg.retentionDays).toBe(30);
    expect(cfg.token).toBe('');
  });

  it('saves and reloads config', () => {
    const cfg = store.load();
    cfg.token = 'abc123';
    cfg.apiUrl = 'https://example.com';
    store.save(cfg);

    const store2 = new TokenStore(path.join(tmpDir, 'config.json'));
    const reloaded = store2.load();
    expect(reloaded.token).toBe('abc123');
    expect(reloaded.apiUrl).toBe('https://example.com');
  });
});
```

- [ ] **Step 2: Run test — verify it fails**

```bash
npx jest tests/tokenStore.test.ts
```

Expected: FAIL.

- [ ] **Step 3: Implement `src/main/tokenStore.ts`**

```typescript
import * as fs from 'fs';
import { Config } from '../shared/types';

const DEFAULTS: Config = {
  token: '',
  apiUrl: '',
  discordId: '',
  discordUsername: '',
  udpPort: 20440,
  retentionDays: 30,
};

export class TokenStore {
  constructor(private readonly configPath: string) {}

  load(): Config {
    try {
      const raw = fs.readFileSync(this.configPath, 'utf8');
      return { ...DEFAULTS, ...JSON.parse(raw) };
    } catch {
      return { ...DEFAULTS };
    }
  }

  save(config: Config): void {
    fs.writeFileSync(this.configPath, JSON.stringify(config, null, 2));
  }
}
```

- [ ] **Step 4: Run test — verify it passes**

```bash
npx jest tests/tokenStore.test.ts
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add fh6-relay/src/main/tokenStore.ts fh6-relay/tests/tokenStore.test.ts
git commit -m "feat(relay): add token/config store with tests"
```

---

## Task 7: API Client

**Files:**
- Create: `fh6-relay/src/main/apiClient.ts`
- Create: `fh6-relay/tests/apiClient.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// tests/apiClient.test.ts
import { ApiClient } from '../src/main/apiClient';

const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('ApiClient', () => {
  const client = new ApiClient('https://bot.example.com', 'tok', 'disc123', 'player1');

  beforeEach(() => mockFetch.mockReset());

  it('GET /api/vehicles returns parsed JSON', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ['Toyota GR86', 'Subaru BRZ'],
    });

    const vehicles = await client.getVehicles();
    expect(vehicles).toEqual(['Toyota GR86', 'Subaru BRZ']);
    expect(mockFetch).toHaveBeenCalledWith('https://bot.example.com/api/vehicles');
  });

  it('GET /api/tracks returns parsed JSON', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ['Hokubu Circuit', 'Horizon Festival'],
    });

    const tracks = await client.getTracks();
    expect(tracks).toEqual(['Hokubu Circuit', 'Horizon Festival']);
  });

  it('POST /api/lap sends correct payload and returns entry_id', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ entry_id: 42 }),
    });

    const result = await client.submitLap({
      lapTimeMs: 83456,
      track: 'Hokubu Circuit',
      vehicleName: '2024 Toyota GR86',
      carClassInt: 3,
      carOrdinal: 1234,
    });

    expect(result.entry_id).toBe(42);
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('https://bot.example.com/api/lap');
    const body = JSON.parse(opts.body);
    expect(body.token).toBe('tok');
    expect(body.discord_id).toBe('disc123');
    expect(body.lap_time_ms).toBe(83456);
  });

  it('throws on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 401 });
    await expect(client.submitLap({
      lapTimeMs: 1000, track: 'x', vehicleName: 'y', carClassInt: 0, carOrdinal: 0,
    })).rejects.toThrow('401');
  });
});
```

- [ ] **Step 2: Run test — verify it fails**

```bash
npx jest tests/apiClient.test.ts
```

Expected: FAIL.

- [ ] **Step 3: Implement `src/main/apiClient.ts`**

```typescript
interface SubmitPayload {
  lapTimeMs: number;
  track: string;
  vehicleName: string;
  carClassInt: number;
  carOrdinal: number;
}

export class ApiClient {
  constructor(
    private readonly apiUrl: string,
    private readonly token: string,
    private readonly discordId: string,
    private readonly discordUsername: string,
  ) {}

  async getVehicles(): Promise<string[]> {
    const res = await fetch(`${this.apiUrl}/api/vehicles`);
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  }

  async getTracks(): Promise<string[]> {
    const res = await fetch(`${this.apiUrl}/api/tracks`);
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  }

  async submitLap(payload: SubmitPayload): Promise<{ entry_id: number }> {
    const res = await fetch(`${this.apiUrl}/api/lap`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: this.token,
        discord_id: this.discordId,
        discord_username: this.discordUsername,
        lap_time_ms: payload.lapTimeMs,
        track: payload.track,
        vehicle_name: payload.vehicleName,
        car_class_int: payload.carClassInt,
        car_ordinal: payload.carOrdinal,
      }),
    });
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  }
}
```

- [ ] **Step 4: Run test — verify it passes**

```bash
npx jest tests/apiClient.test.ts
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add fh6-relay/src/main/apiClient.ts fh6-relay/tests/apiClient.test.ts
git commit -m "feat(relay): add API client with tests"
```

---

## Task 8: UDP Listener

**Files:**
- Create: `fh6-relay/src/main/udpListener.ts`

No unit tests — dgram is a Node built-in and the socket behavior requires integration. Manual verification in Task 11.

- [ ] **Step 1: Implement `src/main/udpListener.ts`**

```typescript
import * as dgram from 'dgram';
import { parsePacket } from './packetParser';
import { SessionManager } from './sessionManager';
import { Frame } from '../shared/types';

export class UdpListener {
  private socket: dgram.Socket | null = null;

  constructor(
    private readonly sessionManager: SessionManager,
    private readonly onFrame: (frame: Frame) => void,
    private readonly onRaceOff: () => void,
  ) {}

  start(port: number): void {
    this.socket = dgram.createSocket('udp4');
    let wasRaceOn = false;

    this.socket.on('message', (msg) => {
      const frame = parsePacket(msg);
      if (frame === null) {
        if (wasRaceOn) {
          wasRaceOn = false;
          this.onRaceOff();
          this.sessionManager.reset();
        }
        return;
      }
      wasRaceOn = true;
      this.sessionManager.onFrame(frame);
      this.onFrame(frame);
    });

    this.socket.bind(port, '127.0.0.1');
  }

  stop(): void {
    this.socket?.close();
    this.socket = null;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add fh6-relay/src/main/udpListener.ts
git commit -m "feat(relay): add UDP listener"
```

---

## Task 9: Electron Main Entry, Tray, and IPC

**Files:**
- Create: `fh6-relay/src/main/preload.ts`
- Create: `fh6-relay/src/main/ipcHandlers.ts`
- Create: `fh6-relay/src/main/index.ts`

- [ ] **Step 1: Create `src/main/preload.ts`**

```typescript
import { contextBridge, ipcRenderer } from 'electron';
import { IPC } from '../shared/types';

// Expose a typed IPC surface to the renderer (no direct Node access)
contextBridge.exposeInMainWorld('ipc', {
  on: (channel: string, listener: (...args: unknown[]) => void) => {
    ipcRenderer.on(channel, (_event, ...args) => listener(...args));
  },
  invoke: (channel: string, ...args: unknown[]) => {
    return ipcRenderer.invoke(channel, ...args);
  },
  IPC,
});
```

- [ ] **Step 2: Create `src/main/ipcHandlers.ts`**

```typescript
import { ipcMain, BrowserWindow } from 'electron';
import { IPC, Config } from '../shared/types';
import { ReplayStore } from './replayStore';
import { ApiClient } from './apiClient';
import { TokenStore } from './tokenStore';

export function registerIpcHandlers(
  store: ReplayStore,
  tokenStore: TokenStore,
  getClient: () => ApiClient | null,
): void {
  ipcMain.handle(IPC.GET_LAP, (_e, lapNumber: number) => {
    return store.getLap(lapNumber);
  });

  ipcMain.handle(IPC.GET_FULL_RACE, () => {
    return store.getFullRace();
  });

  ipcMain.handle(IPC.GET_VEHICLES, async () => {
    const client = getClient();
    if (!client) throw new Error('Not configured');
    return client.getVehicles();
  });

  ipcMain.handle(IPC.GET_TRACKS, async () => {
    const client = getClient();
    if (!client) throw new Error('Not configured');
    return client.getTracks();
  });

  ipcMain.handle(IPC.SUBMIT_LAP, async (_e, payload) => {
    const client = getClient();
    if (!client) throw new Error('Not configured');
    return client.submitLap(payload);
  });

  ipcMain.handle(IPC.CONFIG_GET, () => tokenStore.load());

  ipcMain.handle(IPC.CONFIG_SET, (_e, config: Config) => {
    tokenStore.save(config);
  });
}
```

- [ ] **Step 3: Create `src/main/index.ts`**

```typescript
import { app, BrowserWindow, Tray, Menu, nativeImage, shell } from 'electron';
import * as path from 'path';
import * as os from 'os';
import { SessionManager } from './sessionManager';
import { ReplayStore } from './replayStore';
import { UdpListener } from './udpListener';
import { TokenStore } from './tokenStore';
import { ApiClient } from './apiClient';
import { registerIpcHandlers } from './ipcHandlers';
import { IPC } from '../shared/types';

const CONFIG_DIR = path.join(os.homedir(), 'AppData', 'Roaming', 'FH6BotRelay');
const REPLAY_DIR = path.join(CONFIG_DIR, 'replays');
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;

const tokenStore = new TokenStore(CONFIG_FILE);
const replayStore = new ReplayStore(REPLAY_DIR, tokenStore.load().retentionDays);
const sessionManager = new SessionManager();

let apiClient: ApiClient | null = null;
function buildClient(): void {
  const cfg = tokenStore.load();
  if (cfg.token && cfg.apiUrl && cfg.discordId) {
    apiClient = new ApiClient(cfg.apiUrl, cfg.token, cfg.discordId, cfg.discordUsername);
  }
}
buildClient();

sessionManager.on('lapComplete', ({ lapRecord, frames }) => {
  replayStore.storeLap(lapRecord, frames);
  mainWindow?.webContents.send(IPC.LAP_COMPLETE, lapRecord);
});

const udpListener = new UdpListener(
  sessionManager,
  (frame) => { mainWindow?.webContents.send(IPC.FRAME, frame); },
  () => { mainWindow?.webContents.send(IPC.RACE_OFF); },
);

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
    },
  });
  mainWindow.loadFile(path.join(__dirname, '../../src/renderer/index.html'));
  mainWindow.on('close', (e) => {
    e.preventDefault();
    mainWindow?.hide();
  });
}

function createTray(): void {
  tray = new Tray(nativeImage.createEmpty());
  tray.setToolTip('FH6 Relay');
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Show', click: () => mainWindow?.show() },
    { label: 'Quit', click: () => { mainWindow?.destroy(); app.quit(); } },
  ]));
  tray.on('click', () => mainWindow?.show());
}

app.whenReady().then(() => {
  const cfg = tokenStore.load();
  replayStore.runRetentionCleanup();
  registerIpcHandlers(replayStore, tokenStore, () => apiClient);
  createWindow();
  createTray();
  udpListener.start(cfg.udpPort);
});

app.on('window-all-closed', () => { /* keep running in tray */ });
```

- [ ] **Step 4: Run the app and verify it launches**

```bash
npm start
```

Expected: Electron window opens (blank — no renderer HTML yet). Tray icon appears. No crash.

- [ ] **Step 5: Commit**

```bash
git add fh6-relay/src/main/preload.ts fh6-relay/src/main/ipcHandlers.ts fh6-relay/src/main/index.ts
git commit -m "feat(relay): add Electron entry point, tray, IPC handlers"
```

---

## Task 10: Renderer Shell and Tab Navigation

**Files:**
- Create: `fh6-relay/src/renderer/index.html`
- Create: `fh6-relay/src/renderer/styles/main.css`
- Create: `fh6-relay/src/renderer/main.ts`

- [ ] **Step 1: Create `src/renderer/styles/main.css`**

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: #0f0f0f;
  color: #e0e0e0;
  font-family: system-ui, sans-serif;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

#tab-bar {
  display: flex;
  background: #1a1a1a;
  border-bottom: 1px solid #333;
  padding: 0 1rem;
  gap: 0.25rem;
  flex-shrink: 0;
}

.tab-btn {
  background: none;
  border: none;
  color: #999;
  padding: 0.75rem 1.25rem;
  cursor: pointer;
  font-size: 0.9rem;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}
.tab-btn:hover { color: #e0e0e0; }
.tab-btn.active { color: #3b9dff; border-bottom-color: #3b9dff; }

#tab-content { flex: 1; overflow: hidden; position: relative; }

.tab-pane {
  display: none;
  position: absolute;
  inset: 0;
  padding: 1rem;
  overflow-y: auto;
}
.tab-pane.active { display: block; }
```

- [ ] **Step 2: Create `src/renderer/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy"
        content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'" />
  <title>FH6 Relay</title>
  <link rel="stylesheet" href="styles/main.css" />
</head>
<body>
  <nav id="tab-bar">
    <button class="tab-btn active" data-tab="live">Live</button>
    <button class="tab-btn" data-tab="session">Session</button>
    <button class="tab-btn" data-tab="replay">Replay</button>
  </nav>
  <div id="tab-content">
    <div class="tab-pane active" id="tab-live"></div>
    <div class="tab-pane" id="tab-session"></div>
    <div class="tab-pane" id="tab-replay"></div>
  </div>
  <script type="module" src="../../dist/renderer/main.js"></script>
</body>
</html>
```

- [ ] **Step 3: Create `src/renderer/main.ts`**

```typescript
import { initLiveTab } from './tabs/live';
import { initSessionTab } from './tabs/session';

declare global {
  interface Window {
    ipc: {
      on: (channel: string, listener: (...args: unknown[]) => void) => void;
      invoke: (channel: string, ...args: unknown[]) => Promise<unknown>;
      IPC: Record<string, string>;
    };
  }
}

// Tab switching
document.querySelectorAll<HTMLButtonElement>('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`tab-${btn.dataset.tab}`)!.classList.add('active');
  });
});

initLiveTab(document.getElementById('tab-live')!);
initSessionTab(document.getElementById('tab-session')!);
// Replay tab initialized in Plan 2
```

- [ ] **Step 4: Verify app loads shell**

```bash
npm start
```

Expected: Three tab buttons visible. Clicking switches panes. No JS errors in DevTools.

- [ ] **Step 5: Commit**

```bash
git add fh6-relay/src/renderer/
git commit -m "feat(relay): add renderer shell with tab navigation"
```

---

## Task 11: Track Map Component

**Files:**
- Create: `fh6-relay/src/renderer/charts/trackMap.ts`

Used by the Live tab for accumulating the driven line in real time. Extended by Replay tab in Plan 2.

- [ ] **Step 1: Create `src/renderer/charts/trackMap.ts`**

```typescript
export class TrackMap {
  private ctx: CanvasRenderingContext2D;
  private points: { x: number; z: number }[] = [];
  private minX = Infinity; private maxX = -Infinity;
  private minZ = Infinity; private maxZ = -Infinity;

  constructor(private readonly canvas: HTMLCanvasElement) {
    this.ctx = canvas.getContext('2d')!;
  }

  // Append a single point (live mode)
  addPoint(posX: number, posZ: number): void {
    this.points.push({ x: posX, z: posZ });
    this.minX = Math.min(this.minX, posX);
    this.maxX = Math.max(this.maxX, posX);
    this.minZ = Math.min(this.minZ, posZ);
    this.maxZ = Math.max(this.maxZ, posZ);
  }

  // Load a complete set of points (replay mode)
  loadPoints(posX: number[], posZ: number[]): void {
    this.points = posX.map((x, i) => ({ x, z: posZ[i] }));
    this.minX = Math.min(...posX);
    this.maxX = Math.max(...posX);
    this.minZ = Math.min(...posZ);
    this.maxZ = Math.max(...posZ);
  }

  reset(): void {
    this.points = [];
    this.minX = Infinity; this.maxX = -Infinity;
    this.minZ = Infinity; this.maxZ = -Infinity;
    this.clear();
  }

  private toCanvas(posX: number, posZ: number): { cx: number; cy: number } {
    const pad = 20;
    const rangeX = this.maxX - this.minX || 1;
    const rangeZ = this.maxZ - this.minZ || 1;
    const w = this.canvas.width - pad * 2;
    const h = this.canvas.height - pad * 2;
    return {
      cx: pad + ((posX - this.minX) / rangeX) * w,
      cy: pad + ((posZ - this.minZ) / rangeZ) * h,
    };
  }

  clear(): void {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }

  // Draw the full driven line
  drawLine(): void {
    if (this.points.length < 2) return;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.beginPath();
    ctx.strokeStyle = '#3b9dff';
    ctx.lineWidth = 2;
    const first = this.toCanvas(this.points[0].x, this.points[0].z);
    ctx.moveTo(first.cx, first.cy);
    for (let i = 1; i < this.points.length; i++) {
      const { cx, cy } = this.toCanvas(this.points[i].x, this.points[i].z);
      ctx.lineTo(cx, cy);
    }
    ctx.stroke();
  }

  // Draw a position dot at the given index into points array
  drawDotAtIndex(index: number): void {
    if (index < 0 || index >= this.points.length) return;
    const { cx, cy } = this.toCanvas(this.points[index].x, this.points[index].z);
    const ctx = this.ctx;
    ctx.beginPath();
    ctx.arc(cx, cy, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#ff4444';
    ctx.fill();
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add fh6-relay/src/renderer/charts/trackMap.ts
git commit -m "feat(relay): add Canvas 2D track map component"
```

---

## Task 12: Live Tab

**Files:**
- Create: `fh6-relay/src/renderer/tabs/live.ts`

- [ ] **Step 1: Create `src/renderer/tabs/live.ts`**

```typescript
import { Frame } from '../../shared/types';
import { TrackMap } from '../charts/trackMap';

export function initLiveTab(container: HTMLElement): void {
  container.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;grid-template-rows:auto auto;gap:1rem;height:100%">
      <div style="grid-row:1/3">
        <canvas id="live-map" width="500" height="500" style="width:100%;background:#111;border-radius:4px"></canvas>
      </div>
      <div id="live-gauges" style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap">
        <div>Speed: <span id="live-speed" style="font-size:2rem;font-weight:bold">0</span> km/h</div>
        <div>Gear: <span id="live-gear" style="font-size:2rem;font-weight:bold">N</span></div>
        <div>RPM: <span id="live-rpm">0</span></div>
      </div>
      <div id="live-inputs" style="display:flex;flex-direction:column;gap:0.5rem">
        <label>Throttle <progress id="bar-throttle" max="255" value="0" style="width:100%"></progress></label>
        <label>Brake <progress id="bar-brake" max="255" value="0" style="width:100%"></progress></label>
        <label>Clutch <progress id="bar-clutch" max="255" value="0" style="width:100%"></progress></label>
        <label>Steer <span id="live-steer">0</span></label>
      </div>
    </div>
    <div id="live-idle" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.6);font-size:1.5rem;color:#666">
      Waiting for session…
    </div>
  `;

  const map = new TrackMap(document.getElementById('live-map') as HTMLCanvasElement);
  const idle = document.getElementById('live-idle')!;
  let animFrame: number | null = null;
  let latest: Frame | null = null;

  function render() {
    if (!latest) return;
    const f = latest;
    (document.getElementById('live-speed')!).textContent = Math.round(f.speed * 3.6).toString();
    (document.getElementById('live-gear')!).textContent = f.gear === 0 ? 'R' : String(f.gear);
    (document.getElementById('live-rpm')!).textContent = Math.round(f.rpm).toString();
    (document.getElementById('bar-throttle') as HTMLProgressElement).value = f.throttle;
    (document.getElementById('bar-brake') as HTMLProgressElement).value = f.brake;
    (document.getElementById('bar-clutch') as HTMLProgressElement).value = f.clutch;
    (document.getElementById('live-steer')!).textContent = f.steer.toString();
    map.addPoint(f.posX, f.posZ);
    map.drawLine();
    map.drawDotAtIndex(Infinity as unknown as number); // last point
  }

  window.ipc.on(window.ipc.IPC['FRAME'], (frame: unknown) => {
    latest = frame as Frame;
    idle.style.display = 'none';
    if (animFrame === null) {
      animFrame = requestAnimationFrame(() => { render(); animFrame = null; });
    }
  });

  window.ipc.on(window.ipc.IPC['RACE_OFF'], () => {
    idle.style.display = 'flex';
    map.reset();
  });
}
```

- [ ] **Step 2: Confirm wiring — no changes needed**

`UdpListener` already accepts an `onFrame` callback (Task 8) and `index.ts` already passes `(frame) => mainWindow?.webContents.send(IPC.FRAME, frame)` (Task 9). Frames flow to the renderer automatically.

- [ ] **Step 3: Build and manually test**

```bash
npm start
```

Open FH6, enable Data Out to `127.0.0.1:20440`. Drive. Expected: Live tab shows speed/gear/RPM updating, throttle/brake bars moving, track line accumulating on map.

- [ ] **Step 4: Commit**

```bash
git add fh6-relay/src/renderer/tabs/live.ts fh6-relay/src/main/udpListener.ts fh6-relay/src/main/index.ts
git commit -m "feat(relay): add live tab with real-time gauges and track map"
```

---

## Task 13: Session Tab

**Files:**
- Create: `fh6-relay/src/renderer/tabs/session.ts`

- [ ] **Step 1: Create `src/renderer/tabs/session.ts`**

```typescript
import { LapRecord, ColumnarLap } from '../../shared/types';

function formatTime(ms: number): string {
  const mins = Math.floor(ms / 60000);
  const secs = ((ms % 60000) / 1000).toFixed(3).padStart(6, '0');
  return `${mins}:${secs}`;
}

export function initSessionTab(container: HTMLElement): void {
  container.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:1rem;max-width:900px">
      <div style="display:flex;gap:1rem;align-items:flex-end">
        <div style="flex:1">
          <label>Track<br/>
            <select id="track-select" style="width:100%;padding:0.4rem;background:#1a1a1a;color:#e0e0e0;border:1px solid #333">
              <option value="">Loading…</option>
            </select>
          </label>
        </div>
        <div style="flex:1">
          <label>Vehicle<br/>
            <select id="vehicle-select" style="width:100%;padding:0.4rem;background:#1a1a1a;color:#e0e0e0;border:1px solid #333">
              <option value="">Loading…</option>
            </select>
          </label>
        </div>
        <button id="btn-full-race" style="padding:0.4rem 1rem;background:#333;color:#e0e0e0;border:none;cursor:pointer;border-radius:4px">
          Full Race Replay
        </button>
      </div>
      <table style="width:100%;border-collapse:collapse">
        <thead>
          <tr style="border-bottom:1px solid #333;text-align:left">
            <th style="padding:0.5rem">#</th>
            <th style="padding:0.5rem">Lap Time</th>
            <th style="padding:0.5rem">Actions</th>
          </tr>
        </thead>
        <tbody id="lap-tbody"></tbody>
      </table>
      <div id="session-status" style="color:#888;font-size:0.85rem"></div>
    </div>
  `;

  const tbody = document.getElementById('lap-tbody')!;
  const status = document.getElementById('session-status')!;
  let laps: LapRecord[] = [];
  let bestMs = Infinity;

  // Load dropdowns
  async function loadDropdowns() {
    try {
      const [tracks, vehicles] = await Promise.all([
        window.ipc.invoke(window.ipc.IPC['GET_TRACKS']),
        window.ipc.invoke(window.ipc.IPC['GET_VEHICLES']),
      ]) as [string[], string[]];

      const trackSel = document.getElementById('track-select') as HTMLSelectElement;
      const vehicleSel = document.getElementById('vehicle-select') as HTMLSelectElement;
      trackSel.innerHTML = tracks.map(t => `<option value="${t}">${t}</option>`).join('');
      vehicleSel.innerHTML = vehicles.map(v => `<option value="${v}">${v}</option>`).join('');
    } catch (e) {
      status.textContent = `Failed to load tracks/vehicles: ${e}`;
    }
  }
  loadDropdowns();

  function renderTable() {
    tbody.innerHTML = laps.map(lap => {
      const isBest = lap.lapTimeMs === bestMs;
      return `
        <tr style="border-bottom:1px solid #222;${isBest ? 'color:#3b9dff' : ''}">
          <td style="padding:0.5rem">${lap.lapNumber}</td>
          <td style="padding:0.5rem">${formatTime(lap.lapTimeMs)}</td>
          <td style="padding:0.5rem;display:flex;gap:0.5rem">
            <button class="btn-replay" data-lap="${lap.lapNumber}"
              style="padding:0.3rem 0.7rem;background:#333;color:#e0e0e0;border:none;cursor:pointer;border-radius:4px">
              Replay
            </button>
            <button class="btn-submit" data-lap="${lap.lapNumber}"
              style="padding:0.3rem 0.7rem;background:#3b9dff;color:#fff;border:none;cursor:pointer;border-radius:4px">
              Submit
            </button>
          </td>
        </tr>
      `;
    }).join('');

    tbody.querySelectorAll<HTMLButtonElement>('.btn-replay').forEach(btn => {
      btn.addEventListener('click', () => openReplay(Number(btn.dataset.lap)));
    });

    tbody.querySelectorAll<HTMLButtonElement>('.btn-submit').forEach(btn => {
      btn.addEventListener('click', () => submitLap(Number(btn.dataset.lap)));
    });
  }

  function openReplay(lapNumber: number) {
    // Switch to Replay tab and pass lap number
    const replayBtn = document.querySelector<HTMLButtonElement>('[data-tab="replay"]')!;
    replayBtn.click();
    window.dispatchEvent(new CustomEvent('open-replay', { detail: { lapNumber } }));
  }

  document.getElementById('btn-full-race')!.addEventListener('click', () => {
    const replayBtn = document.querySelector<HTMLButtonElement>('[data-tab="replay"]')!;
    replayBtn.click();
    window.dispatchEvent(new CustomEvent('open-replay', { detail: { lapNumber: -1 } }));
  });

  async function submitLap(lapNumber: number) {
    const lap = laps.find(l => l.lapNumber === lapNumber);
    if (!lap) return;
    const track = (document.getElementById('track-select') as HTMLSelectElement).value;
    const vehicleName = (document.getElementById('vehicle-select') as HTMLSelectElement).value;
    if (!track || !vehicleName) { status.textContent = 'Select a track and vehicle first.'; return; }
    status.textContent = 'Submitting…';
    try {
      const result = await window.ipc.invoke(window.ipc.IPC['SUBMIT_LAP'], {
        lapTimeMs: lap.lapTimeMs,
        track,
        vehicleName,
        carClassInt: lap.carClass,
        carOrdinal: lap.carOrdinal,
      }) as { entry_id: number };
      status.textContent = `Submitted! Entry #${result.entry_id}`;
    } catch (e) {
      status.textContent = `Submit failed: ${e}`;
    }
  }

  window.ipc.on(window.ipc.IPC['LAP_COMPLETE'], (record: unknown) => {
    const lap = record as LapRecord;
    laps.push(lap);
    if (lap.lapTimeMs < bestMs) bestMs = lap.lapTimeMs;
    renderTable();
  });
}
```

- [ ] **Step 2: Build and test manually**

```bash
npm start
```

Expected: Session tab shows track/vehicle dropdowns (populated from bot API). After driving a lap, the lap appears in the table with Replay and Submit buttons. Submit sends to bot.

- [ ] **Step 3: Commit**

```bash
git add fh6-relay/src/renderer/tabs/session.ts
git commit -m "feat(relay): add session tab with lap table, dropdowns, and submit"
```

---

## Task 14: Settings Panel

**Files:**
- Create: `fh6-relay/src/renderer/tabs/settings.ts`
- Modify: `fh6-relay/src/renderer/main.ts`
- Modify: `fh6-relay/src/renderer/index.html`

The Settings panel is accessible from a gear icon button in the tab bar (not a tray menu item — tray is harder to test and the tab bar is always visible).

- [ ] **Step 1: Add Settings tab button to `index.html`**

Add after the existing Replay button in `<nav id="tab-bar">`:

```html
<button class="tab-btn" data-tab="settings" style="margin-left:auto">⚙ Settings</button>
```

Add a corresponding pane in `<div id="tab-content">`:

```html
<div class="tab-pane" id="tab-settings"></div>
```

- [ ] **Step 2: Create `src/renderer/tabs/settings.ts`**

```typescript
export function initSettingsTab(container: HTMLElement): void {
  container.innerHTML = `
    <div style="max-width:500px;display:flex;flex-direction:column;gap:1rem">
      <h2 style="font-size:1.1rem;margin:0">Settings</h2>

      <label>Bot API URL
        <input id="cfg-api-url" type="text" placeholder="https://your-bot.example.com"
          style="display:block;width:100%;padding:0.4rem;margin-top:0.25rem;background:#1a1a1a;color:#e0e0e0;border:1px solid #333;border-radius:4px" />
      </label>

      <label>Discord User ID
        <input id="cfg-discord-id" type="text" placeholder="123456789012345678"
          style="display:block;width:100%;padding:0.4rem;margin-top:0.25rem;background:#1a1a1a;color:#e0e0e0;border:1px solid #333;border-radius:4px" />
      </label>

      <label>Discord Username
        <input id="cfg-discord-username" type="text" placeholder="playername"
          style="display:block;width:100%;padding:0.4rem;margin-top:0.25rem;background:#1a1a1a;color:#e0e0e0;border:1px solid #333;border-radius:4px" />
      </label>

      <label>Token
        <input id="cfg-token" type="password" placeholder="Paste token from /dataout-register"
          style="display:block;width:100%;padding:0.4rem;margin-top:0.25rem;background:#1a1a1a;color:#e0e0e0;border:1px solid #333;border-radius:4px" />
      </label>

      <label>UDP Port
        <input id="cfg-udp-port" type="number" min="1024" max="65535"
          style="display:block;width:100%;padding:0.4rem;margin-top:0.25rem;background:#1a1a1a;color:#e0e0e0;border:1px solid #333;border-radius:4px" />
      </label>

      <label>Replay Retention (days)
        <input id="cfg-retention" type="number" min="1"
          style="display:block;width:100%;padding:0.4rem;margin-top:0.25rem;background:#1a1a1a;color:#e0e0e0;border:1px solid #333;border-radius:4px" />
      </label>

      <button id="cfg-save"
        style="padding:0.5rem 1.5rem;background:#3b9dff;color:#fff;border:none;cursor:pointer;border-radius:4px;align-self:flex-start">
        Save
      </button>
      <div id="cfg-status" style="color:#aaa;font-size:0.85rem"></div>
    </div>
  `;

  const fields = {
    apiUrl:          document.getElementById('cfg-api-url') as HTMLInputElement,
    discordId:       document.getElementById('cfg-discord-id') as HTMLInputElement,
    discordUsername: document.getElementById('cfg-discord-username') as HTMLInputElement,
    token:           document.getElementById('cfg-token') as HTMLInputElement,
    udpPort:         document.getElementById('cfg-udp-port') as HTMLInputElement,
    retentionDays:   document.getElementById('cfg-retention') as HTMLInputElement,
  };
  const status = document.getElementById('cfg-status')!;

  // Load current config
  window.ipc.invoke(window.ipc.IPC['CONFIG_GET']).then((cfg: unknown) => {
    const c = cfg as Record<string, unknown>;
    fields.apiUrl.value          = String(c.apiUrl ?? '');
    fields.discordId.value       = String(c.discordId ?? '');
    fields.discordUsername.value = String(c.discordUsername ?? '');
    fields.token.value           = String(c.token ?? '');
    fields.udpPort.value         = String(c.udpPort ?? 20440);
    fields.retentionDays.value   = String(c.retentionDays ?? 30);
  });

  document.getElementById('cfg-save')!.addEventListener('click', async () => {
    const config = {
      apiUrl:          fields.apiUrl.value.trim(),
      discordId:       fields.discordId.value.trim(),
      discordUsername: fields.discordUsername.value.trim(),
      token:           fields.token.value.trim(),
      udpPort:         Number(fields.udpPort.value) || 20440,
      retentionDays:   Number(fields.retentionDays.value) || 30,
    };
    await window.ipc.invoke(window.ipc.IPC['CONFIG_SET'], config);
    status.textContent = 'Saved. Restart the app for UDP port changes to take effect.';
  });
}
```

- [ ] **Step 3: Wire up in `main.ts`**

```typescript
import { initSettingsTab } from './tabs/settings';
// ...
initSettingsTab(document.getElementById('tab-settings')!);
```

- [ ] **Step 4: Build and test**

```bash
npm start
```

Expected: Settings tab appears. Loads existing config values. Saving updates config. Navigating away and back retains values.

- [ ] **Step 5: Commit**

```bash
git add fh6-relay/src/renderer/tabs/settings.ts fh6-relay/src/renderer/main.ts fh6-relay/src/renderer/index.html
git commit -m "feat(relay): add settings tab for config management"
```

---

## Task 15: Run All Tests and Final Build Verification

- [ ] **Step 1: Run full test suite**

```bash
cd fh6-relay && npx jest
```

Expected: All tests pass (packetParser, sessionManager, replayStore, tokenStore, apiClient).

- [ ] **Step 2: Build production bundle**

```bash
npm run build
```

Expected: `dist/main/` and `dist/renderer/` populated, no TypeScript errors.

- [ ] **Step 3: Run packaged app**

```bash
npm run pack
```

Expected: `release/win-unpacked/FH6 Relay.exe` produced. Launch it, verify tray appears, window opens, tabs work.

- [ ] **Step 4: Final commit**

```bash
git add fh6-relay/
git commit -m "chore(relay): verify full build and test suite for Plan 1"
```

---

## What's Next

Plan 2 (`2026-05-29-electron-relay-replay.md`) implements the Replay tab: all Chart.js time-series charts, the static analysis panel, the animated playback loop, and the timeline scrubber.
