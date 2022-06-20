import discord
from discord.ext import commands
from cogs.utils import context
import traceback
import logging
import config
import sys

import aiohttp
import asyncpg

log = logging.getLogger(__name__)

startup_cogs = [
    # 'cogs.images',
    'cogs.stats',
    'cogs.owner'
]


class Netero(commands.Bot):

    @property
    def owner(self) -> discord.User:
        return self.bot_app_info.owner

    @property
    def config(self):
        return __import__('config')

    def __init__(self):
        intents = discord.Intents(
            guilds=True,
            members=True,
            bans=True,
            emojis=True,
            voice_states=True,
            messages=True,
            reactions=True,
            message_content=True,
        )
        super().__init__(
            command_prefix='!',
            description='Multi-functional personal slave',
            intents=intents,
            enable_debug_events=True,
        )
        self.session = aiohttp.ClientSession()
        self.blacklist = []
        self.client_id: str = config.client_id

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('This command cannot be used in private messages.')
        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send('Sorry. This command is disabled and cannot be used.')
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if not isinstance(original, discord.HTTPException):
                print(f'In {ctx.command.qualified_name}:', file=sys.stderr)
                traceback.print_tb(original.__traceback__)
                print(f'{original.__class__.__name__}: {original}',
                      file=sys.stderr)
        elif isinstance(error, commands.ArgumentParsingError):
            await ctx.send(str(error))

    async def on_ready(self):
        if not hasattr(self, 'uptime'):
            self.uptime = discord.utils.utcnow()

        for cog in startup_cogs:
            try:
                await self.load_extension(cog)
            except Exception as e:
                print(f'Failed to load cog {cog}.', file=sys.stderr)
                traceback.print_exc()

        print(f'Ready: {self.user} (ID: {self.user.id})')

    async def process_commands(self, message: discord.Message):
        ctx = await self.get_context(message, cls=context.Context)

        if ctx.command is None:
            return

        if ctx.author.id in self.blacklist:
            return

        if ctx.guild is not None and ctx.guild.id in self.blacklist:
            return

        try:
            await self.invoke(ctx)
        finally:
            pass

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        await self.process_commands(message)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        if guild.id in self.blacklist:
            await guild.leave()

    async def start(self) -> None:
        await super().start(config.token, reconnect=True)

    async def close(self) -> None:
        await super().close()
        await self.session.close()

    async def start(self) -> None:
        await super().start(config.token, reconnect=True)
