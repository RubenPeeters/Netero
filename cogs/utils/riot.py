from riotwatcher import LolWatcher, ApiError
import discord
from discord.ext import commands
import math

VERSION = '12.11.1'


class Player:
    def __init__(self, name: str, region: str, DAO: LolWatcher, bot: commands.Bot):
        self.bot = bot
        self.DAO = DAO
        if region.lower() == 'kr' or region.lower() == 'ru' or region.endswith('1'):
            self.region = region
        else:
            self.region = region + '1'

        self.player_object = None
        self.leagues = None
        self.current_match = None

        # get the player object (1 request)
        try:
            self.player_object = DAO.summoner.by_name(self.region, name)
            self.summoner_id = self.player_object['id']
            self.account_id = self.player_object['accountId']
            self.profile_icon_id = self.player_object['profileIconId']
            self.summoner_level = self.player_object['summonerLevel']
            self.puuid = self.player_object['puuid']
            self.name = self.player_object['name']
        except ApiError as err:
            if err.response.status_code == 429:
                print(
                    f'We should retry in {err.headers["Retry-After"]} seconds.')
            elif err.response.status_code == 404:
                print('Summoner with that name not found.')
            else:
                raise

        # get the league object set (1 request)
        try:
            self.leagues = DAO.league.by_summoner(
                self.region, self.summoner_id)

            self.solo_rank = 'Unranked'
            self.solo_winrate = 'not enough games played'
            self.flex_rank = 'Unranked'
            self.flex_winrate = 'not enough games played'
            for league in self.leagues:
                if league['queueType'] == 'RANKED_SOLO_5x5':
                    self.solo_rank = f'{league["tier"].capitalize()}  {league["rank"]} '
                    self.solo_winrate = str(league['wins']) + 'W/' + str(league['losses']) + 'L: ' + str(
                        math.ceil(league['wins']/(league['wins']+league['losses'])*100)) + '% WR'
                if league['queueType'] == 'RANKED_FLEX_SR':
                    self.flex_rank = f'{league["tier"].capitalize()}  {league["rank"]} '
                    self.flex_winrate = str(league['wins']) + 'W/' + str(league['losses']) + 'L: ' + str(
                        math.ceil(league['wins']/(league['wins']+league['losses'])*100)) + '% WR'
        except ApiError as err:
            if err.response.status_code == 429:
                print(
                    f'We should retry in {err.headers["Retry-After"]} seconds.')
            elif err.response.status_code == 404:
                print(
                    f'Leagues with ID {self.summoner_id} and region {self.region} not found.')
            else:
                raise

        # try:
        #     self.current_match = DAO.spectator.by_summoner(
        #         self.region, self.summoner_id)
        # except ApiError as err:
        #     if err.response.status_code == 429:
        #         print(
        #             f'We should retry in {err.headers["Retry-After"]} seconds.')
        #     elif err.response.status_code == 404:
        #         print(
        #             f'Current match with ID {self.summoner_id} and region {self.region} not found.')
        #     else:
        #         raise

    def to_embed(self) -> discord.Embed():
        embed = discord.Embed(
            title=f'{self.name}', color=self.bot.color)
        embed.add_field(name='Solo/duo rank',
                        value=f'{self.solo_rank} - {self.solo_winrate}', inline=False)
        embed.add_field(
            name='Flex rank', value=f'{self.flex_rank} - {self.flex_winrate}', inline=False)
        embed.add_field(name='Level',
                        value=self.summoner_level, inline=False)
        embed.set_thumbnail(
            url=f'http://ddragon.leagueoflegends.com/cdn/12.11.1/img/profileicon/{self.profile_icon_id}.png')
        return embed

    # This blocks the bot for over 2 minutes

    def match_to_embed(self) -> discord.Embed():
        all_gamers = []
        embed = discord.Embed(
            title=f'{self.name}\'s live game', color=self.bot.color)
        if not self.current_match:
            embed.add_field(name='\u200b', value='Currently not in game.')
            return embed
        team1 = "__**Blue team**__:\n"
        team2 = "__**Red team**__:\n"
        ssteam1 = "\u200b\n"
        ssteam2 = "\u200b\n"
        rankteam1 = "\u200b\n"
        rankteam2 = "\u200b\n"
        for gamer in self.current_match["participants"]:
            gamer_info = [gamer["championId"], gamer["summonerName"],
                          gamer["spell1Id"], gamer["spell2Id"], gamer["teamId"]]
            all_gamers.append(gamer_info)
        for gamer in all_gamers:
            print('test')
            player = Player(gamer[1], self.region, self.DAO, self.bot)
            champ_name = player.get_champ_from_id(gamer[0])
            ss1_name = player.get_ss_from_id(gamer[2])
            ss2_name = player.get_ss_from_id(gamer[3])
            # champ_emote = player.get_emote_strings(champ_name)
            # ss1_emote = player.get_emote_strings(ss1_name)
            # ss2_emote = player.get_emote_strings(ss2_name)
            if gamer[4] == 100:
                team1 += "{}{:20}\n".format(champ_name, gamer[1])
                ssteam1 += "\t{}{}\n".format(ss1_name, ss2_name)
                rankteam1 += f"{player.solo_rank}\n"
            else:
                team2 += f"{champ_name} {gamer[1]}\n"
                ssteam2 += "\t{}{}\n".format(ss1_name, ss2_name)
                rankteam2 += f"{player.solo_rank}\n"
        print('after loop')
        teams = team1 + team2
        ssteams = ssteam1 + ssteam2
        rankteams = rankteam1 + rankteam2
        embed.add_field(name="Teams", value=teams)
        embed.add_field(name="Ranks", value=rankteams)
        embed.add_field(name="Summoners", value=ssteams)
        return embed

    def get_champ_from_id(self, id: int) -> str:
        for champ in self.DAO.data_dragon.champions(VERSION)['data']:
            if self.DAO.data_dragon.champions(VERSION)['data'][champ]['key'] == id:
                print(self.DAO.data_dragon.champions(
                    VERSION)['data'][champ]['name'])
                return self.DAO.data_dragon.champions(VERSION)['data'][champ]['name']

        return None

    def get_ss_from_id(self, id: int):
        for spell in self.DAO.data_dragon.champions(VERSION)['data']:
            if self.DAO.data_dragon.champions(VERSION)['data'][spell]['key'] == id:
                print(self.DAO.data_dragon.champions(
                    VERSION)['data'][spell]['name'])
                return self.DAO.data_dragon.champions(VERSION)['data'][spell]['name']
        return None
