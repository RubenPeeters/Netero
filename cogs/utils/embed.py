from discord.ext import commands
import discord


class FooterEmbed(discord.Embed):
    def __init__(self, bot, **kwargs):
        super().__init__(color=discord.Colour(0xda9f31), **kwargs)
        self.bot = bot
        self.set_footer(icon_url=self.bot.user.avatar.url,
                        text="Human potential for evolution is limitless.")
