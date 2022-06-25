import asyncio
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
    """Commands that use the LoL API."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.DAO: LolWatcher = LolWatcher(config.riot_api)

    @commands.hybrid_group(invoke_without_command=False)
    async def league(self, ctx):
        """League of legends commands, !help league for more info."""
        embed = FooterEmbed(self.bot)
        embed.add_field(
            name='Whoops...', value="This command cannot be used without a subcommand.")
        await ctx.send(embed=embed)

    @league.command(name="profile")
    async def profile(self, ctx, region: str, *, name: str):
        """Summoner profile info"""
        summoner = Player(region=region, name=name, DAO=self.DAO, bot=self.bot)
        await ctx.send(embed=summoner.to_embed())

    # @lol.command(name="history")
    # async def profile(self, interaction, region: str, *, name: str):
    #     """Summoner profile info"""
    #     summoner = Player(region=region, name=name, DAO=self.DAO, bot=self.bot)
    #     await interaction.response.send_message(embed=summoner.to_embed())

    # @lol.command(name="live")
    # async def live(self, interaction, region: str, *, name: str):
    #     """Summoner in game info"""
    #     async def a_loop():
    #         summoner = Player(region=region, name=name,
    #                           DAO=self.DAO, bot=self.bot)
    #         await interaction.response.edit_message(embed=summoner.match_to_embed())

    #     loop = asyncio.get_event_loop()
    #     loop.run.until_complete(a_loop())
    #     await interaction.response.defer(thinking=True)


async def setup(bot):
    cog = League(bot)
    await bot.add_cog(cog)
