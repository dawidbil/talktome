import logging
from enum import Enum
from typing import cast

from langchain.chains.moderation import OpenAIModerationChain
from langchain.chat_models import init_chat_model
from langchain.chat_models.base import BaseChatModel
from langchain.schema import BaseMessage

logger = logging.getLogger(__name__)


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

        self.openai_moderation_chain: OpenAIModerationChain = OpenAIModerationChain()

    async def get_model_response(self, input_: list[BaseMessage], model: Model) -> str:
        if model == Model.OPENAI:
            response = await self.openai_chat_model.ainvoke(input_)
        else:
            response = await self.anthropic_chat_model.ainvoke(input_)
        return cast(str, response.content)

    async def is_violating_openai_content_policy(self, input_: str) -> bool:
        result: dict[str, str] = await self.openai_moderation_chain.ainvoke({"input": input_})
        return result["output"] == "Text was found that violates OpenAI's content policy."
