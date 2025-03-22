from commands import overwrite_response
import random 

command_handlers = {
        "gsc": lambda _: (send_gif, ("https://tenor.com/view/scream-screaming-terror-terrified-horrified-gif-24374910")),
        "gjm": lambda _: (jarvis_meme, ()),
}

commands_string = """
    gsc()         - Scream.
    gjm()         - Send a meme regarding jarvis. This can be used as a comeback.
"""

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
