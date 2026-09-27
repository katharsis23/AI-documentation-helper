import datetime
from uuid import UUID

from pydantic import BaseModel


# ====== Query =========
class QueryResponse(BaseModel):
    answer: str
    sources: list  # List of Source References


class SourceReference(BaseModel):
    source_file: str
    section_header: str
    page_number: int
    relevance_score: float


# ========= Ingest ==========


class IngestResult(BaseModel):
    doc_id: UUID
    chunks_created: int


# ======== Responses ========


class DocumentUploadResponse(BaseModel):
    doc_id: UUID
    status: str
    chunks_created: int


# ======== Requests =========
class QueryRequest(BaseModel):
    question: str
    top_k: int
    filters: dict


class DocumentInfo(BaseModel):
    doc_id: UUID
    filename: str
    uploaded_at: datetime
    chunk_count: int
