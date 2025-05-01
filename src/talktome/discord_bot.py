import os
from typing import cast

import discord
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.schema import HumanMessage, SystemMessage

from talktome.prompts import SYSTEM_PROMPT
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
        async with message.channel.typing():
            response = await chat_model.ainvoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT.format(user_name=message.author.name)),
                    HumanMessage(content=message.content),
                ]
            )
            content = cast(str, response.content)
            await message.channel.send(content)


client.run(os.environ["DISCORD_APP_TOKEN"], log_handler=None)
