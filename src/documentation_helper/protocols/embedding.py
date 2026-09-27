from typing import Protocol


class IEmbeddingProvider(Protocol):
    """Protocol for embed models"""

    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class IEmbeddingBackend(Protocol):
    """Minimal contract the embedding provider needs from a model backend."""

    async def post_embedding(self, text: str) -> list[float]: ...


class IBatchEmbeddingBackend(Protocol):
    """Optional contract for backends that can embed many texts at once.

    Implemented e.g. by ``OllamaProvider.post_embeddings``. When a backend
    satisfies it, the provider uses a single (batched) request instead of one
    request per chunk during ingestion, which keeps CPU/RAM usage bounded.
    """

    async def post_embeddings(self, texts: list[str]) -> list[list[float]]: ...
