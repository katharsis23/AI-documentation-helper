"""The RAG orchestrator.

:class:`RAGPipeline` is the single class that wires the whole retrieval
augmented generation flow together. It depends only on the abstractions
(``ParserFactory``, ``Chunker``, ``EmbeddingProvider``, ``VectorStore``,
``LLMProvider``, ``PromptBuilder``) so that any concrete implementation can be
swapped without touching this file (see the project specification, section 4.7).

Two public entry points:

* :meth:`ingest_document` — parse → chunk → embed → store.
* :meth:`answer_query` — embed query → search → build prompt → generate.
"""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID, uuid4

from src.documentation_helper.config import Config
from src.documentation_helper.protocols.chunker import SearchResult
from src.documentation_helper.protocols.llm import LLMResponse
from src.documentation_helper.protocols.model import (
    IngestResult,
    QueryResponse,
    SourceReference,
)


class RAGPipeline:
    """Orchestrates document ingestion and question answering."""

    def __init__(
        self,
        config: Config,
        parser_factory,
        chunker,
        embedding_provider,
        vector_store,
        llm_provider,
        prompt_builder,
    ):
        self.config = config
        self.parser_factory = parser_factory
        self.chunker = chunker
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.llm_provider = llm_provider
        # ``prompt_builder`` is a class: it is instantiated per query with the
        # retrieved chunks, so the pipeline stores the type, not an instance.
        self.prompt_builder = prompt_builder

    # =========================================================================
    # Ingestion
    # =========================================================================
    async def ingest_document(
        self,
        file_path: str,
        metadata: dict[str, Any] | None = None,
        doc_id: str | None = None,
    ) -> IngestResult:
        """Parses, chunks, embeds and stores a single document.

        Args:
            file_path: path to the uploaded file (``.md`` or ``.pdf``).
            metadata: optional extra metadata (currently unused for storage).
            doc_id: optional id to force, otherwise a new UUID is generated.

        Returns:
            An :class:`IngestResult` holding the document id and the number of
            created chunks.
        """
        doc_id = str(doc_id or uuid4())
        filename = os.path.basename(file_path)

        extension = os.path.splitext(filename)[1]
        parser = self.parser_factory.get_parser(extension)
        document = parser.parse(file_path)

        chunks = self.chunker.split(document)

        if chunks:
            vectors = await self.embedding_provider.embed(
                [chunk.text for chunk in chunks]
            )
            self.vector_store.add(
                chunks=chunks,
                vectors=vectors,
                doc_id=doc_id,
                filename=filename,
            )

        return IngestResult(doc_id=UUID(doc_id), chunks_created=len(chunks))

    # =========================================================================
    # Querying
    # =========================================================================
    async def answer_query(
        self,
        question: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> QueryResponse:
        """Retrieves the most relevant chunks and asks the LLM to answer.

        Args:
            question: the user's natural-language question.
            top_k: number of chunks to retrieve.
            filters: optional storage filters (e.g. ``{"doc_id": "..."}``).

        Returns:
            A :class:`QueryResponse` with the answer and its source references.
        """
        query_vector = await self.embedding_provider.embed_query(question)

        results: list[SearchResult] = self.vector_store.search(
            query_vector=query_vector,
            top_k=top_k,
            filters=filters,
        )

        prompt = self.prompt_builder(question, [r.chunk for r in results]).build()
        response: LLMResponse = await self.llm_provider.query(prompt)

        return QueryResponse(
            answer=response.text,
            sources=[self._to_source_reference(result) for result in results],
        )

    # =========================================================================
    # Helpers
    # =========================================================================
    @staticmethod
    def _to_source_reference(result: SearchResult) -> SourceReference:
        chunk = result.chunk
        return SourceReference(
            source_file=chunk.source_file,
            section_header=chunk.section_header,
            page_number=chunk.page_number,
            relevance_score=result.score,
        )
