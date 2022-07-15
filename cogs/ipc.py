from wsgiref.simple_server import WSGIRequestHandler
from discord.ext import commands, ipc
import config


class IpcRoutes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, "ipc"):
            bot.ipc = ipc.Server(self.bot, host=config.host,
                                 port=config.server_port, secret_key=config.secret_key)
            bot.ipc.start()

    async def on_ipc_ready(self):
        """Called upon the IPC Server being ready"""
        print("Ipc is ready.")

    async def on_ipc_error(self, endpoint, error):
        """Called upon an error being raised within an IPC route"""
        print(endpoint, "raised", error)

    @ipc.server.route()
    async def get_guild_count(self, data):
        return {'guild_count': len(self.bot.guilds) - len(self.bot.emote_servers)}

    @ipc.server.route()
    async def get_user_count(self, data):
        return {'user_count': sum(1 for _ in self.bot.get_all_members())}

    @ipc.server.route()
    async def get_guild_ids(self, data):
        final = []
        for guild in self.bot.guilds:
            final.append(guild.id)
        print(final)
        return {'guilds': final}  # returns the guild ids to the client

    @ipc.server.route()
    async def get_guild(self, data):
        guild = self.bot.get_guild(data.guild_id)
        if guild is None:
            return None

        guild_data = {
            "name": guild.name,
            "id": guild.id,
            "prefix": "?"
        }

        return {'guild_data': guild_data}

    @ipc.server.route()
    async def get_start_time(self, data):
        return {'start_time': str(self.bot.uptime)}


async def setup(bot):
    await bot.add_cog(IpcRoutes(bot))
