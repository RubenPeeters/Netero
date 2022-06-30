import sys
import traceback
from typing import List
from cogs.utils.exceptions import RegionException
from .emotes import get_emote_strings
from pathlib import Path
import discord
import math
import os

import json

from datetime import datetime, timedelta

from pyot.models import lol
from pyot.utils.lol.routing import platform_to_region

VERSION = '12.11.1'

PLATFORMS = ["br1", "eun1", "euw1", "jp1", "kr",
             "la1", "la2", "na1", "oc1", "tr1", "ru"]
REGIONS = ["americas", "asia", "europe", "esports",
           "ap", "br", "eu", "kr", "latam", "na"]
PLATFORMS_TO_REGIONS = {"br1": "americas", "eun1": "europe", "euw1": "europe", "jp1": "asia", "kr": "asia",
                        "la1": "americas", "la2": "americas", "na1": "americas", "oc1": "americas", "tr1": "europe", "ru": "europe"}

INPUT_TO_PLATFORM = {
    'br': 'br1',
    'eune': 'eun1',
    'euw': 'euw1',
    'jp': 'jp1',
    'lan': 'la1',
    'las': 'la2',
    'na': 'na1',
    'oce': 'oc1',
    'tr': 'tr1',
    'ru': 'ru',
    'kr': 'kr'
}


class StaticData:
    def __init__(self) -> None:
        self.champions_json = None
        self.summoner_json = None
        self.loaded = False

    def load_static(self):
        path = Path(__file__).parent
        print(path)
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
        path = Path(__file__).parent
        FILES_PATH = os.path.join(path, 'static', "league", "queues.json")
        if os.path.exists(FILES_PATH):
            try:
                with open(FILES_PATH, encoding="utf-8") as f:
                    self.queues_json = json.load(f)
            except Exception as err:
                print(f'error {err}')
        else:
            print('no file')
        self.loaded = True


async def get_ranks(name: str, region: str):
    try:
        region = verify_region(region)
        summoner = await lol.Summoner(name=name, platform=region).get()
        leagues = await summoner.league_entries.get()
        solo_rank = 'Unranked'
        solo_winrate = 'not enough games played'
        flex_rank = 'Unranked'
        flex_winrate = 'not enough games played'
        solo_LP = None
        flex_LP = None
        flex_winrate_compact = None
        solo_winrate_compact = None
        for league in leagues:
            if league.queue == 'RANKED_SOLO_5x5':
                solo_rank = f'{league["tier"].capitalize()}  {league["rank"]} '
                solo_winrate = str(league['wins']) + 'W/' + str(league['losses']) + 'L: ' + str(
                    math.ceil(league['wins']/(league['wins']+league['losses'])*100)) + '% WR'
                solo_LP = league['leaguePoints']
                solo_winrate_compact = f"{str(math.ceil(league['wins']/(league['wins']+league['losses'])*100))}% {str(league['wins']+league['losses'])}G"
            if league.queue == 'RANKED_FLEX_SR':
                flex_rank = f'{league["tier"].capitalize()}  {league["rank"]} '
                flex_winrate = str(league['wins']) + 'W/' + str(league['losses']) + 'L: ' + str(
                    math.ceil(league['wins']/(league['wins']+league['losses'])*100)) + '% WR'
                flex_LP = league['leaguePoints']
                flex_winrate_compact = f"{str(math.ceil(league['wins']/(league['wins']+league['losses'])*100))}% {str(league['wins']+league['losses'])}G"
    except Exception as e:
        print(e)
        raise
    return solo_rank, solo_winrate, flex_rank, flex_winrate, solo_LP, flex_LP, flex_winrate_compact, solo_winrate_compact


async def to_embed(name: str, region: str, data: StaticData, ctx) -> discord.Embed():
    region = verify_region(region)
    summoner = await lol.Summoner(name=name, platform=region).get()
    solo_rank, solo_winrate, flex_rank, flex_winrate, _, _, _, _ = await get_ranks(
        name=name, region=region)
    try:
        game = await summoner.current_game.get()
    except Exception as err:
        game = None
        traceback.print_tb(err.__traceback__)
        print(f'{err.__class__.__name__}: {err}',
              file=sys.stderr)
    try:
        if game is not None:
            participants = game.participants
            for summ in participants:
                if summ.summoner_id == summoner.id:
                    break
                champ_id = get_champ_from_id(summ.champion_id, data)
                champ_name = get_champ_name_from_id(summ.champion_id, data)
                champ_emote = get_emote_strings(champ_id, ctx.bot)
                q_id = int(summoner.current_game.queue_id)
                queue = None
                for entry in data.queues_json:
                    if entry['queueId'] == q_id:
                        queue = entry['description']
                match_info = f'Currently playing {queue} as {champ_emote} {champ_name}.'
        else:
            match_info = 'Currently not in game.'
        embed = discord.Embed(
            title=f'{summoner.name}', color=ctx.bot.color)
        embed.add_field(name='Solo/duo rank',
                        value=f'{solo_rank} - {solo_winrate}', inline=False)
        embed.add_field(
            name='Flex rank', value=f'{flex_rank} - {flex_winrate}', inline=False)
        embed.add_field(name='Level',
                        value=summoner.level, inline=False)
        embed.add_field(name='LIVE', value=match_info)
        embed.set_thumbnail(
            url=f'http://ddragon.leagueoflegends.com/cdn/{VERSION}/img/profileicon/{summoner.profile_icon_id}.png')
        return embed
    except Exception as err:
        traceback.print_tb(err.__traceback__)
        print(f'{err.__class__.__name__}: {err}',
              file=sys.stderr)
        return None


async def match_to_embed(name: str, region: str, data: StaticData, ctx) -> discord.Embed():
    region = verify_region(region)
    summoner = await lol.Summoner(name=name, platform=region).get()
    try:
        game = await summoner.current_game.get()
    except Exception as err:
        traceback.print_tb(err.__traceback__)
        print(f'{err.__class__.__name__}: {err}',
              file=sys.stderr)
        game = None
    embed = discord.Embed(
        title=f'{summoner.name}s live game', color=ctx.bot.color)
    if not game:
        embed.add_field(name='\u200b', value='Currently not in game.')
        return embed
    team1 = "\n[Blue team]\n\n"
    team2 = "\n[Red team]\n\n"
    ssteam1 = "\n\u200b\n\n"
    ssteam2 = "\n\u200b\n\n"
    rankteam1 = "\n\u200b\n\n"
    rankteam2 = "\n\u200b\n\n"
    bansteam1 = "🟦: "
    bansteam2 = "🟥: "
    for participant in game.participants:
        solo_rank, _, _, _, solo_LP, _, _, _ = await get_ranks(
            name=participant.summoner_name, region=region)
        champ_id = get_champ_from_id(participant.champion_id, data=data)
        assert len(participant.spell_ids) == 2
        ss1_name = get_ss_from_id(participant.spell_ids[0], data=data)
        ss2_name = get_ss_from_id(participant.spell_ids[1], data=data)
        champ_emote = get_emote_strings(champ_id, ctx.bot)
        ss1_emote = get_emote_strings(ss1_name, ctx.bot)
        ss2_emote = get_emote_strings(ss2_name, ctx.bot)
        if participant.team_id == 100:
            if participant.summoner_name == summoner.name:
                team1 += f"{champ_emote} **{participant.summoner_name}**\n"
            else:
                team1 += f"{champ_emote} {participant.summoner_name}\n"
            ssteam1 += "\t{} {}\n".format(ss1_emote, ss2_emote)
            rankteam1 += f"{solo_rank} ({solo_LP} LP)\n"
        else:
            if participant.summoner_name == summoner.name:
                team2 += f"{champ_emote} **{participant.summoner_name}**\n"
            else:
                team2 += f"{champ_emote} {participant.summoner_name}\n"
            ssteam2 += "\t{} {}\n".format(ss1_emote, ss2_emote)
            rankteam2 += f"{solo_rank} ({solo_LP} LP)\n"
    for i, bans in enumerate(game.banned_champions):
        ban_champ_id = get_champ_from_id(bans.champion_id, data=data)
        ban_champ_emote = get_emote_strings(ban_champ_id, ctx.bot)
        if i <= 4:
            bansteam1 += f"{ban_champ_emote} "
        elif i > 4 and i < 10:
            bansteam2 += f"{ban_champ_emote} "

    teams = team1 + team2
    ssteams = ssteam1 + ssteam2
    rankteams = rankteam1 + rankteam2
    bansteams = f'{bansteam1}\t - \t{bansteam2}'
    embed.add_field(name="Teams", value=teams, inline=True)
    embed.add_field(name="Ranks", value=rankteams, inline=True)
    embed.add_field(name="Spells", value=ssteams, inline=True)
    embed.add_field(name="Bans", value=bansteams, inline=True)
    embed.set_author(
        name=f'{summoner.name}', icon_url=f'http://ddragon.leagueoflegends.com/cdn/{VERSION}/img/profileicon/{summoner.profile_icon_id}.png')
    return embed


def get_champ_from_id(id: int, data: StaticData) -> str:
    for champ in data.champions_json['data']:
        if int(data.champions_json['data'][champ]['key']) == id:
            return data.champions_json['data'][champ]['id']

    return None


def get_champ_name_from_id(id: int, data: StaticData) -> str:
    for champ in data.champions_json['data']:
        if int(data.champions_json['data'][champ]['key']) == id:
            return data.champions_json['data'][champ]['name']

    return None


def get_ss_from_id(id: int, data: StaticData):
    for spell in data.summoner_json['data']:
        if int(data.summoner_json['data'][spell]['key']) == id:
            return data.summoner_json['data'][spell]['name']
    return None


async def get_match_ids(name: str, platform: str):
    try:
        summoner = await lol.Summoner(name=name, platform=platform).get()
        match_history = await lol.MatchHistory(
            puuid=summoner.puuid,
            region=platform_to_region(summoner.platform)
        ).query(
            count=100,
            queue=420,
            start_time=datetime.now() - timedelta(days=200)
        ).get()
    except Exception as e:
        print(str(e))
    return match_history.ids


def verify_region(region: str):
    if region not in INPUT_TO_PLATFORM.keys() and region not in PLATFORMS:
        raise RegionException(region, list(
            INPUT_TO_PLATFORM.keys()))
    if region in INPUT_TO_PLATFORM.keys():
        return INPUT_TO_PLATFORM[region]
    else:
        return region


async def history_to_embed(ctx, name: str, matches: List[int], data: StaticData, count: int = 10) -> discord.Embed():
    payload = ""
    wins = 0
    assert count < len(matches)
    for id in matches[0:count]:
        match = await lol.Match(id=id).get()
        for participant in match.info.participants:
            if participant.summoner_name == name:
                queue = None
                for entry in data.queues_json:
                    if entry['queueId'] == match.info.queue_id:
                        queue = entry['description']
                if participant.win:
                    wins += 1
                queue = queue.replace('5v5', '')
                queue = queue.replace('games', '')
                queue = queue.strip()
                if participant.deaths != 0:
                    payload += f"{'🔵' if participant.win else '🔴'} : {get_emote_strings(participant.champion_name, ctx.bot)} **{participant.kills}/{participant.deaths}/{participant.assists}** {queue} **{float(participant.kills + participant.assists)/participant.deaths:.2f}** KDA \n"
                else:
                    payload += f"{'🔵' if participant.win else '🔴'} : {get_emote_strings(participant.champion_name, ctx.bot)} **{participant.kills}/{participant.deaths}/{participant.assists}** {queue} **Perfect** KDA \n"
                break

    embed = discord.Embed(
        title=f'Match history', color=ctx.bot.color)
    embed.set_author(
        name=f'{name}', icon_url=f'http://ddragon.leagueoflegends.com/cdn/{VERSION}/img/profileicon/{participant.profile_icon_id}.png')
    embed.add_field(name='\u200b', value=f"{payload}")
    embed.set_footer(
        text=f'{(float(wins)/count)*100 if count != 0 else 100.0:.2f}% WR in last {count} games.')
    return embed
