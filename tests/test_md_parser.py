"""Tests for :class:`documentation_helper.parsers.md_parser.MDParser`."""

from pathlib import Path

import pytest

from src.documentation_helper.parsers.md_parser import MDParser
from src.documentation_helper.protocols.parsers import ParsedDocument


def test_parse_returns_parsed_document(sample_md_file: Path) -> None:
    document = MDParser().parse(str(sample_md_file))

    assert isinstance(document, ParsedDocument)
    assert document.raw_text == sample_md_file.read_text(encoding="utf-8")


def test_source_file_is_just_the_basename(sample_md_file: Path) -> None:
    document = MDParser().parse(str(sample_md_file))

    assert document.source_file == "sample.md"


def test_source_metadata_contains_extension(sample_md_file: Path) -> None:
    document = MDParser().parse(str(sample_md_file))

    assert document.source_metadata["extension"] == ".md"
    assert document.source_metadata["source_file"] == str(sample_md_file)


def test_sections_are_extracted_by_heading(sample_md_file: Path) -> None:
    document = MDParser().parse(str(sample_md_file))

    headings = [section.heading for section in document.sections]
    # A heading with no body (e.g. ``# Notes``) is skipped; nested headings
    # that do have a body are kept.
    assert headings == [
        "Python Documentation",
        "Installation",
        "Windows",
        "Linux",
        "Usage",
        "Nested",
    ]


def test_section_levels_match_heading_depth(sample_md_file: Path) -> None:
    document = MDParser().parse(str(sample_md_file))

    levels = {section.heading: section.level for section in document.sections}
    assert levels["Python Documentation"] == 1
    assert levels["Installation"] == 2
    assert levels["Windows"] == 3
    assert levels["Nested"] == 3


def test_section_text_does_not_include_the_heading(sample_md_file: Path) -> None:
    document = MDParser().parse(str(sample_md_file))

    installation = next(s for s in document.sections if s.heading == "Installation")
    assert installation.text == "Install Python from python.org."
    assert not installation.text.startswith("#")


def test_empty_heading_body_is_skipped(tmp_path: Path) -> None:
    file_path = tmp_path / "empty_sections.md"
    file_path.write_text(
        "# Title\n\nbody\n\n## Empty\n\n## Filled\n\nbody\n", encoding="utf-8"
    )

    document = MDParser().parse(str(file_path))

    headings = [section.heading for section in document.sections]
    assert "Empty" not in headings
    assert headings == ["Title", "Filled"]


def test_text_before_first_heading_is_captured_as_intro(tmp_path: Path) -> None:
    file_path = tmp_path / "intro.md"
    file_path.write_text("preamble text\n\n# Title\n\nbody\n", encoding="utf-8")

    document = MDParser().parse(str(file_path))

    assert document.sections[0].heading == "Intro"
    assert document.sections[0].text == "preamble text"


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        MDParser().parse(str(tmp_path / "does-not-exist.md"))

