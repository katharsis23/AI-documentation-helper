import os
import re

from src.documentation_helper.protocols.parsers import ParsedDocument, Section

# Matches Markdown ATX headings and captures the leading `#`s and the title.
_HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$")


class MDParser:
    """Parses Markdown files into a :class:`ParsedDocument`.

    The document is split into :class:`Section` objects by ``#``, ``##``,
    ``###`` (up to six levels) headings, which allows the chunker and the
    final answer to reference a specific section.
    """

    def parse(self, filepath: str) -> ParsedDocument:
        with open(filepath, encoding="utf-8") as file:
            raw_text = file.read()

        source_file = os.path.basename(filepath)

        return ParsedDocument(
            raw_text=raw_text,
            source_file=source_file,
            source_metadata={"source_file": filepath, "extension": ".md"},
            sections=self._extract_sections(raw_text),
        )

    def _extract_sections(self, raw_text: str) -> list[Section]:
        sections: list[Section] = []
        current_heading = "Intro"
        current_level = 0
        buffer: list[str] = []

        def flush() -> None:
            body = "\n".join(buffer).strip()
            if body:
                sections.append(
                    Section(
                        heading=current_heading,
                        text=body,
                        page_number=1,
                        level=current_level,
                    )
                )

        for line in raw_text.splitlines():
            match = _HEADER_PATTERN.match(line)
            if match:
                flush()
                buffer = []
                current_level = len(match.group(1))
                current_heading = match.group(2).strip()
            else:
                buffer.append(line)

        flush()
        return sections
