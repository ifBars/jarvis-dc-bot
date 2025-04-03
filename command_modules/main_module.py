from commands import overwrite_response
import random
import requests
import json
import io
from config import TENOR_API_KEY
import re

CLIENT_KEY = "jarvis-support-bot"
LIMIT = 8

command_handlers = {
    "gsc": lambda _: (send_gif, ("https://tenor.com/view/scream-screaming-terror-terrified-horrified-gif-24374910")),
    "gjm": lambda _: (jarvis_meme, ()),
    "ggs": lambda term: (search_and_send_gif, (term,)),
}

# "wrf": lambda content: (send_file, parse_file_input(content)),

commands_string = """
    gsc()         - Scream.
    gjm()         - Send a meme regarding jarvis. This can be used as a comeback.
    ggs(search)   - Search and send a gif using the provided search term.
"""

# wrf(filename|content)         - Send content as a file. This can be used when fitting.

def parse_file_input(content):
    """
    Parses the input string from Gemini.
    
    Expected format: "filename|file content"
    
    If the pipe '|' separator is not found, the default filename 'gemini_file.txt' is used,
    and the entire content is treated as the file content.
    """
    if not content:
        return ("gemini_file.txt", "No content provided")
    parts = content.split("|", 1)
    if len(parts) == 2:
        filename = parts[0].strip()
        file_content = parts[1].strip()
        return (filename, file_content)
    else:
        return ("gemini_file.txt", content.strip())

def send_file(filename, content):
    """
    Sends the provided content as a file. The payload is structured as a dictionary
    containing the filename and the content.
    """
    file_payload = io.BytesIO(content.encode())
    overwrite_response(file_payload)

def send_gif(url):
    overwrite_response(url)

def jarvis_meme():
    gifs = [
        "https://tenor.com/view/jarvis-iron-man-tony-stark-meme-memecoin-gif-9302496998732219055",
        "https://tenor.com/view/jarvis-hawk-hawk-tu-tuah-gif-3696881901305765010",
        "https://tenor.com/view/jarvis-tony-stark-iron-man-meme-dank-memes-gif-8688445319860298090",
        "https://tenor.com/view/jarvis-show-the-boys-parents-his-search-history-parenting-meme-dank-memes-gif-480415464354840479",
        "https://tenor.com/view/removehisballs-jarvis-gif-16584391341947717030",
        "https://tenor.com/view/jarvis-spam-ni--gif-15332231782679983694",
        "https://tenor.com/view/jarvis-tell-my-father-i-miss-him-dank-memes-jarvis-absent-father-iron-man-gif-8887834262831499190",
        "https://tenor.com/view/jarvis-iron-man-tony-stark-meme-memecoin-gif-6343695765403333511",
        "https://tenor.com/view/jarvis-galaxy-gas-ironman-meme-helmet-gif-9232080266832628026",
        "https://tenor.com/view/jarvis-galaxy-gas-ironman-meme-helmet-gif-9232080266832628026",
        "https://tenor.com/view/iron-man-jarvis-marvel-rivals-instalock-duelist-gif-13619046644159670842",
        "https://tenor.com/view/source-i-made-it-up-jarvis-iron-man-tony-stark-gif-573727876722239845",
        "https://tenor.com/view/jarvis-iron-man-tony-stark-meme-memecoin-gif-3465773927378715773",
        "https://tenor.com/view/marvel-rivals-jarvis-tony-stark-iron-man-jeff-the-land-shark-gif-17584344460561197894",
        "https://tenor.com/view/xd-gif-24372769"
    ]
    send_gif(random.choice(gifs))

def search_and_send_gif(search_term):
    """
    Searches for a gif using the Google Tenor API (v2) with the given search term,
    then sends the first result's gif URL. Uses the 'media_formats' from the v2 response.
    """
    if search_term.strip().lower() == "search":
        return

    # More robust content filtering
    if contains_inappropriate_content(search_term):
        overwrite_response("I cannot search for that term. Please refrain from asking me to send inappropriate content.")
        return
    
    search_url = (
        f"https://tenor.googleapis.com/v2/search?q={search_term}"
        f"&key={TENOR_API_KEY}"
        f"&client_key={CLIENT_KEY}"
        f"&limit={LIMIT}"
    )
    
    try:
        response = requests.get(search_url)
        response.raise_for_status()
        data = response.json()
        results = data.get("results")
        if results:
            random_result = random.choice(results)
            gif_url = random_result["media_formats"]["gif"]["url"]
            overwrite_response(gif_url)
        else:
            overwrite_response("No gif found for your search term.")
    except Exception as e:
        overwrite_response(f"An error occurred: {e}")

def contains_inappropriate_content(text):
    """
    Checks if the text contains inappropriate content using more advanced detection.
    Handles bypassing attempts like spaces between letters, character substitution, etc.
    """
    # Normalize the text: remove spaces, convert to lowercase
    normalized_text = re.sub(r'\s+', '', text.lower())
    
    # Handle common letter substitutions (leetspeak variants)
    substitutions = {
        '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', 
        '@': 'a', '$': 's', '!': 'i', '+': 't', '(': 'c',
        ')': 'o', '|': 'l', '\/': 'v'
    }
    
    for char, replacement in substitutions.items():
        normalized_text = normalized_text.replace(char, replacement)
    
    # List of inappropriate terms and patterns
    inappropriate_terms = [
        'nude', 'naked', 'boob', 'tits', 'ass', 
        'hotwoman', 'hotwomen', 'sexywoman', 'sexywomen',
        'hotgirl', 'hotgirls', 'sexygirl', 'sexygirls',
        'stripper', 'erotic', 'explicit'
    ]
    
    # Check for inappropriate content
    for term in inappropriate_terms:
        if term in normalized_text:
            return True
            
    # Check for combinations of concerning terms
    concerning_pairs = [
        ('hot', 'woman'), ('hot', 'girl'), ('sexy', 'woman'), 
        ('sexy', 'girl'), ('naked', 'woman'), ('naked', 'girl')
    ]
    
    for term1, term2 in concerning_pairs:
        if term1 in normalized_text and term2 in normalized_text:
            return True
    
    return False