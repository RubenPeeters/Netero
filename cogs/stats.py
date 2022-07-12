from cogs.owner import MY_GUILD
import discord
from discord.ext import commands
from discord import app_commands


from .utils import time
from .utils.embed import FooterEmbed
from .views.button import TestButton


class Stats(commands.Cog):
    """Statistics about the bot and its usage."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    def get_bot_uptime(self, *, brief=False):
        return time.human_timedelta(self.bot.uptime, accuracy=None, brief=brief, suffix=False)

    @commands.hybrid_command(name="uptime")
    async def uptime(self, ctx):
        """Tells you how long the bot has been up for."""
        await ctx.reply(content=f'Uptime: **{self.get_bot_uptime()}**')

    @commands.hybrid_command(name="ui", hidden=True)
    async def ui(self, ctx):
        """Discord UI testing."""
        view = discord.ui.View()
        button = TestButton(self.bot)
        input = discord.ui.TextInput(label="Test input")
        options = discord.SelectOption(label='Test 1', value='test-1')
        select = discord.ui.Select(options=[options])
        view.add_item(button)
        # view.add_item(input)
        # view.add_item(select)
        await ctx.reply(content=f'Test message', view=view)

    @commands.hybrid_command(name="stats")
    async def stats(self, ctx):
        """Tells you information about the bot itself."""
        try:
            embed = FooterEmbed(self.bot, title='Netero statistics')

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
            payload = f'```fix\n{"Members":8}: {total_members}\n{"Channels":8}: {text + voice}\n{"Servers":8}: {str(len(self.bot.guilds) - len(self.bot.emote_servers))}\n{"Uptime":8}: {self.get_bot_uptime(brief=True)}```\n'
            embed.set_thumbnail(
                url='https://github.com/RubenPeeters/Netero/blob/main/cogs/assets/netero_thumbnail.jpg?raw=true')
            embed.add_field(
                name='\u200b', value=payload)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.reply('{}: {}'.format(type(e).__name__, e))


async def setup(bot):
    cog = Stats(bot)
    await bot.add_cog(cog)
