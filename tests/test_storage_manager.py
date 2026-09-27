"""Tests for the high-level :class:`StorageManager` facade."""

import pytest

from src.documentation_helper.protocols.chunker import Chunk, SearchResult
from src.documentation_helper.storage.storage_manager import StorageManager

DIM = 4


def _make_manager(tmp_path) -> StorageManager:
    return StorageManager(
        db_provider="sqlite",
        db_path=str(tmp_path / "store.db"),
        uploads_dir=str(tmp_path / "uploads"),
        embedding_dim=DIM,
    )


def _chunk(index: int, text: str = "text") -> Chunk:
    chunk = Chunk(
        text=text,
        source_file="python-docs.md",
        section_header="Heading",
        page_number=1,
        chunk_index=index,
    )
    chunk.calculate_hash()
    return chunk


def test_get_db_returns_sqlite_provider(tmp_path) -> None:
    from src.documentation_helper.storage.sqlite_provider import SQLiteProvider

    manager = _make_manager(tmp_path)
    try:
        assert isinstance(manager.get_db(), SQLiteProvider)
    finally:
        manager.close()


def test_get_db_is_cached(tmp_path) -> None:
    manager = _make_manager(tmp_path)
    try:
        assert manager.get_db() is manager.get_db()
    finally:
        manager.close()


def test_unknown_provider_raises(tmp_path) -> None:
    with pytest.raises(ValueError, match="Unknown DB provider"):
        StorageManager(
            db_provider="qdrant",
            db_path=str(tmp_path / "store.db"),
            embedding_dim=DIM,
        )


def test_add_and_list_roundtrip(tmp_path) -> None:
    manager = _make_manager(tmp_path)
    try:
        chunks = [_chunk(0, "a"), _chunk(1, "b")]
        manager.add(
            chunks,
            vectors=[[1.0, 1.0, 1.0, 1.0], [2.0, 2.0, 2.0, 2.0]],
            doc_id="doc-1",
            filename="python-docs.md",
        )

        documents = manager.list_documents()

        assert len(documents) == 1
        assert documents[0]["doc_id"] == "doc-1"
        assert documents[0]["chunk_count"] == 2
    finally:
        manager.close()


def test_add_rejects_mismatched_lengths(tmp_path) -> None:
    manager = _make_manager(tmp_path)
    try:
        with pytest.raises(ValueError, match="chunks but"):
            manager.add(
                [_chunk(0)],
                vectors=[[1.0, 1.0, 1.0, 1.0], [2.0, 2.0, 2.0, 2.0]],
                doc_id="doc-1",
                filename="python-docs.md",
            )
    finally:
        manager.close()


def test_search_returns_search_results(tmp_path) -> None:
    manager = _make_manager(tmp_path)
    try:
        chunks = [_chunk(0, "close"), _chunk(1, "far")]
        manager.add(
            chunks,
            vectors=[[1.0, 1.0, 1.0, 1.0], [9.0, 9.0, 9.0, 9.0]],
            doc_id="doc-1",
            filename="python-docs.md",
        )

        results = manager.search(
            [1.0, 1.0, 1.0, 1.0], top_k=2, filters={"doc_id": "doc-1"}
        )

        assert all(isinstance(result, SearchResult) for result in results)
        assert results[0].chunk.text == "close"
        assert results[0].score <= results[1].score
    finally:
        manager.close()


def test_search_without_filter_scans_all_documents(tmp_path) -> None:
    manager = _make_manager(tmp_path)
    try:
        for doc_id in ("doc-1", "doc-2"):
            manager.add(
                [_chunk(0, doc_id)],
                vectors=[[1.0, 1.0, 1.0, 1.0]],
                doc_id=doc_id,
                filename=f"{doc_id}.md",
            )

        results = manager.search([1.0, 1.0, 1.0, 1.0], top_k=5)

        assert {result.chunk.text for result in results} == {"doc-1", "doc-2"}
    finally:
        manager.close()


def test_delete_by_document(tmp_path) -> None:
    manager = _make_manager(tmp_path)
    try:
        manager.add(
            [_chunk(0)],
            vectors=[[1.0, 1.0, 1.0, 1.0]],
            doc_id="doc-1",
            filename="python-docs.md",
        )

        manager.delete_by_document("doc-1")

        assert manager.list_documents() == []
    finally:
        manager.close()


def test_get_path_to_documents_creates_dir(tmp_path) -> None:
    manager = _make_manager(tmp_path)
    try:
        path = manager.get_path_to_documents()

        assert path == str(tmp_path / "uploads")
        from pathlib import Path

        assert Path(path).is_dir()
    finally:
        manager.close()
