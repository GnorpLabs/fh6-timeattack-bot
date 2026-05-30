import { initLiveTab } from './tabs/live';
import { initSessionTab } from './tabs/session';
import { initReplayTab } from './tabs/replay';
import { initSettingsTab } from './tabs/settings';

declare global {
  interface Window {
    ipc: {
      on: (channel: string, listener: (...args: unknown[]) => void) => void;
      invoke: (channel: string, ...args: unknown[]) => Promise<unknown>;
      IPC: Record<string, string>;
    };
  }
}

document.querySelectorAll<HTMLButtonElement>('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`tab-${btn.dataset.tab}`)!.classList.add('active');
  });
});

initLiveTab(document.getElementById('tab-live')!);
initSessionTab(document.getElementById('tab-session')!);
initReplayTab(document.getElementById('tab-replay')!);
initSettingsTab(document.getElementById('tab-settings')!);
