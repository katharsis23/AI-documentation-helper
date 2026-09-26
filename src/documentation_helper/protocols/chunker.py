from hashlib import sha256
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel


class IChunker(Protocol):
    """Split documents into chunks"""

    ...


class Chunk(BaseModel):
    chunk_id: uuid4
    text: str
    source_file: str
    section_header: str
    page_number: int
    chunk_index: int
    content_hash: sha256
    tags: dict


class SearchResult(BaseModel):
    chunk: Chunk
    score: float
