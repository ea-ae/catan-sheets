import sheets

import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import re
import requests
import traceback
from datetime import datetime, timedelta
import pytz
import collections


load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
}

DIV1_CHANNELS = [827273190014320652, 1324153205575389207]
DIV2_CHANNELS = [827274292244512780, 1324207273785954364]
CK_CHANNELS = [879366959202983936]
ERR_CHANNEL = 1324202972997091480
COLONIST_REPLAY_REGEX = r"colonist\.io\/replay\/([^? &\/\\()[\]\n]+)"


@bot.event
async def on_message(message: discord.Message):
    try:
        await process_message(message)
    except Exception:
        err = traceback.format_exc()
        print(err)
        await bot.get_channel(ERR_CHANNEL).send(f"Error: {err}")  # type: ignore


@bot.event
async def on_message_edit(_: discord.Message, after: discord.Message):
    try:
        # if bot already reacted to message, then it's valid; ignore
        for reaction in after.reactions:
            async for user in reaction.users():
                if bot.user is None or user == bot.user.id:
                    return

        await process_message(after)
    except Exception:
        err = traceback.format_exc()
        print(err)
        await bot.get_channel(ERR_CHANNEL).send(f"Error: {err}")  # type: ignore


@bot.event
async def on_message_delete(message: discord.Message):
    async for msg in message.channel.history(limit=15):
        if msg.reference is not None and msg.reference.message_id == message.id:
            await msg.add_reaction("🗑️")
            break


# trash can reaction deletes from our excel
@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    if user == bot.user:
        return

    if reaction.emoji == "🗑️":
        message = reaction.message
        print(message.content)

        # gapi_creds = sheets.get_creds()
        # members = message.guild.members


message_id_circbuf = collections.deque(maxlen=100)


async def process_message(message: discord.Message):
    if message.channel.id in DIV1_CHANNELS:
        div = "1"
    elif message.channel.id in DIV2_CHANNELS:
        div = "2"
    else:
        return

    if message.author == bot.user:
        return
    
    if message.id in message_id_circbuf:
        # we somehow received a duplicate message event! skip it
        return
    message_id_circbuf.append(message.id)

    if message.content == "ping":
        await message.channel.send("pong", reference=message)  # type: ignore
        return

    if "gameId=" in message.content:
        await message.channel.send(
            "Please post a replay link in the /replay/abcdefg format instead of /replay?gameId=12345.\
            \nTo do this, press the share button in the replay view (located in the top-right, above the 'Open Stats' button on PC).\
            \n**PS:** In case the lobby for this game was created manually by a non-premium user, the bot can't view it. In that case, \
just disregard this message.",
            reference=message,
        )
        return

    slug_matches = re.findall(COLONIST_REPLAY_REGEX, message.content, re.DOTALL)
    if len(slug_matches) == 0:
        return
    data = query_colonist(slug_matches[0])

    played_at = datetime.fromisoformat(
        data["eventHistory"]["startTime"].replace("Z", "+00:00")
    )
    played_at_epoch = int(played_at.timestamp())

    colors_to_names: dict[int, str] = {
        player["selectedColor"]: player["username"]
        for player in data["playerUserStates"]
    }

    msg = []
    sheet_data = []
    msg.append(
        f"**Division {div} colonist.io game** posted by {message.author.mention} (played <t:{played_at_epoch}>)"
    )
    game_players = data["eventHistory"]["endGameState"]["players"]

    members = message.guild.members  # type: ignore
    gapi_creds = sheets.get_creds()

    if played_at < datetime.now(tz=pytz.UTC) - timedelta(hours=4):
        msg.append('*⚠️ Warning: this game was played more than 4 hours ago.*')

    msg.append("")

    for player in game_players.values():
        name = colors_to_names[player["color"]]

        discord_name = sheets.translate_name(gapi_creds, name)

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
        sheet_data.append(
            ["", discord_name if discord_name else fallback_name + " (FALLBACK)", vp]
        )
    
    # add metadata
    sheet_data[0][0] = f"https://colonist.io/replay/{slug_matches[0]}"
    sheet_data[1][0] = played_at.isoformat()

    sheets.update(gapi_creds, div, sheet_data)

    await message.add_reaction("🤖")
    await message.channel.send("\n".join(msg), reference=message)


def query_colonist(game: str):
    api_url = f"https://colonist.io/api/replay/data-from-slug?replayUrlSlug={game}"
    res = requests.get(api_url, headers=HEADERS)
    if res.status_code != 200:
        raise Exception(
            f"colonist.io api call to {api_url} failed with {res.status_code}, {res.json()}"
        )

    return res.json()["data"]


def main():
    token = os.getenv("DISCORD_TOKEN")
    if token is None:
        raise Exception(
            "no token found, create a valid .env file with the DISCORD_TOKEN"
        )
    bot.run(token)


if __name__ == "__main__":
    main()
