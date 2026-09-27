"""Local embedding provider.

Implements :class:`~documentation_helper.protocols.embedding.IEmbeddingProvider`.
The provider is deliberately thin: it does not know *how* a model produces a
vector. It receives an already-built model backend (e.g. ``OllamaProvider``)
that exposes ``post_embedding()`` and only orchestrates batch vs. single-query
embedding on top of it.
"""

from __future__ import annotations

from src.documentation_helper.protocols.embedding import (
    IEmbeddingBackend,
    IEmbeddingProvider,
)


class LocalEmbeddingProvider(IEmbeddingProvider):
    """Turns text into vectors using an injected local model backend.

    ``embed()`` is used in batch during ingestion while ``embed_query()`` is
    used for a single user question. They are kept separate because some models
    may apply different preprocessing to a query than to a document.
    """

    def __init__(self, model_name: str, backend: IEmbeddingBackend) -> None:
        self.model_name = model_name
        self.backend = backend

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embeds a batch of documents (chunks) during ingestion."""
        return [await self.backend.post_embedding(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        """Embeds a single user query."""
        return await self.backend.post_embedding(text)
