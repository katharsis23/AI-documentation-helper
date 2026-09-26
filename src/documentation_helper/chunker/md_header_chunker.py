import os
import re

from src.documentation_helper.protocols.chunker import Chunk
from src.documentation_helper.protocols.parsers import ParsedDocument

# Matches Markdown ATX headings: `# Heading`, `## Heading`, ...
_HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$")


class MarkdownHeaderChunker:
    """Splits a Markdown document into chunks aligned with its headings.

    The algorithm walks the document line by line and groups the text that
    belongs to every heading into a logical block. Each block becomes one or
    more :class:`Chunk` objects:

    * a block shorter than ``max_chunk_size`` produces a single chunk;
    * a longer block is split into windows of ``max_chunk_size`` characters
      that share ``overlap`` characters so that context is not lost across
      the boundaries.
    """

    def __init__(self, max_chunk_size: int = 1000, overlap: int = 100):
        if max_chunk_size <= 0:
            raise ValueError("`max_chunk_size` must be a positive integer")
        if overlap < 0:
            raise ValueError("`overlap` must not be negative")
        if overlap >= max_chunk_size:
            raise ValueError("`overlap` must be smaller than `max_chunk_size`")

        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def split(self, document: ParsedDocument) -> list[Chunk]:
        chunks: list[Chunk] = []
        chunk_index = 0

        source_file = os.path.basename(
            document.source_file or document.source_metadata.get("source_file", "")
        )

        for header, block in self._iter_blocks(document.raw_text):
            for piece in self._split_block(block):
                chunks.append(
                    self._create_chunk(
                        text=piece,
                        source_file=source_file,
                        header=header,
                        index=chunk_index,
                    )
                )
                chunk_index += 1

        return chunks

    def _iter_blocks(self, raw_text: str) -> list[tuple[str, str]]:
        """Groups raw text into ``(heading, body)`` pairs.

        Text that appears before the first heading is returned under the
        ``"Intro"`` heading.
        """
        blocks: list[tuple[str, str]] = []
        current_header = "Intro"
        buffer: list[str] = []

        for line in raw_text.splitlines():
            match = _HEADER_PATTERN.match(line)
            if match:
                body = "\n".join(buffer).strip()
                if body:
                    blocks.append((current_header, body))
                buffer = []
                current_header = match.group(2).strip()
            else:
                buffer.append(line)

        body = "\n".join(buffer).strip()
        if body:
            blocks.append((current_header, body))

        return blocks

    def _split_block(self, text: str) -> list[str]:
        """Splits an oversized block into size-bounded, overlapping pieces."""
        if len(text) <= self.max_chunk_size:
            return [text]

        pieces: list[str] = []
        step = self.max_chunk_size - self.overlap
        for start in range(0, len(text), step):
            piece = text[start : start + self.max_chunk_size]
            if piece:
                pieces.append(piece)
            if start + self.max_chunk_size >= len(text):
                break
        return pieces

    def _create_chunk(
        self, text: str, source_file: str, header: str, index: int
    ) -> Chunk:
        chunk = Chunk(
            text=text,
            source_file=source_file,
            section_header=header,
            chunk_index=index,
        )
        chunk.calculate_hash()
        return chunk
