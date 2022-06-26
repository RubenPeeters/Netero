import os
import requests

VERSION = '12.11.1'

dir_path = os.path.dirname(os.path.realpath(__file__))
FOLDER = "static"
FILES_PATH = os.path.join(dir_path, FOLDER, "league")
print(FILES_PATH)


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
    for url in urls:
        fetch_file(url)


if __name__ == '__main__':
    download_files_from_url([
        f'http://ddragon.leagueoflegends.com/cdn/{VERSION}/data/en_US/champion.json',
        f'http://ddragon.leagueoflegends.com/cdn/{VERSION}/data/en_US/summoner.json',
        f'http://ddragon.leagueoflegends.com/cdn/{VERSION}/data/en_US/profileicon.json',
        f'http://ddragon.leagueoflegends.com/cdn/{VERSION}/data/en_US/item.json',
    ]
    )
