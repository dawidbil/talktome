from enum import Enum
from typing import cast

from langchain.chat_models import init_chat_model
from langchain.chat_models.base import BaseChatModel
from langchain.schema import BaseMessage


class Model(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ChatBot:
    def __init__(self) -> None:
        self.openai_chat_model: BaseChatModel = init_chat_model(
            model="gpt-4o-mini",
            model_provider="openai",
        )

        self.anthropic_chat_model: BaseChatModel = init_chat_model(
            model="claude-3-5-haiku-20241022",
            model_provider="anthropic",
        )

    async def get_model_response(self, input_: list[BaseMessage], model: Model) -> str:
        if model == Model.OPENAI:
            response = await self.openai_chat_model.ainvoke(input_)
        else:
            response = await self.anthropic_chat_model.ainvoke(input_)
        return cast(str, response.content)
