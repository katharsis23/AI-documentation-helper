"""Tests for :class:`documentation_helper.parsers.parser_factory.ParserFactory`."""

import pytest

from src.documentation_helper.parsers.md_parser import MDParser
from src.documentation_helper.parsers.parser_factory import ParserFactory
from src.documentation_helper.parsers.pdf_parser import PDFParser


@pytest.mark.parametrize("ext", [".md", "md", ".markdown", ".MD", "md"])
def test_markdown_extensions_return_md_parser(ext: str) -> None:
    assert isinstance(ParserFactory().get_parser(ext), MDParser)


@pytest.mark.parametrize("ext", [".pdf", "pdf", ".PDF"])
def test_pdf_extension_returns_pdf_parser(ext: str) -> None:
    assert isinstance(ParserFactory().get_parser(ext), PDFParser)


def test_unsupported_extension_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported file extension"):
        ParserFactory().get_parser(".docx")
