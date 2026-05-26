from pathlib import Path

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

import config
from database import add_entry
from utils import format_lap_time, parse_lap_time

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class SubmissionCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="submit", description="Submit a time attack lap time")
    @app_commands.describe(
        time="Lap time in mm:ss.ms format (e.g. 1:23.456)",
        track="Time attack track",
        vehicle="Vehicle used",
        class_="Vehicle class",
        screenshot="Screenshot of your finish time",
    )
    @app_commands.rename(class_="class")
    async def submit(
        self,
        interaction: discord.Interaction,
        time: str,
        track: str,
        vehicle: str,
        class_: str,
        screenshot: discord.Attachment,
    ) -> None:
        try:
            lap_ms = parse_lap_time(time)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        ext = Path(screenshot.filename).suffix.lower()
        if ext not in _IMAGE_EXTENSIONS:
            await interaction.response.send_message(
                "Screenshot must be a jpg, png, or webp image.", ephemeral=True
            )
            return

        await interaction.response.defer()

        config.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{interaction.user.id}_{int(discord.utils.utcnow().timestamp())}{ext}"
        dest = config.SCREENSHOTS_DIR / filename

        async with aiohttp.ClientSession() as session:
            async with session.get(screenshot.url) as resp:
                if resp.status != 200:
                    await interaction.followup.send(
                        "Failed to download screenshot — please try again.", ephemeral=True
                    )
                    return
                try:
                    dest.write_bytes(await resp.read())
                except OSError as exc:
                    await interaction.followup.send(
                        "Failed to save screenshot — please try again.", ephemeral=True
                    )
                    return

        entry_id = add_entry(
            discord_id=str(interaction.user.id),
            username=interaction.user.display_name,
            track=track,
            vehicle=vehicle,
            class_=class_,
            lap_time_ms=lap_ms,
            screenshot_path=str(dest),
        )

        embed = discord.Embed(title="Time Attack Entry Recorded", color=discord.Color.green())
        embed.add_field(name="Track", value=track, inline=True)
        embed.add_field(name="Class", value=class_, inline=True)
        embed.add_field(name="Vehicle", value=vehicle, inline=True)
        embed.add_field(name="Lap Time", value=format_lap_time(lap_ms), inline=True)
        embed.add_field(name="Entry ID", value=str(entry_id), inline=True)
        embed.set_thumbnail(url=screenshot.url)
        embed.set_footer(text=f"Submitted by {interaction.user.display_name}")

        await interaction.followup.send(embed=embed)

    @submit.autocomplete("track")
    async def _track_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=t, value=t)
            for t in config.TRACKS
            if current.lower() in t.lower()
        ][:25]

    @submit.autocomplete("class_")
    async def _class_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=c, value=c)
            for c in config.CLASSES
            if current.lower() in c.lower()
        ][:25]

    @submit.autocomplete("vehicle")
    async def _vehicle_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=v["name"], value=v["name"])
            for v in config.VEHICLES
            if current.lower() in v["name"].lower() or current.lower() in v["manufacturer"].lower()
        ][:25]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SubmissionCog(bot))
