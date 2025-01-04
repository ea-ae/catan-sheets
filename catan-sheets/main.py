import db
from shared import Division
from colonist import colonist
from twosheep import twosheep, get_twosheep_api_key

import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import traceback
import collections


load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


DIV1_CHANNELS = [827273190014320652, 1324153205575389207]
DIV2_CHANNELS = [827274292244512780, 1324207273785954364]
CK_CHANNELS = [879366959202983936, 1324500081189060729]
ERR_CHANNEL = 1324202972997091480


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message: discord.Message):
    try:
        await process_message(message)
    except Exception:
        err = traceback.format_exc()
        print(err)
        await bot.get_channel(ERR_CHANNEL).send(f"Error: {err}")  # type: ignore


naughty_list = collections.deque(maxlen=10)


async def process_message(message: discord.Message):
    if message.channel.id in DIV1_CHANNELS:
        div = Division.DIV1
    elif message.channel.id in DIV2_CHANNELS:
        div = Division.DIV2
    elif message.channel.id in CK_CHANNELS:
        div = Division.CK
    else:
        return

    if message.author.bot:
        return

    if message.content == "ping":
        await message.channel.send("pong", reference=message)  # type: ignore
        return

    if "gameId=" in message.content:
        embed = discord.Embed()
        embed.set_image(url="https://i.imgur.com/qLWL6N8.png")
        await message.channel.send(
            "Please post a properly formatted replay link by pressing 'Return to Map' on the top right of the end game screen. Then, press share button in the top-right to copy the replay link.\
            \nIf you're on mobile, the share button is only visible with vertical orientation.\
            \n\nPS: If you're having technical issues or the lobby for this game was created manually by a non-premium user, just disregard this warning; the standings team will handle your game manually.",
            reference=message,
            embed=embed,
            delete_after=180.0,
        )
        return

    game_data = colonist(message, div)
    if game_data is None and div != Division.CK:
        game_data = twosheep(message, div)
    if game_data is None:
        # detect if message contains an image embed
        if len(message.attachments) > 0:
            err_msg = "Please include a replay link with your game results (in a new message).\nIn case you already did so in a previous message, you can ignore this warning."
            if message.author.id in naughty_list:
                await message.channel.send(
                    f"{err_msg} >:(", reference=message, delete_after=180.0
                )
            else:
                await message.channel.send(
                    err_msg, reference=message, delete_after=180.0
                )
                naughty_list.append(message.author.id)

        return  # doesn't contain any colonist/twosheep replay links
    
    # todo: make this async if we wanna tryhard
    session = db.get_session()
    game_data.persist(session)
    session.commit()

    await message.add_reaction("🤖")

    await message.channel.send(
        game_data.message(author=message.author), reference=message
    )


def main():
    if get_twosheep_api_key() is None:
        raise Exception(
            "no token found, create a valid .env file with TWOSHEEP_API_KEY"
        )

    discord_token = os.getenv("DISCORD_TOKEN")
    if discord_token is None:
        raise Exception(
            "no token found, create a valid .env file with the DISCORD_TOKEN"
        )

    db.start()
    bot.run(discord_token)


if __name__ == "__main__":
    main()
