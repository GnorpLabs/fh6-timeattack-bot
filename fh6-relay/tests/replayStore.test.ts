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
    carOrdinal: 1234, carClass: 3,
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
