from discord.ext import commands


def get_emote_strings(name: str, bot: commands.Bot):
    if bot.emote_servers:
        for guild_id in bot.emote_servers:
            server = bot.get_guild(guild_id)
            for emote in server.emojis:
                if emote.name.lower() == name.lower():
                    return str(emote)
    return '❔'
