"""Tests for the HTTP routes in :mod:`documentation_helper.api.router`.

The app is exercised through ``fastapi.testclient.TestClient``. The heavy
singletons (pipeline / storage) are replaced with in-memory fakes so no model,
network or disk is involved.
"""

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.documentation_helper.main import app
from src.documentation_helper.protocols.model import (
    IngestResult,
    QueryResponse,
    SourceReference,
)


class FakePipeline:
    def __init__(self):
        self.ingest_calls: list[str] = []
        self.query_calls: list[dict] = []
        self.answer = "The answer."
        self.sources: list[SourceReference] = []
        self.ingest_result = IngestResult(doc_id=uuid4(), chunks_created=3)
        self.raise_on_ingest: Exception | None = None

    async def ingest_document(self, file_path: str, metadata=None) -> IngestResult:
        self.ingest_calls.append(file_path)
        if self.raise_on_ingest is not None:
            raise self.raise_on_ingest
        return self.ingest_result

    async def answer_query(self, question, top_k, filters) -> QueryResponse:
        self.query_calls.append(
            {"question": question, "top_k": top_k, "filters": filters}
        )
        return QueryResponse(answer=self.answer, sources=self.sources)


class FakeStorage:
    def __init__(self, uploads_dir: Path, documents: list[dict] | None = None):
        self.uploads_dir = uploads_dir
        self.documents = documents or []
        self.deleted: list[str] = []

    def get_path_to_documents(self) -> str:
        return str(self.uploads_dir)

    def list_documents(self) -> list[dict]:
        return self.documents

    def delete_by_document(self, doc_id: str) -> None:
        self.deleted.append(doc_id)
        self.documents = [d for d in self.documents if d["doc_id"] != doc_id]


@pytest.fixture
def client(tmp_path: Path):
    """A TestClient with fake pipeline/storage bound to ``app.state``.

    ``lifespan`` is disabled (``with TestClient`` is not used) so the real
    ``StorageManager``/LLM wiring is never built during tests.
    """
    pipeline = FakePipeline()
    storage = FakeStorage(uploads_dir=tmp_path / "uploads")
    (tmp_path / "uploads").mkdir(parents=True, exist_ok=True)

    app.state.pipeline = pipeline
    app.state.storage = storage

    test_client = TestClient(app)
    test_client.fake_pipeline = pipeline
    test_client.fake_storage = storage
    yield test_client


# =========================================================================
# Upload
# =========================================================================


def test_upload_document_saves_file_and_returns_response(client: TestClient):
    response = client.post(
        "/documents",
        files={"file": ("guide.md", b"# Title\n\nbody", "text/markdown")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "indexed"
    assert body["chunks_created"] == 3
    assert body["doc_id"] == str(client.fake_pipeline.ingest_result.doc_id)
    # The uploaded file was persisted to the uploads directory.
    assert (client.fake_storage.uploads_dir / "guide.md").exists()


def test_upload_calls_pipeline_with_saved_path(client: TestClient):
    client.post("/documents", files={"file": ("guide.md", b"body", "text/markdown")})

    assert client.fake_pipeline.ingest_calls == [
        str(client.fake_storage.uploads_dir / "guide.md")
    ]


def test_upload_unsupported_extension_returns_400(client: TestClient):
    client.fake_pipeline.raise_on_ingest = ValueError(
        "Unsupported file extension: '.docx'"
    )

    response = client.post(
        "/documents", files={"file": ("bad.docx", b"data", "application/octet-stream")}
    )

    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


# =========================================================================
# List
# =========================================================================


def test_list_documents_returns_models(client: TestClient):
    doc_id = uuid4()
    client.fake_storage.documents = [
        {
            "doc_id": str(doc_id),
            "filename": "python-docs.md",
            "uploaded_at": "2024-01-01T00:00:00",
            "chunk_count": 5,
        }
    ]

    response = client.get("/documents")

    assert response.status_code == 200
    body = response.json()
    assert body == [
        {
            "doc_id": str(doc_id),
            "filename": "python-docs.md",
            "uploaded_at": "2024-01-01T00:00:00",
            "chunk_count": 5,
        }
    ]


def test_list_documents_empty(client: TestClient):
    response = client.get("/documents")

    assert response.status_code == 200
    assert response.json() == []


# =========================================================================
# Delete
# =========================================================================


def test_delete_existing_document(client: TestClient):
    doc_id = uuid4()
    client.fake_storage.documents = [
        {
            "doc_id": str(doc_id),
            "filename": "x.md",
            "uploaded_at": "2024-01-01T00:00:00",
            "chunk_count": 1,
        }
    ]

    response = client.delete(f"/documents/{doc_id}")

    assert response.status_code == 204
    assert client.fake_storage.deleted == [str(doc_id)]


def test_delete_unknown_document_returns_404(client: TestClient):
    response = client.delete(f"/documents/{uuid4()}")

    assert response.status_code == 404


def test_delete_invalid_uuid_returns_422(client: TestClient):
    response = client.delete("/documents/not-a-uuid")

    assert response.status_code == 422


# =========================================================================
# Query
# =========================================================================


def test_query_returns_answer_and_sources(client: TestClient):
    client.fake_pipeline.answer = "Create a Deployment with a YAML manifest."
    client.fake_pipeline.sources = [
        SourceReference(
            source_file="k8s-docs.md",
            section_header="Workloads",
            page_number=1,
            relevance_score=0.87,
        )
    ]

    response = client.post(
        "/query",
        json={"question": "How do I create a Deployment?", "top_k": 5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Create a Deployment with a YAML manifest."
    assert body["sources"][0]["source_file"] == "k8s-docs.md"
    assert body["sources"][0]["relevance_score"] == 0.87


def test_query_forwards_question_top_k_and_filters(client: TestClient):
    client.post(
        "/query",
        json={"question": "q", "top_k": 3, "filters": {"doc_id": "doc-1"}},
    )

    call = client.fake_pipeline.query_calls[0]
    assert call["question"] == "q"
    assert call["top_k"] == 3
    assert call["filters"] == {"doc_id": "doc-1"}


def test_query_requires_question(client: TestClient):
    response = client.post("/query", json={"top_k": 5})

    assert response.status_code == 422


def test_query_missing_filters_defaults_to_none(client: TestClient):
    client.post("/query", json={"question": "q"})

    assert client.fake_pipeline.query_calls[0]["filters"] is None


# =========================================================================
# Healthcheck
# =========================================================================


def test_healthcheck(client: TestClient):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["healthy"] is True
