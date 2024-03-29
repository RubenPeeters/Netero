import asyncio
from asyncio.log import logger
from quart import Quart, render_template, request, session, redirect, url_for
from quart_discord import DiscordOAuth2Session
from discord.ext import ipc
import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve

import logging

import config


log = logging.getLogger(__name__)

app = Quart(__name__)
ipc_client = ipc.Client(host=config.host, port=config.client_port,
                        secret_key=config.secret_key)
app.config["SECRET_KEY"] = config.secret_key
app.config["DISCORD_CLIENT_ID"] = config.client_id
app.config["DISCORD_CLIENT_SECRET"] = config.client_secret
app.config["DISCORD_REDIRECT_URI"] = config.redirect_uri
app.config["DEBUG"] = True
app.config["TESTING"] = True

discord = DiscordOAuth2Session(app)


@app.route("/")
async def home():
    guild_count = (await app.ipc.request("get_guild_count"))['guild_count']
    user_count = (await app.ipc.request("get_user_count"))['user_count']
    start_time = (await app.ipc.request("get_start_time"))['start_time']
    return await render_template("index.html", start_time=start_time, guild_count=guild_count, user_count=user_count, authorized=await discord.authorized)


@app.route("/login")
async def login():
    return await discord.create_session()


@app.route("/callback")
async def callback():
    try:
        await discord.callback()
    except Exception:
        return redirect(url_for("login"))

    return redirect(url_for("dashboard"))


@app.route("/dashboard")
async def dashboard():
    if not await discord.authorized:
        return redirect(url_for("login"))

    guild_ids = (await app.ipc.request("get_guild_ids"))['guilds']

    user_guilds = await discord.fetch_guilds()

    guilds = []

    for guild in user_guilds:
        if guild.permissions.administrator:
            guild.class_color = "green-border" if guild.id in guild_ids else "red-border"
            guilds.append(guild)

    guilds.sort(key=lambda x: x.class_color == "red-border")
    name = (await discord.fetch_user()).name
    return await render_template("dashboard.html",  guilds=guilds, username=name)


@app.route("/dashboard/<int:guild_id>")
async def dashboard_server(guild_id):
    if not await discord.authorized:
        return redirect(url_for("login"))

    guild = (await app.ipc.request("get_guild", guild_id=guild_id))['TO BE FILLED']
    if guild is None:
        return redirect(f'https://discord.com/oauth2/authorize?&client_id={app.config["DISCORD_CLIENT_ID"]}&scope=bot&permissions=8&guild_id={guild_id}&response_type=code&redirect_uri={app.config["DISCORD_REDIRECT_URI"]}')
    return guild["name"]


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    serve_config = Config()
    serve_config.bind = [f"{config.public_ip}:{config.public_port}"]
    print(ipc_client)
    try:
        # `Client.start()` returns new Client instance or None if it fails to start
        log.info('start app ipc')
        app.ipc = loop.run_until_complete(
            ipc_client.start(loop=loop, logger=log))
        log.info('start serving')
        loop.run_until_complete(serve(app, serve_config))
    finally:
        # Closes the session, doesn't close the loop
        loop.run_until_complete(app.ipc.close())
        loop.close()
