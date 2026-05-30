import * as dgram from 'dgram';
import { parsePacket } from './packetParser';
import { SessionManager } from './sessionManager';
import { Frame } from '../shared/types';

export class UdpListener {
  private socket: dgram.Socket | null = null;

  constructor(
    private readonly sessionManager: SessionManager,
    private readonly onFrame: (frame: Frame) => void,
    private readonly onRaceOff: () => void,
  ) {}

  start(port: number): void {
    this.socket = dgram.createSocket('udp4');
    let wasRaceOn = false;

    this.socket.on('message', (msg) => {
      const frame = parsePacket(msg);
      if (frame === null) {
        if (wasRaceOn) {
          wasRaceOn = false;
          this.onRaceOff();
          this.sessionManager.reset();
        }
        return;
      }
      wasRaceOn = true;
      this.sessionManager.onFrame(frame);
      this.onFrame(frame);
    });

    this.socket.on('error', (err) => {
      console.error('[udpListener] socket error:', err.message);
      this.socket?.close();
      this.socket = null;
    });

    this.socket.bind(port, '127.0.0.1');
  }

  stop(): void {
    this.socket?.close();
    this.socket = null;
  }
}
