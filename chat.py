import asyncio
import google.genai as genai
from google.genai import types
from datetime import datetime, timezone
from instructions import build_system_instructions
from config import GEMINI_API_KEY

chat_sessions = {}
session_locks = {}
session_last_used = {}
SESSION_EXPIRY_SECONDS = 1800  # Sessions expire after 30 minutes of inactivity

async def get_chat_session(channel_id: int, user_id: int):
    key = (channel_id, user_id)
    now = datetime.now(timezone.utc)
    if key not in chat_sessions:
        print(f"Creating new chat session for channel {channel_id} and user {user_id}.")
        client = genai.Client(api_key=GEMINI_API_KEY)
        gen_config = types.GenerateContentConfig(temperature=0.9)
        chat = await asyncio.to_thread(client.chats.create, model="gemini-2.0-flash", config=gen_config)
        system_instructions = await build_system_instructions()
        await asyncio.to_thread(chat.send_message, system_instructions)
        print("Chat session primed with system instructions.")
        chat_sessions[key] = chat
        session_locks[key] = asyncio.Lock()
    else:
        print(f"Using existing chat session for channel {channel_id} and user {user_id}.")
    session_last_used[key] = now
    return chat_sessions[key], session_locks[key]

async def send_message_with_timeout(chat, message, timeout=20):
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(chat.send_message, message),
            timeout=timeout
        )
        return response
    except asyncio.TimeoutError:
        print("Timeout when sending message via Gemini API.")
        raise
    except asyncio.CancelledError:
        print("Operation cancelled (possibly due to rate limiting).")
        raise

async def cleanup_old_sessions():
    while True:
        now = datetime.now(timezone.utc)
        expired_keys = [
            key for key, last_used in session_last_used.items()
            if (now - last_used).total_seconds() > SESSION_EXPIRY_SECONDS
        ]
        for key in expired_keys:
            chat_sessions.pop(key, None)
            session_locks.pop(key, None)
            session_last_used.pop(key, None)
            print(f"Cleaned up expired session for {key}")
        await asyncio.sleep(300)  # Check every 5 minutes
