from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
from database import get_history, get_leaderboard, get_user_times
from utils import format_lap_time


class QueryCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="leaderboard", description="View fastest times on a track")
    @app_commands.describe(track="The track", class_="Filter by vehicle class (optional)")
    @app_commands.rename(class_="class")
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        track: str,
        class_: Optional[str] = None,
    ) -> None:
        entries = get_leaderboard(track, class_)
        if not entries:
            label = f"**{track}**" + (f" ({class_})" if class_ else "")
            await interaction.response.send_message(
                f"No times recorded for {label}.", ephemeral=True
            )
            return

        title = f"Leaderboard — {track}" + (f" [{class_}]" if class_ else " — Top 5 Per Class")
        embed = discord.Embed(title=title, color=discord.Color.gold())

        if class_:
            lines = [
                f"{i}. **{e['username']}** — {format_lap_time(e['lap_time_ms'])} | {e['vehicle']}"
                for i, e in enumerate(entries, 1)
            ]
            desc = "\n".join(lines)
            embed.description = desc[:4096] + ("…" if len(desc) > 4096 else "")
        else:
            by_class: dict[str, list[dict]] = {}
            for e in entries:
                by_class.setdefault(e["class"], []).append(e)
            for cls in config.CLASSES:
                cls_entries = by_class.get(cls)
                if not cls_entries:
                    continue
                lines = [
                    f"{i}. **{e['username']}** — {format_lap_time(e['lap_time_ms'])} | {e['vehicle']}"
                    for i, e in enumerate(cls_entries, 1)
                ]
                value = "\n".join(lines)
                embed.add_field(
                    name=f"Class {cls}",
                    value=value[:1024] + ("…" if len(value) > 1024 else ""),
                    inline=False,
                )

        await interaction.response.send_message(embed=embed)

    @leaderboard.autocomplete("track")
    async def _lb_track_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=t, value=t)
            for t in config.TRACKS if current.lower() in t.lower()
        ][:25]

    @leaderboard.autocomplete("class_")
    async def _lb_class_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=c, value=c)
            for c in config.CLASSES if current.lower() in c.lower()
        ][:25]

    @app_commands.command(name="my-times", description="View your personal lap times")
    @app_commands.describe(track="Filter to a specific track (optional)")
    async def my_times(
        self,
        interaction: discord.Interaction,
        track: Optional[str] = None,
    ) -> None:
        entries = get_user_times(str(interaction.user.id), track)
        if not entries:
            suffix = f" on **{track}**" if track else ""
            await interaction.response.send_message(
                f"You have no times recorded{suffix}.", ephemeral=True
            )
            return

        title = "Your Times" + (f" — {track}" if track else "")
        embed = discord.Embed(title=title, color=discord.Color.blue())
        lines = [
            f"**{e['track']}** [{e['class']}] — {format_lap_time(e['lap_time_ms'])} | {e['vehicle']} *(ID: {e['id']})*"
            for e in entries
        ]
        desc = "\n".join(lines)
        embed.description = desc[:4000] + ("\n..." if len(desc) > 4000 else "")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @my_times.autocomplete("track")
    async def _mt_track_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=t, value=t)
            for t in config.TRACKS if current.lower() in t.lower()
        ][:25]

    @app_commands.command(name="history", description="View full submission history for a track")
    @app_commands.describe(track="The track", class_="Filter by class (optional)")
    @app_commands.rename(class_="class")
    async def history(
        self,
        interaction: discord.Interaction,
        track: str,
        class_: Optional[str] = None,
    ) -> None:
        entries = get_history(track, class_)
        if not entries:
            label = f"**{track}**" + (f" ({class_})" if class_ else "")
            await interaction.response.send_message(
                f"No history for {label}.", ephemeral=True
            )
            return

        title = f"History — {track}" + (f" [{class_}]" if class_ else "")
        embed = discord.Embed(title=title, color=discord.Color.purple())
        lines = [
            f"`{e['submitted_at'][:10]}` **{e['username']}** [{e['class']}] — {format_lap_time(e['lap_time_ms'])} | {e['vehicle']}"
            for e in entries
        ]
        desc = "\n".join(lines)
        embed.description = desc[:4000] + ("\n..." if len(desc) > 4000 else "")
        await interaction.response.send_message(embed=embed)

    @history.autocomplete("track")
    async def _hist_track_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=t, value=t)
            for t in config.TRACKS if current.lower() in t.lower()
        ][:25]

    @history.autocomplete("class_")
    async def _hist_class_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=c, value=c)
            for c in config.CLASSES if current.lower() in c.lower()
        ][:25]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(QueryCog(bot))
