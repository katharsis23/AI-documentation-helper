from typing import Protocol


class IEmbeddingProvider(Protocol):
    """Protocol for embed models"""

    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class IEmbeddingBackend(Protocol):
    """Minimal contract the embedding provider needs from a model backend."""

    async def post_embedding(self, text: str) -> list[float]: ...
