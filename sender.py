import io
import discord

async def send_long_message(channel, content, max_length: int = 2000, filename: str = "file.txt"):
    if isinstance(content, io.BytesIO):
        content.seek(0)
        await channel.send(file=discord.File(content, filename))
    elif isinstance(content, str):
        if len(content) <= max_length:
            await channel.send(content)
        else:
            chunks = [content[i:i+max_length] for i in range(0, len(content), max_length)]
            for chunk in chunks:
                await channel.send(chunk)
    else:
        await channel.send(str(content))
    print("Sent long message to channel.")

async def send_long_reply(target_message, content, max_length: int = 2000, filename: str = "file.txt"):
    if isinstance(content, io.BytesIO):
        content.seek(0)
        await target_message.reply(file=discord.File(content, filename))
    elif isinstance(content, str):
        if len(content) <= max_length:
            await target_message.reply(content)
        else:
            chunks = [content[i:i+max_length] for i in range(0, len(content), max_length)]
            await target_message.reply(chunks[0])
            for chunk in chunks[1:]:
                await target_message.channel.send(chunk)
    else:
        await target_message.reply(str(content))
    print("Sent long reply.")
