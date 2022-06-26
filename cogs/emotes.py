from typing import Optional
from cogs.owner import MY_GUILD
from cogs.utils.help import PaginatedHelpCommand
import discord
from discord.app_commands.commands import describe
from discord.ext import commands
from discord import app_commands


from .utils import time
from .utils.embed import FooterEmbed
from .views.button import TestButton
from .utils.context import Context
from .utils.emotes import get_emote_strings


class Emotes(commands.Cog):
    """Emote commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot


async def setup(bot):
    cog = Emotes(bot)
    await bot.add_cog(cog)
