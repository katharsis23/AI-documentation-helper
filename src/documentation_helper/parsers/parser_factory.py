from src.documentation_helper.parsers.md_parser import MDParser
from src.documentation_helper.parsers.pdf_parser import PDFParser


class ParserFactory:
    """Chooses the parsing strategy by choosing the appropriate parser"""

    _PARSERS = {
        ".md": MDParser,
        ".markdown": MDParser,
        ".pdf": PDFParser,
    }

    def get_parser(self, file_ext: str):
        ext = file_ext.lower()
        if not ext.startswith("."):
            ext = f".{ext}"

        parser_cls = self._PARSERS.get(ext)
        if parser_cls is None:
            raise ValueError(f"Unsupported file extension: {file_ext!r}")

        return parser_cls()
