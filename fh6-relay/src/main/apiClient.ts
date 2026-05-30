interface SubmitPayload {
  lapTimeMs: number;
  track: string;
  vehicleName: string;
  carClassInt: number;
  carOrdinal: number;
}

export class ApiClient {
  constructor(
    private readonly apiUrl: string,
    private readonly token: string,
    private readonly discordId: string,
    private readonly discordUsername: string,
  ) {}

  async getVehicles(): Promise<string[]> {
    const res = await fetch(`${this.apiUrl}/api/vehicles`);
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  }

  async getTracks(): Promise<string[]> {
    const res = await fetch(`${this.apiUrl}/api/tracks`);
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  }

  async submitLap(payload: SubmitPayload): Promise<{ entry_id: number }> {
    const res = await fetch(`${this.apiUrl}/api/lap`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: this.token,
        discord_id: this.discordId,
        discord_username: this.discordUsername,
        lap_time_ms: payload.lapTimeMs,
        track: payload.track,
        vehicle_name: payload.vehicleName,
        car_class_int: payload.carClassInt,
        car_ordinal: payload.carOrdinal,
      }),
    });
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  }
}
