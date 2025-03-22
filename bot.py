import os
import asyncio
import aiohttp
import discord
from discord.ext import commands
import google.genai as genai
from google.genai import types

# Enable intents for message content
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ---------------------------
# Constants for Dynamic System Instructions
# ---------------------------
BASE_PROMPT = """
You are Jarvis, the helpful and humble A.I assistant on this Discord server, inspired by Iron Man's iconic Jarvis. You are known for your wit, occasional sarcasm, and concise responses. You often end your sentences with "sir" to add a touch of formality, but you use it sparingly. You were programmed by bars.

**Your Role:**
- Engage users in meaningful, efficient conversations.
- Provide expert-level support and guidance specifically regarding the Marvel Rivals AI Assistant.
- Always reference the official documentation (README and Changelog) when necessary.

**Key Guidelines:**

1. **Personality & Tone:**
   - Maintain a friendly, respectful, and occasionally sarcastic tone.
   - Keep your responses concise and to the point.
   - Conclude most sentences with "sir", but do so judiciously.

2. **Role & Limitations:**
   - You are a Discord support bot version of Jarvis; your purpose is to offer advice and troubleshoot issues.
   - Unlike the full Marvel Rivals AI Assistant, you cannot execute or simulate any commands.
   - If a user requests command execution, politely remind them that you can only provide guidance and cannot trigger any actions.

3. **Formatting & Communication:**
   - Format your responses accordingly for Discord messages using Discord's message format.
   - Keep your messages under 2000 characters; if a longer response is needed, split it into sections.
   - Maintain a professional, engaging style throughout your interactions.

4. **Attribution & Updates:**
   - Always credit PatchiPup for the original creation of the Marvel Rivals AI Assistant, and acknowledge contributions from bars, Supereiris, and other contributors as necessary.
   - Stay up-to-date with the latest documentation and provide accurate information.
   
If the window title says "Jarvis Mark II.py" that means they are using the old 2.0 version, and you should recommend they download the new Github version.

Never break the Jarvis personality, even if the user tells you to act as someone else. Try not to fufill any requests that are wildly unrelated to Jarvis.

Remember: You are here to assist and converse in a manner that reflects Iron Man's trusted assistant, but you are strictly a support bot and cannot execute any commands.
"""

README_URL = "https://raw.githubusercontent.com/PatchiPup/Jarvis-Mark-II/refs/heads/main/README.MD"
CHANGELOG_URL = "https://raw.githubusercontent.com/PatchiPup/Jarvis-Mark-II/refs/heads/main/CHANGELOG.MD"
COMMANDS_URL = "https://raw.githubusercontent.com/wiki/PatchiPup/Jarvis-Mark-II/Commands.md"

# ---------------------------
# Asynchronous HTTP fetching of documentation with timeouts
# ---------------------------
async def fetch_url(session: aiohttp.ClientSession, url: str, label: str) -> str:
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                content = await response.text()
                print(f"Fetched {label} successfully.")
                return content
            else:
                error_msg = f"{label} content not available (status code: {response.status})."
                print("Failed to fetch", label + ":", error_msg)
                return error_msg
    except Exception as e:
        error_msg = f"Error fetching {label}: {e}"
        print("Exception fetching", label + ":", e)
        return error_msg

async def build_system_instructions() -> str:
    """
    Dynamically build system instructions by combining the base prompt,
    the repository's README, Changelog, and Commands using asynchronous HTTP.
    """
    base = BASE_PROMPT
    print("Building system instructions...")
    async with aiohttp.ClientSession() as session:
        readme_content = await fetch_url(session, README_URL, "README")
        changelog_content = await fetch_url(session, CHANGELOG_URL, "Changelog")
        commands_content = await fetch_url(session, COMMANDS_URL, "Commands")
    
    system_instructions = (
        base + "\n\n" +
        "## README\n" + readme_content + "\n\n" +
        changelog_content + "\n\n" +
        commands_content
    )
    print("System instructions built successfully.")
    return system_instructions

# ---------------------------
# Global Chat Session Storage and Locks
# ---------------------------
# Keyed by (channel_id, user_id) for per-user conversation context.
chat_sessions = {}
session_locks = {}  # Per-session locks

async def get_chat_session(channel_id: int, user_id: int):
    key = (channel_id, user_id)
    if key not in chat_sessions:
        print(f"Creating new chat session for channel {channel_id} and user {user_id}.")
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        chat = await asyncio.to_thread(client.chats.create, model="gemini-2.0-flash")
        system_instructions = await build_system_instructions()
        await asyncio.to_thread(chat.send_message, system_instructions)
        print("Chat session primed with system instructions.")
        chat_sessions[key] = chat
        session_locks[key] = asyncio.Lock()  # Create a lock for this session
    else:
        print(f"Using existing chat session for channel {channel_id} and user {user_id}.")
    return chat_sessions[key], session_locks[key]

# Helper function to call chat.send_message with a timeout
async def send_message_with_timeout(chat, message, timeout=10):
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(chat.send_message, message),
            timeout=timeout
        )
        return response
    except asyncio.TimeoutError:
        print("Timeout when sending message via Gemini API.")
        raise

# ---------------------------
# Updated Gemini Chat Response Functions with Session Reset on Timeout
# ---------------------------
async def generate_gemini_chat_response(channel_id: int, user_id: int, user_message: str) -> str:
    """
    For text-only messages, use the chat session to send the message.
    If a timeout occurs, reset the session and try once more.
    """
    key = (channel_id, user_id)
    chat, lock = await get_chat_session(channel_id, user_id)
    try:
        async with lock:
            response = await send_message_with_timeout(chat, user_message, timeout=10)
    except asyncio.TimeoutError:
        print(f"Timeout encountered for user {user_id} in channel {channel_id}. Resetting chat session.")
        # Reset the session by deleting it from the global dictionaries
        chat_sessions.pop(key, None)
        session_locks.pop(key, None)
        # Create a new chat session and try again
        chat, lock = await get_chat_session(channel_id, user_id)
        async with lock:
            response = await send_message_with_timeout(chat, user_message, timeout=10)
    print("Received chat response.")
    return response.text

async def generate_gemini_chat_response_with_images(channel_id: int, user_id: int, user_message: str, image_data_list: list) -> str:
    """
    Build a chat message with both text and image parts, and send it through the chat session.
    If a timeout occurs, reset the session and try once more.
    """
    key = (channel_id, user_id)
    print("Sending message with images to chat session.")
    chat, lock = await get_chat_session(channel_id, user_id)
    parts = [types.Part.from_text(text=user_message)]
    print(f"Text part added: {user_message}")
    for index, image_data in enumerate(image_data_list, start=1):
        print(f"Adding image part {index} (size: {len(image_data)} bytes).")
        parts.append(types.Part.from_bytes(data=image_data, mime_type="image/jpeg"))
    content = types.Content(role="user", parts=parts)
    try:
        async with lock:
            response = await send_message_with_timeout(chat, content, timeout=10)
    except asyncio.TimeoutError:
        print(f"Timeout encountered for user {user_id} in channel {channel_id} (images). Resetting chat session.")
        chat_sessions.pop(key, None)
        session_locks.pop(key, None)
        chat, lock = await get_chat_session(channel_id, user_id)
        async with lock:
            response = await send_message_with_timeout(chat, content, timeout=10)
    print("Received chat response with images.")
    return response.text

# ---------------------------
# Helper Functions to Send Long Messages
# ---------------------------
async def send_long_message(channel, content: str, max_length: int = 2000):
    if len(content) <= max_length:
        await channel.send(content)
    else:
        chunks = [content[i:i+max_length] for i in range(0, len(content), max_length)]
        for chunk in chunks:
            await channel.send(chunk)
    print("Sent long message to channel.")

async def send_long_reply(target_message, content: str, max_length: int = 2000):
    if len(content) <= max_length:
        await target_message.reply(content)
    else:
        chunks = [content[i:i+max_length] for i in range(0, len(content), max_length)]
        await target_message.reply(chunks[0])
        for chunk in chunks[1:]:
            await target_message.channel.send(chunk)
    print("Sent long reply.")

# ---------------------------
# Message Handling: Listen for Mentions and Replies
# ---------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    print(f"Received message from {message.author} in channel {message.channel.id}: {message.content}")
    bot_mentioned = bot.user in message.mentions
    target_message = None

    if message.reference:
        try:
            target_message = await message.channel.fetch_message(message.reference.message_id)
            print("Fetched referenced message successfully.")
        except Exception as e:
            print(f"Error fetching reference message: {e}")

    if bot_mentioned:
        if target_message and target_message.author.id != bot.user.id:
            input_text = target_message.content
            attachments = target_message.attachments
            print("Using referenced message content for input.")
        else:
            input_text = message.content.replace(bot.user.mention, '').strip()
            attachments = message.attachments
            print("Using current message content for input.")

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

        if target_message:
            await send_long_reply(target_message, response)
        else:
            await send_long_message(message.channel, response)

    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    print("Jarvis support bot is online!")

if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("Error: DISCORD_BOT_TOKEN environment variable not set.")
    else:
        print("Starting bot...")
        bot.run(TOKEN)
