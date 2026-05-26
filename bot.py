import asyncio
import json
import logging
import os
from pathlib import Path

import discord
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
]


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

    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready() -> None:
        log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
        guild_id = config.DISCORD_GUILD_ID
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            log.info(f"Slash commands synced to guild {guild_id}")
        else:
            await bot.tree.sync()
            log.info("Slash commands synced globally")

    for cog in COGS:
        await bot.load_extension(cog)
        log.info(f"Loaded cog: {cog}")

    await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
