import os

import discord
from dotenv import load_dotenv
from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage

from talktome.channel_cache import ChannelCache, Message
from talktome.chatbot import ChatBot, Model
from talktome.prompts import Prompts
from talktome.setup_logging import setup_logging

load_dotenv()

logger = setup_logging()

chatbot = ChatBot()
prompts = Prompts(os.environ["PROMPTS_JSON_PATH"])
channel_cache = ChannelCache(chatbot, int(os.environ["CHANNEL_MESSAGE_HISTORY_LIMIT"]))

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


async def get_oneshot_model_response(message: discord.Message, model: Model) -> str:
    input_: list[BaseMessage] = [
        SystemMessage(
            content=prompts.get_prompt("DISCORD_ONESHOT_PROMPT").format(
                user_name=message.author.name
            )
        ),
        HumanMessage(content=message.content),
    ]
    response = await chatbot.get_model_response(input_, model)
    return response


def get_message(message: Message, client_name: str) -> BaseMessage:
    if message.author == client_name:
        return AIMessage(content=message.content)
    else:
        return HumanMessage(content=f"{message.author}: {message.content}")


async def get_conversation_model_response(messages: list[Message], client_name: str) -> str:
    human_messages = [get_message(message, client_name) for message in messages]
    input_: list[BaseMessage] = [
        SystemMessage(content=prompts.get_prompt("DISCORD_CONVERSATION_PROMPT")),
        *human_messages,
    ]
    response = await chatbot.get_model_response(input_, Model.OPENAI)
    return response


async def send_conversation_message(message: discord.Message, client_name: str):
    logger.info(f"Fetching {channel_cache.limit} messages from channel {message.channel.id}")
    channel_messages = [
        message async for message in message.channel.history(limit=channel_cache.limit)
    ]
    for channel_message in reversed(channel_messages):
        logger.debug(f"Fetched message: {channel_message}")
        await channel_cache.add_message(channel_message)
    channel_messages = channel_cache.get_messages(message.channel.id)
    filtered_messages = [
        message for message in channel_messages if not message.violating_openai_content_policy
    ]
    response = await get_conversation_model_response(filtered_messages, client_name)
    await message.channel.send(response)


def replace_mentions_with_display_name(message: discord.Message):
    for user in message.mentions:
        mention_patterns = [f"<@{user.id}>", f"<@!{user.id}>"]
        for pattern in mention_patterns:
            message.content = message.content.replace(pattern, user.display_name)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_message(message: discord.Message):
    assert client.user is not None
    if message.author == client.user:
        return

    replace_mentions_with_display_name(message)

    if client.user.mentioned_in(message):
        async with message.channel.typing():
            await send_conversation_message(message, client.user.name)
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
            await message.channel.send(prompts.get_prompt("DISCORD_INAPPROPRIATE_MESSAGE"))
            return
        response = await get_oneshot_model_response(message, model)
        await message.channel.send(response)


client.run(os.environ["DISCORD_APP_TOKEN"], log_handler=None)
