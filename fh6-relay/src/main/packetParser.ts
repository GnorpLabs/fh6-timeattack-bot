import { Frame } from '../shared/types';

export const PACKET_SIZE = 324;

export function parsePacket(data: Buffer): Frame | null {
  if (data.length !== PACKET_SIZE) return null;
  if (data.readInt32LE(0) === 0) return null; // IsRaceOn === 0

  return {
    t:              data.readFloatLE(304),  // CurrentLap
    posX:           data.readFloatLE(232),
    posY:           data.readFloatLE(236),
    posZ:           data.readFloatLE(240),
    speed:          data.readFloatLE(244),
    rpm:            data.readFloatLE(16),   // CurrentEngineRpm
    gear:           data.readUInt8(319),
    throttle:       data.readUInt8(315),
    brake:          data.readUInt8(316),
    clutch:         data.readUInt8(317),
    handbrake:      data.readUInt8(318),
    steer:          data.readInt8(320),
    tireTempFL:     data.readFloatLE(256),
    tireTempFR:     data.readFloatLE(260),
    tireTempRL:     data.readFloatLE(264),
    tireTempRR:     data.readFloatLE(268),
    tireSlipFL:     data.readFloatLE(180),
    tireSlipFR:     data.readFloatLE(184),
    tireSlipRL:     data.readFloatLE(188),
    tireSlipRR:     data.readFloatLE(192),
    suspFL:         data.readFloatLE(196),
    suspFR:         data.readFloatLE(200),
    suspRL:         data.readFloatLE(204),
    suspRR:         data.readFloatLE(208),
    boost:          data.readFloatLE(272),
    distanceTraveled: data.readFloatLE(280),
    carOrdinal:     data.readInt32LE(212),
    carClass:       data.readInt32LE(216),
  };
}
