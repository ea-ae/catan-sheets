from datetime import datetime
from dotenv import load_dotenv
from shared import Division, GameData, GameMetadata, PlayerScore, get_discord_user
import sheets

from functools import cache
import re
import discord
import requests
import os
import pytz


TWOSHEEP_REPLAY_REGEX = r"twosheep\.io\/replay\/([^? &\/\\()[\]\n]+)"

HEADERS = {"Content-Type": "application/json"}


def twosheep(message: discord.Message, div: Division):
    if div == "CK":
        return None

    slug_matches = re.findall(TWOSHEEP_REPLAY_REGEX, message.content, re.DOTALL)
    if len(slug_matches) == 0:
        return None
    data = query_twosheep(slug_matches[0])

    members = message.guild.members  # type: ignore
    gapi_creds = sheets.get_creds()

    played_at_epoch = data["c"]
    played_at = datetime.fromtimestamp(played_at_epoch, tz=pytz.UTC)

    game_data = GameData(metadata=None, scores=[])

    for player in data["p"].values():
        name = player["n"]
        score = player["v"]

        discord_name = sheets.translate_name(gapi_creds, div, name)
        discord_user = get_discord_user(members, discord_name) if discord_name else None

        game_data.scores.append(PlayerScore.from_names(discord_user, discord_name, name, score))

    game_data.metadata = GameMetadata(
        division=div,
        replay_link=f"https://twosheep.io/replay/{slug_matches[0]}",
        timestamp=played_at,
        is_duplicate=False,
    )

    sheets.update(gapi_creds, div, game_data)

    return game_data


def query_twosheep(game_slug: str):
    api_key = get_twosheep_api_key()
    api_url = f"https://twosheep.io/api/getReplay?id={game_slug}&apiKey={api_key}"
    res = requests.get(api_url, headers=HEADERS)
    if res.status_code != 200:
        raise Exception(f"twosheep.io api call failed with {res.status_code}")

    return res.json()


def get_twosheep_api_key():
    twosheep_api_key = os.getenv("TWOSHEEP_API_KEY")
    if twosheep_api_key is None:
        raise Exception(
            "no api key found, create a valid .env file with the TWOSHEEP_API_KEY"
        )
    return twosheep_api_key
