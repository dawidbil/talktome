import json
import os
from datetime import datetime, timedelta
from typing import cast

import discord
from dotenv import load_dotenv
from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage

from talktome.channel_cache import ChannelCache, Message
from talktome.chatbot import ChatBot, MessageWithUsage, Model
from talktome.database import Database
from talktome.prompts import Prompts
from talktome.setup_logging import setup_logging

load_dotenv()

TOKEN_USAGE_LIMIT = int(os.environ["DISCORD_TOKEN_USAGE_LIMIT"])
POWER_USER_IDS: list[int] = cast(list[int], json.loads(os.environ["POWER_USERS_IDS"]))
DISCORD_BOT_NAME = os.environ["DISCORD_BOT_NAME"]

logger = setup_logging()

chatbot = ChatBot()
prompts = Prompts(os.environ["PROMPTS_JSON_PATH"])
channel_cache = ChannelCache(chatbot, int(os.environ["CHANNEL_MESSAGE_HISTORY_LIMIT"]))
database = Database()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


def get_message(message: Message, client_name: str) -> BaseMessage:
    if message.author == client_name:
        return AIMessage(content=message.content)
    else:
        return HumanMessage(content=f"{message.author}: {message.content}")


async def get_conversation_model_response(
    messages: list[Message], client_name: str
) -> MessageWithUsage:
    base_messages = [get_message(message, client_name) for message in messages]
    input_: list[BaseMessage] = [
        SystemMessage(content=prompts.get_prompt("DISCORD_CONVERSATION_PROMPT")),
        *base_messages,
    ]
    response = await chatbot.get_model_response(input_, Model.OPENAI)
    return response


async def add_message_history_to_cache(message: discord.Message):
    logger.info(f"Fetching {channel_cache.limit} messages from channel {message.channel.id}")
    channel_messages = [
        message async for message in message.channel.history(limit=channel_cache.limit)
    ]
    for channel_message in reversed(channel_messages):
        logger.debug(f"Fetched message: {channel_message}")
        await channel_cache.add_message(channel_message)


async def send_conversation_message(message: discord.Message, client_name: str):
    await add_message_history_to_cache(message)
    channel_messages = channel_cache.get_messages(message.channel.id)
    filtered_messages = [
        message for message in channel_messages if not message.violating_openai_content_policy
    ]
    response = await get_conversation_model_response(filtered_messages, client_name)
    database.add_request_tokens(message.channel.id, response["usage"])
    await message.channel.send(response["content"])


def token_usage_last_24_hours(channel_id: int) -> int:
    token_usage = database.get_request_tokens(channel_id)
    day_ago = datetime.now() - timedelta(hours=24)
    token_usage_last_24_hours = [row for row in token_usage if row.created_at > day_ago]
    return sum([row.tokens for row in token_usage_last_24_hours])


def is_token_usage_reached(channel_id: int):
    return token_usage_last_24_hours(channel_id) >= TOKEN_USAGE_LIMIT


def replace_mentions_with_display_name(message: discord.Message):
    for user in message.mentions:
        mention_patterns = [f"<@{user.id}>", f"<@!{user.id}>"]
        for pattern in mention_patterns:
            message.content = message.content.replace(pattern, user.display_name)


@client.event
async def on_ready():
    logger.info(f"We have logged in as {client.user}")
    database.delete_request_tokens_older_than_24_hours()


@client.event
async def on_message(message: discord.Message):
    assert client.user is not None
    if message.author == client.user:
        return

    if message.content.startswith(f"!{DISCORD_BOT_NAME}_token_usage"):
        async with message.channel.typing():
            await message.channel.send(
                f"Token usage for {message.channel.id} in the last 24 hours: {token_usage_last_24_hours(message.channel.id)}"
            )
            return

    if message.content.startswith(f"!{DISCORD_BOT_NAME}_token_usage"):
        if message.author.id not in POWER_USER_IDS:
            await message.channel.send(prompts.get_prompt("DISCORD_YOU_ARE_NOT_AUTHORIZED"))
            return
        async with message.channel.typing():
            await message.channel.send(
                f"Token usage for {message.channel.id}:\n{database.get_request_tokens(message.channel.id)}"
            )
        return

    if message.content.startswith(f"!{DISCORD_BOT_NAME}_reset_token_usage"):
        if message.author.id not in POWER_USER_IDS:
            await message.channel.send(prompts.get_prompt("DISCORD_YOU_ARE_NOT_AUTHORIZED"))
            return
        database.delete_request_tokens(message.channel.id)
        await message.channel.send("Token usage reset")
        return

    replace_mentions_with_display_name(message)

    if client.user.mentioned_in(message):
        if is_token_usage_reached(message.channel.id):
            await message.channel.send(prompts.get_prompt("DISCORD_TOKEN_USAGE_LIMIT_REACHED"))
            return
        async with message.channel.typing():
            await send_conversation_message(message, client.user.name)
        return


client.run(os.environ["DISCORD_APP_TOKEN"], log_handler=None)
