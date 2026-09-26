class FixedSizeChunker:
    chunk_size: int
    overlap: int

    def split(self, document):
        ...
