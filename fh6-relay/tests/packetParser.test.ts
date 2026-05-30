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
