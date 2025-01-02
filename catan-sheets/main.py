import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import re
import requests
import traceback
import sheets
from datetime import datetime

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


DIV1_CHANNEL = 1324153205575389207
DIV2_CHANNEL = 1324207273785954364
ERR_CHANNEL = 1324202972997091480
COLONIST_REGEX = r".*colonist.io\/replay\/([^? /\\]*)"


@bot.event
async def on_message(message: discord.Message):
    try:
        await process_message(message)
    except Exception:
        err = traceback.format_exc()
        print("error", err)
        await bot.get_channel(ERR_CHANNEL).send(f"Error: {err}")  # type: ignore


async def process_message(message: discord.Message):
    if message.channel.id not in [DIV1_CHANNEL, DIV2_CHANNEL]:
        return
    div = {DIV1_CHANNEL: 1, DIV2_CHANNEL: 2}[message.channel.id]

    if message.author == bot.user:
        return

    match = re.match(COLONIST_REGEX, message.content)
    if match is None:
        return

    game_id = match.group(1)
    api_url = f"https://colonist.io/api/replay/data-from-slug?replayUrlSlug={game_id}"

    res = requests.get(api_url)
    if not res.status_code == 200:
        raise Exception(f"colonist.io api call failed with {res.status_code}")
    
    data = res.json()["data"]
    played_at = datetime.fromisoformat(data["eventHistory"]["startTime"].replace("Z", "+00:00"))
    played_at_epoch = int(played_at.timestamp())

    colors_to_names: dict[int, str] = {
        player["selectedColor"]: player["username"]
        for player in data["playerUserStates"]
    }

    msg = []
    sheet_data = []
    msg.append(f"**Division {div} colonist.io game** posted by {message.author.mention} (played <t:{played_at_epoch}>)")
    game_players = data["eventHistory"]["endGameState"]["players"]

    members = message.guild.members  # type: ignore

    for player in game_players.values():
        name = colors_to_names[player["color"]]

        discord_name = sheets.translate_name(name)

        discord_user = None
        if discord_name is not None:
            discord_user = discord.utils.get(members, name=discord_name)  # type: ignore
            if discord_user is None:
                discord_user = discord.utils.get(members, global_name=discord_name)  # type: ignore
            if discord_user is None:
                discord_user = discord.utils.get(members, nick=discord_name)  # type: ignore
        
        vp_data = player["victoryPoints"]
        settles = vp_data.get("0", 0)
        cities = vp_data.get("1", 0)
        vp_devs = vp_data.get("2", 0)
        largest_army = vp_data.get("3", 0)
        longest_road = vp_data.get("4", 0)

        vp = sum((settles, cities * 2, vp_devs, largest_army * 2, longest_road * 2))

        # coalesce all 3
        fallback_name = discord_name if discord_name is not None else name
        msg.append(
            f"{name} ({discord_user.mention if discord_user else '@' + fallback_name}): {vp} VPs"
        )
        sheet_data.append([discord_name if discord_name else fallback_name + ' (FALLBACK)', vp])

    if len(sheet_data) == 4:
        sheets.update(div, sheet_data)

    await message.channel.send("\n".join(msg))


def main():
    token = os.getenv("DISCORD_TOKEN")
    if token is None:
        raise Exception(
            "no token found, create a valid .env file with the DISCORD_TOKEN"
        )
    bot.run(token)


if __name__ == "__main__":
    main()
