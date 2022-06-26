from discord.ext import commands


def get_emote_strings(name: str, bot: commands.Bot):
    print('start')
    if bot.emote_servers:
        print(bot.emote_servers)
        for guild_id in bot.emote_servers:
            print(guild_id)
            server = bot.get_guild(guild_id)
            print(server)
            for emote in server.emojis:
                print(emote)
                print(emote.name)
                if emote.name.lower() == name.lower():
                    return str(emote)
    return '❔'
