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