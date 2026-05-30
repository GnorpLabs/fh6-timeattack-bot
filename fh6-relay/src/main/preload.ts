import { contextBridge, ipcRenderer } from 'electron';
import { IPC } from '../shared/types';

contextBridge.exposeInMainWorld('ipc', {
  on: (channel: string, listener: (...args: unknown[]) => void) => {
    ipcRenderer.on(channel, (_event, ...args) => listener(...args));
  },
  invoke: (channel: string, ...args: unknown[]) => {
    return ipcRenderer.invoke(channel, ...args);
  },
  IPC,
});
