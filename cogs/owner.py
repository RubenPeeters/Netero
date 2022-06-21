from discord.ext import commands
import asyncio
import traceback
import discord
import inspect
import textwrap
import importlib
from contextlib import redirect_stdout
import io
import os
import re
import sys
import copy
import time
import subprocess
import config
from .utils.context import Context
from typing import Literal, Union, Optional

# to expose to the eval command
import datetime
from collections import Counter

MY_GUILD = discord.Object(id=config.owner_guild)


class GlobalChannel(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return await commands.TextChannelConverter().convert(ctx, argument)
        except commands.BadArgument:
            # Not found... so fall back to ID + global lookup
            try:
                channel_id = int(argument, base=10)
            except ValueError:
                raise commands.BadArgument(
                    f'Could not find a channel by ID {argument!r}.')
            else:
                channel = ctx.bot.get_channel(channel_id)
                if channel is None:
                    raise commands.BadArgument(
                        f'Could not find a channel by ID {argument!r}.')
                return channel


class Owner(commands.Cog):
    """Default owner commands."""

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None
        self.sessions = set()

    async def cog_check(self, ctx: Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    async def run_process(self, command):
        try:
            process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await self.bot.loop.run_in_executor(None, process.communicate)

        return [output.decode() for output in result]

    @commands.command(hidden=True)
    async def sync(self, ctx: Context, spec: str = None) -> None:
        async with ctx.typing():
            if spec == "~":
                fmt = await ctx.bot.tree.sync(guild=MY_GUILD)
                print('done')
            else:
                fmt = await ctx.bot.tree.sync()
                print('done')
            print(fmt)
            await ctx.send(
                f"Synced {len(fmt)} commands {'globally' if spec is None else 'to the current guild.'}"
            )

    @commands.command(hidden=True)
    async def load(self, ctx, *, module):
        """Loads a module."""
        try:
            await self.bot.load_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @commands.command(hidden=True)
    async def unload(self, ctx, *, module):
        """Unloads a module."""
        try:
            await self.bot.unload_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @commands.group(name='reload', hidden=True, invoke_without_command=True)
    async def _reload(self, ctx, *, module):
        """Reloads a module."""
        try:
            await self.bot.reload_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.send('\N{OK HAND SIGN}')

    _GIT_PULL_REGEX = re.compile(r'\s*(?P<filename>.+?)\s*\|\s*[0-9]+\s*[+-]+')

    def find_modules_from_git(self, output):
        files = self._GIT_PULL_REGEX.findall(output)
        ret = []
        for file in files:
            root, ext = os.path.splitext(file)
            if ext != '.py':
                continue

            if root.startswith('cogs/'):
                # A submodule is a directory inside the main cog directory for
                # my purposes
                ret.append((root.count('/') - 1, root.replace('/', '.')))

        # For reload order, the submodules should be reloaded first
        ret.sort(reverse=True)
        return ret

    async def reload_or_load_extension(self, module):
        try:
            await self.bot.reload_extension(module)
        except commands.ExtensionNotLoaded:
            await self.bot.load_extension(module)

    @_reload.command(name='all', hidden=True)
    async def _reload_all(self, ctx):
        """Reloads all modules, while pulling from git."""

        async with ctx.typing():
            stdout, stderr = await self.run_process('git pull')

        # progress and stuff is redirected to stderr in git pull
        # however, things like "fast forward" and files
        # along with the text "already up-to-date" are in stdout

        if stdout.startswith('Already up-to-date.'):
            return await ctx.send(stdout)

        modules = self.find_modules_from_git(stdout)
        mods_text = '\n'.join(
            f'{index}. `{module}`' for index, (_, module) in enumerate(modules, start=1))
        prompt_text = f'This will update the following modules, are you sure?\n{mods_text}'
        confirm = await ctx.prompt(prompt_text, reacquire=False)
        if not confirm:
            return await ctx.send('Aborting.')

        statuses = []
        for is_submodule, module in modules:
            if is_submodule:
                try:
                    actual_module = sys.modules[module]
                except KeyError:
                    statuses.append((ctx.tick(None), module))
                else:
                    try:
                        importlib.reload(actual_module)
                    except Exception as e:
                        statuses.append((ctx.tick(False), module))
                    else:
                        statuses.append((ctx.tick(True), module))
            else:
                try:
                    await self.reload_or_load_extension(module)
                except commands.ExtensionError:
                    statuses.append((ctx.tick(False), module))
                else:
                    statuses.append((ctx.tick(True), module))

        await ctx.send('\n'.join(f'{status}: `{module}`' for status, module in statuses))

    @commands.command(hidden=True)
    async def sudo(self, ctx, channel: Optional[GlobalChannel], who: Union[discord.Member, discord.User], *, command: str):
        """Run a command as another user optionally in another channel."""
        msg = copy.copy(ctx.message)
        channel = channel or ctx.channel
        msg.channel = channel
        msg.author = who
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        new_ctx._db = ctx._db
        await self.bot.invoke(new_ctx)

    @commands.command(hidden=True)
    async def do(self, ctx, times: int, *, command):
        """Repeats a command a specified number of times."""
        msg = copy.copy(ctx.message)
        msg.content = ctx.prefix + command

        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        new_ctx._db = ctx._db

        for i in range(times):
            await new_ctx.reinvoke()

    @commands.command()
    async def get_app_commands(self, ctx):
        print(await self.bot.tree.fetch_commands())


async def setup(bot):
    await bot.add_cog(Owner(bot))
