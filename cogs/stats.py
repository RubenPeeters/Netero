from discord.ext import commands
import discord

from .utils import time


class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    def get_bot_uptime(self, *, brief=False):
        return time.human_timedelta(self.bot.uptime, accuracy=None, brief=brief, suffix=False)

    @commands.hybrid_group(name="stats")
    async def stats(self, ctx):
        """Dummy command for cog group"""
        pass

    @stats.command(name="uptime")
    async def uptime_command(self, ctx):
        """Tells you how long the bot has been up for."""
        await ctx.send(f'Uptime: **{self.get_bot_uptime()}**')


async def setup(bot):
    cog = Stats(bot)
    await bot.add_cog(cog)
