import os

import discord
from dotenv import load_dotenv

from .setup_logging import setup_logging

load_dotenv()

logger = setup_logging()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if message.content.startswith("$hello"):
        await message.channel.send("Hello!")


client.run(os.environ["DISCORD_APP_TOKEN"], log_handler=None)
