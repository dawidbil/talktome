import os
from typing import cast

import discord
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.schema import HumanMessage

from talktome.setup_logging import setup_logging

load_dotenv()

logger = setup_logging()

chat_model = init_chat_model(
    model="gpt-4o-mini",
    model_provider="openai",
)

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

    if message.content.startswith("!ela"):
        response = await chat_model.ainvoke(
            [
                HumanMessage(content=message.content),
            ]
        )
        content = cast(str, response.content)
        await message.channel.send(content)


client.run(os.environ["DISCORD_APP_TOKEN"], log_handler=None)
