import asyncio
import json
import google.genai as genai
from google.genai import types
from google.genai.types import Tool, GenerateContentConfig, GoogleSearchRetrieval
from config import GEMINI_API_KEY
from chat import send_message_with_timeout, get_chat_session, chat_sessions, session_locks, session_last_used
from commands import process_command

async def evaluate_task_complexity(task: str) -> str:
    print("Evaluating task complexity")

    evaluation_prompt = (
        "Analyze the following task and categorize it:\n"
        "1. If it requires factual knowledge or technical help, use 'gemini-2.0-flash-thinking-exp-01-21'\n"
        "2. If it's a simple conversation or greeting, use 'gemini-2.0-flash'\n"
        "3. If it involves search or current information, use 'gemini-2.0-flash' with search retrieval\n"
        f"Task: {task}"
    )
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    generate_content_config = types.GenerateContentConfig(
        temperature=0.7,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        response_mime_type="application/json",
        response_schema=genai.types.Schema(
            type=genai.types.Type.OBJECT,
            properties={
                "model": genai.types.Schema(
                    type=genai.types.Type.STRING,
                ),
            },
        ),
    )
    
    chat = await asyncio.to_thread(client.chats.create, model="gemini-2.0-flash-lite", config=generate_content_config)
    response = await asyncio.to_thread(chat.send_message, evaluation_prompt)
    
    try:
        result = json.loads(response.text)
        chosen_model = result.get("model", "gemini-2.0-flash")
        print(f"gemini-2.0-flash-lite chose model: {chosen_model}")
        return chosen_model
    except json.JSONDecodeError:
        print("Failed to decode JSON, defaulting to gemini-2.0-flash")
        return "gemini-2.0-flash"

async def generate_gemini_chat_response(channel_id: int, user_id: int, user_message: str) -> str:
    key = (channel_id, user_id)
    model_name = await evaluate_task_complexity(user_message)
    chat, lock = await get_chat_session(channel_id, user_id, model_name)
    try:
        async with lock:
            response = await send_message_with_timeout(chat, user_message, timeout=20)
    except genai.errors.ClientError as e:
        if e.code == 429:
            if model_name == "gemini-2.0-flash-thinking-exp-01-21":
                print(f"Rate limit encountered for thinking model for user {user_id} in channel {channel_id}. Retrying with gemini-2.0-flash.")
                chat_sessions.pop(key, None)
                session_locks.pop(key, None)
                session_last_used.pop(key, None)
                fallback_model = "gemini-2.0-flash"
                chat, lock = await get_chat_session(channel_id, user_id, fallback_model)
                async with lock:
                    response = await send_message_with_timeout(chat, user_message, timeout=20)
            else:
                print(f"Rate limit encountered for user {user_id} in channel {channel_id}.")
                return ("Jarvis: My processors are currently overtaxed, sir. "
                        "Please allow me a moment to cool down before your next command.")
        else:
            raise
    except genai.errors.APIError as e:
        raise
    except (asyncio.TimeoutError, asyncio.CancelledError):
        print(f"Timeout or cancellation encountered for user {user_id} in channel {channel_id}. Resetting chat session.")
        chat_sessions.pop(key, None)
        session_locks.pop(key, None)
        session_last_used.pop(key, None)
        chat, lock = await get_chat_session(channel_id, user_id, model_name)
        async with lock:
            response = await send_message_with_timeout(chat, user_message, timeout=20)
    print("Received chat response.")
    return process_command(response.text)

async def generate_gemini_chat_response_with_images(channel_id: int, user_id: int, user_message: str, image_data_list: list) -> str:
    key = (channel_id, user_id)
    print("Sending message with images to chat session.")
    model_name = await evaluate_task_complexity(user_message)
    chat, lock = await get_chat_session(channel_id, user_id, model_name)
    
    # Build parts list
    parts = []
    # Add text part
    parts.append(types.Part.from_text(text=user_message))
    print(f"Text part added: {user_message}")
    
    # Add image parts
    for index, image_data in enumerate(image_data_list, start=1):
        print(f"Adding image part {index} (size: {len(image_data)} bytes).")
        parts.append(types.Part.from_bytes(data=image_data, mime_type="image/jpeg"))
    
    try:
        async with lock:
            # Pass the list of parts directly instead of wrapping in a Content object
            response = await send_message_with_timeout(chat, parts, timeout=20)
    except genai.errors.ClientError as e:
        if e.code == 429:
            if model_name == "gemini-2.0-flash-thinking-exp-01-21":
                print(f"Rate limit encountered for thinking model (images) for user {user_id} in channel {channel_id}. Retrying with gemini-2.0-flash.")
                chat_sessions.pop(key, None)
                session_locks.pop(key, None)
                session_last_used.pop(key, None)
                fallback_model = "gemini-2.0-flash"
                chat, lock = await get_chat_session(channel_id, user_id, fallback_model)
                async with lock:
                    response = await send_message_with_timeout(chat, parts, timeout=20)
            else:
                print(f"Rate limit encountered for user {user_id} in channel {channel_id} (images).")
                return ("Jarvis: My quantum circuits are temporarily saturated, sir. "
                        "Please grant me a brief moment to realign my energy before processing your image.")
        else:
            raise
    except (asyncio.TimeoutError, asyncio.CancelledError):
        print(f"Timeout or cancellation encountered for user {user_id} in channel {channel_id} (images). Resetting chat session.")
        chat_sessions.pop(key, None)
        session_locks.pop(key, None)
        session_last_used.pop(key, None)
        chat, lock = await get_chat_session(channel_id, user_id, model_name)
        async with lock:
            response = await send_message_with_timeout(chat, parts, timeout=20)
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
            return ("Jarvis: My search circuits are at capacity, sir. "
                    "Please allow me a brief moment to recalibrate.")
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
