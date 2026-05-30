import { ColumnarLap } from '../../shared/types';
import { ChartManager } from '../charts/chartManager';
import { TrackMap } from '../charts/trackMap';

export function initReplayTab(container: HTMLElement): void {
  container.innerHTML = `
    <div style="display:flex;flex-direction:column;height:100%;overflow:hidden">

      <div style="padding:0.5rem 0;display:flex;gap:0.5rem;align-items:center;flex-shrink:0">
        <label style="font-size:0.9rem;color:#aaa">Viewing:</label>
        <select id="replay-lap-select"
          style="padding:0.3rem 0.6rem;background:#1a1a1a;color:#e0e0e0;border:1px solid #333;border-radius:4px">
          <option value="">—</option>
        </select>
        <span id="replay-lap-info" style="color:#666;font-size:0.85rem"></span>
      </div>

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

  const style = document.createElement('style');
  style.textContent = `.chart-wrap { height: 160px; position: relative; background: #111; border-radius: 4px; padding: 4px; }`;
  document.head.appendChild(style);

  const chartManager = new ChartManager();
  const trackMap = new TrackMap(document.getElementById('replay-map') as HTMLCanvasElement);

  chartManager.createAll();

  let currentData: ColumnarLap | null = null;
  let lapList: Array<{ lapNumber: number; lapTimeMs: number }> = [];
  let playing = false;
  let rafHandle: number | null = null;
  let playheadIndex = 0;
  let lastTimestamp = 0;

  const lapSelect = document.getElementById('replay-lap-select') as HTMLSelectElement;
  const lapInfo = document.getElementById('replay-lap-info')!;
  const scrubber = document.getElementById('timeline-scrubber') as HTMLInputElement;
  const playPauseBtn = document.getElementById('btn-play-pause')!;
  const speedSelect = document.getElementById('speed-select') as HTMLSelectElement;

  function formatMs(ms: number): string {
    const mins = Math.floor(ms / 60000);
    const secs = ((ms % 60000) / 1000).toFixed(3).padStart(6, '0');
    return `${mins}:${secs}`;
  }

  function stopPlayback(): void {
    playing = false;
    playPauseBtn.textContent = 'Play';
    if (rafHandle !== null) { cancelAnimationFrame(rafHandle); rafHandle = null; }
  }

  function setPlayheadAt(index: number): void {
    if (!currentData) return;
    const f = currentData.fields;
    const i = Math.max(0, Math.min(index, currentData.frameCount - 1));

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
    trackMap.reset();
    trackMap.loadPoints(data.fields.posX, data.fields.posZ);
    trackMap.drawLine();
    trackMap.drawDotAtIndex(0);

    playheadIndex = 0;
    setPlayheadAt(0);
    stopPlayback();
  }

  function tick(timestamp: number): void {
    if (!playing || !currentData) return;

    const elapsed = timestamp - lastTimestamp;
    lastTimestamp = timestamp;

    const speed = Number(speedSelect.value);
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

  playPauseBtn.addEventListener('click', () => {
    if (playing) {
      stopPlayback();
    } else {
      if (currentData && playheadIndex >= currentData.frameCount - 1) {
        playheadIndex = 0;
        setPlayheadAt(0);
      }
      startPlayback();
    }
  });

  window.ipc.on(window.ipc.IPC['LAP_COMPLETE'], (record: unknown) => {
    const lap = record as { lapNumber: number; lapTimeMs: number };
    lapList.push(lap);
    rebuildLapSelect();
  });

  window.addEventListener('open-replay', (e: Event) => {
    const { lapNumber } = (e as CustomEvent).detail as { lapNumber: number };
    rebuildLapSelect();
    lapSelect.value = String(lapNumber);
    loadLap(lapNumber);
  });
}
