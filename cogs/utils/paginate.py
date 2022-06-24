import asyncio
from typing import TYPE_CHECKING, Any, Dict, Optional, Union
import discord
from discord.ext import commands
from discord.ext.commands import Paginator as CommandPaginator
from discord.ext import menus

from .context import Context


class Pages(discord.ui.View):
    def __init__(self, source: menus.PageSource, *, ctx: Context):
        super().__init__()
        self.ctx: Context = ctx
        self.source = source
        self._current_page: int = 0

    @discord.ui.button(label='First', style=discord.ButtonStyle.blurple)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the first page"""
        await self.show_page(interaction, 0)

    @discord.ui.button(label='Previous', style=discord.ButtonStyle.blurple)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the previous page"""
        await self.show_page(interaction, self._current_page - 1)

    @discord.ui.button(label='-', style=discord.ButtonStyle.grey, disabled=True)
    async def current_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label='Next', style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the next page"""
        await self.show_page(interaction, self._current_page + 1)

    @discord.ui.button(label='Last', style=discord.ButtonStyle.blurple)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the last page"""
        await self.show_page(interaction, self.source.get_max_pages() - 1)

    async def _get_kwargs_from_page(self, page: int) -> Dict[str, Any]:
        value = await discord.utils.maybe_coroutine(self.source.format_page, self, page)
        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            return {'content': value, 'embed': None}
        elif isinstance(value, discord.Embed):
            return {'embed': value, 'content': None}
        else:
            return {}

    async def show_page(self, interaction: discord.Interaction, page_number: int) -> None:
        page = await self.source.get_page(page_number)
        self._current_page = page_number
        kwargs = await self._get_kwargs_from_page(page)
        print(kwargs)
        self.update_current(page_number)
        if kwargs:
            if interaction.response.is_done():
                if self.message:
                    await self.message.edit(**kwargs, view=self)
            else:
                await interaction.response.edit_message(**kwargs, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id in (self.ctx.bot.owner_id, self.ctx.author.id):
            return True
        await interaction.response.send_message('This pagination menu cannot be controlled by you, sorry!', ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        if self.message:
            await self.message.edit(view=None)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        if interaction.response.is_done():
            await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
        else:
            await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

    async def start(self, *, content: Optional[str] = None) -> None:

        await self.source._prepare_once()
        page = await self.source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        if content:
            kwargs.setdefault('content', content)

        self.update_current(0)
        self.message = await self.ctx.send(**kwargs, view=self)

    def update_current(self, page_number: int) -> None:
        self.current_page.label = str(page_number + 1)
        max_pages = self.source.get_max_pages()
        if max_pages is not None:
            self.last_page.disabled = (page_number + 1) >= max_pages
            if (page_number + 1) >= max_pages:
                self.next_page.disabled = True
            if page_number == 0:
                self.previous_page.disabled = True
