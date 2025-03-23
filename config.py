import configparser

config_file = 'config.ini'
config = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
config.read(config_file)

GEMINI_API_KEY = config['General']['gemini_api_key']
TENOR_API_KEY = config['General']['tenor_api_key']
DISCORD_TOKEN = config['General']['discord_token']