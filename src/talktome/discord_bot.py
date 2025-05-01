import os
from typing import cast

import discord
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.chat_models.base import BaseChatModel
from langchain.schema import HumanMessage, SystemMessage

from talktome.prompts import SYSTEM_PROMPT
from talktome.setup_logging import setup_logging

load_dotenv()

logger = setup_logging()

openai_chat_model = init_chat_model(
    model="gpt-4o-mini",
    model_provider="openai",
)

anthropic_chat_model = init_chat_model(
    model="claude-3-5-haiku-20241022",
    model_provider="anthropic",
)

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


async def get_model_response(message: discord.Message,  model: BaseChatModel) -> str:
    response = await model.ainvoke(
        [
            SystemMessage(content=SYSTEM_PROMPT.format(user_name=message.author.name)),
            HumanMessage(content=message.content),
        ]
    )
    return cast(str, response.content)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if message.content.startswith("!ela"):
        model = openai_chat_model
        message.content = message.content[4:]
    elif message.content.startswith("!claude"):
        model = anthropic_chat_model
        message.content = message.content[6:]
    else:
        return

    async with message.channel.typing():
        response = await get_model_response(message, model)
        await message.channel.send(response)


client.run(os.environ["DISCORD_APP_TOKEN"], log_handler=None)
