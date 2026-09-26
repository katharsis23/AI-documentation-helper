from typing import Protocol
from pydantic import BaseModel


class ILLMRequest(Protocol):
    """Unified protocol that makes sure that we use similar API's for different LLM providers"""
    ...


class LLMResponse(BaseModel):
    """Interface that describes LLM output"""
    ...
