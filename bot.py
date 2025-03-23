import discord
from discord.ext import commands
from response import generate_gemini_chat_response, generate_gemini_chat_response_with_images
from sender import send_long_message, send_long_reply
from chat import cleanup_old_sessions

# Enable intents for message content
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user not in message.mentions:
        return

    reply_target = message
    input_text = message.content.replace(bot.user.mention, '').strip()

    if message.reference:
        try:
            referenced_message = await message.channel.fetch_message(message.reference.message_id)
            print("Fetched referenced message successfully.")
            if referenced_message.author.id != bot.user.id:
                input_text = f"{referenced_message.content}\n{input_text}"
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

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    print("Jarvis support bot is online!")
    bot.loop.create_task(cleanup_old_sessions())  # Start cleanup task