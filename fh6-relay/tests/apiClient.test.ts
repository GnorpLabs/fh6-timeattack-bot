// tests/apiClient.test.ts
import { ApiClient } from '../src/main/apiClient';

const mockFetch = jest.fn();
global.fetch = mockFetch as jest.Mock;

describe('ApiClient', () => {
  const client = new ApiClient('https://bot.example.com', 'tok', 'disc123', 'player1');

  beforeEach(() => mockFetch.mockReset());

  it('GET /api/vehicles returns parsed JSON', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ['Toyota GR86', 'Subaru BRZ'],
    });

    const vehicles = await client.getVehicles();
    expect(vehicles).toEqual(['Toyota GR86', 'Subaru BRZ']);
    expect(mockFetch).toHaveBeenCalledWith('https://bot.example.com/api/vehicles');
  });

  it('GET /api/tracks returns parsed JSON', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ['Hokubu Circuit', 'Horizon Festival'],
    });

    const tracks = await client.getTracks();
    expect(tracks).toEqual(['Hokubu Circuit', 'Horizon Festival']);
  });

  it('POST /api/lap sends correct payload and returns entry_id', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ entry_id: 42 }),
    });

    const result = await client.submitLap({
      lapTimeMs: 83456,
      track: 'Hokubu Circuit',
      vehicleName: '2024 Toyota GR86',
      carClassInt: 3,
      carOrdinal: 1234,
    });

    expect(result.entry_id).toBe(42);
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('https://bot.example.com/api/lap');
    const body = JSON.parse(opts.body);
    expect(body.token).toBe('tok');
    expect(body.discord_id).toBe('disc123');
    expect(body.lap_time_ms).toBe(83456);
  });

  it('throws on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 401 });
    await expect(client.submitLap({
      lapTimeMs: 1000, track: 'x', vehicleName: 'y', carClassInt: 0, carOrdinal: 0,
    })).rejects.toThrow('401');
  });
});
