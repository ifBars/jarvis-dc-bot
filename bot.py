import discord
from discord import app_commands
from discord.ext import commands
from response import (
    generate_gemini_chat_response,
    generate_gemini_chat_response_with_images,
    generate_gemini_chat_response_with_google_search_retrieval,
)
from sender import send_long_message, send_long_reply
from chat import cleanup_old_sessions
import io
import os
import json
from datetime import datetime, timedelta
import asyncio

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    if bot.user not in message.mentions:
        return

    reply_target = message
    sender_info = f"{message.author.display_name}"
    input_text = message.content.replace(bot.user.mention, "").strip()
    input_text = f"[From {sender_info}]: {input_text}"

    image_data_list = []

    for attachment in message.attachments:
        if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            try:
                image_bytes = await attachment.read()
                image_data_list.append(image_bytes)
                print(
                    f"Read image attachment: {attachment.filename} ({len(image_bytes)} bytes)."
                )
            except Exception as e:
                print(f"Error reading image attachment {attachment.filename}: {e}")

    if message.reference:
        try:
            referenced_message = await message.channel.fetch_message(
                message.reference.message_id
            )
            print("Fetched referenced message successfully.")
            ref_sender = f"{referenced_message.author.display_name}"
            ref_context = f"[From {ref_sender}]: {referenced_message.content}"
            input_text = f"{ref_context}\n{input_text}"
            print("Using referenced message content as context.")

            for ref_attachment in referenced_message.attachments:
                if ref_attachment.filename.lower().endswith(
                    ('.png', '.jpg', '.jpeg', '.gif')
                ):
                    try:
                        ref_image_bytes = await ref_attachment.read()
                        image_data_list.append(ref_image_bytes)
                        print(
                            f"Read image attachment from referenced message: {ref_attachment.filename} ({len(ref_image_bytes)} bytes)."
                        )
                    except Exception as e:
                        print(
                            f"Error reading image attachment from referenced message {ref_attachment.filename}: {e}"
                        )
        except Exception as e:
            print(f"Error fetching referenced message: {e}")

    mention_info = ""
    other_mentions = [m for m in message.mentions if m.id != bot.user.id]
    if other_mentions:
        mention_info = "Mentioned Users: " + ", ".join(
            [f"{m.name}" for m in other_mentions]
        )
        input_text += f"\n{mention_info}"

    try:
        if image_data_list:
            print(f"Generating chat response with {len(image_data_list)} image(s).")
            response = await generate_gemini_chat_response_with_images(
                message.channel.id,
                message.author.id,
                input_text,
                image_data_list,
            )
        else:
            print("Generating chat response for text message.")
            response = await generate_gemini_chat_response(
                message.channel.id, message.author.id, input_text
            )
    except Exception as e:
        print(f"Error generating response: {e}")
        response = (
            "I encountered an error processing your message with images. Please try again or "
            "send your message without images."
        )

    await send_long_reply(reply_target, response)

@bot.tree.command(name="search", description="Search using GoogleSearchRetrieval.")
async def search_command(interaction: discord.Interaction, query: str):
    """
    Uses GoogleSearchRetrieval to fetch search results.
    Usage: /search <your query here>
    """
    print(
        f"Received search command from {interaction.user.name} with query: {query}"
    )
    await interaction.response.defer()

    try:
        response = await generate_gemini_chat_response_with_google_search_retrieval(
            channel_id=interaction.channel.id,
            user_id=interaction.user.id,
            user_message=query,
        )
    except Exception as e:
        print(f"Error during search command execution: {e}")
        response = "I'm sorry, but I encountered an error processing your search request."

    if len(response) > 2000:
        file_obj = io.BytesIO(response.encode("utf-8"))
        file = discord.File(file_obj, filename="response.txt")
        await interaction.followup.send(
            "Response too long; see attached file:", file=file
        )
    else:
        await interaction.followup.send(response)

@bot.tree.command(name="help", description="Display a list of commands that Jarvis can run")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Jarvis Commands",
        description=(
            "Text commands can be ran by sending a message similar to the command name. "
            "You can also just ask Jarvis anything and he will reply."
        ),
        color=discord.Color.blue(),
    )

    slash_commands = (
        "**/help** - Display this list of commands.\n"
        "**/search** - Search google and get a summarized result."
    )
    embed.add_field(name="Slash Commands", value=slash_commands, inline=False)

    text_commands = (
        "`scream` - Make Jarvis scream.\n"
        "`jarvis meme` - Sends a meme regarding Jarvis.\n"
        "`send a [term] gif` - Search and send a gif using the provided search term."
    )
    embed.add_field(name="Text Commands", value=text_commands, inline=False)

    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    print("Jarvis support bot is online!")

    await bot.tree.sync()
    print("Global slash commands synced")

    GUILD_ID = 1342208748147576924
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print("Guild slash commands synced")

    bot.loop.create_task(cleanup_old_sessions())

async def daily_code():
    channel_id = 1353101129495482559  
    compliment_target_id = 709073508772216885  

    target_mention = f"<@{compliment_target_id}>"
    prompt = (
        f"Generate a warm, friendly, and unique daily compliment for "
        f"{target_mention}. The compliment should be heartfelt and make "
        f"them feel appreciated. Tell them this is their daily compliment and you will send another tomorrow. "
        f"Generate nothing but the compliment and tag them in it. "
    )

    print(f"Requesting daily compliment from Gemini for {target_mention}")

    try:
        compliment_text = await generate_gemini_chat_response(
            channel_id, compliment_target_id, prompt
        )
    except Exception as e:
        print("Error generating compliment:", e)
        compliment_text = "You are truly amazing and appreciated!"

    compliment_message = f"{compliment_text}"

    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(compliment_message)
        print("Daily compliment sent.")
    else:
        print(f"Channel with ID {channel_id} not found!")

async def schedule_daily_code():
    """
    This scheduler checks for a last run timestamp in last_run.json.
    If no record exists, it runs daily_code() immediately (so you can see it happen)
    and then schedules subsequent runs every 24 hours.
    """
    last_run_file = "last_run.json"

    try:
        if os.path.exists(last_run_file):
            with open(last_run_file, "r") as f:
                data = json.load(f)
            last_run_str = data.get("last_run")
            last_run = datetime.fromisoformat(last_run_str) if last_run_str else None
        else:
            last_run = None
    except Exception as e:
        print(f"Error reading {last_run_file}: {e}")
        last_run = None

    if last_run is None:
        print("No last run found. Running daily code immediately.")
        await daily_code()
        last_run = datetime.utcnow()
        try:
            with open(last_run_file, "w") as f:
                json.dump({"last_run": last_run.isoformat()}, f)
        except Exception as e:
            print(f"Error writing {last_run_file}: {e}")

    while True:
        now = datetime.utcnow()
        next_run = last_run + timedelta(days=1)
        time_to_wait = (next_run - now).total_seconds()

        if time_to_wait < 0:
            time_to_wait = 0

        print(f"Daily task scheduled to run in {time_to_wait} seconds.")
        await asyncio.sleep(time_to_wait)
        await daily_code()

        last_run = datetime.utcnow()
        try:
            with open(last_run_file, "w") as f:
                json.dump({"last_run": last_run.isoformat()}, f)
        except Exception as e:
            print(f"Error writing {last_run_file}: {e}")