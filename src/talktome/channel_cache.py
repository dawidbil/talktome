import logging
from dataclasses import dataclass

import discord

from talktome.chatbot import ChatBot

logger = logging.getLogger(__name__)


@dataclass
class Message:
    id: int
    content: str
    author: str
    violating_openai_content_policy: bool


class ChannelCache:
    def __init__(self, chatbot: ChatBot, limit: int):
        self.chatbot: ChatBot = chatbot
        self.limit: int = limit
        self.messages: dict[int, list[Message]] = {}

    async def add_message(self, message: discord.Message):
        if message.channel.id not in self.messages:
            self.messages[message.channel.id] = []
        if self.message_in_cache(message):
            logger.info(f"Message {message.id} already in cache")
            return
        channel_message = await self.discord_message_to_message(message)
        logger.info(f"Adding message to cache: {channel_message}")
        self.messages[message.channel.id].append(channel_message)
        if len(self.messages[message.channel.id]) > self.limit:
            self.messages[message.channel.id].pop(0)

    async def discord_message_to_message(self, message: discord.Message) -> Message:
        return Message(
            id=message.id,
            content=message.content,
            author=message.author.name,
            violating_openai_content_policy=await self.chatbot.is_violating_openai_content_policy(
                message.content
            ),
        )

    def message_in_cache(self, message: discord.Message) -> bool:
        return any(m.id == message.id for m in self.messages[message.channel.id])

    def get_messages(self, channel_id: int) -> list[Message]:
        return self.messages[channel_id]
