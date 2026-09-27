"""Tests for :class:`documentation_helper.embedding_provider.LocalEmbeddingProvider`."""


from src.documentation_helper.embedding_provider import LocalEmbeddingProvider


class SingleOnlyBackend:
    """Backend that only implements per-text embedding."""

    def __init__(self):
        self.calls: list[str] = []

    async def post_embedding(self, text: str) -> list[float]:
        self.calls.append(text)
        return [float(len(text))]


class BatchBackend:
    """Backend implementing the optional batch method."""

    def __init__(self):
        self.batch_calls: list[list[str]] = []
        self.single_calls: list[str] = []

    async def post_embedding(self, text: str) -> list[float]:
        self.single_calls.append(text)
        return [0.0]

    async def post_embeddings(self, texts: list[str]) -> list[list[float]]:
        self.batch_calls.append(list(texts))
        return [[float(i)] for i in range(len(texts))]


async def test_embed_uses_batch_method_when_available():
    backend = BatchBackend()
    provider = LocalEmbeddingProvider(model_name="nomic", backend=backend)

    vectors = await provider.embed(["a", "bb", "ccc"])

    assert vectors == [[0.0], [1.0], [2.0]]
    assert backend.batch_calls == [["a", "bb", "ccc"]]
    assert backend.single_calls == []


async def test_embed_falls_back_to_per_text_method():
    backend = SingleOnlyBackend()
    provider = LocalEmbeddingProvider(model_name="mini", backend=backend)

    vectors = await provider.embed(["a", "bb"])

    assert vectors == [[1.0], [2.0]]
    assert backend.calls == ["a", "bb"]


async def test_embed_empty_list_returns_empty():
    provider = LocalEmbeddingProvider(model_name="mini", backend=BatchBackend())

    assert await provider.embed([]) == []


async def test_embed_query_uses_single_method():
    backend = SingleOnlyBackend()
    provider = LocalEmbeddingProvider(model_name="mini", backend=backend)

    vector = await provider.embed_query("hello")

    assert vector == [5.0]
    assert backend.calls == ["hello"]
