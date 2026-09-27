"""Tests for the low-level :class:`SQLiteProvider` (raw SQLite access)."""

import sqlite3

import pytest

from src.documentation_helper.storage.sqlite_provider import SQLiteProvider

DIM = 4


def _vector(seed: float) -> list[float]:
    return [seed, seed, seed, seed]


@pytest.fixture
def provider() -> SQLiteProvider:
    """An in-memory provider with a tiny embedding dimension."""
    db = SQLiteProvider(db_path=":memory:", embedding_dim=DIM)
    yield db
    db.close()


def test_schema_is_created(provider: SQLiteProvider) -> None:
    tables = {
        row["name"]
        for row in provider.connection.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
        ).fetchall()
    }
    assert {"documents", "chunks", "chunk_vectors"} <= tables


def test_add_and_list_document(provider: SQLiteProvider) -> None:
    provider.add_document("doc-1", "python-docs.md", "2024-01-01T00:00:00")

    documents = provider.list_documents()

    assert len(documents) == 1
    assert documents[0]["doc_id"] == "doc-1"
    assert documents[0]["filename"] == "python-docs.md"
    assert documents[0]["chunk_count"] == 0


def test_chunk_count_reflects_stored_chunks(provider: SQLiteProvider) -> None:
    provider.add_document("doc-1", "python-docs.md", "2024-01-01T00:00:00")
    chunks = [
        {
            "chunk_id": f"c{i}",
            "doc_id": "doc-1",
            "text": f"text {i}",
            "source_file": "python-docs.md",
            "section_header": "Heading",
            "page_number": 1,
            "chunk_index": i,
            "content_hash": f"hash{i}",
            "tags": {},
        }
        for i in range(3)
    ]
    provider.add_document_chunks(chunks, [_vector(0.1 * i) for i in range(3)])

    documents = provider.list_documents()

    assert documents[0]["chunk_count"] == 3


def test_search_returns_nearest_first(provider: SQLiteProvider) -> None:
    provider.add_document("doc-1", "python-docs.md", "2024-01-01T00:00:00")
    chunks = [
        {
            "chunk_id": f"c{i}",
            "doc_id": "doc-1",
            "text": f"text {i}",
            "source_file": "python-docs.md",
            "section_header": "Heading",
            "page_number": 1,
            "chunk_index": i,
            "content_hash": f"hash{i}",
            "tags": {},
        }
        for i in range(2)
    ]
    # c0 is very close to the query vector, c1 is far away.
    provider.add_document_chunks(chunks, [[1.0, 1.0, 1.0, 1.0], [9.0, 9.0, 9.0, 9.0]])

    results = provider.search_document([1.0, 1.0, 1.0, 1.0], top_k=2, doc_id="doc-1")

    assert results[0]["chunk_id"] == "c0"
    assert results[0]["score"] <= results[1]["score"]


def test_search_can_be_scoped_to_doc(provider: SQLiteProvider) -> None:
    for doc_id in ("doc-1", "doc-2"):
        provider.add_document(doc_id, f"{doc_id}.md", "2024-01-01T00:00:00")
        provider.add_document_chunks(
            [
                {
                    "chunk_id": f"{doc_id}-c0",
                    "doc_id": doc_id,
                    "text": "text",
                    "source_file": f"{doc_id}.md",
                    "section_header": "H",
                    "page_number": 1,
                    "chunk_index": 0,
                    "content_hash": "h",
                    "tags": {},
                }
            ],
            [[1.0, 1.0, 1.0, 1.0]],
        )

    results = provider.search_document([1.0, 1.0, 1.0, 1.0], top_k=5, doc_id="doc-2")

    assert [r["doc_id"] for r in results] == ["doc-2"]


def test_delete_by_document_removes_everything(provider: SQLiteProvider) -> None:
    provider.add_document("doc-1", "python-docs.md", "2024-01-01T00:00:00")
    provider.add_document_chunks(
        [
            {
                "chunk_id": "c0",
                "doc_id": "doc-1",
                "text": "text",
                "source_file": "python-docs.md",
                "section_header": "H",
                "page_number": 1,
                "chunk_index": 0,
                "content_hash": "h",
                "tags": {},
            }
        ],
        [[1.0, 1.0, 1.0, 1.0]],
    )

    provider.delete_by_document("doc-1")

    assert provider.list_documents() == []
    assert provider.search_document([1.0, 1.0, 1.0, 1.0], top_k=5) == []


def test_persists_to_file(tmp_path) -> None:
    db_file = tmp_path / "store.db"
    first = SQLiteProvider(db_path=str(db_file), embedding_dim=DIM)
    first.add_document("doc-1", "python-docs.md", "2024-01-01T00:00:00")
    first.close()

    second = SQLiteProvider(db_path=str(db_file), embedding_dim=DIM)
    try:
        assert second.list_documents()[0]["doc_id"] == "doc-1"
    finally:
        second.close()


def test_exposes_sqlite_connection(provider: SQLiteProvider) -> None:
    assert isinstance(provider.connection, sqlite3.Connection)
