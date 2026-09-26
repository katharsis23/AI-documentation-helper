class FixedSizeChunker:
    chunk_size: int
    overlap: int

    def split(self, document):
        raise NotImplementedError("Fixed Size Chunker is not implemented yet")
