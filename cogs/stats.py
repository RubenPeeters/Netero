from cogs.owner import MY_GUILD
import discord
from discord.ext import commands
from discord import app_commands


from .utils import time
from .views.button import TestButton


class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    def get_bot_uptime(self, *, brief=False):
        return time.human_timedelta(self.bot.uptime, accuracy=None, brief=brief, suffix=False)

    @discord.ui.button(label='TEST')
    async def test_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=f'Button pressed!', view=self)

    @app_commands.command(name="uptime")
    async def uptime(self, interaction):
        """Tells you how long the bot has been up for."""
        await interaction.response.send_message(content=f'Uptime: **{self.get_bot_uptime()}**')

    @app_commands.command(name="ui")
    async def ui(self, interaction):
        """Discord UI testing."""
        view = discord.ui.View()
        button = TestButton(self.bot)
        input = discord.ui.TextInput(label="Test input")
        options = discord.SelectOption(label='Test 1', value='test-1')
        select = discord.ui.Select(options=[options])
        view.add_item(button)
        # view.add_item(input)
        # view.add_item(select)
        await interaction.response.send_message(content=f'Test message', view=view)


async def setup(bot):
    cog = Stats(bot)
    await bot.add_cog(cog)
