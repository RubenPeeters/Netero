import asyncio

from cogs.owner import MY_GUILD
import discord
from discord.ext import commands
from discord import app_commands

import config

from pantheon import pantheon
import asyncio

from riotwatcher import LolWatcher, ApiError

from .utils import time, db
from .utils.embed import FooterEmbed
from .views.button import TestButton
from .utils.riot import PantheonPlayer, VERSION


# class Players(db.Table):
#     id = db.PrimaryKeyColumn()
#     summoner_id = db.Column(db.String, index=True)
#     updated = db.Column(db.Datetime, default="now() at time zone 'utc'")
#     account_id = db.Column(db.String)
#     profile_icon_id = db.Column(db.String)
#     summoner_level = db.Column(db.String)
#     puuid = db.Column(db.String)
#     name = db.Column(db.String)
#     solo_rank = db.Column(db.String)
#     solo_winrate = db.Column(db.String)
#     flex_rank = db.Column(db.String)
#     flex_winrate = db.Column(db.String)
#     solo_LP = db.Column(db.String)
#     flex_LP = db.Column(db.String)


class Summoner(db.Table):
    id = db.PrimaryKeyColumn()
    # riot
    summoner_id = db.Column(db.String, index=True)
    region = db.Column(db.String)
    # discord
    account_id = db.Column(db.String)


class League(commands.Cog):
    """Commands that use the LoL API."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.waiting_embed = FooterEmbed(self.bot,
                                         title="Crunching the numbers...", description="Just a moment.")
        self.waiting_embed.set_thumbnail(
            url='https://raw.githubusercontent.com/RubenPeeters/Netero/main/cogs/assets/netero_waiting.gif')

    @commands.hybrid_group(invoke_without_command=False)
    async def league(self, ctx):
        """League of legends commands, !help league for more info."""
        embed = FooterEmbed(self.bot)
        embed.add_field(
            name='Whoops...', value="This command cannot be used without a subcommand.")
        await ctx.reply(embed=embed)

    @league.command(name="profile")
    async def profile(self, ctx, region: str, *, name: str):
        """Summoner profile info"""
        summoner = PantheonPlayer(
            region=region, name=name, bot=self.bot)

        message = await ctx.send(embed=self.waiting_embed)
        embed = await summoner.to_embed()
        await message.edit(embed=embed)

    @league.command(name="live")
    async def live(self, ctx, region: str, *, name: str):
        """Summoner in game info"""
        summoner = PantheonPlayer(
            region=region, name=name, bot=self.bot)
        message = await ctx.send(embed=self.waiting_embed)
        embed = await summoner.match_to_embed()
        await message.edit(embed=embed)

    @league.command(name="add")
    async def add(self, ctx, region: str, *, name: str):
        """Link a league of legends summoner to your discord account."""
        query = """
                    INSERT INTO Summoner (summoner_id, region, account_id)
                    VALUES ($1, $2, $3);
                """
        summoner = PantheonPlayer(
            region=region, name=name, bot=self.bot)
        await summoner.initialize_player_object(ranks=False, match=False, data=False)
        try:
            await ctx.db.execute(query, summoner.summoner_id, summoner.region, str(ctx.author.id))
        except Exception as e:
            print(e)
            await ctx.send('Could not link account.')
            return

        message = await ctx.send(embed=self.waiting_embed)
        embed = FooterEmbed(self.bot, title='Succes!',
                            description=f'{summoner.name} is now linked to your account with region {region.upper()}.')
        embed.set_author(
            name=f'{summoner.name}', icon_url=f'http://ddragon.leagueoflegends.com/cdn/{VERSION}/img/profileicon/{summoner.profile_icon_id}.png')
        await message.edit(embed=embed)


async def setup(bot):
    cog = League(bot)
    await bot.add_cog(cog)
