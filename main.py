from bot import bot
from config import DISCORD_TOKEN

if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print("Error: Set your API key in config.ini")
    else:
        print("Starting bot...")
        bot.run(DISCORD_TOKEN)