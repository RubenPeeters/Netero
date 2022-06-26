
from .emotes import get_emote_strings
from pathlib import Path
import aiofiles
from riotwatcher import LolWatcher, ApiError
import discord
from discord.ext import commands
import math
import os

from pantheon import pantheon
import asyncio
import config
import json

VERSION = '12.11.1'


class StaticData:
    def __init__(self) -> None:
        self.champions_json = None
        self.summoner_json = None
        self.loaded = False

    def load_static(self):
        path = Path(__file__).parent
        FILES_PATH = os.path.join(path, 'static', "league", "champion.json")
        if os.path.exists(FILES_PATH):
            try:
                with open(FILES_PATH, encoding="utf-8") as f:
                    self.champions_json = json.load(f)
            except Exception as err:
                print(f'error {err}')
        else:
            print('no file')
        path = Path(__file__).parent
        FILES_PATH = os.path.join(path, 'static', "league", "summoner.json")
        if os.path.exists(FILES_PATH):
            try:
                with open(FILES_PATH, encoding="utf-8") as f:
                    self.summoner_json = json.load(f)
            except Exception as err:
                print(f'error {err}')
        else:
            print('no file')
        self.loaded = True


class PantheonPlayer:

    def __init__(self, name: str, region: str, bot: commands.Bot):
        self.bot = bot
        self.name = name
        if region.lower() == 'kr' or region.lower() == 'ru' or region.endswith('1'):
            self.region = region
        else:
            self.region = region + '1'
        self.DAO = pantheon.Pantheon(
            self.region, config.riot_api, requests_logging_function=lambda url, status, headers: print(url, status, headers), debug=True)
        self.player_object = None
        self.leagues = None
        self.current_match = None
        self.data = StaticData()

    async def initialize_player_object(self):
        if self.player_object is None:
            self.player_object = await self.DAO.get_summoner_by_name(self.name)
            self.summoner_id = self.player_object['id']
            self.account_id = self.player_object['accountId']
            self.profile_icon_id = self.player_object['profileIconId']
            self.summoner_level = self.player_object['summonerLevel']
            self.puuid = self.player_object['puuid']
            self.name = self.player_object['name']
            # initialize ranks
            await self.update_ranks()
            if not self.data.loaded:
                self.data.load_static()

    async def update_ranks(self):
        self.leagues = await self.DAO.get_league_position(self.summoner_id)
        self.solo_rank = 'Unranked'
        self.solo_winrate = 'not enough games played'
        self.flex_rank = 'Unranked'
        self.flex_winrate = 'not enough games played'
        self.solo_LP = None
        self.flex_LP = None
        for league in self.leagues:
            if league['queueType'] == 'RANKED_SOLO_5x5':
                self.solo_rank = f'{league["tier"].capitalize()}  {league["rank"]} '
                self.solo_winrate = str(league['wins']) + 'W/' + str(league['losses']) + 'L: ' + str(
                    math.ceil(league['wins']/(league['wins']+league['losses'])*100)) + '% WR'
                self.solo_LP = league['leaguePoints']
                self.solo_winrate_compact = f"{str(math.ceil(league['wins']/(league['wins']+league['losses'])*100))}% {str(league['wins']+league['losses'])}G"
            if league['queueType'] == 'RANKED_FLEX_SR':
                self.flex_rank = f'{league["tier"].capitalize()}  {league["rank"]} '
                self.flex_winrate = str(league['wins']) + 'W/' + str(league['losses']) + 'L: ' + str(
                    math.ceil(league['wins']/(league['wins']+league['losses'])*100)) + '% WR'
                self.flex_LP = league['leaguePoints']
                self.flex_winrate_compact = f"{str(math.ceil(league['wins']/(league['wins']+league['losses'])*100))}% {str(league['wins']+league['losses'])}G"

    async def get_current_match(self):
        try:
            self.current_match = await self.DAO.get_current_game(self.summoner_id)
        except:
            self.current_match = None

    async def getSummonerId(self, name):
        try:
            data = await self.DAO.get_summoner_by_name(name)
            return (data['id'], data['puuid'])
        except Exception as e:
            print(e)

    async def getRecentMatchlist(self, accountId, amount: int = 10):
        try:
            data = await self.DAO.get_matchlist(accountId, params={"start": 0, "count": amount})
            return data
        except Exception as e:
            print(e)

    async def getRecentMatches(self, accountId):
        try:
            matchlist = await self.getRecentMatchlist(accountId)
            tasks = [self.DAO.get_match(match)
                     for match in matchlist]
            return await asyncio.gather(*tasks)
        except Exception as e:
            print(e)

    async def to_embed(self) -> discord.Embed():
        await self.initialize_player_object()
        embed = discord.Embed(
            title=f'{self.name}', color=self.bot.color)
        embed.add_field(name='Solo/duo rank',
                        value=f'{self.solo_rank} - {self.solo_winrate}', inline=False)
        embed.add_field(
            name='Flex rank', value=f'{self.flex_rank} - {self.flex_winrate}', inline=False)
        embed.add_field(name='Level',
                        value=self.summoner_level, inline=False)
        embed.set_thumbnail(
            url=f'http://ddragon.leagueoflegends.com/cdn/{VERSION}/img/profileicon/{self.profile_icon_id}.png')
        return embed

    async def match_to_embed(self) -> discord.Embed():
        await self.initialize_player_object()
        all_gamers = []

        await self.get_current_match()
        embed = discord.Embed(
            title=f'{self.name}s live game', color=self.bot.color)
        if not self.current_match:
            embed.add_field(name='\u200b', value='Currently not in game.')
            return embed
        team1 = "\n[Blue team]\n\n"
        team2 = "\n[Red team]\n\n"
        ssteam1 = "\n\u200b\n\n"
        ssteam2 = "\n\u200b\n\n"
        rankteam1 = "\n\u200b\n\n"
        rankteam2 = "\n\u200b\n\n"
        bansteam1 = "🟦:"
        bansteam2 = "🟥:"
        for gamer in self.current_match["participants"]:
            gamer_info = [gamer["championId"], gamer["summonerName"],
                          gamer["spell1Id"], gamer["spell2Id"], gamer["teamId"]]
            all_gamers.append(gamer_info)
        for gamer in all_gamers:
            player = PantheonPlayer(gamer[1], self.region, self.bot)
            await player.initialize_player_object()
            champ_id = self.get_champ_from_id(gamer[0])
            # champ_name = self.get_champ_name_from_id(gamer[0])
            ss1_name = self.get_ss_from_id(gamer[2])
            ss2_name = self.get_ss_from_id(gamer[3])
            champ_emote = get_emote_strings(champ_id, self.bot)
            ss1_emote = get_emote_strings(ss1_name, self.bot)
            ss2_emote = get_emote_strings(ss2_name, self.bot)
            if gamer[4] == 100:
                team1 += f"{champ_emote} {gamer[1]}\n"
                ssteam1 += "\t{} {}\n".format(ss1_emote, ss2_emote)
                rankteam1 += f"{player.solo_rank} ({player.solo_LP} LP)\n"
            else:
                team2 += f"{champ_emote} {gamer[1]}\n"
                ssteam2 += "\t{} {}\n".format(ss1_emote, ss2_emote)
                rankteam2 += f"{player.solo_rank} ({player.solo_LP} LP)\n"
        for i, bans in enumerate(self.current_match["bannedChampions"]):
            ban_champ_id = self.get_champ_from_id(bans['championId'])
            ban_champ_emote = get_emote_strings(ban_champ_id, self.bot)
            if i <= 4:
                bansteam1 += f"{ban_champ_emote} "
            elif i > 4 and i < 10:
                bansteam2 += f"{ban_champ_emote} "

        teams = team1 + team2
        ssteams = ssteam1 + ssteam2
        rankteams = rankteam1 + rankteam2
        bansteams = f'{bansteam1:<>}\t\t{bansteam2:<>}'
        embed.add_field(name="Teams", value=teams, inline=True)
        embed.add_field(name="Ranks", value=rankteams, inline=True)
        embed.add_field(name="Spells", value=ssteams, inline=True)
        embed.add_field(name="Bans", value=bansteams, inline=True)
        embed.set_author(
            name=f'{self.name}', icon_url=f'http://ddragon.leagueoflegends.com/cdn/{VERSION}/img/profileicon/{self.profile_icon_id}.png')
        return embed

    def get_champ_from_id(self, id: int) -> str:
        for champ in self.data.champions_json['data']:
            if int(self.data.champions_json['data'][champ]['key']) == id:
                return self.data.champions_json['data'][champ]['id']

        return None

    def get_champ_name_from_id(self, id: int) -> str:
        for champ in self.data.champions_json['data']:
            if int(self.data.champions_json['data'][champ]['key']) == id:
                return self.data.champions_json['data'][champ]['name']

        return None

    def get_ss_from_id(self, id: int):
        for spell in self.data.summoner_json['data']:
            if int(self.data.summoner_json['data'][spell]['key']) == id:
                return self.data.summoner_json['data'][spell]['name']
        return None
