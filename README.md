# FH6 Time Attack Bot

A Discord bot for tracking and leaderboarding Forza Horizon 6 time attack lap times. Players submit times manually with a screenshot, or automatically via the **Data Out** telemetry feature using `fh6-relay.exe`.

## Commands

| Command | Description |
|---|---|
| `/submit` | Submit a lap time with track, class, vehicle, and a screenshot |
| `/leaderboard` | View the fastest times on a track, optionally filtered by class |
| `/my-times` | View all of your personal submitted times |
| `/history` | View the full submission history for a track |
| `/delete` | Delete one of your own entries by ID |
| `/dataout-register` | Generate an API token for use with `fh6-relay.exe` (auto-submit) |
| `/dataout-refresh` | Regenerate your token (invalidates the old one immediately) |

---

## Setup

### 1. Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and click **New Application**.
2. Navigate to the **Bot** tab and click **Add Bot**.
3. Under **Token**, click **Reset Token** and copy it — you'll need it in step 3.
4. Under **Privileged Gateway Intents**, leave all three toggles **off** (this bot doesn't need any).

### 2. Invite the Bot to Your Server

1. Go to **OAuth2 → URL Generator**.
2. Under **Scopes**, check both:
   - `bot`
   - `applications.commands` ← required for slash commands
3. Under **Bot Permissions**, check:
   - Send Messages
   - Embed Links
   - Attach Files
   - Use Application Commands
4. Copy the generated URL, open it in your browser, and add the bot to your server.

### 3. Configure Environment Variables

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

```env
DISCORD_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=your_server_id_here   # Right-click server icon → Copy Server ID (requires Developer Mode)
DB_PATH=data/timeattack.db
SCREENSHOTS_DIR=screenshots
API_PORT=8080                           # HTTP port for the Data Out relay API (default: 8080)
```

To get your server ID: enable **Developer Mode** in Discord (User Settings → Advanced → Developer Mode), then right-click your server icon and select **Copy Server ID**.

> Setting `DISCORD_GUILD_ID` makes slash commands appear instantly in that server. Leaving it blank syncs commands globally, which can take up to an hour.

### 4. Run the Bot

**Locally (Python virtualenv):**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

**Docker Compose:**

```bash
docker compose up -d
```

Data and screenshots are persisted to `./data` and `./screenshots` via volume mounts.

**Kubernetes (Helm):**

```bash
helm install fh6-bot ./helm \
  --set discord.token=your_token \
  --set discord.guildId=your_guild_id
```

See `helm/values.yaml` for storage class and resource configuration.

### 5. Verify Startup

Successful startup looks like this in the logs:

```
Loaded 616 vehicles from data/vehicles.json
Database initialised
Loaded cog: cogs.submission
Loaded cog: cogs.query
Loaded cog: cogs.admin
Loaded cog: cogs.telemetry
Logged in as YourBot#0000 (ID: ...)
Slash commands synced to guild 123456789
```

---

## Data Out Auto-Submit

Instead of manually typing your time into Discord, you can use **`fh6-relay.exe`** — a lightweight Windows tray app that listens to FH6's telemetry stream and lets you submit a lap with one click.

### How it works

```
FH6 Game  ──UDP──►  fh6-relay.exe  ──HTTPS──►  Bot server  ──►  Discord DM
(localhost)          (your PC)                   (this bot)
```

FH6 sends telemetry to `127.0.0.1:20440`. The relay captures lap completions silently in the background. When you're done driving, open the Session Review window from the tray icon, pick your track + vehicle, select the lap you want to submit, and click **Submit**. The bot validates your token and posts the entry — you get a Discord DM confirmation identical to a `/submit` response.

Screenshots are optional for auto-submitted entries.

### Setup (players)

**1. Configure FH6 Data Out**

In Forza Horizon 6: Settings → HUD and Gameplay → scroll to **Data Out** → enable it with:
- IP: `127.0.0.1`
- Port: `20440`
- Data format: Car Dash

**2. Get your token**

Run `/dataout-register` in any channel the bot can see. It will reply **privately** (ephemeral) with a 64-character token and setup instructions. Tokens expire after 30 days — run `/dataout-refresh` to get a new one.

**3. Download and run `fh6-relay.exe`**

Download the latest release from the GitHub Releases page. Run it — on first launch a setup dialog appears asking for:

| Field | What to enter |
|---|---|
| **Server IP or FQDN** | IP address or hostname of the bot server (ask your server admin) |
| **Discord User ID** | Your numeric Discord ID — enable Developer Mode (User Settings → Advanced), then right-click your profile → **Copy User ID** |
| **Discord Username** | Your Discord username (e.g. `alice`) |
| **Token** | The token from `/dataout-register` |

These are saved to `%APPDATA%\FH6BotRelay\config.json` and won't be asked again unless you open Settings.

**4. Drive and submit**

The tray icon appears. Drive laps — each completed lap shows a brief tray notification. When ready to submit:

1. Click the tray icon → **Session Review**
2. Choose your track and vehicle from the dropdowns
3. Select a lap row in the table
4. Click **Submit Selected Lap**

You'll receive a Discord DM confirming the entry. Use **Clear Session** to reset the lap list between outings.

### Setup (server admins)

The bot listens for relay submissions on `API_PORT` (default `8080`). Make this port reachable from players' machines:

- **Firewall:** open TCP `8080` (or your chosen port) inbound
- **Reverse proxy (recommended):** proxy `https://your-domain.com` → `localhost:8080` so players use a clean FQDN with valid TLS
- **Kubernetes:** expose the API port via a Service alongside the existing bot deployment; see `helm/values.yaml`

---

## FAQ

**Slash commands aren't showing up in my server.**

There are a few common causes:
- The bot was invited without the `applications.commands` OAuth2 scope. Re-invite using the URL generator with both `bot` and `applications.commands` scopes selected — re-inviting to the same server is safe and won't remove the bot.
- `DISCORD_GUILD_ID` is not set, so commands synced globally. Global sync can take up to an hour. Set the guild ID for instant sync.
- `DISCORD_GUILD_ID` is set to the wrong server. Make sure it matches the server you invited the bot to.

**The bot crashes on startup with `403 Forbidden (Missing Access)`.**

The `DISCORD_GUILD_ID` in your `.env` doesn't match a server the bot is in. Right-click the correct server in Discord → Copy Server ID, and update the env variable.

**The bot crashes on startup with `RuntimeError: DISCORD_TOKEN is not set`.**

Your `.env` file is missing or the `DISCORD_TOKEN` value is empty. Make sure `.env` exists in the project root and contains a valid token.

**Commands are being rate limited on startup (`429`).**

Discord rate-limits the command sync endpoint. This happens when the bot is restarted many times in quick succession. The bot handles this automatically with a retry — wait ~30 seconds for it to resolve. Avoid restarting the bot repeatedly during testing.

**Vehicle validation rejects my submission.**

The vehicle name must exactly match an entry in `data/vehicles.json`. Use the autocomplete list when typing — it searches by both vehicle name and manufacturer.

**The bot shows old usernames on the leaderboard.**

Usernames are recorded at submission time from your Discord account's global username. If you've changed your username since submitting, older entries will show your previous name. Your Discord ID is always used for ownership checks (e.g. `/delete`), so this is cosmetic only.

**How do I add or update tracks?**

Edit the `TRACKS` list in `config.py`. Changes take effect on the next bot restart. Note that existing submissions reference track names as plain strings, so renaming a track will orphan old entries.

**Where are screenshots stored?**

Locally in the `screenshots/` directory (or the path set by `SCREENSHOTS_DIR` in `.env`). When using Docker Compose, this is bind-mounted to `./screenshots` on the host. Screenshots are deleted when an entry is deleted via `/delete`.

**Can I run multiple instances of the bot?**

No — multiple instances will conflict over the SQLite database. SQLite supports only one writer at a time and the file is not safe for concurrent access across processes.

**`fh6-relay.exe` says "Token Expired".**

Your token is valid for 30 days. Run `/dataout-refresh` in Discord, copy the new token, then open the relay's tray icon → **Settings** and paste it into the Token field.

**`fh6-relay.exe` says "Connection Refused".**

The bot server's API port is not reachable. Check that:
- The server address you entered (without `https://`) is correct and reachable from your network.
- Port `8080` (or your admin's custom port) is open in the server firewall.
- The bot is running — check with your server admin.

**Laps aren't being captured by the relay.**

Verify FH6 Data Out is enabled: Settings → HUD and Gameplay → Data Out. IP must be `127.0.0.1`, Port `20440`, format `Car Dash`. The relay only records laps while `IsRaceOn` is active, so laps driven in the menus or during loading are ignored. Check the tray icon — if it shows an error state, restart the exe.

**The relay captures a lap but submission fails with a validation error.**

The track name or vehicle name you typed doesn't match the bot's list. Use the autocomplete dropdowns in the Session Review window — they are populated from the bot on window open. If they're empty (server unreachable), type the exact name as it appears in `/submit` autocomplete.
