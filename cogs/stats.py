from discord.ext import commands
import discord

from .utils import time


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_bot_uptime(self, *, brief=False):
        return time.human_timedelta(self.bot.uptime, accuracy=None, brief=brief, suffix=False)

    @commands.command()
    async def uptime(self, ctx):
        """Tells you how long the bot has been up for."""
        await ctx.send(f'Uptime: **{self.get_bot_uptime()}**')


async def setup(bot):
    cog = Stats(bot)
    await bot.add_cog(cog)
