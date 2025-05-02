import os

import discord
from dotenv import load_dotenv
from langchain.schema import BaseMessage, HumanMessage, SystemMessage

from talktome.chatbot import ChatBot, Model
from talktome.prompts import DISCORD_SYSTEM_PROMPT
from talktome.setup_logging import setup_logging

load_dotenv()

logger = setup_logging()

chatbot = ChatBot()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


async def get_model_response(message: discord.Message, model: Model) -> str:
    input_: list[BaseMessage] = [
        SystemMessage(content=DISCORD_SYSTEM_PROMPT.format(user_name=message.author.name)),
        HumanMessage(content=message.content),
    ]
    response = await chatbot.get_model_response(input_, model)
    return response


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if message.content.startswith("!ela"):
        model = Model.OPENAI
        message.content = message.content[4:]
    elif message.content.startswith("!claude"):
        model = Model.ANTHROPIC
        message.content = message.content[6:]
    else:
        return

    async with message.channel.typing():
        if await chatbot.is_violating_openai_content_policy(message.content):
            await message.channel.send("This message was flagged as inappropriate.")
            return
        response = await get_model_response(message, model)
        await message.channel.send(response)


client.run(os.environ["DISCORD_APP_TOKEN"], log_handler=None)
