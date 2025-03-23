import discord
from discord import app_commands
from discord.ext import commands
from response import generate_gemini_chat_response, generate_gemini_chat_response_with_images, generate_gemini_chat_response_with_google_search_retrieval
from sender import send_long_message, send_long_reply
from chat import cleanup_old_sessions
import io

# Enable intents for message content
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
    sender_info = f"{message.author.name}"
    input_text = message.content.replace(bot.user.mention, '').strip()
    input_text = f"[From {sender_info}]: {input_text}"

    if message.reference:
        try:
            referenced_message = await message.channel.fetch_message(message.reference.message_id)
            print("Fetched referenced message successfully.")
            if referenced_message.author.id != bot.user.id:
                ref_sender = f"{referenced_message.author.name}"
                ref_context = f"[From {ref_sender}]: {referenced_message.content}"
                input_text = f"{ref_context}\n{input_text}"
                print("Using referenced message content as context.")
            else:
                print("Referenced message is from Jarvis; ignoring its content.")
        except Exception as e:
            print(f"Error fetching referenced message: {e}")

    attachments = message.attachments
    image_data_list = []
    for attachment in attachments:
        if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            try:
                image_bytes = await attachment.read()
                image_data_list.append(image_bytes)
                print(f"Read image attachment: {attachment.filename} ({len(image_bytes)} bytes).")
            except Exception as e:
                print(f"Error reading image attachment {attachment.filename}: {e}")
                
    mention_info = ""
    other_mentions = [m for m in message.mentions if m.id != bot.user.id]
    if other_mentions:
        mention_info = "Mentioned Users: " + ", ".join([f"{m.name}" for m in other_mentions])
        input_text += f"\n{mention_info}"

    if image_data_list:
        print("Generating chat response with image(s).")
        response = await generate_gemini_chat_response_with_images(
            message.channel.id, message.author.id, input_text, image_data_list
        )
    else:
        print("Generating chat response for text message.")
        response = await generate_gemini_chat_response(
            message.channel.id, message.author.id, input_text
        )

    await send_long_reply(reply_target, response)
    await bot.process_commands(message)

@bot.tree.command(name='search', description="Search using GoogleSearchRetrieval.")
async def search_command(interaction: discord.Interaction, query: str):
    """
    A Discord bot command that uses GoogleSearchRetrieval to fetch search results.
    Usage: /search <your query here>
    """
    print(f"Received search command from {interaction.user.name} with query: {query}")
    # Defer the response to prevent the interaction from expiring.
    await interaction.response.defer()
    
    try:
        response = await generate_gemini_chat_response_with_google_search_retrieval(
            channel_id=interaction.channel.id, 
            user_id=interaction.user.id, 
            user_message=query
        )
    except Exception as e:
        print(f"Error during search command execution: {e}")
        response = "Jarvis: I'm sorry, but I encountered an error processing your search request."
    
    # Check if the response exceeds Discord's 2000-character limit.
    if len(response) > 2000:
        file_obj = io.BytesIO(response.encode('utf-8'))
        file = discord.File(file_obj, filename="response.txt")
        await interaction.followup.send("Response too long; see attached file:", file=file)
    else:
        await interaction.followup.send(response)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    print("Jarvis support bot is online!")
    await bot.tree.sync()
    print("Slash commands synced")
    bot.loop.create_task(cleanup_old_sessions())  # Start cleanup task