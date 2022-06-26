from typing import Union
import discord
from discord import activity
from discord.ext import commands
from cogs.utils.context import Context
import traceback
import logging
import config
import sys

import aiohttp
import asyncpg

log = logging.getLogger(__name__)

startup_cogs = [
    'cogs.league',
    'cogs.stats',
    'cogs.owner',
    'cogs.info'
]


class Netero(commands.Bot):

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
            activity=discord.Game('/help')
        )

        self.blacklist = []
        self.client_id: str = config.client_id
        self.owner_id: int = 150907968068648960
        self.color = discord.Colour(0xda9f31)
        self.emote_servers = [460816759554048000, 460816847437037580, 460816987912798252, 460817157756813312,
                              460817260341100556, 475616108766953482, 475630608073228290, 619836603543584769,
                              645690086893158429, 645689982677155840, 645690039908696065, 645689931313971210,
                              645690394910130217, 645690451696943124, 645690495078760469]

    async def setup_hook(self):
        for cog in startup_cogs:
            try:
                await self.load_extension(cog)
                log.info(f'{cog} is loaded succesfully.')
            except Exception as e:
                log.warn(f'Failed to load {cog}.')
                traceback.print_exc()

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
            print(f'In {ctx.command.qualified_name}:', file=sys.stderr)
            traceback.print_tb(original.__traceback__)
            print(f'{original.__class__.__name__}: {original}',
                  file=sys.stderr)

    async def on_ready(self):
        if not hasattr(self, 'uptime'):
            self.uptime = discord.utils.utcnow()

        log.info(f'Ready: {self.user} (ID: {self.user.id})')

    async def get_context(self, origin: Union[discord.Interaction, discord.Message], /, *, cls=Context) -> Context:
        return await super().get_context(origin, cls=cls)

    async def process_commands(self, message: discord.Message):
        ctx = await self.get_context(message, cls=Context)

        if ctx.command is None:
            return

        if ctx.author.id in self.blacklist:
            return

        if ctx.guild is not None and ctx.guild.id in self.blacklist:
            return

        try:
            await self.invoke(ctx)
        finally:
            await ctx.release()

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        await self.process_commands(message)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        if guild.id in self.blacklist:
            await guild.leave()

    async def close(self) -> None:
        await super().close()
        await self.session.close()

    async def start(self) -> None:
        await super().start(config.token, reconnect=True)
