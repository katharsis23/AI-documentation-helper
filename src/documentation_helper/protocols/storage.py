"""Protocols that unify the API of the vector storage backends.

Any storage backend (``sqlite-vec``, Qdrant, pgvector, ...) must satisfy
:class:`IVectorStorage`. The :class:`~documentation_helper.rag_pipeline.RAGPipeline`
depends only on this contract, so swapping the concrete database does not
require changing the pipeline.
"""

from typing import Any, Protocol

from src.documentation_helper.protocols.chunker import Chunk, SearchResult


class IVectorStorage(Protocol):
    """Unified interface for a vector database.

    The contract intentionally stays at the domain level: callers pass in
    :class:`Chunk` objects and vectors, and receive :class:`SearchResult`
    objects back, without knowing anything about the underlying database.
    """

    def add(
        self,
        chunks: list[Chunk],
        vectors: list[list[float]],
        doc_id: str | None = None,
    ) -> None:
        """Stores ``chunks`` together with their embedding ``vectors``."""
        ...

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Returns the ``top_k`` most similar chunks, optionally filtered."""
        ...

    def delete_by_document(self, doc_id: str) -> None:
        """Removes a document and all of its chunks/vectors (for re-indexing)."""
        ...

    def list_documents(self) -> list[dict[str, Any]]:
        """Returns metadata about every stored document."""
        ...
