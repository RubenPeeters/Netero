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

    @app_commands.command(name="stats")
    async def stats(self, interaction):
        """Tells you information about the bot itself."""
        try:
            owner = self.bot.get_user(self.bot.owner_id)
            embed = discord.Embed(color=owner.color)

            embed.set_author(
                name=str(owner), icon_url=owner.display_avatar.url)

            # statistics
            total_members = sum(1 for _ in self.bot.get_all_members())
            total_online = len({m.id for m in self.bot.get_all_members(
            ) if m.status is not discord.Status.offline})
            total_unique = len(self.bot.users)

            voice_channels = []
            text_channels = []
            for guild in self.bot.guilds:
                voice_channels.extend(guild.voice_channels)
                text_channels.extend(guild.text_channels)

            text = len(text_channels)
            voice = len(voice_channels)
            payload = f' \
            `Members:` {total_members}\n \
            `Channels:` {text + voice}\n \
            `Guilds:` {str(len(self.bot.guilds))}\n \
            `Uptime:` {self.get_bot_uptime(brief=True)}\n \
            '
            embed.set_thumbnail(url='../assets/netero_thumbnail.jpg')
            embed.add_field(
                name='\u200b', value=payload)
            embed.set_footer(
                text='Made with discord.py', icon_url=self.bot.user.display_avatar.url)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message('{}: {}'.format(type(e).__name__, e))


async def setup(bot):
    cog = Stats(bot)
    await bot.add_cog(cog)
