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
