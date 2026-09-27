"""Low-level SQLite data-access layer.

``SQLiteProvider`` is intentionally dumb: it owns *only* the SQLite connection
and the raw SQL statements needed to persist documents, chunks and their
vectors via the ``sqlite-vec`` extension. It knows nothing about domain models
(``Chunk``, ``SearchResult``) or application logic — that belongs to
:class:`~documentation_helper.storage.storage_manager.StorageManager`, which
sits on top of this class.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

import sqlite_vec

from src.documentation_helper.config import config


class SQLiteProvider:
    """Thin wrapper over the SQLite API for storing documents and vectors."""

    def __init__(
        self,
        connection: sqlite3.Connection | None = None,
        db_path: str | None = None,
        embedding_dim: int | None = None,
    ) -> None:
        self.db_path = db_path
        self.embedding_dim = embedding_dim or config.embedding_dim
        self.connection = connection or self._connect()
        self._initiate()

    # =========================================================================
    # Connection / schema
    # =========================================================================
    def _connect(self) -> sqlite3.Connection:
        """Opens the database (defaults to in-memory when no path is set)."""
        connection = sqlite3.connect(self.db_path or ":memory:")
        connection.row_factory = sqlite3.Row
        connection.enable_load_extension(True)
        sqlite_vec.load(connection)
        connection.enable_load_extension(False)
        return connection

    def _initiate(self) -> None:
        """Ensures the extension is loaded and the schema exists."""
        self._create_tables()

    def _create_tables(self) -> None:
        """Creates the relational tables and the ``vec0`` virtual table."""
        with self.connection:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    uploaded_at TEXT NOT NULL
                )
                """
            )
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    section_header TEXT NOT NULL DEFAULT '',
                    page_number INTEGER NOT NULL DEFAULT 1,
                    chunk_index INTEGER NOT NULL DEFAULT 0,
                    content_hash TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            self.connection.execute(
                f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vectors USING vec0(
                    chunk_id TEXT PRIMARY KEY,
                    embedding FLOAT[{self.embedding_dim}]
                )
                """
            )

    # =========================================================================
    # Documents
    # =========================================================================
    def add_document(self, doc_id: str, filename: str, uploaded_at: str) -> None:
        """Inserts (or replaces) a document record."""
        with self.connection:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO documents (doc_id, filename, uploaded_at)
                VALUES (?, ?, ?)
                """,
                (doc_id, filename, uploaded_at),
            )

    def list_documents(self) -> list[sqlite3.Row]:
        """Returns every stored document row."""
        cursor = self.connection.execute(
            """
            SELECT
                d.doc_id,
                d.filename,
                d.uploaded_at,
                COUNT(c.chunk_id) AS chunk_count
            FROM documents AS d
            LEFT JOIN chunks AS c ON c.doc_id = d.doc_id
            GROUP BY d.doc_id
            ORDER BY d.uploaded_at DESC
            """
        )
        return cursor.fetchall()

    # =========================================================================
    # Chunks + vectors
    # =========================================================================
    def add_document_chunks(
        self,
        chunks: list[dict[str, Any]],
        vectors: list[list[float]],
    ) -> None:
        """Persists chunk metadata together with their embedding vectors."""
        with self.connection:
            self.connection.executemany(
                """
                INSERT OR REPLACE INTO chunks (
                    chunk_id, doc_id, text, source_file, section_header,
                    page_number, chunk_index, content_hash, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk["chunk_id"],
                        chunk["doc_id"],
                        chunk["text"],
                        chunk["source_file"],
                        chunk["section_header"],
                        chunk["page_number"],
                        chunk["chunk_index"],
                        chunk["content_hash"],
                        json.dumps(chunk["tags"]),
                    )
                    for chunk in chunks
                ],
            )
            self.connection.executemany(
                """
                INSERT OR REPLACE INTO chunk_vectors (chunk_id, embedding)
                VALUES (?, vec_f32(?))
                """,
                [
                    (chunk["chunk_id"], sqlite_vec.serialize_float32(vector))
                    for chunk, vector in zip(chunks, vectors, strict=True)
                ],
            )

    def search_document(
        self,
        query_vector: list[float],
        top_k: int = 5,
        doc_id: str | None = None,
    ) -> list[sqlite3.Row]:
        """Top-k nearest chunks joined with their metadata.

        ``doc_id`` optionally restricts the search to a single document.
        """
        serialized = sqlite_vec.serialize_float32(query_vector)
        cursor = self.connection.execute(
            """
            WITH knn_matches AS (
                SELECT chunk_id, distance
                FROM chunk_vectors
                WHERE embedding MATCH ?
                  AND k = ?
            )
            SELECT
                c.*,
                knn_matches.distance AS score
            FROM knn_matches
            JOIN chunks AS c ON c.chunk_id = knn_matches.chunk_id
            WHERE (? IS NULL OR c.doc_id = ?)
            ORDER BY knn_matches.distance
            """,
            (serialized, top_k, doc_id, doc_id),
        )
        return cursor.fetchall()

    def delete_by_document(self, doc_id: str) -> None:
        """Removes a document, its chunks and their vectors."""
        with self.connection:
            chunk_ids = [
                row["chunk_id"]
                for row in self.connection.execute(
                    "SELECT chunk_id FROM chunks WHERE doc_id = ?", (doc_id,)
                ).fetchall()
            ]
            if chunk_ids:
                placeholders = ",".join("?" for _ in chunk_ids)
                self.connection.execute(
                    f"DELETE FROM chunk_vectors WHERE chunk_id IN ({placeholders})",
                    chunk_ids,
                )
            self.connection.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
            self.connection.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))

    # =========================================================================
    # Lifecycle
    # =========================================================================
    def close(self) -> None:
        """Closes the underlying connection."""
        self.connection.close()
