"""FastAPI application entry point.

Builds the process-wide singletons (vector storage + RAG pipeline) during the
``startup`` event and stores them on ``app.state`` so every request handler can
reach them without global mutable state.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.documentation_helper.api.router import router
from src.documentation_helper.chunker.md_header_chunker import MarkdownHeaderChunker
from src.documentation_helper.config import config
from src.documentation_helper.embedding_provider import LocalEmbeddingProvider
from src.documentation_helper.llm.llm_factory import get_llm_provider
from src.documentation_helper.llm.prompt_builder import PromptBuilder
from src.documentation_helper.parsers.parser_factory import ParserFactory
from src.documentation_helper.rag_pipeline import RAGPipeline
from src.documentation_helper.storage.storage_manager import StorageManager


def _build_embedding_provider() -> LocalEmbeddingProvider:
    """Builds the embedding provider selected by ``config.embedding_provider``.

    Embeddings are wired independently from generation: they may target a
    different server/model (e.g. chat via DeepSeek, embeddings via a local
    Ollama with ``bge-m3``). A chat model cannot produce embeddings, so it must
    never be reused for this purpose.
    """
    backend = get_llm_provider(
        provider_name=config.embedding_provider,
        url=config.embedding_base_url,
        model=config.active_embedding_model,
        api_key=config.embedding_api_key,
    )
    if not hasattr(backend, "post_embedding"):
        raise ValueError(
            f"Embedding provider {config.embedding_provider!r} does not support "
            "embeddings (missing `post_embedding`)"
        )
    return LocalEmbeddingProvider(
        model_name=config.active_embedding_model,
        backend=backend,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Builds the singletons once and tears them down on shutdown."""
    storage = StorageManager()
    llm_provider = get_llm_provider(
        provider_name=config.ai_provider,
        url=config.active_base_url,
        model=config.active_model,
        api_key=config.deepseek_api_key,
    )
    embedding_provider = _build_embedding_provider()

    app.state.storage = storage
    app.state.pipeline = RAGPipeline(
        config=config,
        parser_factory=ParserFactory(),
        chunker=MarkdownHeaderChunker(),
        embedding_provider=embedding_provider,
        vector_store=storage,
        llm_provider=llm_provider,
        prompt_builder=PromptBuilder,
    )

    yield

    storage.close()


app = FastAPI(
    debug=True,
    title="Ai documentation Helper lightweight server",
    default_response_class=JSONResponse,
    version="0.0.1",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=True,
)

app.include_router(router)


@app.get(path="/", description="Healthcheck router", response_class=JSONResponse)
async def healthcheck() -> JSONResponse:
    return JSONResponse(
        content={"msg": "The server is healthy", "healthy": True}, status_code=200
    )
