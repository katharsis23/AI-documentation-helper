from pydantic import BaseModel
from uuid import uuid4


# ====== Query =========
class QueryResponse(BaseModel):
    answer: str
    sources: list   # List of Source References


class SourceReference(BaseModel):
    source_file: str
    section_header: str
    page_number: int
    relevance_score: float



# ========= Ingest ==========

class IngestResult(BaseModel):
    doc_id: uuid4
    chunks_created: int

