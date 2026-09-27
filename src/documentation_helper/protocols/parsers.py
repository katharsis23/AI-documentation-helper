from typing import Protocol

from pydantic import BaseModel, Field


class IDocumentParser(Protocol):
    """Unified protocol that makes sure we have similar API's for MD and PDF parsers"""

    def parse(self, filepath: str) -> "ParsedDocument": ...


class Section(BaseModel):
    """A single logical section of a document, tied to a heading/page."""

    heading: str
    text: str
    page_number: int = 1
    level: int = 1


class ParsedDocument(BaseModel):
    """Model that describes the output of parser"""

    raw_text: str
    source_file: str = ""
    source_metadata: dict = Field(default_factory=dict)
    sections: list[Section] = Field(default_factory=list)
