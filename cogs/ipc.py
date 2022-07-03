from discord.ext import commands, ipc
import config


class IpcRoutes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, "ipc"):
            bot.ipc = ipc.Server(self.bot, host=config.host,
                                 port=80, secret_key=config.secret_key)
            bot.ipc.start(self)

    @ipc.server.route()
    async def get_guild_count(self, data):
        return len(self.guilds)

    @ipc.server.route()
    async def get_guild_ids(self, data):
        final = []
        for guild in self.guilds:
            final.append(guild.id)
        return final  # returns the guild ids to the client

    @ipc.server.route()
    async def get_guild(self, data):
        guild = self.get_guild(data.guild_id)
        if guild is None:
            return None

        guild_data = {
            "name": guild.name,
            "id": guild.id,
            "prefix": "?"
        }

        return guild_data


async def setup(bot):
    await bot.add_cog(IpcRoutes(bot))
