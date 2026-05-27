import discord
from discord import app_commands
from discord.ext import commands

import database


class TelemetryCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="dataout-register", description="Register for Data Out auto-submit")
    async def dataout_register(self, interaction: discord.Interaction) -> None:
        token = database.create_token(str(interaction.user.id))
        await interaction.response.send_message(
            f"**Your Data Out token:**\n```\n{token}\n```\n"
            "Paste this into the fh6-relay app when prompted on first launch.\n"
            "This token expires in **30 days** — use `/dataout-refresh` to renew it.\n"
            "⚠️ Keep this private — anyone with your token can submit times on your behalf.",
            ephemeral=True,
        )

    @app_commands.command(name="dataout-refresh", description="Refresh your Data Out token (invalidates old one)")
    async def dataout_refresh(self, interaction: discord.Interaction) -> None:
        token = database.create_token(str(interaction.user.id))
        await interaction.response.send_message(
            f"**Your new Data Out token:**\n```\n{token}\n```\n"
            "Your previous token has been invalidated. Update it in fh6-relay via the Settings menu.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TelemetryCog(bot))
