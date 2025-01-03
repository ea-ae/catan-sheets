import sheets
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
# DIV1_CHANNELS = [1324153205575389207]
# DIV2_CHANNELS = [1324207273785954364]
# CK_CHANNELS = [1324500081189060729]
ERR_CHANNEL = 1324202972997091480


# class GameView(discord.ui.View):
#     @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
#     async def on_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
#         owner = message_id_to_replay_owner.get(interaction.message.id) # type: ignore
#         if owner is not None:

#             await interaction.response.send_message("The replay has been deleted.", ephemeral=True)
#             return

#         await interaction.response.send_message("The replay can only be deleted by the submitter.", ephemeral=True)


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
            "Please post a replay link by going to 'Return to Map' on the top right from the end game screen.\
            \nTo acquire the link, press the share button in the replay view.\
            \n\nPS: In case the lobby for this game was created manually by a non-premium user, the bot can't view it. In that case, just disregard this message.",
            reference=message,
            embed=embed,
        )
        return

    game_data = colonist(message, div)
    if game_data is None and div != Division.CK:
        game_data = twosheep(message, div)
    if game_data is None:
        # detect if message contains an image embed
        if len(message.attachments) > 0:
            if message.author.id in naughty_list:
                await message.channel.send("Include a replay link with your results (in a new message).")
            else:
                await message.channel.send("Please include a replay link with your results (in a new message).", reference=message)
                naughty_list.append(message.author.id)

        return  # doesn't contain any colonist/twosheep replay links

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
    bot.run(discord_token)


if __name__ == "__main__":
    main()
