from idna import valid_contexto
from cogs.owner import MY_GUILD
import discord
from discord.ext import commands
from discord import app_commands


from .utils import time
from .utils.embed import FooterEmbed
from .views.button import TestButton


class Info(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    info = app_commands.Group(
        name="info", description='Info on the bot, servers or users.')

    @info.command()
    async def bot(self, interaction):
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
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            exc = "{}: {}".format(type(e).__name__, e)
            print('Failed to send embed\n{}'.format(exc))

    @info.command()
    @app_commands.guild_only()
    async def server(self, interaction):
        '''Show information on the current server'''
        try:
            server = interaction.guild
            roles = [x.name for x in server.roles]
            role_length = len(roles)
            if role_length > 50:
                roles = roles[:50]
                roles.append('... [50/%s] roles' % role_length)
            roles = ', '.join(roles)
            channelz = len(server.channels)
            join = FooterEmbed(self.bot, description='%s ' % (
                str(server)), title='Server name', colour=self.bot.color)
            join.set_thumbnail(url=server.icon.url)
            join.add_field(name=' __Owner__', value=str(
                server.owner), inline=False)
            join.add_field(name='__Members__', value=str(
                server.member_count), inline=False)
            join.add_field(
                name='__Channels__', value=str(channelz), inline=False)
            join.add_field(name=' __Roles__', value=roles, inline=False)
            await interaction.response.send_message(embed=join)
        except Exception as e:
            exc = "{}: {}".format(type(e).__name__, e)
            print('Failed to send embed\n{}'.format(exc))


async def setup(bot):
    cog = Info(bot)
    await bot.add_cog(cog)
