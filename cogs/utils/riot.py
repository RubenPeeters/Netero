from riotwatcher import LolWatcher, ApiError
import discord
from discord.ext import commands
import math


class Player:
    def __init__(self, name: str, region: str, DAO: LolWatcher, bot: commands.Bot):
        self.bot = bot
        if region.lower() == "kr" or region.lower() == "ru":
            self.region = region
        else:
            self.region = region + "1"
        # get the player object (1 request)
        try:
            self.player_object = DAO.summoner.by_name(self.region, name)
            self.summoner_id = self.player_object["id"]
            self.account_id = self.player_object["accountId"]
            self.profile_icon_id = self.player_object["profileIconId"]
            self.summoner_level = self.player_object["summonerLevel"]
            self.name = self.player_object['name']
        except ApiError as err:
            if err.response.status_code == 429:
                print(
                    f'We should retry in {err.headers["Retry-After"]} seconds.')
            elif err.response.status_code == 404:
                print('Summoner with that ridiculous name not found.')
            else:
                raise

        # get the league object set (1 request)
        try:
            self.leagues = DAO.league.by_summoner(
                self.region, self.summoner_id)

            self.solo_rank = "Unranked"
            self.solo_winrate = "not enough games played"
            self.flex_rank = "Unranked"
            self.flex_winrate = "not enough games played"
            for league in self.leagues:
                if league["queueType"] == "RANKED_SOLO_5x5":
                    self.solo_rank = f"{league['tier'].capitalize()}  {league['rank']} "
                    self.solo_winrate = str(league["wins"]) + "W/" + str(league["losses"]) + "L: " + str(
                        math.ceil(league["wins"]/(league["wins"]+league["losses"])*100)) + "% WR"
                if league["queueType"] == "RANKED_FLEX_SR":
                    self.flex_rank = f"{league['tier'].capitalize()}  {league['rank']} "
                    self.flex_winrate = str(league["wins"]) + "W/" + str(league["losses"]) + "L: " + str(
                        math.ceil(league["wins"]/(league["wins"]+league["losses"])*100)) + "% WR"
        except ApiError as err:
            if err.response.status_code == 429:
                print(
                    f'We should retry in {err.headers["Retry-After"]} seconds.')
            elif err.response.status_code == 404:
                print(
                    f'Leagues with ID {self.summoner_id} and region {self.region} not found.')
            else:
                raise

    def to_embed(self) -> discord.Embed():
        embed = discord.Embed(
            title=f"{self.name}", color=self.bot.color)
        embed.add_field(name="Solo/duo rank",
                        value=f'{self.solo_rank} - {self.solo_winrate}', inline=False)
        embed.add_field(
            name="Flex rank", value=f'{self.flex_rank} - {self.flex_winrate}', inline=False)
        embed.add_field(name="Level",
                        value=self.summoner_level, inline=False)
        embed.set_thumbnail(
            url=f'http://ddragon.leagueoflegends.com/cdn/12.11.1/img/profileicon/{self.profile_icon_id}.png')
        return embed
