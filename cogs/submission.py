from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

import config
from database import add_entry
from image_extractor import ExtractionResult
from utils import format_lap_time, parse_lap_time

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _build_success_embed(
    *,
    track: str,
    class_: str,
    vehicle: str,
    lap_ms: int,
    entry_id: int,
    rank: int | None,
    screenshot_url: str | None,
    username: str,
) -> discord.Embed:
    embed = discord.Embed(title="Time Attack Entry Recorded", color=discord.Color.green())
    embed.add_field(name="Track", value=track, inline=True)
    embed.add_field(name="Class", value=class_, inline=True)
    embed.add_field(name="Vehicle", value=vehicle, inline=True)
    embed.add_field(name="Lap Time", value=format_lap_time(lap_ms), inline=True)
    embed.add_field(name="Entry ID", value=str(entry_id), inline=True)
    if rank is not None:
        embed.add_field(name="Global Rank", value=f"#{rank:,}", inline=True)
    if screenshot_url:
        embed.set_thumbnail(url=screenshot_url)
    embed.set_footer(text=f"Submitted by {username}")
    return embed


class SubmissionModal(discord.ui.Modal, title="Submit Time Attack Entry"):
    vehicle_input = discord.ui.TextInput(
        label="Vehicle", max_length=200, required=True
    )
    time_input = discord.ui.TextInput(
        label="Time (e.g. 1:23.456)", max_length=20, required=True
    )
    class_input = discord.ui.TextInput(
        label="Class (D/C/B/A/S1/S2/R/X)", max_length=5, required=True
    )
    rank_input = discord.ui.TextInput(
        label="Global Rank (optional)", required=False, max_length=10
    )

    def __init__(
        self,
        track: str,
        screenshot_path: str,
        screenshot_url: str,
        prefill: ExtractionResult,
    ) -> None:
        super().__init__()
        self._track = track
        self._screenshot_path = screenshot_path
        self._screenshot_url = screenshot_url
        if prefill.vehicle:
            self.vehicle_input.default = prefill.vehicle
        if prefill.time_str:
            self.time_input.default = prefill.time_str
        if prefill.class_:
            self.class_input.default = prefill.class_
        if prefill.global_rank is not None:
            self.rank_input.default = str(prefill.global_rank)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            lap_ms = parse_lap_time(self.time_input.value)
        except ValueError as exc:
            await interaction.response.send_message(f"**Time:** {exc}", ephemeral=True)
            return

        class_val = self.class_input.value.strip().upper()
        if class_val not in config.CLASSES:
            valid = ", ".join(f"`{c}`" for c in config.CLASSES)
            await interaction.response.send_message(
                f"**Class:** `{class_val}` isn't valid — choose from {valid}.",
                ephemeral=True,
            )
            return

        vehicle_val = self.vehicle_input.value.strip()
        vehicle_names = config.get_vehicle_names()
        if vehicle_names and vehicle_val not in vehicle_names:
            await interaction.response.send_message(
                f"**Vehicle:** `{vehicle_val}` isn't in the vehicle list — "
                "check the spelling matches the autocomplete list.",
                ephemeral=True,
            )
            return

        rank: int | None = None
        rank_str = self.rank_input.value.strip()
        if rank_str:
            try:
                rank = int(rank_str.lstrip("#").replace(",", ""))
            except ValueError:
                await interaction.response.send_message(
                    "**Global Rank:** must be a number (e.g. `1234`).",
                    ephemeral=True,
                )
                return

        entry_id = add_entry(
            discord_id=str(interaction.user.id),
            username=interaction.user.name,
            track=self._track,
            vehicle=vehicle_val,
            class_=class_val,
            lap_time_ms=lap_ms,
            screenshot_path=self._screenshot_path or None,
            global_rank=rank,
        )

        embed = _build_success_embed(
            track=self._track,
            class_=class_val,
            vehicle=vehicle_val,
            lap_ms=lap_ms,
            entry_id=entry_id,
            rank=rank,
            screenshot_url=self._screenshot_url or None,
            username=interaction.user.display_name,
        )
        await interaction.response.send_message(embed=embed)


class ConfirmView(discord.ui.View):
    def __init__(
        self,
        track: str,
        screenshot_path: str,
        screenshot_url: str,
        result: ExtractionResult,
    ) -> None:
        super().__init__(timeout=300)
        self._track = track
        self._screenshot_path = screenshot_path
        self._screenshot_url = screenshot_url
        self._result = result
        all_present = all([
            result.vehicle,
            result.time_str,
            result.class_,
            result.global_rank is not None,
        ])
        if not all_present:
            self.remove_item(self.confirm_btn)

    @discord.ui.button(label="Confirm ✓", style=discord.ButtonStyle.green)
    async def confirm_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        lap_ms = parse_lap_time(self._result.time_str)
        entry_id = add_entry(
            discord_id=str(interaction.user.id),
            username=interaction.user.name,
            track=self._track,
            vehicle=self._result.vehicle,
            class_=self._result.class_,
            lap_time_ms=lap_ms,
            screenshot_path=self._screenshot_path or None,
            global_rank=self._result.global_rank,
        )
        embed = _build_success_embed(
            track=self._track,
            class_=self._result.class_,
            vehicle=self._result.vehicle,
            lap_ms=lap_ms,
            entry_id=entry_id,
            rank=self._result.global_rank,
            screenshot_url=self._screenshot_url or None,
            username=interaction.user.display_name,
        )
        self.stop()
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Edit ✏️", style=discord.ButtonStyle.secondary)
    async def edit_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        modal = SubmissionModal(
            track=self._track,
            screenshot_path=self._screenshot_path,
            screenshot_url=self._screenshot_url,
            prefill=self._result,
        )
        await interaction.response.send_modal(modal)


class SubmissionCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="submit-manual", description="Submit a time attack lap time (manual entry)")
    @app_commands.describe(
        time="e.g. 1:23.456 or 58.120 for sub-minute laps",
        track="Select a track from the list",
        vehicle="Search by name or manufacturer",
        class_="Select a vehicle class from the list",
        screenshot="Attach a .jpg, .png, or .webp screenshot",
    )
    @app_commands.rename(class_="class")
    async def submit_manual(
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
            await interaction.response.send_message(f"**Time:** {exc}", ephemeral=True)
            return

        if track not in config.TRACKS:
            await interaction.response.send_message(
                f"**Track:** `{track}` isn't recognised — select a track from the autocomplete list.",
                ephemeral=True,
            )
            return

        if class_ not in config.CLASSES:
            valid = ", ".join(f"`{c}`" for c in config.CLASSES)
            await interaction.response.send_message(
                f"**Class:** `{class_}` isn't valid — choose from {valid}.",
                ephemeral=True,
            )
            return

        vehicle_names = config.get_vehicle_names()
        if vehicle_names and vehicle not in vehicle_names:
            await interaction.response.send_message(
                f"**Vehicle:** `{vehicle}` isn't in the vehicle list — use the autocomplete to search by name or manufacturer.",
                ephemeral=True,
            )
            return

        ext = Path(screenshot.filename).suffix.lower()
        if ext not in _IMAGE_EXTENSIONS:
            await interaction.response.send_message(
                f"**Screenshot:** `{screenshot.filename}` isn't a supported file type — attach a `.jpg`, `.png`, or `.webp` image.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        config.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{interaction.user.id}_{int(discord.utils.utcnow().timestamp())}{ext}"
        dest = config.SCREENSHOTS_DIR / filename

        http_session = self.bot.http_session  # type: ignore[attr-defined]
        async with http_session.get(screenshot.url) as resp:
            if resp.status != 200:
                await interaction.followup.send(
                    "Failed to download screenshot — please try again.", ephemeral=True
                )
                return
            try:
                data = await resp.content.read(10 * 1024 * 1024)  # 10 MB cap
                dest.write_bytes(data)
            except OSError:
                await interaction.followup.send(
                    "Failed to save screenshot — please try again.", ephemeral=True
                )
                return

        entry_id = add_entry(
            discord_id=str(interaction.user.id),
            username=interaction.user.name,
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

    @submit_manual.autocomplete("track")
    async def _track_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=t, value=t)
            for t in config.TRACKS
            if current.lower() in t.lower()
        ][:25]

    @submit_manual.autocomplete("class_")
    async def _class_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=c, value=c)
            for c in config.CLASSES
            if current.lower() in c.lower()
        ][:25]

    @submit_manual.autocomplete("vehicle")
    async def _vehicle_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=v["name"], value=v["name"])
            for v in config.VEHICLES
            if current.lower() in v["name"].lower() or current.lower() in v["manufacturer"].lower()
        ][:25]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SubmissionCog(bot))
