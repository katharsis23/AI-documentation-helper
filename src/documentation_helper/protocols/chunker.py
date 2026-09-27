from hashlib import sha256
from typing import Any, Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.documentation_helper.protocols.parsers import ParsedDocument


class Chunk(BaseModel):
    chunk_id: UUID = Field(default_factory=uuid4)
    text: str
    source_file: str
    section_header: str = ""
    page_number: int = 1
    chunk_index: int = 0
    content_hash: str = ""
    tags: dict[str, Any] = Field(default_factory=dict)

    def calculate_hash(self) -> str:
        """Generates SHA-256 hash by content"""
        self.content_hash = sha256(self.text.encode("utf-8")).hexdigest()
        return self.content_hash


class SearchResult(BaseModel):
    chunk: Chunk
    score: float


class IChunker(Protocol):
    """Protocol to chunk the files"""

    def split(self, document: ParsedDocument) -> list[Chunk]: ...
