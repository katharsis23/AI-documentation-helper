"""Tests for :class:`documentation_helper.rag_pipeline.RAGPipeline`.

The pipeline is exercised with lightweight fakes for every collaborator, so
the tests stay fast and free of network access.
"""

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from src.documentation_helper.protocols.chunker import Chunk, SearchResult
from src.documentation_helper.protocols.llm import LLMResponse
from src.documentation_helper.protocols.model import (
    IngestResult,
    QueryResponse,
    SourceReference,
)
from src.documentation_helper.protocols.parsers import ParsedDocument
from src.documentation_helper.rag_pipeline import RAGPipeline

# =========================================================================
# Fakes
# =========================================================================


class FakeParserFactory:
    def __init__(self, document: ParsedDocument):
        self.document = document
        self.requested_extensions: list[str] = []

    def get_parser(self, file_ext: str):
        self.requested_extensions.append(file_ext)
        document = self.document

        class _Parser:
            def parse(self, file_path: str) -> ParsedDocument:
                return document

        return _Parser()


class FakeChunker:
    def __init__(self, chunks: list[Chunk]):
        self._chunks = chunks
        self.received: ParsedDocument | None = None

    def split(self, document: ParsedDocument) -> list[Chunk]:
        self.received = document
        return self._chunks


class FakeEmbeddingProvider:
    def __init__(self):
        self.embedded: list[list[str]] = []
        self.queries: list[str] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.embedded.append(texts)
        return [[float(len(text))] * 2 for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return [1.0, 1.0]


class FakeVectorStore:
    def __init__(self, results: list[SearchResult] | None = None):
        self.added: dict | None = None
        self.search_calls: list[dict] = []
        self._results = results or []

    def add(self, chunks, vectors, doc_id, filename) -> None:
        self.added = {
            "chunks": chunks,
            "vectors": vectors,
            "doc_id": doc_id,
            "filename": filename,
        }

    def search(self, query_vector, top_k, filters) -> list[SearchResult]:
        self.search_calls.append(
            {"query_vector": query_vector, "top_k": top_k, "filters": filters}
        )
        return self._results


class FakeLLMProvider:
    def __init__(self, text: str = "Answer from the docs."):
        self.text = text
        self.prompts: list[str] = []

    async def query(self, prompt: str) -> LLMResponse:
        self.prompts.append(prompt)
        return LLMResponse(text=self.text, raw_response={})


class FakePromptBuilder:
    """Records the arguments it was constructed with and returns a marker."""

    calls: list[tuple[str, list[Chunk]]] = []

    def __init__(self, question: str, chunks: list[Chunk]):
        type(self).calls.append((question, chunks))
        self.question = question
        self.chunks = chunks

    def build(self) -> str:
        return f"PROMPT[{self.question}]"


# =========================================================================
# Fixtures / helpers
# =========================================================================


def _chunk(text: str = "text", section: str = "Heading") -> Chunk:
    chunk = Chunk(text=text, source_file="python-docs.md", section_header=section)
    chunk.calculate_hash()
    return chunk


@pytest.fixture(autouse=True)
def _reset_prompt_builder_calls():
    FakePromptBuilder.calls = []
    yield
    FakePromptBuilder.calls = []


def _make_pipeline(
    *,
    document: ParsedDocument | None = None,
    chunks: list[Chunk] | None = None,
    results: list[SearchResult] | None = None,
    llm_text: str = "Answer from the docs.",
):
    parser_factory = FakeParserFactory(
        document or ParsedDocument(raw_text="raw", source_file="doc.md")
    )
    chunker = FakeChunker(chunks if chunks is not None else [_chunk()])
    embedding_provider = FakeEmbeddingProvider()
    vector_store = FakeVectorStore(results)
    llm_provider = FakeLLMProvider(llm_text)

    pipeline = RAGPipeline(
        config=None,
        parser_factory=parser_factory,
        chunker=chunker,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        llm_provider=llm_provider,
        prompt_builder=FakePromptBuilder,
    )
    return {
        "pipeline": pipeline,
        "parser_factory": parser_factory,
        "chunker": chunker,
        "embedding_provider": embedding_provider,
        "vector_store": vector_store,
        "llm_provider": llm_provider,
    }


# =========================================================================
# Ingestion
# =========================================================================


async def test_ingest_returns_result_with_doc_id_and_count(tmp_path: Path):
    chunks = [_chunk("a"), _chunk("b")]
    deps = _make_pipeline(chunks=chunks)

    result = await deps["pipeline"].ingest_document(str(tmp_path / "doc.md"))

    assert isinstance(result, IngestResult)
    assert isinstance(result.doc_id, UUID)
    assert result.chunks_created == 2


async def test_ingest_uses_extension_to_pick_parser(tmp_path: Path):
    deps = _make_pipeline()

    await deps["pipeline"].ingest_document(str(tmp_path / "guide.pdf"))

    assert deps["parser_factory"].requested_extensions == [".pdf"]


async def test_ingest_embeds_chunk_texts_and_stores_them(tmp_path: Path):
    chunks = [_chunk("first"), _chunk("second")]
    deps = _make_pipeline(chunks=chunks)

    result = await deps["pipeline"].ingest_document(str(tmp_path / "doc.md"))

    assert deps["embedding_provider"].embedded == [["first", "second"]]
    added = deps["vector_store"].added
    assert added["chunks"] == chunks
    assert added["doc_id"] == str(result.doc_id)
    assert added["filename"] == "doc.md"
    assert len(added["vectors"]) == 2


async def test_ingest_honours_forced_doc_id(tmp_path: Path):
    forced = uuid4()
    deps = _make_pipeline()

    result = await deps["pipeline"].ingest_document(
        str(tmp_path / "doc.md"), doc_id=str(forced)
    )

    assert result.doc_id == forced
    assert deps["vector_store"].added["doc_id"] == str(forced)


async def test_ingest_without_chunks_skips_storage(tmp_path: Path):
    deps = _make_pipeline(chunks=[])

    result = await deps["pipeline"].ingest_document(str(tmp_path / "doc.md"))

    assert result.chunks_created == 0
    assert deps["vector_store"].added is None
    assert deps["embedding_provider"].embedded == []


# =========================================================================
# Querying
# =========================================================================


async def test_answer_query_returns_response_with_answer():
    results = [SearchResult(chunk=_chunk("ctx"), score=0.9)]
    deps = _make_pipeline(results=results, llm_text="The answer.")

    response = await deps["pipeline"].answer_query("What is Python?")

    assert isinstance(response, QueryResponse)
    assert response.answer == "The answer."


async def test_answer_query_embeds_the_question():
    deps = _make_pipeline()

    await deps["pipeline"].answer_query("How do I install it?")

    assert deps["embedding_provider"].queries == ["How do I install it?"]


async def test_answer_query_passes_top_k_and_filters_to_search():
    deps = _make_pipeline()

    await deps["pipeline"].answer_query("q", top_k=3, filters={"doc_id": "doc-1"})

    call = deps["vector_store"].search_calls[0]
    assert call["top_k"] == 3
    assert call["filters"] == {"doc_id": "doc-1"}


async def test_answer_query_builds_prompt_from_retrieved_chunks():
    chunk_a = _chunk("a", section="Install")
    chunk_b = _chunk("b", section="Usage")
    results = [
        SearchResult(chunk=chunk_a, score=0.8),
        SearchResult(chunk=chunk_b, score=0.5),
    ]
    deps = _make_pipeline(results=results)

    await deps["pipeline"].answer_query("How?")

    question, chunks = FakePromptBuilder.calls[0]
    assert question == "How?"
    assert chunks == [chunk_a, chunk_b]
    assert deps["llm_provider"].prompts == ["PROMPT[How?]"]


async def test_answer_query_maps_results_to_source_references():
    chunk = Chunk(
        text="ctx",
        source_file="k8s-docs.md",
        section_header="Workloads",
        page_number=4,
    )
    results = [SearchResult(chunk=chunk, score=0.87)]
    deps = _make_pipeline(results=results)

    response = await deps["pipeline"].answer_query("q")

    assert response.sources == [
        SourceReference(
            source_file="k8s-docs.md",
            section_header="Workloads",
            page_number=4,
            relevance_score=0.87,
        )
    ]


async def test_answer_query_with_no_results_still_answers():
    deps = _make_pipeline(results=[], llm_text="I cannot find information.")

    response = await deps["pipeline"].answer_query("unknown topic")

    assert response.sources == []
    assert response.answer == "I cannot find information."
    assert deps["llm_provider"].prompts == ["PROMPT[unknown topic]"]
