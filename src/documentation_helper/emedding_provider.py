class LocalEmbeddingProvider:
    def __init__(
        self,
        model_name: str,
        model: object,
    ): ...

    def embed(self): ...

    def embed_query(self): ...
