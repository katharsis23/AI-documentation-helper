"""HTTP routes for the documentation assistant.

All handlers depend on the singletons built during the FastAPI ``startup``
event and stored on ``request.app.state`` (``state.pipeline`` and
``state.storage``). Responses are the Pydantic models from
:mod:`src.documentation_helper.protocols.model`.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, UploadFile, status

from src.documentation_helper.protocols.model import (
    DocumentInfo,
    DocumentUploadResponse,
    QueryRequest,
    QueryResponse,
)

router = APIRouter()


def _storage(request: Request):
    return request.app.state.storage


def _pipeline(request: Request):
    return request.app.state.pipeline


@router.post(
    path="/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    description="Upload a Markdown/PDF file and index it.",
)
async def upload_document(
    request: Request,
    file: UploadFile,
) -> DocumentUploadResponse:
    storage = _storage(request)
    pipeline = _pipeline(request)

    filename = Path(file.filename or "upload").name
    uploads_dir = Path(storage.get_path_to_documents())
    destination = uploads_dir / filename

    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        result = await pipeline.ingest_document(str(destination))
    except ValueError as exc:
        # e.g. unsupported extension
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return DocumentUploadResponse(
        doc_id=result.doc_id,
        status="indexed",
        chunks_created=result.chunks_created,
    )


@router.get(
    path="/documents",
    response_model=list[DocumentInfo],
    description="List every indexed document.",
)
async def list_documents(request: Request) -> list[DocumentInfo]:
    storage = _storage(request)
    return [DocumentInfo(**row) for row in storage.list_documents()]


@router.delete(
    path="/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete a document and all of its chunks.",
)
async def delete_document(request: Request, doc_id: UUID) -> None:
    storage = _storage(request)

    known_ids = {str(row["doc_id"]) for row in storage.list_documents()}
    if str(doc_id) not in known_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )

    storage.delete_by_document(str(doc_id))


@router.post(
    path="/query",
    response_model=QueryResponse,
    description="Ask a question and get an answer with source references.",
)
async def query(request: Request, payload: QueryRequest) -> QueryResponse:
    pipeline = _pipeline(request)
    return await pipeline.answer_query(
        question=payload.question,
        top_k=payload.top_k,
        filters=payload.filters or None,
    )
