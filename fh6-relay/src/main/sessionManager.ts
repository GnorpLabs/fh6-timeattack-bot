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
  private lapStartT: number | null = null;
  private lastFrameInterval: number = 0;
  private currentFrames: Frame[] = [];
  private lapCount = 0;

  onFrame(frame: Frame): void {
    if (this.prevT === null) {
      this.prevT = frame.t;
      this.lapStartT = frame.t;
      this.currentFrames.push(frame);
      return;
    }

    // Track the most recent frame-to-frame interval (when advancing normally)
    if (frame.t > this.prevT) {
      this.lastFrameInterval = frame.t - this.prevT;
    }

    if (
      this.prevT > MIN_LAP_SECONDS &&
      frame.t < this.prevT - RESET_THRESHOLD
    ) {
      this.lapCount++;
      // Lap time = from start of first frame to end of last frame (prevT + one interval)
      const elapsed = this.prevT - (this.lapStartT ?? 0) + this.lastFrameInterval;
      const lapTimeMs = Math.round(elapsed * 1000);
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
      this.lapStartT = frame.t;
    } else if (this.currentFrames.length === 0) {
      this.lapStartT = frame.t;
    }

    this.currentFrames.push(frame);
    this.prevT = frame.t;
  }

  reset(): void {
    this.prevT = null;
    this.lapStartT = null;
    this.lastFrameInterval = 0;
    this.currentFrames = [];
    this.lapCount = 0;
  }

  getLapCount(): number {
    return this.lapCount;
  }
}
