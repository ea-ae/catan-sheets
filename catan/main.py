from typing import Literal
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import re
import requests
import sheets

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


DIV1_CHANNEL = 1324153205575389207
DIV2_CHANNEL = 42
COLONIST_REGEX = r".*colonist.io\/replay\/([^? /\\]*)"


@bot.event
async def on_message(message: discord.Message):
    if message.channel.id not in [DIV1_CHANNEL, DIV2_CHANNEL]:
        return
    div = {DIV1_CHANNEL: 1, DIV2_CHANNEL: 2}[message.channel.id]

    if message.author == bot.user:
        return

    print(f"Message from {message.author}: {message.content}")

    match = re.match(COLONIST_REGEX, message.content)
    if match is None:
        return

    game_id = match.group(1)
    api_url = f"https://colonist.io/api/replay/data-from-slug?replayUrlSlug={game_id}"

    res = requests.get(api_url)
    if not res.status_code == 200:
        print("api call failed with", res.status_code)

    data = res.json()["data"]

    colors_to_names: dict[int, str] = {
        player["selectedColor"]: player["username"]
        for player in data["playerUserStates"]
    }

    msg = []
    msg.append(f"**Division {div}**")
    game_players = data["eventHistory"]["endGameState"]["players"]
    for player in game_players.values():
        name = colors_to_names[player["color"]]
        vp = sum(player["victoryPoints"].values())
        msg.append(f"{name}: {vp} VPs")

    await message.channel.send("\n".join(msg))


def append_to_sheets(div: Literal[1] | Literal[2]):
    pass


def main():
    token = os.getenv("DISCORD_TOKEN")
    if token is None:
        raise Exception("no token found, create a valid .env file with the DISCORD_TOKEN")
    bot.run(token)


if __name__ == "__main__":
    # main()
    sheets.auth()   
