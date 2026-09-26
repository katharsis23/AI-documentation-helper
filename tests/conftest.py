"""Shared pytest fixtures."""

from pathlib import Path

import pytest

SAMPLE_MD = """\
# Python Documentation

Welcome to the Python documentation.

## Installation

Install Python from python.org.

### Windows

Download the installer and run it.

### Linux

Use your package manager.

## Usage

Run scripts with ``python script.py``.

## Notes

### Nested

Some nested notes.
"""


@pytest.fixture
def sample_md_text() -> str:
    """A small, self-contained Markdown document as a string."""
    return SAMPLE_MD


@pytest.fixture
def sample_md_file(tmp_path: Path, sample_md_text: str) -> Path:
    """Writes :data:`SAMPLE_MD` to a temp file and returns its path."""
    file_path = tmp_path / "sample.md"
    file_path.write_text(sample_md_text, encoding="utf-8")
    return file_path