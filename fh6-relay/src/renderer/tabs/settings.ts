export function initSettingsTab(container: HTMLElement): void {
  container.innerHTML = `
    <div style="max-width:500px;display:flex;flex-direction:column;gap:1rem">
      <h2 style="font-size:1.1rem;margin:0">Settings</h2>

      <label>Bot API URL
        <input id="cfg-api-url" type="text" placeholder="https://your-bot.example.com"
          style="display:block;width:100%;padding:0.4rem;margin-top:0.25rem;background:#1a1a1a;color:#e0e0e0;border:1px solid #333;border-radius:4px" />
      </label>

      <label>Discord User ID
        <input id="cfg-discord-id" type="text" placeholder="123456789012345678"
          style="display:block;width:100%;padding:0.4rem;margin-top:0.25rem;background:#1a1a1a;color:#e0e0e0;border:1px solid #333;border-radius:4px" />
      </label>

      <label>Discord Username
        <input id="cfg-discord-username" type="text" placeholder="playername"
          style="display:block;width:100%;padding:0.4rem;margin-top:0.25rem;background:#1a1a1a;color:#e0e0e0;border:1px solid #333;border-radius:4px" />
      </label>

      <label>Token
        <input id="cfg-token" type="password" placeholder="Paste token from /dataout-register"
          style="display:block;width:100%;padding:0.4rem;margin-top:0.25rem;background:#1a1a1a;color:#e0e0e0;border:1px solid #333;border-radius:4px" />
      </label>

      <label>UDP Port
        <input id="cfg-udp-port" type="number" min="1024" max="65535"
          style="display:block;width:100%;padding:0.4rem;margin-top:0.25rem;background:#1a1a1a;color:#e0e0e0;border:1px solid #333;border-radius:4px" />
      </label>

      <label>Replay Retention (days)
        <input id="cfg-retention" type="number" min="1"
          style="display:block;width:100%;padding:0.4rem;margin-top:0.25rem;background:#1a1a1a;color:#e0e0e0;border:1px solid #333;border-radius:4px" />
      </label>

      <button id="cfg-save"
        style="padding:0.5rem 1.5rem;background:#3b9dff;color:#fff;border:none;cursor:pointer;border-radius:4px;align-self:flex-start">
        Save
      </button>
      <div id="cfg-status" style="color:#aaa;font-size:0.85rem"></div>
    </div>
  `;

  const fields = {
    apiUrl:          document.getElementById('cfg-api-url') as HTMLInputElement,
    discordId:       document.getElementById('cfg-discord-id') as HTMLInputElement,
    discordUsername: document.getElementById('cfg-discord-username') as HTMLInputElement,
    token:           document.getElementById('cfg-token') as HTMLInputElement,
    udpPort:         document.getElementById('cfg-udp-port') as HTMLInputElement,
    retentionDays:   document.getElementById('cfg-retention') as HTMLInputElement,
  };
  const status = document.getElementById('cfg-status')!;

  window.ipc.invoke(window.ipc.IPC['CONFIG_GET']).then((cfg: unknown) => {
    const c = cfg as Record<string, unknown>;
    fields.apiUrl.value          = String(c.apiUrl ?? '');
    fields.discordId.value       = String(c.discordId ?? '');
    fields.discordUsername.value = String(c.discordUsername ?? '');
    fields.token.value           = String(c.token ?? '');
    fields.udpPort.value         = String(c.udpPort ?? 20440);
    fields.retentionDays.value   = String(c.retentionDays ?? 30);
  });

  document.getElementById('cfg-save')!.addEventListener('click', async () => {
    const config = {
      apiUrl:          fields.apiUrl.value.trim(),
      discordId:       fields.discordId.value.trim(),
      discordUsername: fields.discordUsername.value.trim(),
      token:           fields.token.value.trim(),
      udpPort:         Number(fields.udpPort.value) || 20440,
      retentionDays:   Number(fields.retentionDays.value) || 30,
    };
    try {
      await window.ipc.invoke(window.ipc.IPC['CONFIG_SET'], config);
      status.textContent = 'Saved. Restart the app for UDP port changes to take effect.';
    } catch (e) {
      status.textContent = `Save failed: ${e}`;
    }
  });
}
