from typing import Optional, Union

from colorama import Back
import discord
from discord.enums import ButtonStyle
from discord.ui import Button

"""
Classes for buttons and their views
Opting not to use back button as we would need to save a previous state, which seems abundant for now.
"""

# DEFAULT BUTTON


class TestButton(Button):
    def __init__(self, bot) -> None:
        self.bot = bot
        super().__init__(style=ButtonStyle.success, label='TEST')

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            self.view.clear_items()
            self.view.add_item(BackButton(self.bot))
            # message = await interaction.original_message()
            # await message.edit(content='Button tested :D', view=self._view)
            await interaction.response.edit_message(content='Button tested :D', view=self.view)
        except discord.NotFound:
            await interaction.response.defer()

# BACK BUTTON TO BE USED WITH TEST BUTTON


class BackButton(Button):
    def __init__(self, bot) -> None:
        self.bot = bot
        super().__init__(style=ButtonStyle.success, label='BACK')

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            self.view.clear_items()
            self.view.add_item(TestButton(self.bot))
            await interaction.response.edit_message(content='Back button pressed', view=self.view)
        except discord.NotFound:
            await interaction.response.defer()
