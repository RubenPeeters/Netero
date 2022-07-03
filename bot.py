from typing import Union
import discord
from discord import activity
from discord.ext import commands, ipc
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
    'cogs.info',
    # 'cogs.ipc'
]


def _prefix_callable(bot: commands.Bot, msg: discord.Message):
    user_id = bot.user.id
    base = [f'<@!{user_id}> ', f'<@{user_id}> ']
    if msg.guild is None:
        base.append('')
    return base


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
            command_prefix=_prefix_callable,
            description=f'Bot by Ruben.',
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
        self.logging_channel = 992146724002996314
        # create our IPC Server
        self.ipc = ipc.Server(self, secret_key=config.secret_key)

    async def setup_hook(self):
        for cog in startup_cogs:
            try:
                await self.load_extension(cog)
                log.info(f'{cog} is loaded succesfully.')
            except Exception as e:
                log.warn(f'Failed to load {cog}.')
                traceback.print_exc()
        self.ipc.start()

    # @commands.ipc.route()
    # async def get_guild_count(self, data):
    #     return len(self.guilds)

    # @commands.ipc.route()
    # async def get_guild_ids(self, data):
    #     final = []
    #     for guild in self.guilds:
    #         final.append(guild.id)
    #     return final  # returns the guild ids to the client

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

    async def on_ipc_ready(self):
        """Called upon the IPC Server being ready"""
        print("Ipc is ready.")

    async def on_ipc_error(self, endpoint, error):
        """Called upon an error being raised within an IPC route"""
        print(endpoint, "raised", error)

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

    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self.log_guild(guild=guild, color=0x00FF00, join=True)

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        await self.log_guild(guild=guild, color=0xFF0000, join=False)

    async def log_guild(self, guild: discord.Guild, color, join):
        MAX = 25
        embed = discord.Embed(
            colour=color, title=f'{"Joined" if join else "Left"} guild {guild.name}')
        emojis = ""
        count = 0

        if len(guild.emojis) > MAX:
            count = MAX
        else:
            count = len(guild.emojis)
        if join:
            for e in guild.emojis[:count]:
                emojis += f'{str(e)} '
        if join:
            payload = f"```fix\n{'Members':8}: {guild.member_count}\n{'Owner':8}: {guild.owner}\n{'ID':8}: {guild.id}```{emojis} [{count}/{len(guild.emojis)}]\n"
        else:
            payload = f"```fix\n{'Members':8}: {guild.member_count}\n{'Owner':8} {guild.owner}\n{'ID':8}: {guild.id}\n{'Emojis':8}: {len(guild.emojis)}```"
        embed.add_field(name='\u200b', value=payload)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        log_channel = await self.fetch_channel(self.logging_channel)
        await log_channel.send(embed=embed)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        await self.process_commands(message)

    async def close(self) -> None:
        await super().close()
        await self.session.close()

    async def start(self) -> None:
        await super().start(config.token, reconnect=True)
