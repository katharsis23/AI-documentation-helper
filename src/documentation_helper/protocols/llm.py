from typing import Protocol

from pydantic import BaseModel


class ILLMRequest(Protocol):
    """Unified protocol that makes sure that we use similar API's for different LLM providers"""

    model: str
    url: str
    api_key: str

    @staticmethod
    async def query(
        prompt: str,
    ):  # Returns LLMResponse
        ...


class LLMResponse(BaseModel):
    """Interface that describes LLM output"""

    text: str
    raw_response: dict
