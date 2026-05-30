# Electron Relay — Replay Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Replay tab for the fh6-relay Electron app — a scrollable static analysis panel with nine Chart.js charts sharing a time axis, an animated Canvas 2D track map, and a fixed playback bar with scrubbing and speed control.

**Architecture:** A `ChartManager` class owns all Chart.js instances and exposes a single `setPlayhead(index)` method that draws the vertical playhead line across every chart simultaneously. The `TrackMap` component from Plan 1 is extended with a `drawDotAtIndex()` fix. The `ReplayTab` module orchestrates data loading, chart rendering, and the `requestAnimationFrame` animation loop.

**Tech Stack:** Chart.js 4 (time-series charts), Canvas 2D (track map), `requestAnimationFrame` (animation loop). No new dependencies beyond Plan 1.

**Prerequisite:** Plan 1 (`2026-05-29-electron-relay-core.md`) must be fully implemented and passing before starting this plan.

---

## File Map

| Path | Role |
|------|------|
| `fh6-relay/src/renderer/charts/chartManager.ts` | Creates and owns all Chart.js instances; exposes `load()` and `setPlayhead()` |
| `fh6-relay/src/renderer/tabs/replay.ts` | Replay tab: layout, lap selector, playback controls, animation loop |
| `fh6-relay/src/renderer/charts/trackMap.ts` | **Modify** — fix `drawDotAtIndex()` to accept a valid index (Plan 1 had a placeholder) |

---

## Task 1: Fix TrackMap `drawDotAtIndex`

Plan 1's `live.ts` called `drawDotAtIndex(Infinity)` as a placeholder for "last point". Fix this properly.

**Files:**
- Modify: `fh6-relay/src/renderer/charts/trackMap.ts`
- Modify: `fh6-relay/src/renderer/tabs/live.ts`

- [ ] **Step 1: Fix `drawDotAtIndex` and add `drawDotAtLast` helper in `trackMap.ts`**

Replace the existing `drawDotAtIndex` method with:

```typescript
// Draw a position dot at the given index
drawDotAtIndex(index: number): void {
  if (this.points.length === 0) return;
  const clamped = Math.max(0, Math.min(index, this.points.length - 1));
  const { cx, cy } = this.toCanvas(this.points[clamped].x, this.points[clamped].z);
  const ctx = this.ctx;
  ctx.beginPath();
  ctx.arc(cx, cy, 5, 0, Math.PI * 2);
  ctx.fillStyle = '#ff4444';
  ctx.fill();
}

// Convenience: draw dot at the most recently added point
drawDotAtLast(): void {
  this.drawDotAtIndex(this.points.length - 1);
}
```

- [ ] **Step 2: Fix `live.ts` to use `drawDotAtLast()`**

In `src/renderer/tabs/live.ts`, replace:

```typescript
map.drawDotAtIndex(Infinity as unknown as number); // last point
```

with:

```typescript
map.drawDotAtLast();
```

- [ ] **Step 3: Build and verify Live tab still works**

```bash
cd fh6-relay && npm start
```

Expected: Live tab track map shows red dot at current position. No TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add fh6-relay/src/renderer/charts/trackMap.ts fh6-relay/src/renderer/tabs/live.ts
git commit -m "fix(relay): fix trackMap drawDotAtIndex, add drawDotAtLast helper"
```

---

## Task 2: Chart Manager

**Files:**
- Create: `fh6-relay/src/renderer/charts/chartManager.ts`

The `ChartManager` creates all nine Chart.js chart instances and provides:
- `load(fields)` — populates all charts with columnar data
- `setPlayhead(index)` — draws/moves the vertical playhead line across all charts
- `destroy()` — tears down Chart.js instances on tab switch

- [ ] **Step 1: Create `src/renderer/charts/chartManager.ts`**

```typescript
import { Chart, ChartConfiguration, registerables } from 'chart.js';
import { ColumnarLap } from '../../shared/types';

Chart.register(...registerables);

type ChartEntry = { chart: Chart; canvasId: string };

function makeLineChart(
  canvasId: string,
  label: string | string[],
  colors: string | string[],
  yLabel: string,
): Chart {
  const canvas = document.getElementById(canvasId) as HTMLCanvasElement;
  const labels_ = Array.isArray(label) ? label : [label];
  const colors_ = Array.isArray(colors) ? colors : [colors];

  const cfg: ChartConfiguration = {
    type: 'line',
    data: {
      labels: [],
      datasets: labels_.map((l, i) => ({
        label: l,
        data: [],
        borderColor: colors_[i],
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0,
      })),
    },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#aaa', boxWidth: 12, font: { size: 11 } } },
        annotation: {},  // populated by setPlayhead
      },
      scales: {
        x: { ticks: { color: '#666', maxTicksLimit: 10 }, grid: { color: '#222' } },
        y: { ticks: { color: '#aaa' }, grid: { color: '#222' }, title: { display: true, text: yLabel, color: '#666' } },
      },
    },
  };
  return new Chart(canvas, cfg);
}

export class ChartManager {
  private entries: ChartEntry[] = [];
  private charts: Chart[] = [];

  createAll(): void {
    this.charts = [
      makeLineChart('chart-elevation', 'Elevation', '#4ecdc4', 'Y (m)'),
      makeLineChart('chart-speed', 'Speed', '#ffe66d', 'km/h'),
      makeLineChart(
        'chart-inputs',
        ['Throttle', 'Brake', 'Clutch', 'Handbrake', 'Steer'],
        ['#2ecc71', '#e74c3c', '#9b59b6', '#e67e22', '#3498db'],
        '0–255 / -127–127',
      ),
      makeLineChart('chart-gear', 'Gear', '#f39c12', 'Gear'),
      makeLineChart('chart-rpm', 'RPM', '#e74c3c', 'RPM'),
      makeLineChart('chart-boost', 'Boost', '#1abc9c', 'PSI'),
      makeLineChart(
        'chart-tire-temp',
        ['FL', 'FR', 'RL', 'RR'],
        ['#e74c3c', '#3498db', '#2ecc71', '#f39c12'],
        '°C',
      ),
      makeLineChart(
        'chart-tire-slip',
        ['FL', 'FR', 'RL', 'RR'],
        ['#e74c3c', '#3498db', '#2ecc71', '#f39c12'],
        'Slip',
      ),
      makeLineChart(
        'chart-suspension',
        ['FL', 'FR', 'RL', 'RR'],
        ['#e74c3c', '#3498db', '#2ecc71', '#f39c12'],
        'm',
      ),
    ];
  }

  load(col: ColumnarLap): void {
    const f = col.fields;
    const tLabels = f.t.map(t => t.toFixed(2));
    const speedKmh = f.speed.map(s => s * 3.6);

    const datasets: (number[] | number[][])[] = [
      [f.posY],
      [speedKmh],
      [f.throttle, f.brake, f.clutch, f.handbrake, f.steer],
      [f.gear],
      [f.rpm],
      [f.boost],
      [f.tireTempFL, f.tireTempFR, f.tireTempRL, f.tireTempRR],
      [f.tireSlipFL, f.tireSlipFR, f.tireSlipRL, f.tireSlipRR],
      [f.suspFL, f.suspFR, f.suspRL, f.suspRR],
    ];

    this.charts.forEach((chart, i) => {
      chart.data.labels = tLabels;
      const ds = datasets[i];
      chart.data.datasets.forEach((dataset, j) => {
        dataset.data = ds[j] ?? ds[0];
      });
      chart.update('none');
    });
  }

  // Draw a vertical line at the given frame index across all charts
  setPlayhead(frameIndex: number): void {
    this.charts.forEach(chart => {
      const meta = chart.data.labels as string[];
      if (!meta || frameIndex >= meta.length) return;
      const xPos = chart.scales['x'].getPixelForValue(meta[frameIndex]);
      const { top, bottom } = chart.scales['y'];
      const ctx = chart.ctx;
      ctx.save();
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(255,255,255,0.8)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      ctx.moveTo(xPos, top);
      ctx.lineTo(xPos, bottom);
      ctx.stroke();
      ctx.restore();
      // Re-draw next update will clear this — we call chart.draw() in animation loop
    });
  }

  // Redraw all charts then draw the playhead line on top.
  // Must be called as: redrawAll() then setPlayhead() — chart.draw() clears the canvas.
  redrawAll(): void {
    this.charts.forEach(c => c.draw());
  }

  destroy(): void {
    this.charts.forEach(c => c.destroy());
    this.charts = [];
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add fh6-relay/src/renderer/charts/chartManager.ts
git commit -m "feat(relay): add ChartManager with all nine Chart.js instances"
```

---

## Task 3: Replay Tab Layout

**Files:**
- Create: `fh6-relay/src/renderer/tabs/replay.ts`
- Modify: `fh6-relay/src/renderer/main.ts` (wire up replay tab init)

- [ ] **Step 1: Create the replay tab HTML structure in `src/renderer/tabs/replay.ts`**

```typescript
import { ColumnarLap } from '../../shared/types';
import { ChartManager } from '../charts/chartManager';
import { TrackMap } from '../charts/trackMap';

export function initReplayTab(container: HTMLElement): void {
  container.innerHTML = `
    <div style="display:flex;flex-direction:column;height:100%;overflow:hidden">

      <!-- Lap selector -->
      <div style="padding:0.5rem 0;display:flex;gap:0.5rem;align-items:center;flex-shrink:0">
        <label style="font-size:0.9rem;color:#aaa">Viewing:</label>
        <select id="replay-lap-select"
          style="padding:0.3rem 0.6rem;background:#1a1a1a;color:#e0e0e0;border:1px solid #333;border-radius:4px">
          <option value="">—</option>
        </select>
        <span id="replay-lap-info" style="color:#666;font-size:0.85rem"></span>
      </div>

      <!-- Scrollable analysis panel -->
      <div id="replay-charts-panel" style="flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:1rem;padding-bottom:80px">
        <canvas id="replay-map" width="600" height="280"
          style="width:100%;background:#111;border-radius:4px;max-height:280px"></canvas>

        <div class="chart-wrap"><canvas id="chart-elevation"></canvas></div>
        <div class="chart-wrap"><canvas id="chart-speed"></canvas></div>
        <div class="chart-wrap"><canvas id="chart-inputs"></canvas></div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">
          <div class="chart-wrap"><canvas id="chart-gear"></canvas></div>
          <div class="chart-wrap"><canvas id="chart-rpm"></canvas></div>
        </div>
        <div class="chart-wrap"><canvas id="chart-boost"></canvas></div>
        <div class="chart-wrap"><canvas id="chart-tire-temp"></canvas></div>
        <div class="chart-wrap"><canvas id="chart-tire-slip"></canvas></div>
        <div class="chart-wrap"><canvas id="chart-suspension"></canvas></div>
      </div>

      <!-- Fixed playback bar -->
      <div id="replay-playback-bar" style="
        position:fixed;bottom:0;left:0;right:0;
        background:#1a1a1a;border-top:1px solid #333;
        padding:0.5rem 1rem;display:flex;flex-direction:column;gap:0.3rem;
        z-index:100
      ">
        <div style="display:flex;gap:1rem;align-items:center;font-size:0.85rem;color:#aaa">
          <span id="playhead-readout">Speed: — | Gear: — | Throttle: — | Brake: — | Steer: —</span>
          <span id="playhead-time" style="margin-left:auto;font-variant-numeric:tabular-nums">0:00.000</span>
        </div>
        <div style="display:flex;gap:0.75rem;align-items:center">
          <button id="btn-play-pause" style="padding:0.3rem 0.8rem;background:#333;color:#e0e0e0;border:none;cursor:pointer;border-radius:4px;min-width:60px">Play</button>
          <select id="speed-select" style="padding:0.3rem;background:#1a1a1a;color:#e0e0e0;border:1px solid #333;border-radius:4px">
            <option value="0.25">0.25×</option>
            <option value="0.5">0.5×</option>
            <option value="1" selected>1×</option>
            <option value="2">2×</option>
            <option value="4">4×</option>
          </select>
          <input type="range" id="timeline-scrubber" min="0" max="100" value="0"
            style="flex:1;accent-color:#3b9dff" />
        </div>
      </div>
    </div>
  `;

  // Add chart-wrap style
  const style = document.createElement('style');
  style.textContent = `.chart-wrap { height: 160px; position: relative; background: #111; border-radius: 4px; padding: 4px; }`;
  document.head.appendChild(style);

  // Initialize sub-modules (Tasks 4 and 5 complete these)
  const chartManager = new ChartManager();
  const trackMap = new TrackMap(document.getElementById('replay-map') as HTMLCanvasElement);

  initReplayLogic(chartManager, trackMap);
}

function initReplayLogic(chartManager: ChartManager, trackMap: TrackMap): void {
  // Implemented in Tasks 4 and 5
}
```

- [ ] **Step 2: Wire replay tab in `src/renderer/main.ts`**

Add import and call after `initSessionTab`:

```typescript
import { initReplayTab } from './tabs/replay';
// ...
initReplayTab(document.getElementById('tab-replay')!);
```

- [ ] **Step 3: Build and verify layout**

```bash
npm start
```

Switch to Replay tab. Expected: Empty charts panel visible, playback bar fixed at bottom, lap selector at top. No errors.

- [ ] **Step 4: Commit**

```bash
git add fh6-relay/src/renderer/tabs/replay.ts fh6-relay/src/renderer/main.ts
git commit -m "feat(relay): add replay tab layout shell"
```

---

## Task 4: Load and Render Lap Data

**Files:**
- Modify: `fh6-relay/src/renderer/tabs/replay.ts`

This task populates `initReplayLogic` to load data when the tab receives an `open-replay` event, build the lap selector, and render all charts.

- [ ] **Step 1: Replace `initReplayLogic` in `replay.ts` with the data loading implementation**

```typescript
function initReplayLogic(chartManager: ChartManager, trackMap: TrackMap): void {
  chartManager.createAll();

  let currentData: ColumnarLap | null = null;
  let lapList: Array<{ lapNumber: number; lapTimeMs: number }> = [];

  const lapSelect = document.getElementById('replay-lap-select') as HTMLSelectElement;
  const lapInfo = document.getElementById('replay-lap-info')!;
  const scrubber = document.getElementById('timeline-scrubber') as HTMLInputElement;

  function formatMs(ms: number): string {
    const mins = Math.floor(ms / 60000);
    const secs = ((ms % 60000) / 1000).toFixed(3).padStart(6, '0');
    return `${mins}:${secs}`;
  }

  async function loadLap(lapNumber: number): Promise<void> {
    const ipcChannel = lapNumber === -1
      ? window.ipc.IPC['GET_FULL_RACE']
      : window.ipc.IPC['GET_LAP'];
    const data = await window.ipc.invoke(ipcChannel, lapNumber) as ColumnarLap | null;
    if (!data) { lapInfo.textContent = 'No data'; return; }

    currentData = data;
    scrubber.max = String(data.frameCount - 1);
    scrubber.value = '0';
    lapInfo.textContent = `${data.frameCount} frames · ${formatMs(data.lapTimeMs)}`;

    chartManager.load(data);
    trackMap.loadPoints(data.fields.posX, data.fields.posZ);
    trackMap.reset();
    trackMap.loadPoints(data.fields.posX, data.fields.posZ);
    trackMap.drawLine();
    trackMap.drawDotAtIndex(0);

    setPlayheadAt(0);
    stopPlayback();
  }

  function setPlayheadAt(index: number): void {
    if (!currentData) return;
    const f = currentData.fields;
    const i = Math.max(0, Math.min(index, currentData.frameCount - 1));

    // Update readout
    const speed = Math.round((f.speed[i] ?? 0) * 3.6);
    const gear = f.gear[i] ?? 0;
    const throttle = Math.round(((f.throttle[i] ?? 0) / 255) * 100);
    const brake = Math.round(((f.brake[i] ?? 0) / 255) * 100);
    const steer = f.steer[i] ?? 0;
    document.getElementById('playhead-readout')!.textContent =
      `Speed: ${speed} km/h | Gear: ${gear === 0 ? 'R' : gear} | Throttle: ${throttle}% | Brake: ${brake}% | Steer: ${steer}`;

    const t = f.t[i] ?? 0;
    document.getElementById('playhead-time')!.textContent = formatMs(t * 1000);

    scrubber.value = String(i);
    chartManager.redrawAll();
    chartManager.setPlayhead(i);

    trackMap.drawLine();
    trackMap.drawDotAtIndex(i);
  }

  // Populate lap selector when a new lap is recorded
  window.ipc.on(window.ipc.IPC['LAP_COMPLETE'], (record: unknown) => {
    const lap = record as { lapNumber: number; lapTimeMs: number };
    lapList.push(lap);
    rebuildLapSelect();
  });

  function rebuildLapSelect(): void {
    const prev = lapSelect.value;
    lapSelect.innerHTML =
      '<option value="-1">Full Race</option>' +
      lapList.map(l => `<option value="${l.lapNumber}">Lap ${l.lapNumber} — ${formatMs(l.lapTimeMs)}</option>`).join('');
    lapSelect.value = prev || '-1';
  }

  lapSelect.addEventListener('change', () => loadLap(Number(lapSelect.value)));

  scrubber.addEventListener('input', () => {
    stopPlayback();
    setPlayheadAt(Number(scrubber.value));
  });

  // Triggered from Session tab
  window.addEventListener('open-replay', (e: Event) => {
    const { lapNumber } = (e as CustomEvent).detail as { lapNumber: number };
    rebuildLapSelect();
    lapSelect.value = String(lapNumber);
    loadLap(lapNumber);
  });

  // Playback — wired in Task 5
  (window as any).__replaySetPlayheadAt = setPlayheadAt;
  (window as any).__replayGetData = () => currentData;
}
```

- [ ] **Step 2: Build and test**

```bash
npm start
```

Drive a lap. Go to Session tab, click "Replay" on the lap. Expected: Replay tab populates — all nine charts show data, track map draws the driven line, playhead at frame 0.

- [ ] **Step 3: Commit**

```bash
git add fh6-relay/src/renderer/tabs/replay.ts
git commit -m "feat(relay): load and render lap data in replay tab"
```

---

## Task 5: Playback Animation Loop

**Files:**
- Modify: `fh6-relay/src/renderer/tabs/replay.ts`

- [ ] **Step 1: Add playback state and animation loop to `initReplayLogic`**

Append the following to the end of `initReplayLogic` (before the closing `}`):

```typescript
  // --- Playback ---
  let playing = false;
  let rafHandle: number | null = null;
  let playheadIndex = 0;
  let lastTimestamp = 0;

  const playPauseBtn = document.getElementById('btn-play-pause')!;
  const speedSelect = document.getElementById('speed-select') as HTMLSelectElement;

  function tick(timestamp: number): void {
    if (!playing || !currentData) return;

    const elapsed = timestamp - lastTimestamp;
    lastTimestamp = timestamp;

    const speed = Number(speedSelect.value);
    // Each frame represents ~8.33ms at 120Hz; advance proportionally
    const framesToAdvance = (elapsed * speed) / (1000 / 120);
    playheadIndex = Math.min(
      Math.floor(playheadIndex + framesToAdvance),
      currentData.frameCount - 1,
    );

    setPlayheadAt(playheadIndex);

    if (playheadIndex >= currentData.frameCount - 1) {
      stopPlayback();
      return;
    }

    rafHandle = requestAnimationFrame(tick);
  }

  function startPlayback(): void {
    if (!currentData) return;
    playing = true;
    playPauseBtn.textContent = 'Pause';
    lastTimestamp = performance.now();
    rafHandle = requestAnimationFrame(tick);
  }

  function stopPlayback(): void {
    playing = false;
    playPauseBtn.textContent = 'Play';
    if (rafHandle !== null) { cancelAnimationFrame(rafHandle); rafHandle = null; }
  }

  playPauseBtn.addEventListener('click', () => {
    if (playing) {
      stopPlayback();
    } else {
      // If at end, restart from beginning
      if (currentData && playheadIndex >= currentData.frameCount - 1) {
        playheadIndex = 0;
        setPlayheadAt(0);
      }
      startPlayback();
    }
  });
```

Also remove the placeholder `stopPlayback()` call from Task 4's `loadLap` and replace with a proper reference. Since `stopPlayback` is now defined in scope, `loadLap` already calls it correctly via closure if the function is defined before `loadLap`. Move `stopPlayback` definition before `loadLap` in the final code, or hoist it.

**Final ordering in `initReplayLogic`:**
1. `chartManager.createAll()`
2. State variables (`currentData`, `lapList`, `playing`, etc.)
3. DOM element refs
4. `formatMs()`
5. `stopPlayback()` — must be defined before `loadLap`
6. `startPlayback()`
7. `tick()`
8. `setPlayheadAt()`
9. `loadLap()`
10. Event listeners

- [ ] **Step 2: Build and test playback**

```bash
npm start
```

Load a lap in Replay tab. Click Play. Expected:
- Playhead line sweeps across all charts in sync
- Red dot moves along track map
- Speed/gear/throttle readout updates
- Play button changes to Pause
- Clicking Pause stops animation
- Scrubbing while paused moves playhead correctly
- Speed selector (0.25×, 1×, 4×) changes animation speed

- [ ] **Step 3: Test Full Race mode**

Drive two laps. In Session tab click "Full Race Replay". Expected: Timeline covers both laps (second lap's t values offset by first lap duration), all charts show continuous data across both laps.

- [ ] **Step 4: Commit**

```bash
git add fh6-relay/src/renderer/tabs/replay.ts
git commit -m "feat(relay): add playback animation loop with speed control and scrubbing"
```

---

## Task 6: Run All Tests and Final Verification

- [ ] **Step 1: Run full test suite**

```bash
cd fh6-relay && npx jest
```

Expected: All tests still pass.

- [ ] **Step 2: Manual end-to-end test**

Run the app, drive 3 laps, then verify:

| Check | Expected |
|-------|----------|
| Live tab | Speed/RPM/gear update in real time; track line builds; red dot moves |
| Lap complete | Session tab updates lap table automatically |
| Per-lap replay | Click Replay on Lap 2; all 9 charts load; track map shows lap 2 line |
| Playback | Play button animates; pause stops; scrub moves playhead across all charts simultaneously |
| Speed control | 4× feels fast; 0.25× is slow-motion |
| Full Race | Timeline spans all 3 laps; no discontinuities |
| Submit | Sends to bot; status shows "Submitted! Entry #..." |
| Tray | Minimize to tray; tray click restores window |
| Retention | Settings panel saves retention days; restart respects new value |

- [ ] **Step 3: Build installer**

```bash
npm run dist
```

Expected: `release/FH6 Relay Setup 2.0.0.exe` produced.

- [ ] **Step 4: Final commit**

```bash
git add fh6-relay/
git commit -m "feat(relay): complete replay viewer — charts, playback, full race mode"
```
