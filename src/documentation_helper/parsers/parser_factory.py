class ParserFactory:
    """Chooses the parsing strategy by choosing the appropriate parser"""
    def get_parser(self, file_ext: str):
        ...
