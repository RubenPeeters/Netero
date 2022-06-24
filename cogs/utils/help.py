""" 
COMPLETELY UNNECESARY WITH SLASH COMMANDS
still here as an example
"""

from __future__ import annotations


from discord.ext import commands, menus

from .paginate import Pages
import discord

from .context import Context


class HelpMenu(Pages):
    def __init__(self, source: menus.PageSource, ctx: Context):
        super().__init__(source, ctx=ctx)

    async def rebind(self, source: menus.PageSource, interaction: discord.Interaction) -> None:
        self.source = source
        self.current_page = 0

        await self.source._prepare_once()
        page = await self.source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        self.update_current(0)
        await interaction.response.edit_message(**kwargs, view=self)


class PaginatedHelpCommand(commands.HelpCommand):
    context: Context

    def __init__(self):
        super().__init__(
            command_attrs={
                'cooldown': commands.CooldownMapping.from_cooldown(1, 3.0, commands.BucketType.member),
                'help': 'Shows help about the bot',
            }
        )

    def get_command_signature(self, command: commands.Command) -> str:
        parent = command.full_parent_name
        if len(command.aliases) > 0:
            aliases = '|'.join(command.aliases)
            fmt = f'[{command.name}|{aliases}]'
            if parent:
                fmt = f'{parent} {fmt}'
            alias = fmt
        else:
            alias = command.name if not parent else f'{parent} {command.name}'
        return f'{alias} {command.signature}'

    async def send_bot_help(self, mapping):
        bot = self.context.bot

        def key(command) -> str:
            cog = command.cog
            return cog.qualified_name if cog else '\U0010ffff'

        entries: list[commands.Command] = await self.filter_commands(bot.commands, sort=True, key=key)
        menu = HelpMenu(HelpPageSource(
            entries), ctx=self.context)
        await self.context.release()
        await menu.start()

    async def send_cog_help(self, cog):
        entries = await self.filter_commands(cog.get_commands(), sort=True)
        menu = HelpMenu(HelpPageSource(
            entries), ctx=self.context)
        await self.context.release()
        await menu.start()

    def common_command_formatting(self, embed_like, command):
        embed_like.title = self.get_command_signature(command)
        if command.description:
            embed_like.description = f'{command.description}\n\n{command.help}'
        else:
            embed_like.description = command.help or 'No help found...'

    async def send_command_help(self, command):
        # No pagination necessary for a single command.
        embed = discord.Embed(colour=discord.Colour(0xA8B9CD))
        self.common_command_formatting(embed, command)
        await self.context.send(embed=embed)

    async def send_command_help(self, command):
        # No pagination necessary for a single command.
        embed = discord.Embed(colour=discord.Colour(0xA8B9CD))
        self.common_command_formatting(embed, command)
        await self.context.send(embed=embed)

    async def send_group_help(self, group):
        subcommands = group.commands
        if len(subcommands) == 0:
            return await self.send_command_help(group)

        entries = await self.filter_commands(subcommands, sort=True)
        if len(entries) == 0:
            return await self.send_command_help(group)

        source = HelpPageSource(entries, prefix=self.context.clean_prefix)
        self.common_command_formatting(source, group)
        menu = HelpMenu(source, ctx=self.context)
        await self.context.release()
        await menu.start()


class HelpPageSource(menus.ListPageSource):
    def __init__(self, commands: list[commands.Command]):
        super().__init__(entries=commands, per_page=6)
        self.title: str = f'All commands'
        self.description: str = 'If you need more help, join [the support server.](https://discord.gg/2XfmHUH)'

    async def format_page(self, menu: Pages, commands: list[commands.Command]):
        embed = discord.Embed(
            title=self.title, description=self.description, colour=menu.ctx.bot.color)

        for command in commands:
            signature = f'{command.qualified_name} {command.signature}'
            embed.add_field(
                name=signature, value=command.short_doc or 'No help given...', inline=False)

        maximum = self.get_max_pages()
        if maximum > 1:
            embed.set_author(
                name=f'Page {menu._current_page + 1}/{maximum} ({len(self.entries)} commands)')

        embed.set_footer(
            text=f'Use "/help command" for more info on a command.')
        return embed
