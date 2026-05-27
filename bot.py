import asyncio
import json
import logging
from pathlib import Path

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import config
from database import init_db

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

COGS = [
    "cogs.submission",
    "cogs.query",
    "cogs.admin",
    "cogs.telemetry",
]


class TimeAttackBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.http_session: aiohttp.ClientSession | None = None
        self._api_runner: aiohttp.web.AppRunner | None = None

    async def setup_hook(self) -> None:
        self.http_session = aiohttp.ClientSession()

        for cog in COGS:
            await self.load_extension(cog)
            log.info(f"Loaded cog: {cog}")

        guild_id = config.DISCORD_GUILD_ID
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info(f"Slash commands synced to guild {guild_id}")
        else:
            await self.tree.sync()
            log.info("Slash commands synced globally")

        import api_server
        from aiohttp import web as aiohttp_web
        _app = api_server.create_app(self)
        self._api_runner = aiohttp_web.AppRunner(_app)
        await self._api_runner.setup()
        site = aiohttp_web.TCPSite(self._api_runner, "0.0.0.0", config.API_PORT)
        await site.start()
        log.info(f"API server listening on port {config.API_PORT}")

        @self.tree.error
        async def on_app_command_error(
            interaction: discord.Interaction, error: app_commands.AppCommandError
        ) -> None:
            log.exception("Unhandled slash command error", exc_info=error)
            msg = "Something went wrong. Please try again."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)

    async def close(self) -> None:
        if self._api_runner:
            await self._api_runner.cleanup()
        if self.http_session:
            await self.http_session.close()
        await super().close()

    async def on_ready(self) -> None:
        log.info(f"Logged in as {self.user} (ID: {self.user.id})")


async def main() -> None:
    vehicles_path = Path("data/vehicles.json")
    if vehicles_path.exists():
        with open(vehicles_path) as f:
            config.VEHICLES = json.load(f)
        log.info(f"Loaded {len(config.VEHICLES)} vehicles from {vehicles_path}")
    else:
        log.warning("data/vehicles.json not found — vehicle autocomplete will be empty")

    config.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    init_db()
    log.info("Database initialised")

    if not config.DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set — check your .env file")

    bot = TimeAttackBot()
    await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
