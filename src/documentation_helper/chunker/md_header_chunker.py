from src.documentation_helper.protocols.parsers import ParsedDocument


class MDHeaderChunker:
    """Splits markdowns by chunking in headers"""

    max_chunk_size: int
    overlap: int

    def split(self, document: ParsedDocument): ...
