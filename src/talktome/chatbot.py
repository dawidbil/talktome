import logging
from enum import Enum
from typing import TypedDict

from langchain.chains.moderation import OpenAIModerationChain
from langchain.chat_models import init_chat_model
from langchain.schema import AIMessage, BaseMessage
from langchain_core.language_models.base import LanguageModelInput
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnableLambda

logger = logging.getLogger(__name__)


class Model(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class MessageWithUsage(TypedDict):
    content: str
    usage: int


def extract_content_and_usage(response: BaseMessage) -> MessageWithUsage:
    if not isinstance(response, AIMessage):
        raise ValueError("Expected AIMessage response")
    logger.debug(f"Response: {response}")
    content = StrOutputParser().invoke(response)
    usage = 0 if response.usage_metadata is None else response.usage_metadata.get("total_tokens", 0)
    return MessageWithUsage(content=content, usage=usage)


class ChatBot:
    def __init__(self) -> None:
        self.openai_chat_model: Runnable[LanguageModelInput, MessageWithUsage] = init_chat_model(
            model="gpt-4o-mini",
            model_provider="openai",
        ) | RunnableLambda(extract_content_and_usage)

        self.anthropic_chat_model: Runnable[LanguageModelInput, MessageWithUsage] = init_chat_model(
            model="claude-3-5-haiku-20241022",
            model_provider="anthropic",
        ) | RunnableLambda(extract_content_and_usage)

        self.openai_moderation_chain: OpenAIModerationChain = OpenAIModerationChain()

    async def get_model_response(self, input_: list[BaseMessage], model: Model) -> MessageWithUsage:
        if model == Model.OPENAI:
            response = await self.openai_chat_model.ainvoke(input_)
        else:
            response = await self.anthropic_chat_model.ainvoke(input_)
        return response

    async def is_violating_openai_content_policy(self, input_: str) -> bool:
        result: dict[str, str] = await self.openai_moderation_chain.ainvoke({"input": input_})
        return result["output"] == "Text was found that violates OpenAI's content policy."
