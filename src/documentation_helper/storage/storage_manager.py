"""High-level storage facade.

``StorageManager`` is the single entry point the rest of the application uses
to talk to persistence. It has two responsibilities:

1. **Factory** — :meth:`get_db` builds the concrete backend selected by
   ``config.db_provider`` (``sqlite`` for the course project) and keeps it on
   the instance.
2. **Wrapper / access layer** — it exposes a domain-level API (``Chunk`` in,
   ``SearchResult`` out) by delegating to the backend's raw methods, and it
   owns cross-cutting concerns such as the connection context manager and the
   path to uploaded documents.

Keeping the raw SQL in :class:`~documentation_helper.storage.sqlite_provider.SQLiteProvider`
and the domain mapping here means a new backend (Qdrant, pgvector) only has to
implement the raw methods — the rest of the app keeps using ``StorageManager``.
"""

from __future__ import annotations

import datetime
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from src.documentation_helper.config import config
from src.documentation_helper.protocols.chunker import Chunk, SearchResult
from src.documentation_helper.storage.sqlite_provider import SQLiteProvider


class StorageManager:
    """High level class that chooses DB provider and gives the context."""

    # Maps the ``config.db_provider`` value to a backend class.
    _PROVIDERS: dict[str, type] = {
        "sqlite": SQLiteProvider,
    }

    def __init__(
        self,
        db_provider: str | None = None,
        db_path: str | None = None,
        uploads_dir: str | None = None,
        embedding_dim: int | None = None,
    ) -> None:
        self.db_provider = db_provider or config.db_provider
        self.db_path = db_path or config.db_path
        self.uploads_dir = uploads_dir or config.uploads_dir
        self.embedding_dim = embedding_dim or config.embedding_dim
        self._db: Any = None
        self.get_db()

    # =========================================================================
    # Factory / backend
    # =========================================================================
    def get_db(self) -> Any:
        """Builds (once) and returns the concrete DB provider instance."""
        if self._db is not None:
            return self._db

        provider_class = self._PROVIDERS.get(self.db_provider)
        if provider_class is None:
            raise ValueError(f"Unknown DB provider: {self.db_provider!r}")

        # Ensure the parent directory of the database exists.
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._db = provider_class(
            db_path=self.db_path, embedding_dim=self.embedding_dim
        )
        return self._db

    def get_path_to_documents(self) -> str:
        """Returns (and creates) the directory holding uploaded documents."""
        Path(self.uploads_dir).mkdir(parents=True, exist_ok=True)
        return self.uploads_dir

    # =========================================================================
    # Context management / access
    # =========================================================================
    @contextmanager
    def context_manager(self) -> Iterator[Any]:
        """Context manager that yields the raw DB provider.

        Guarantees the connection is flushed/committed by delegating to the
        backend, and closes it on exit so callers never leak a connection.
        """
        db = self.get_db()
        try:
            yield db
        finally:
            db.connection.commit()

    # =========================================================================
    # Domain-level API (implements IVectorStorage semantics)
    # =========================================================================
    def add(
        self,
        chunks: list[Chunk],
        vectors: list[list[float]],
        doc_id: str,
        filename: str,
        uploaded_at: datetime.datetime | None = None,
    ) -> None:
        """Stores a document record together with its chunks and vectors."""
        if len(chunks) != len(vectors):
            raise ValueError(
                f"Received {len(chunks)} chunks but {len(vectors)} vectors"
            )

        uploaded_at = uploaded_at or datetime.datetime.now(datetime.UTC)
        document_rows = [self._chunk_to_row(chunk, doc_id) for chunk in chunks]

        with self.context_manager() as db:
            db.add_document(
                doc_id=doc_id,
                filename=filename,
                uploaded_at=uploaded_at.isoformat(),
            )
            db.add_document_chunks(document_rows, vectors)

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Returns the ``top_k`` closest chunks as domain ``SearchResult``s.

        ``filters`` optionally supports the ``doc_id`` key to restrict the
        search to a single document. When omitted, all documents are searched.
        """
        doc_id = (filters or {}).get("doc_id")

        with self.context_manager() as db:
            rows = db.search_document(query_vector, top_k=top_k, doc_id=doc_id)

        return [self._row_to_search_result(row) for row in rows]

    def list_documents(self) -> list[dict[str, Any]]:
        """Returns metadata (id, filename, uploaded_at, chunk_count)."""
        with self.context_manager() as db:
            rows = db.list_documents()

        return [
            {
                "doc_id": row["doc_id"],
                "filename": row["filename"],
                "uploaded_at": row["uploaded_at"],
                "chunk_count": row["chunk_count"],
            }
            for row in rows
        ]

    def delete_by_document(self, doc_id: str) -> None:
        """Deletes a document and all of its chunks/vectors."""
        with self.context_manager() as db:
            db.delete_by_document(doc_id)

    def close(self) -> None:
        """Closes the underlying backend connection."""
        if self._db is not None:
            self._db.close()
            self._db = None

    # =========================================================================
    # Mapping helpers (domain <-> raw rows)
    # =========================================================================
    @staticmethod
    def _chunk_to_row(chunk: Chunk, doc_id: str) -> dict[str, Any]:
        return {
            "chunk_id": str(chunk.chunk_id),
            "doc_id": doc_id,
            "text": chunk.text,
            "source_file": chunk.source_file,
            "section_header": chunk.section_header,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "content_hash": chunk.content_hash,
            "tags": chunk.tags,
        }

    @staticmethod
    def _row_to_search_result(row: sqlite3.Row) -> SearchResult:
        chunk = Chunk(
            chunk_id=row["chunk_id"],
            text=row["text"],
            source_file=row["source_file"],
            section_header=row["section_header"],
            page_number=row["page_number"],
            chunk_index=row["chunk_index"],
            content_hash=row["content_hash"],
            tags=json.loads(row["tags"] or "{}"),
        )
        return SearchResult(chunk=chunk, score=row["score"])
