import asyncio

from cogs.owner import MY_GUILD
import discord
from discord.ext import commands
from discord import app_commands

import config

from pantheon import pantheon
import asyncio

from riotwatcher import LolWatcher, ApiError

from .utils import time
from .utils.embed import FooterEmbed
from .views.button import TestButton
from .utils.riot import PantheonPlayer


class League(commands.Cog):
    """Commands that use the LoL API."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.waiting_embed = FooterEmbed(self.bot,
                                         title="Crunching the numbers...", description="Just a moment.")
        self.waiting_embed.set_thumbnail(
            url='https://github.com/RubenPeeters/Netero/blob/main/cogs/assets/netero_waiting.gif?raw=true')

    @commands.hybrid_group(invoke_without_command=False)
    async def league(self, ctx):
        """League of legends commands, !help league for more info."""
        embed = FooterEmbed(self.bot)
        embed.add_field(
            name='Whoops...', value="This command cannot be used without a subcommand.")
        await ctx.reply(embed=embed)

    @league.command(name="profile")
    async def profile(self, ctx, region: str, *, name: str):
        """Summoner profile info"""
        summoner = PantheonPlayer(
            region=region, name=name, bot=self.bot)

        message = await ctx.send(embed=self.waiting_embed)
        embed = await summoner.to_embed()
        await message.edit(embed=embed)

    @league.command(name="live")
    async def live(self, ctx, region: str, *, name: str):
        """Summoner in game info"""
        summoner = PantheonPlayer(
            region=region, name=name, bot=self.bot)
        message = await ctx.send(embed=self.waiting_embed)
        embed = await summoner.match_to_embed()
        await message.edit(embed=embed)


async def setup(bot):
    cog = League(bot)
    await bot.add_cog(cog)
