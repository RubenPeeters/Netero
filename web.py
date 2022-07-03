import asyncio
from quart import Quart, render_template, request, session, redirect, url_for
from quart_discord import DiscordOAuth2Session
from discord.ext import ipc


import config


app = Quart(__name__)
ipc_client = ipc.Client(host=config.host, port=config.client_port,
                        secret_key=config.secret_key)
app.config["SECRET_KEY"] = config.secret_key
app.config["DISCORD_CLIENT_ID"] = config.client_id
app.config["DISCORD_CLIENT_SECRET"] = config.client_secret
app.config["DISCORD_REDIRECT_URI"] = config.redirect_uri

discord = DiscordOAuth2Session(app)


@app.route("/")
async def home():
    return await render_template("index.html", authorized=await discord.authorized)


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

    guild_count = await ipc_client.request("get_guild_count")
    guild_ids = await ipc_client.request("get_guild_ids")

    user_guilds = await discord.fetch_guilds()

    guilds = []

    for guild in user_guilds:
        if guild.permissions.administrator:
            guild.class_color = "green-border" if guild.id in guild_ids else "red-border"
            guilds.append(guild)

    guilds.sort(key=lambda x: x.class_color == "red-border")
    name = (await discord.fetch_user()).name
    return await render_template("dashboard.html", guild_count=guild_count, guilds=guilds, username=name)


@app.route("/dashboard/<int:guild_id>")
async def dashboard_server(guild_id):
    if not await discord.authorized:
        return redirect(url_for("login"))

    guild = await ipc_client.request("get_guild", guild_id=guild_id)
    if guild is None:
        return redirect(f'https://discord.com/oauth2/authorize?&client_id={app.config["DISCORD_CLIENT_ID"]}&scope=bot&permissions=8&guild_id={guild_id}&response_type=code&redirect_uri={app.config["DISCORD_REDIRECT_URI"]}')
    return guild["name"]


print('start')
loop = asyncio.get_event_loop() or asyncio.new_event_loop()
print('start')
try:
    # `Client.start()` returns new Client instance or None if it fails to start
    print('start')
    app.ipc = loop.run_until_complete(ipc_client.start(loop=loop))
    app.run(loop=loop)
finally:
    # Closes the session, doesn't close the loop
    loop.run_until_complete(app.ipc.close())
    loop.close()
