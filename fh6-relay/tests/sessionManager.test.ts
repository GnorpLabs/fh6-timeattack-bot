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
    carOrdinal: 0, carClass: 0,
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
