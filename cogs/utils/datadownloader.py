import json
import os
from pathlib import Path
import requests

VERSION = '12.13.1'

dir_path = os.path.dirname(os.path.realpath(__file__))
FOLDER = "static"
FILES_PATH = os.path.join(dir_path, FOLDER, "league")
# print(FILES_PATH)

# redefine because of some import problems


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


def download_files_from_url(urls):

    os.makedirs(FILES_PATH, exist_ok=True)

    def fetch_file(url):
        fname = url.split("/")[-1]
        response = requests.get(url)

        with open(
            os.path.join(FILES_PATH, fname), "wb"
        ) as outfile:
            print(outfile)
            outfile.write(response.content)
            print(response)
    for url in urls:
        fetch_file(url)


def get_champs():
    data = StaticData()
    data.load_static()
    for champ in data.champions_json['data']:
        png = str(
            data.champions_json["data"][champ]["image"]["full"])
        champ = png.split('.')[0]
        download_files_from_url([
            f'http://ddragon.leagueoflegends.com/cdn/{VERSION}/data/en_US/champion/{champ}.json',
            f'http://ddragon.leagueoflegends.com/cdn/{VERSION}/img/champion/{png}'
        ])


if __name__ == '__main__':
    download_files_from_url([
        f'http://ddragon.leagueoflegends.com/cdn/{VERSION}/data/en_US/champion.json',
        f'http://ddragon.leagueoflegends.com/cdn/{VERSION}/data/en_US/summoner.json',
        f'http://ddragon.leagueoflegends.com/cdn/{VERSION}/data/en_US/profileicon.json',
        f'http://ddragon.leagueoflegends.com/cdn/{VERSION}/data/en_US/item.json',
        'https://static.developer.riotgames.com/docs/lol/queues.json'
    ]
    )
    get_champs()
