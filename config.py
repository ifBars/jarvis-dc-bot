import configparser
import os

# Define default configuration
DEFAULT_CONFIG = {
    'General': {
        'gemini_api_key': 'your_api_key',
        'tenor_api_key': 'your_tenor_key',
        'discord_token': 'your_bot_token'
    }
}

def create_default_config(filename):
    """Creates a new config file with the default placeholder values."""
    config = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    config.read_dict(DEFAULT_CONFIG)
    with open(filename, 'w') as configfile:
        config.write(configfile)
    print(f"Default config created at {filename}")
    return config

def load_config(filename):
    """Loads the config file, ensuring that all expected options are present.
    
    If the file is missing or options are missing, it is updated with default values.
    """
    config = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    
    if not os.path.exists(filename):
        print(f"Config file {filename} does not exist. Creating default config.")
        return create_default_config(filename)
    
    config.read(filename)
    updated = False
    
    if 'General' not in config:
        config['General'] = {}
        updated = True
    
    for key, default_value in DEFAULT_CONFIG['General'].items():
        if key not in config['General']:
            config['General'][key] = default_value
            updated = True
            print(f"Missing option '{key}' added with default value.")
    
    if updated:
        with open(filename, 'w') as configfile:
            config.write(configfile)
        print(f"Config file {filename} updated with missing options.")
    
    return config

# Use the helper function to load and update the config
config_file = 'config.ini'
config = load_config(config_file)

# Retrieve configuration options
GEMINI_API_KEY = config['General']['gemini_api_key']
TENOR_API_KEY = config['General']['tenor_api_key']
DISCORD_TOKEN = config['General']['discord_token']