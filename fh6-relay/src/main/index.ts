import { app, BrowserWindow, Tray, Menu, nativeImage } from 'electron';
import * as path from 'path';
import * as os from 'os';
import { SessionManager } from './sessionManager';
import { ReplayStore } from './replayStore';
import { UdpListener } from './udpListener';
import { TokenStore } from './tokenStore';
import { ApiClient } from './apiClient';
import { registerIpcHandlers } from './ipcHandlers';
import { IPC } from '../shared/types';

const CONFIG_DIR = path.join(os.homedir(), 'AppData', 'Roaming', 'FH6BotRelay');
const REPLAY_DIR = path.join(CONFIG_DIR, 'replays');
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;

const tokenStore = new TokenStore(CONFIG_FILE);
const replayStore = new ReplayStore(REPLAY_DIR, tokenStore.load().retentionDays);
const sessionManager = new SessionManager();

let apiClient: ApiClient | null = null;
function buildClient(): void {
  const cfg = tokenStore.load();
  if (cfg.token && cfg.apiUrl && cfg.discordId) {
    apiClient = new ApiClient(cfg.apiUrl, cfg.token, cfg.discordId, cfg.discordUsername);
  }
}
buildClient();

sessionManager.on('lapComplete', ({ lapRecord, frames }) => {
  replayStore.storeLap(lapRecord, frames);
  mainWindow?.webContents.send(IPC.LAP_COMPLETE, lapRecord);
});

const udpListener = new UdpListener(
  sessionManager,
  (frame) => { mainWindow?.webContents.send(IPC.FRAME, frame); },
  () => { mainWindow?.webContents.send(IPC.RACE_OFF); },
);

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
    },
  });
  mainWindow.loadFile(path.join(__dirname, '../../src/renderer/index.html'));
  mainWindow.on('close', (e) => {
    e.preventDefault();
    mainWindow?.hide();
  });
}

function createTray(): void {
  tray = new Tray(nativeImage.createEmpty());
  tray.setToolTip('FH6 Relay');
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Show', click: () => mainWindow?.show() },
    { label: 'Quit', click: () => { mainWindow?.destroy(); app.quit(); } },
  ]));
  tray.on('click', () => mainWindow?.show());
}

app.whenReady().then(() => {
  const cfg = tokenStore.load();
  replayStore.runRetentionCleanup();
  registerIpcHandlers(replayStore, tokenStore, () => apiClient);
  createWindow();
  createTray();
  udpListener.start(cfg.udpPort);
});

app.on('window-all-closed', () => { /* keep running in tray */ });
