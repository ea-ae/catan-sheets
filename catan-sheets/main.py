import sheets
from colonist import colonist
from twosheep import twosheep, get_twosheep_api_key

import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import re
import requests
import traceback
from datetime import datetime
import collections


load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


# DIV1_CHANNELS = [827273190014320652, 1324153205575389207]
# DIV2_CHANNELS = [827274292244512780, 1324207273785954364]
DIV1_CHANNELS = [1324153205575389207]
DIV2_CHANNELS = [1324207273785954364]
CK_CHANNELS = [879366959202983936]
ERR_CHANNEL = 1324202972997091480


handled_replay_messages: set[int] = set()
message_id_to_replay_owner: dict[int, str] = {}


# class GameView(discord.ui.View):
#     @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
#     async def on_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
#         owner = message_id_to_replay_owner.get(interaction.message.id) # type: ignore
#         if owner is not None:

#             await interaction.response.send_message("The replay has been deleted.", ephemeral=True)
#             return

#         await interaction.response.send_message("The replay can only be deleted by the submitter.", ephemeral=True)


@bot.event
async def on_message(message: discord.Message):
    try:
        await process_message(message)
    except Exception:
        err = traceback.format_exc()
        print(err)
        await bot.get_channel(ERR_CHANNEL).send(f"Error: {err}")  # type: ignore


# @bot.event
# async def on_message_edit(_: discord.Message, after: discord.Message):
#     try:
#         # if bot already reacted to message, then it's valid; ignore
#         if after.id in handled_replay_messages:
#             return

#         await process_message(after, is_edit=True)
#     except Exception:
#         err = traceback.format_exc()
#         await bot.get_channel(ERR_CHANNEL).send(f"Error: {err}")  # type: ignore


# trash can reaction "deletes" from our excel
# @bot.event
# async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
#     if user == bot.user:
#         return

#     if reaction.emoji == "🗑️" and reaction.message.author == bot.user:
#         reference_message_id = reaction.message.reference.message_id  # type: ignore
#         print(reaction.message.content)


message_id_circbuf = collections.deque(maxlen=100)  # to prevent duplicate events


async def process_message(message: discord.Message, is_edit=False):
    if message.channel.id in DIV1_CHANNELS:
        div = "1"
    elif message.channel.id in DIV2_CHANNELS:
        div = "2"
    else:
        return

    if message.author.bot:
        return

    if message.id in message_id_circbuf and not is_edit:
        # we somehow received a duplicate message event! skip it
        return
    message_id_circbuf.append(message.id)

    if message.content == "ping":
        await message.channel.send("pong", reference=message)  # type: ignore
        return

    if "gameId=" in message.content:
        embed = discord.Embed()
        embed.set_image(url="https://i.imgur.com/qLWL6N8.png")
        await message.channel.send(
            "Please post a replay link by going to 'Return to Map' on the top right from the end game screen.\
            \nTo acquire the link, press the share button in the replay view.\
            \n\nPS: In case the lobby for this game was created manually by a non-premium user, the bot can't view it. In that case, just disregard this message.",
            reference=message,
            embed=embed
        )
        return

    game_data = colonist(message, div)
    if game_data is None:
        game_data = twosheep(message, div)
    if game_data is None:
        return  # doesn't contain any colonist/twosheep replay links

    # if we already have this reaction, skip
    # for reaction in message.reactions:
    #     if reaction.emoji == "🤖":
    #         return
    await message.add_reaction("🤖")

    handled_replay_messages.add(message.id)
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
    bot.run(discord_token)


if __name__ == "__main__":
    main()
