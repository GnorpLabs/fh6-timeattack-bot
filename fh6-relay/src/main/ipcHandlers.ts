import { ipcMain } from 'electron';
import { IPC, Config } from '../shared/types';
import { ReplayStore } from './replayStore';
import { ApiClient } from './apiClient';
import { TokenStore } from './tokenStore';

export function registerIpcHandlers(
  store: ReplayStore,
  tokenStore: TokenStore,
  getClient: () => ApiClient | null,
): void {
  ipcMain.handle(IPC.GET_LAP, (_e, lapNumber: number) => {
    return store.getLap(lapNumber);
  });

  ipcMain.handle(IPC.GET_FULL_RACE, () => {
    return store.getFullRace();
  });

  ipcMain.handle(IPC.GET_VEHICLES, async () => {
    const client = getClient();
    if (!client) throw new Error('Not configured');
    return client.getVehicles();
  });

  ipcMain.handle(IPC.GET_TRACKS, async () => {
    const client = getClient();
    if (!client) throw new Error('Not configured');
    return client.getTracks();
  });

  ipcMain.handle(IPC.SUBMIT_LAP, async (_e, payload) => {
    const client = getClient();
    if (!client) throw new Error('Not configured');
    return client.submitLap(payload);
  });

  ipcMain.handle(IPC.CONFIG_GET, () => tokenStore.load());

  ipcMain.handle(IPC.CONFIG_SET, async (_e, config: Config) => {
    tokenStore.save(config);
  });
}
