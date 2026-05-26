from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from database import delete_entry, get_entry
from utils import format_lap_time


class _ConfirmDeleteView(discord.ui.View):
    def __init__(self, entry: dict) -> None:
        super().__init__(timeout=30)
        self.entry = entry

    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        deleted = delete_entry(self.entry["id"], str(interaction.user.id))
        if deleted:
            screenshot = Path(self.entry["screenshot_path"])
            if screenshot.exists():
                screenshot.unlink()
            await interaction.response.edit_message(
                content=f"Entry #{self.entry['id']} deleted.", embed=None, view=None
            )
        else:
            await interaction.response.edit_message(
                content="Could not delete entry — it may have already been removed.",
                embed=None,
                view=None,
            )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        await interaction.response.edit_message(
            content="Deletion cancelled.", embed=None, view=None
        )

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="delete", description="Delete one of your own time entries")
    @app_commands.describe(entry_id="Entry ID to delete — find it with /my-times")
    async def delete(self, interaction: discord.Interaction, entry_id: int) -> None:
        entry = get_entry(entry_id)

        if entry is None:
            await interaction.response.send_message(
                f"Entry #{entry_id} not found.", ephemeral=True
            )
            return

        if entry["discord_id"] != str(interaction.user.id):
            await interaction.response.send_message(
                "You can only delete your own entries.", ephemeral=True
            )
            return

        embed = discord.Embed(title=f"Delete Entry #{entry_id}?", color=discord.Color.red())
        embed.add_field(name="Track", value=entry["track"], inline=True)
        embed.add_field(name="Class", value=entry["class"], inline=True)
        embed.add_field(name="Vehicle", value=entry["vehicle"], inline=True)
        embed.add_field(name="Lap Time", value=format_lap_time(entry["lap_time_ms"]), inline=True)
        embed.set_footer(text="This action cannot be undone.")

        await interaction.response.send_message(
            embed=embed, view=_ConfirmDeleteView(entry), ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
