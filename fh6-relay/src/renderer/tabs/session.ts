import { LapRecord } from '../../shared/types';
import { formatLapTime } from '../utils';

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
          <td style="padding:0.5rem">${formatLapTime(lap.lapTimeMs)}</td>
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
