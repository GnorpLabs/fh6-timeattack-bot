export interface Frame {
  t: number;           // currentLap seconds — timeline reference
  posX: number;
  posY: number;        // elevation
  posZ: number;
  speed: number;       // m/s
  rpm: number;
  gear: number;
  throttle: number;    // 0–255
  brake: number;       // 0–255
  clutch: number;      // 0–255
  handbrake: number;   // 0–255
  steer: number;       // -127 to 127
  tireTempFL: number;
  tireTempFR: number;
  tireTempRL: number;
  tireTempRR: number;
  tireSlipFL: number;
  tireSlipFR: number;
  tireSlipRL: number;
  tireSlipRR: number;
  suspFL: number;
  suspFR: number;
  suspRL: number;
  suspRR: number;
  boost: number;
  distanceTraveled: number;
  carOrdinal: number;  // static per session, repeated each frame
  carClass: number;    // 0=D 1=C 2=B 3=A 4=S1 5=S2 6=R 7=X
}

export interface ColumnarLap {
  version: 1;
  lapNumber: number;
  lapTimeMs: number;
  carOrdinal: number;
  carClass: number;
  capturedAt: string;
  frameCount: number;
  fields: { [K in keyof Frame]: number[] };
}

export interface LapRecord {
  lapNumber: number;
  lapTimeMs: number;
  carOrdinal: number;
  carClass: number;
  capturedAt: string;
}

export interface Config {
  token: string;
  apiUrl: string;
  discordId: string;
  discordUsername: string;
  udpPort: number;
  retentionDays: number;
}

export const IPC = {
  // Main → Renderer (webContents.send)
  FRAME: 'telemetry:frame',
  LAP_COMPLETE: 'telemetry:lapComplete',
  RACE_OFF: 'telemetry:raceOff',
  // Renderer → Main (ipcMain.handle)
  GET_LAP: 'replay:getLap',
  GET_FULL_RACE: 'replay:getFullRace',
  SUBMIT_LAP: 'submit:lap',
  GET_VEHICLES: 'api:getVehicles',
  GET_TRACKS: 'api:getTracks',
  CONFIG_GET: 'config:get',
  CONFIG_SET: 'config:set',
} as const;
