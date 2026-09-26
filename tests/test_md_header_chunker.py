"""Tests for the Markdown header chunker."""

import pytest

from src.documentation_helper.chunker.md_header_chunker import MarkdownHeaderChunker
from src.documentation_helper.protocols.chunker import Chunk
from src.documentation_helper.protocols.parsers import ParsedDocument, Section


@pytest.fixture
def parsed_document() -> ParsedDocument:
    raw_text = (
        "# Title\n\n"
        "Intro body.\n\n"
        "## Installation\n\n"
        "Install it.\n\n"
        "## Usage\n\n"
        "Use it.\n"
    )
    return ParsedDocument(
        raw_text=raw_text,
        source_file="python-docs.md",
        source_metadata={"source_file": "python-docs.md"},
        sections=[Section(heading="Title", text="Intro body.", level=1)],
    )


def test_split_returns_chunks(parsed_document: ParsedDocument) -> None:
    chunks = MarkdownHeaderChunker().split(parsed_document)

    assert chunks
    assert all(isinstance(chunk, Chunk) for chunk in chunks)


def test_one_chunk_per_section(parsed_document: ParsedDocument) -> None:
    chunks = MarkdownHeaderChunker().split(parsed_document)

    assert [chunk.section_header for chunk in chunks] == [
        "Title",
        "Installation",
        "Usage",
    ]
    assert [chunk.text for chunk in chunks] == ["Intro body.", "Install it.", "Use it."]


def test_chunk_index_is_sequential(parsed_document: ParsedDocument) -> None:
    chunks = MarkdownHeaderChunker().split(parsed_document)

    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_source_file_is_propagated(parsed_document: ParsedDocument) -> None:
    chunks = MarkdownHeaderChunker().split(parsed_document)

    assert all(chunk.source_file == "python-docs.md" for chunk in chunks)


def test_content_hash_is_populated(parsed_document: ParsedDocument) -> None:
    chunks = MarkdownHeaderChunker().split(parsed_document)

    for chunk in chunks:
        assert chunk.content_hash
        assert chunk.content_hash == chunk.calculate_hash()


def test_content_before_first_heading_is_kept_as_intro() -> None:
    document = ParsedDocument(raw_text="leading text\n\n# Heading\n\nbody\n")

    chunks = MarkdownHeaderChunker().split(document)

    assert chunks[0].section_header == "Intro"
    assert chunks[0].text == "leading text"


def test_long_block_is_split_with_overlap() -> None:
    long_block = "a" * 2500
    document = ParsedDocument(raw_text=f"# Big\n\n{long_block}\n")

    chunker = MarkdownHeaderChunker(max_chunk_size=1000, overlap=100)
    chunks = chunker.split(document)

    assert len(chunks) == 3
    assert all(len(chunk.text) <= 1000 for chunk in chunks)
    # Consecutive windows share exactly `overlap` characters.
    assert chunks[0].text[-100:] == chunks[1].text[:100]


def test_empty_document_produces_no_chunks() -> None:
    chunks = MarkdownHeaderChunker().split(ParsedDocument(raw_text="\n\n   \n"))

    assert chunks == []


@pytest.mark.parametrize(
    ("max_chunk_size", "overlap"),
    [(0, 0), (-1, 0), (100, -1), (100, 100), (100, 200)],
)
def test_invalid_parameters_raise(max_chunk_size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        MarkdownHeaderChunker(max_chunk_size=max_chunk_size, overlap=overlap)
