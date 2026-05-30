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
    map.drawDotAtLast();
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
