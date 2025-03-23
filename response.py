import asyncio
import google.genai as genai
from google.genai import types
from google.genai.types import Tool, GenerateContentConfig, GoogleSearchRetrieval
from config import GEMINI_API_KEY
from chat import send_message_with_timeout, get_chat_session, chat_sessions, session_locks, session_last_used
from commands import process_command

async def generate_gemini_chat_response(channel_id: int, user_id: int, user_message: str) -> str:
    key = (channel_id, user_id)
    chat, lock = await get_chat_session(channel_id, user_id)
    try:
        async with lock:
            response = await send_message_with_timeout(chat, user_message, timeout=20)
    except genai.errors.ClientError as e:
        if e.code == 429:
            print(f"Rate limit encountered for user {user_id} in channel {channel_id}.")
            return "Jarvis: My processors are currently overtaxed, sir. Please allow me a moment to cool down before your next command."
        else:
            raise
    except genai.errors.APIError as e:
        raise
    except (asyncio.TimeoutError, asyncio.CancelledError):
        print(f"Timeout or cancellation encountered for user {user_id} in channel {channel_id}. Resetting chat session.")
        chat_sessions.pop(key, None)
        session_locks.pop(key, None)
        session_last_used.pop(key, None)
        chat, lock = await get_chat_session(channel_id, user_id)
        async with lock:
            response = await send_message_with_timeout(chat, user_message, timeout=20)
    print("Received chat response.")
    return process_command(response.text)

async def generate_gemini_chat_response_with_images(channel_id: int, user_id: int, user_message: str, image_data_list: list) -> str:
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
            response = await send_message_with_timeout(chat, content, timeout=20)
    except genai.errors.ClientError as e:
        if e.code == 429:
            print(f"Rate limit encountered for user {user_id} in channel {channel_id} (images).")
            return "Jarvis: My quantum circuits are temporarily saturated, sir. Please grant me a brief moment to realign my energy before processing your image."
        else:
            raise
    except (asyncio.TimeoutError, asyncio.CancelledError):
        print(f"Timeout or cancellation encountered for user {user_id} in channel {channel_id} (images). Resetting chat session.")
        chat_sessions.pop(key, None)
        session_locks.pop(key, None)
        session_last_used.pop(key, None)
        chat, lock = await get_chat_session(channel_id, user_id)
        async with lock:
            response = await send_message_with_timeout(chat, content, timeout=20)
    print("Received chat response with images.")
    return process_command(response.text)

search_client = genai.Client(api_key=GEMINI_API_KEY)
model_id = "gemini-2.0-flash"
google_search_tool = Tool(
    google_search=GoogleSearchRetrieval()
)

async def generate_gemini_chat_response_with_google_search_retrieval(channel_id: int, user_id: int, user_message: str) -> str:
    key = (channel_id, user_id)
    chat, lock = await get_chat_session(channel_id, user_id)
    loop = asyncio.get_event_loop()
    
    try:
        async with lock:
            response = await loop.run_in_executor(
                None,
                lambda: search_client.models.generate_content(
                    model=model_id,
                    contents=user_message,
                    config=GenerateContentConfig(
                        tools=[google_search_tool],
                    )
                )
            )
    except genai.errors.ClientError as e:
        if e.code == 429:
            print(f"Rate limit encountered for user {user_id} in channel {channel_id} (search retrieval).")
            return "Jarvis: My search circuits are at capacity, sir. Please allow me a brief moment to recalibrate."
        else:
            raise
    except (asyncio.TimeoutError, asyncio.CancelledError) as err:
        print(f"Timeout or cancellation encountered for user {user_id} in channel {channel_id} (search retrieval). Resetting chat session.")
        chat_sessions.pop(key, None)
        session_locks.pop(key, None)
        session_last_used.pop(key, None)
        chat, lock = await get_chat_session(channel_id, user_id)
        async with lock:
            response = await loop.run_in_executor(
                None,
                lambda: search_client.models.generate_content(
                    model=model_id,
                    contents=user_message,
                    config=GenerateContentConfig(
                        tools=[google_search_tool],
                    )
                )
            )
    combined_text = "\n".join(part.text for part in response.candidates[0].content.parts)
    print("Received search retrieval response.")
    return process_command(combined_text)
