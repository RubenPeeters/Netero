from cogs.owner import MY_GUILD
import discord
from discord.ext import commands
from discord import app_commands

import config

from riotwatcher import LolWatcher, ApiError

from .utils import time
from .utils.embed import FooterEmbed
from .views.button import TestButton
from .utils.riot import Player


class League(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.DAO: LolWatcher = LolWatcher(config.riot_api)

    lol = app_commands.Group(
        name="league", description="Overall league of legends commands.")

    @lol.command(name="profile")
    async def profile(self, interaction, region: str, *, name: str):
        """Summoner profile info"""
        summoner = Player(region=region, name=name, DAO=self.DAO, bot=self.bot)
        await interaction.response.send_message(embed=summoner.to_embed())


async def setup(bot):
    cog = League(bot)
    await bot.add_cog(cog)
