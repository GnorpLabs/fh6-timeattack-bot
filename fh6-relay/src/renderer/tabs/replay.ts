import { ColumnarLap, Frame } from '../../shared/types';
import { TrackMap } from '../charts/trackMap';

function formatTime(ms: number): string {
  const mins = Math.floor(ms / 60000);
  const secs = ((ms % 60000) / 1000).toFixed(3).padStart(6, '0');
  return `${mins}:${secs}`;
}

export function initReplayTab(container: HTMLElement): void {
  container.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:1rem;height:100%">
      <div style="display:flex;align-items:center;gap:1rem;flex-wrap:wrap">
        <span id="replay-title" style="font-size:1rem;color:#888">No replay loaded</span>
        <button id="replay-play"  style="padding:0.3rem 0.9rem;background:#3b9dff;color:#fff;border:none;cursor:pointer;border-radius:4px" disabled>Play</button>
        <button id="replay-pause" style="padding:0.3rem 0.9rem;background:#333;color:#e0e0e0;border:none;cursor:pointer;border-radius:4px" disabled>Pause</button>
        <input id="replay-scrub" type="range" min="0" value="0" style="flex:1;min-width:120px" disabled />
        <span id="replay-time" style="font-size:0.85rem;color:#aaa">0:00.000</span>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;grid-template-rows:auto auto;gap:1rem;flex:1">
        <div style="grid-row:1/3">
          <canvas id="replay-map" width="500" height="500" style="width:100%;background:#111;border-radius:4px"></canvas>
        </div>

        <div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap">
          <div>Speed: <span id="replay-speed" style="font-size:2rem;font-weight:bold">0</span> km/h</div>
          <div>Gear: <span id="replay-gear" style="font-size:2rem;font-weight:bold">N</span></div>
          <div>RPM: <span id="replay-rpm">0</span></div>
        </div>

        <div style="display:flex;flex-direction:column;gap:0.5rem">
          <label>Throttle <progress id="replay-bar-throttle" max="255" value="0" style="width:100%"></progress></label>
          <label>Brake    <progress id="replay-bar-brake"    max="255" value="0" style="width:100%"></progress></label>
          <label>Clutch   <progress id="replay-bar-clutch"   max="255" value="0" style="width:100%"></progress></label>
          <label>Steer    <span id="replay-steer">0</span></label>
        </div>
      </div>
    </div>
  `;

  const map       = new TrackMap(document.getElementById('replay-map') as HTMLCanvasElement);
  const titleEl   = document.getElementById('replay-title')!;
  const playBtn   = document.getElementById('replay-play')  as HTMLButtonElement;
  const pauseBtn  = document.getElementById('replay-pause') as HTMLButtonElement;
  const scrub     = document.getElementById('replay-scrub') as HTMLInputElement;
  const timeEl    = document.getElementById('replay-time')!;

  let frames: Frame[] = [];
  let frameIndex = 0;
  let playing = false;
  let rafId: number | null = null;
  let lastRealTs = 0;
  let playheadMs = 0;

  // ---- helpers -------------------------------------------------------

  function clampIdx(i: number): number {
    return Math.max(0, Math.min(i, frames.length - 1));
  }

  function renderFrame(f: Frame): void {
    (document.getElementById('replay-speed')!).textContent    = Math.round(f.speed * 3.6).toString();
    (document.getElementById('replay-gear')!).textContent     = f.gear === 0 ? 'R' : String(f.gear);
    (document.getElementById('replay-rpm')!).textContent      = Math.round(f.rpm).toString();
    (document.getElementById('replay-bar-throttle') as HTMLProgressElement).value = f.throttle as unknown as number;
    (document.getElementById('replay-bar-brake')    as HTMLProgressElement).value = f.brake    as unknown as number;
    (document.getElementById('replay-bar-clutch')   as HTMLProgressElement).value = f.clutch   as unknown as number;
    (document.getElementById('replay-steer')!).textContent    = f.steer.toString();
  }

  /** Redraw map trail up to frameIndex and update dot/scrub/time. */
  function redrawMap(): void {
    const trail = frames.slice(0, frameIndex + 1);
    map.loadPoints(trail.map(f => f.posX), trail.map(f => f.posZ));
    if (trail.length >= 2) map.drawLine();
    map.drawDotAtLast();
  }

  function seekTo(idx: number): void {
    frameIndex  = clampIdx(idx);
    playheadMs  = frames.length > 0 ? frames[frameIndex].t * 1000 : 0;
    scrub.value = String(frameIndex);
    timeEl.textContent = formatTime(playheadMs);
    if (frames.length > 0) {
      renderFrame(frames[frameIndex]);
      redrawMap();
    }
  }

  // ---- playback loop -------------------------------------------------

  function tick(realTs: number): void {
    if (!playing) return;
    const delta = realTs - lastRealTs;
    lastRealTs  = realTs;
    playheadMs += delta;

    while (frameIndex < frames.length - 1 && frames[frameIndex + 1].t * 1000 <= playheadMs) {
      frameIndex++;
    }

    renderFrame(frames[frameIndex]);
    // Only rebuild trail on map every ~8 frames to avoid thrashing
    if (frameIndex % 8 === 0 || frameIndex === frames.length - 1) {
      redrawMap();
    } else {
      map.drawDotAtIndex(frameIndex);
    }
    scrub.value        = String(frameIndex);
    timeEl.textContent = formatTime(playheadMs);

    if (frameIndex >= frames.length - 1) {
      playing = false;
      playBtn.disabled  = false;
      pauseBtn.disabled = true;
      return;
    }

    rafId = requestAnimationFrame(tick);
  }

  function startPlayback(): void {
    if (frames.length === 0) return;
    playing    = true;
    lastRealTs = performance.now();
    playBtn.disabled  = true;
    pauseBtn.disabled = false;
    rafId = requestAnimationFrame(tick);
  }

  function pausePlayback(): void {
    playing = false;
    if (rafId !== null) { cancelAnimationFrame(rafId); rafId = null; }
    playBtn.disabled  = false;
    pauseBtn.disabled = true;
  }

  // ---- data loading --------------------------------------------------

  function loadColumnarLap(lap: ColumnarLap): void {
    pausePlayback();
    frames = [];
    map.reset();

    const n = lap.frameCount;
    for (let i = 0; i < n; i++) {
      frames.push({
        t:                lap.fields.t[i],
        posX:             lap.fields.posX[i],
        posY:             lap.fields.posY[i],
        posZ:             lap.fields.posZ[i],
        speed:            lap.fields.speed[i],
        rpm:              lap.fields.rpm[i],
        gear:             lap.fields.gear[i],
        throttle:         lap.fields.throttle[i],
        brake:            lap.fields.brake[i],
        clutch:           lap.fields.clutch[i],
        handbrake:        lap.fields.handbrake[i],
        steer:            lap.fields.steer[i],
        tireTempFL:       lap.fields.tireTempFL[i],
        tireTempFR:       lap.fields.tireTempFR[i],
        tireTempRL:       lap.fields.tireTempRL[i],
        tireTempRR:       lap.fields.tireTempRR[i],
        tireSlipFL:       lap.fields.tireSlipFL[i],
        tireSlipFR:       lap.fields.tireSlipFR[i],
        tireSlipRL:       lap.fields.tireSlipRL[i],
        tireSlipRR:       lap.fields.tireSlipRR[i],
        suspFL:           lap.fields.suspFL[i],
        suspFR:           lap.fields.suspFR[i],
        suspRL:           lap.fields.suspRL[i],
        suspRR:           lap.fields.suspRR[i],
        boost:            lap.fields.boost[i],
        distanceTraveled: lap.fields.distanceTraveled[i],
        carOrdinal:       lap.fields.carOrdinal[i],
        carClass:         lap.fields.carClass[i],
      });
    }

    frameIndex        = 0;
    playheadMs        = 0;
    scrub.max         = String(Math.max(0, n - 1));
    scrub.value       = '0';
    scrub.disabled    = n === 0;
    playBtn.disabled  = n === 0;
    pauseBtn.disabled = true;
    timeEl.textContent = formatTime(0);

    if (n > 0) {
      renderFrame(frames[0]);
      // Pre-load all points so the full outline is visible at rest
      map.loadPoints(frames.map(f => f.posX), frames.map(f => f.posZ));
      if (n >= 2) map.drawLine();
      map.drawDotAtIndex(0);
    }
  }

  async function openReplay(lapNumber: number): Promise<void> {
    titleEl.textContent = lapNumber === -1 ? 'Loading full race…' : `Loading lap ${lapNumber}…`;
    playBtn.disabled  = true;
    scrub.disabled    = true;

    try {
      const channel = lapNumber === -1
        ? window.ipc.IPC['GET_FULL_RACE']
        : window.ipc.IPC['GET_LAP'];
      const result  = lapNumber === -1
        ? await window.ipc.invoke(channel)
        : await window.ipc.invoke(channel, lapNumber);
      const lap = result as ColumnarLap;
      loadColumnarLap(lap);
      titleEl.textContent = lapNumber === -1
        ? `Full race — ${formatTime(lap.lapTimeMs)}`
        : `Lap ${lap.lapNumber} — ${formatTime(lap.lapTimeMs)}`;
    } catch (e) {
      titleEl.textContent   = `Failed to load replay: ${e}`;
      playBtn.disabled  = true;
    }
  }

  // ---- controls ------------------------------------------------------

  playBtn.addEventListener('click', () => {
    if (frameIndex >= frames.length - 1) seekTo(0);
    startPlayback();
  });

  pauseBtn.addEventListener('click', pausePlayback);

  scrub.addEventListener('input', () => {
    pausePlayback();
    seekTo(Number(scrub.value));
  });

  window.addEventListener('open-replay', (e: Event) => {
    const detail = (e as CustomEvent<{ lapNumber: number }>).detail;
    void openReplay(detail.lapNumber);
  });
}
