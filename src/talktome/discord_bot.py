import json
import os
from datetime import datetime, timedelta
from typing import cast

import discord
from discord.ext.commands import Bot, Context
from dotenv import load_dotenv
from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage

from talktome.channel_cache import ChannelCache, Message
from talktome.chatbot import ChatBot, MessageWithUsage, Model
from talktome.crud.channel_token_limits import (
    delete_channel_token_limit,
    get_channel_token_limit,
    set_channel_token_limit,
)
from talktome.crud.request_tokens import (
    add_request_tokens,
    delete_request_tokens,
    delete_request_tokens_older_than_24_hours,
    get_request_tokens,
)
from talktome.database import SessionLocal
from talktome.prompts import Prompts
from talktome.setup_logging import setup_logging

load_dotenv()

TOKEN_USAGE_LIMIT = int(os.environ["DISCORD_TOKEN_USAGE_LIMIT"])
POWER_USER_IDS: list[int] = cast(list[int], json.loads(os.environ["POWER_USERS_IDS"]))
DISCORD_BOT_NAME = os.environ["DISCORD_BOT_NAME"]
TESTING_GUILD = discord.Object(id=int(os.environ["TESTING_GUILD_ID"]))

logger = setup_logging()

chatbot = ChatBot()
prompts = Prompts(os.environ["PROMPTS_JSON_PATH"])
channel_cache = ChannelCache(chatbot, int(os.environ["CHANNEL_MESSAGE_HISTORY_LIMIT"]))

intents = discord.Intents.default()
intents.message_content = True

bot = Bot(command_prefix="!", intents=intents)


def get_message(message: Message, client_name: str) -> BaseMessage:
    if message.author == client_name:
        return AIMessage(content=message.content)
    else:
        return HumanMessage(content=f"{message.author}: {message.content}")


async def get_conversation_model_response(
    messages: list[Message], client_name: str, prompt: str
) -> MessageWithUsage:
    base_messages = [get_message(message, client_name) for message in messages]
    input_: list[BaseMessage] = [
        SystemMessage(content=prompt),
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


async def send_conversation_message(message: discord.Message, client_name: str, prompt: str):
    await add_message_history_to_cache(message)
    channel_messages = channel_cache.get_messages(message.channel.id)
    filtered_messages = [
        message for message in channel_messages if not message.violating_openai_content_policy
    ]
    response = await get_conversation_model_response(filtered_messages, client_name, prompt)
    with SessionLocal() as db:
        add_request_tokens(db, message.channel.id, response["usage"])
    await message.channel.send(response["content"])


def token_usage_last_24_hours(channel_id: int) -> int:
    with SessionLocal() as db:
        token_usage = get_request_tokens(db, channel_id)
    day_ago = datetime.now() - timedelta(hours=24)
    token_usage_last_24_hours = [row for row in token_usage if row.created_at > day_ago]
    return sum([row.tokens for row in token_usage_last_24_hours])


def get_channel_token_limit_or_default(channel_id: int):
    with SessionLocal() as db:
        limit = get_channel_token_limit(db, channel_id)
    if limit == 0:
        return TOKEN_USAGE_LIMIT
    return limit


def is_token_usage_reached(channel_id: int):
    return token_usage_last_24_hours(channel_id) >= get_channel_token_limit_or_default(channel_id)


def replace_mentions_with_display_name(message: discord.Message):
    for user in message.mentions:
        mention_patterns = [f"<@{user.id}>", f"<@!{user.id}>"]
        for pattern in mention_patterns:
            message.content = message.content.replace(pattern, user.display_name)


async def check_if_user_is_authorized(ctx: Context[Bot]):
    if ctx.author.id not in POWER_USER_IDS:
        await ctx.send(prompts.get_prompt("DISCORD_YOU_ARE_NOT_AUTHORIZED"))
        return False
    return True


@bot.event
async def on_ready():
    await bot.tree.sync(guild=TESTING_GUILD)
    await bot.tree.sync()
    with SessionLocal() as db:
        delete_request_tokens_older_than_24_hours(db)
    logger.info(f"We have logged in as {bot.user} with discord bot name {DISCORD_BOT_NAME}")


async def answer_conversation_message(message: discord.Message):
    if is_token_usage_reached(message.channel.id):
        await message.channel.send(prompts.get_prompt("DISCORD_TOKEN_USAGE_LIMIT_REACHED"))
        return
    assert bot.user is not None
    async with message.channel.typing():
        await send_conversation_message(
            message, bot.user.name, prompt=prompts.get_prompt("DISCORD_CONVERSATION_PROMPT")
        )


@bot.event
async def on_message(message: discord.Message):
    await bot.process_commands(message)
    assert bot.user is not None
    if message.author == bot.user:
        return

    replace_mentions_with_display_name(message)

    if isinstance(message.channel, discord.DMChannel):
        await answer_conversation_message(message)
        return

    if bot.user.mentioned_in(message):
        await answer_conversation_message(message)


@bot.tree.command(
    name="token_usage",
    description="Get the token usage for the current channel",
    guild=TESTING_GUILD,
)
async def token_usage(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id is None:
        await interaction.response.send_message("Channel not found")
        return
    token_usage = token_usage_last_24_hours(channel_id)
    token_limit = get_channel_token_limit_or_default(channel_id)
    token_usage_percentage = min(token_usage / token_limit, 1)
    await interaction.response.send_message(
        f"Token usage in the last 24 hours: {token_usage_percentage:.2%}"
    )


@bot.tree.command(
    name="help",
    description="Who am I?",
    guild=TESTING_GUILD,
)
async def help(interaction: discord.Interaction):
    await interaction.response.send_message(prompts.get_prompt("DISCORD_HELP_MESSAGE"))


@bot.command(name=f"{DISCORD_BOT_NAME}_db_token_usage")
async def db_token_usage(ctx: Context[Bot]):
    if not await check_if_user_is_authorized(ctx):
        return
    async with ctx.typing():
        with SessionLocal() as db:
            await ctx.send(
                f"Token usage for {ctx.channel.id}:\n{get_request_tokens(db, ctx.channel.id)}"
            )


@bot.command(name=f"{DISCORD_BOT_NAME}_reset_token_usage")
async def reset_token_usage(ctx: Context[Bot]):
    if not await check_if_user_is_authorized(ctx):
        return
    with SessionLocal() as db:
        delete_request_tokens(db, ctx.channel.id)
    await ctx.send("Token usage reset")


@bot.command(name=f"{DISCORD_BOT_NAME}_set_token_limit")
async def set_token_limit(ctx: Context[Bot]):
    if not await check_if_user_is_authorized(ctx):
        return
    limit = int(ctx.message.content.split(" ")[1])
    if limit < 0:
        await ctx.send("Token limit cannot be negative")
        return
    with SessionLocal() as db:
        set_channel_token_limit(db, ctx.channel.id, limit)
    await ctx.send(f"Token limit set to {limit}")


@bot.command(name=f"{DISCORD_BOT_NAME}_get_token_limit")
async def get_token_limit(ctx: Context[Bot]):
    if not await check_if_user_is_authorized(ctx):
        return
    with SessionLocal():
        await ctx.send(
            f"Token limit for {ctx.channel.id}: {get_channel_token_limit_or_default(ctx.channel.id)}"
        )


@bot.command(name=f"{DISCORD_BOT_NAME}_delete_token_limit")
async def delete_token_limit(ctx: Context[Bot]):
    if not await check_if_user_is_authorized(ctx):
        return
    with SessionLocal() as db:
        delete_channel_token_limit(db, ctx.channel.id)
    await ctx.send("Token limit deleted")


@bot.command(name=f"{DISCORD_BOT_NAME}_assistant")
async def assistant(ctx: Context[Bot]):
    if not await check_if_user_is_authorized(ctx):
        return
    assert bot.user is not None
    async with ctx.typing():
        await send_conversation_message(
            ctx.message, bot.user.name, prompt=prompts.get_prompt("DISCORD_POWERUSER_PROMPT")
        )


@bot.command(name=f"{DISCORD_BOT_NAME}_commands")
async def commands(ctx: Context[Bot]):
    await ctx.send(prompts.get_prompt("DISCORD_COMMANDS_MESSAGE"))


bot.run(os.environ["DISCORD_APP_TOKEN"], log_handler=None)
