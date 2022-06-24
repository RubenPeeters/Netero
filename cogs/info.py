from typing import Optional
from idna import valid_contexto
from cogs.owner import MY_GUILD
from cogs.utils.help import PaginatedHelpCommand
import discord
from discord.app_commands.commands import describe
from discord.ext import commands
from discord import app_commands


from .utils import time
from .utils.embed import FooterEmbed
from .views.button import TestButton


class Info(commands.Cog):
    """Information on the bot, the server, ..."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.old_help_command: Optional[commands.HelpCommand] = bot.help_command
        bot.help_command = PaginatedHelpCommand()
        bot.help_command.cog = self

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name='📓')

    @commands.hybrid_group(invoke_without_command=False)
    async def info(self, ctx):
        """General info commands"""
        pass

    def cog_unload(self):
        self.bot.help_command = self.old_help_command

    @info.command()
    async def bot(self, ctx):
        '''Show information on the bot itself'''
        try:
            me = self.bot.get_user(self.bot.owner_id)
            embed = FooterEmbed(self.bot,
                                description="Multipurpose Discord Bot\n")
            embed.set_author(
                name=str(me), icon_url=me.display_avatar.url)
            embed.add_field(name="Want me in your server?",
                            value="Press [this link](https://discord.com/api/oauth2/authorize?client_id=988172257736142928&permissions=8&scope=bot%20applications.commands) or the big button on my profile.", inline=False)
            embed.add_field(name="Support server",
                            value="[Join here](https://discord.gg/2XfmHUH)", inline=False)
            embed.set_thumbnail(
                url='https://github.com/RubenPeeters/Netero/blob/main/cogs/assets/netero_profile.jpg?raw=true')
            embed.add_field(
                name="Donations", value="These are a great incentive for me to keep working on the bot. If you enjoy Netero, consider supporting its development by donating [here.](https://paypal.me/Itachibot)")
            await ctx.send(embed=embed)
        except Exception as e:
            exc = "{}: {}".format(type(e).__name__, e)
            print('Failed to send embed\n{}'.format(exc))

    @info.command()
    async def server(self, ctx):
        '''Show information on the current server'''
        try:
            server = ctx.guild
            if server is None:
                join = FooterEmbed(
                    self.bot, title='Whoops...', colour=self.bot.color, description='This can only be used in a server.')
                await ctx.send(embed=join)
            roles = [x.mention for x in server.roles]
            role_length = len(roles)
            roles.reverse()
            if role_length > 20:
                roles = roles[:20]
                roles.append('... [20/%s] roles' % role_length)
            roles = ', '.join(roles)
            channelz = len(server.channels)
            join = FooterEmbed(self.bot, title=str(
                server), colour=self.bot.color)
            join.set_thumbnail(url=server.icon.url)
            join.add_field(name='Owner', value=str(
                server.owner), inline=False)
            join.add_field(name='Members', value=str(
                server.member_count), inline=False)
            join.add_field(
                name='Channels', value=str(channelz), inline=False)
            join.add_field(name=' Roles', value=roles, inline=False)
            await ctx.send(embed=join)
        except Exception as e:
            exc = "{}: {}".format(type(e).__name__, e)
            print('Failed to send embed\n{}'.format(exc))


async def setup(bot):
    cog = Info(bot)
    await bot.add_cog(cog)
