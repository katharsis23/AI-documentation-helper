from typing import Protocol

from pydantic import BaseModel


class IDocumentParser(Protocol):
    """Unified protocol that makes sure we have similar API's for MD and PDF parsers"""

    ...


class ParsedDocument(BaseModel):
    """Model that describes the output of parser"""

    raw_text: str
    source_metadata: dict
    sections: list


class Section(BaseModel):
    heading: str
    text: str
    page_number: int
    level: int
