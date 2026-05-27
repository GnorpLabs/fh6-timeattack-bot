# FH6 Time Attack Bot

A Discord bot for tracking and leaderboarding Forza Horizon 6 time attack lap times. Players submit times with a screenshot proof, and the bot stores them in a SQLite database with per-track, per-class leaderboards.

## Commands

| Command | Description |
|---|---|
| `/submit` | Submit a lap time with track, class, vehicle, and a screenshot |
| `/leaderboard` | View the fastest times on a track, optionally filtered by class |
| `/my-times` | View all of your personal submitted times |
| `/history` | View the full submission history for a track |
| `/delete` | Delete one of your own entries by ID |

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
Logged in as YourBot#0000 (ID: ...)
Slash commands synced to guild 123456789
```

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
