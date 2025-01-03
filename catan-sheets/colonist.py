from shared import Division, GameData, GameMetadata, PlayerScore, get_discord_user
import sheets

from datetime import datetime
import re
import discord
import requests


COLONIST_REPLAY_REGEX = r"colonist\.io\/replay\/([^? &\/\\()[\]\n]+)"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
}


def colonist(message: discord.Message, div: Division) -> GameData | None:
    slug_matches = re.findall(COLONIST_REPLAY_REGEX, message.content, re.DOTALL)
    if len(slug_matches) == 0:
        return None
    data = query_colonist(slug_matches[0])

    played_at = datetime.fromisoformat(
        data["eventHistory"]["startTime"].replace("Z", "+00:00")
    )

    colors_to_names: dict[int, str] = {
        player["selectedColor"]: player["username"]
        for player in data["playerUserStates"]
    }

    game_players = data["eventHistory"]["endGameState"]["players"]

    members = message.guild.members  # type: ignore
    gapi_creds = sheets.get_creds()

    game_data = GameData(metadata=None, scores=[])

    for player in game_players.values():
        name = colors_to_names[player["color"]]

        discord_name = sheets.translate_name(gapi_creds, div, name)
        discord_user = get_discord_user(members, discord_name) if discord_name else None

        vp_data = player["victoryPoints"]
        settles = vp_data.get("0", 0)
        cities = vp_data.get("1", 0)
        vp_devs = vp_data.get("2", 0)
        largest_army = vp_data.get("3", 0)
        longest_road = vp_data.get("4", 0)
        ck_metropolis = vp_data.get("6", 0)
        ck_catan_points = vp_data.get("7", 0)
        ck_vps = vp_data.get("8", 0)
        ck_merchant = vp_data.get("9", 0)

        score = sum(
            (
                settles,
                cities * 2,
                vp_devs,
                largest_army * 2,
                longest_road * 2,
                ck_metropolis * 2,
                ck_catan_points,
                ck_vps,
                ck_merchant,
            )
        )

        game_data.scores.append(
            PlayerScore.from_names(discord_user, discord_name, name, score)
        )

    game_data.metadata = GameMetadata(
        division=div,
        replay_link=f"https://colonist.io/replay/{slug_matches[0]}",
        timestamp=played_at,
        is_duplicate=False,
    )

    sheets.update(gapi_creds, div, game_data)

    return game_data


def query_colonist(game: str):
    api_url = f"https://colonist.io/api/replay/data-from-slug?replayUrlSlug={game}"
    res = requests.get(api_url, headers=HEADERS)
    if res.status_code != 200:
        raise Exception(
            f"colonist.io api call to {api_url} failed with {res.status_code}, {res.json()}"
        )

    return res.json()["data"]
