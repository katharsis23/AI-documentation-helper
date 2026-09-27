"""Tests for :class:`documentation_helper.llm.ollama_provider.OllamaProvider`.

The HTTP layer is replaced with ``httpx.MockTransport`` so the tests assert the
exact requests the provider builds (endpoint, payload shape) without touching
the network. Both the modern ``/api/embed`` and the legacy ``/api/embeddings``
code paths are covered, including the automatic fallback.
"""

import json

import httpx
import pytest

from src.documentation_helper.llm.ollama_provider import OllamaProvider

BASE_URL = "http://localhost:11434"


class RecordingTransport(httpx.MockTransport):
    """Mock transport that records every request and replies via a handler."""

    def __init__(self, handler):
        self.requests: list[httpx.Request] = []
        super().__init__(self._handle)
        self._handler = handler

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._handler(request)


@pytest.fixture
def make_provider(monkeypatch):
    """Returns a factory building a provider wired to a mock transport."""

    def _factory(handler):
        transport = RecordingTransport(handler)
        original_client = httpx.AsyncClient

        def patched_client(*args, **kwargs):
            kwargs["transport"] = transport
            return original_client(*args, **kwargs)

        monkeypatch.setattr(httpx, "AsyncClient", patched_client)
        provider = OllamaProvider(url=BASE_URL, model="bge-m3", api_key=None)
        return provider, transport

    return _factory


# =========================================================================
# Modern /api/embed path
# =========================================================================


async def test_post_embedding_hits_api_embed_with_input_field(make_provider):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2, 0.3]]})

    provider, transport = make_provider(handler)

    vector = await provider.post_embedding("hello")

    assert vector == [0.1, 0.2, 0.3]
    request = transport.requests[0]
    assert request.url.path == "/api/embed"
    payload = json.loads(request.content)
    assert payload["input"] == ["hello"]
    assert "prompt" not in payload
    assert payload["model"] == "bge-m3"


async def test_post_embeddings_sends_batch_of_inputs(make_provider):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"embeddings": [[1.0], [2.0], [3.0]]})

    provider, transport = make_provider(handler)

    vectors = await provider.post_embeddings(["a", "b", "c"])

    assert vectors == [[1.0], [2.0], [3.0]]
    assert len(transport.requests) == 1
    payload = json.loads(transport.requests[0].content)
    assert payload["input"] == ["a", "b", "c"]


async def test_post_embeddings_splits_large_batches(make_provider):
    calls: list[list[str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        calls.append(payload["input"])
        return httpx.Response(200, json={"embeddings": [[0.0]] * len(payload["input"])})

    provider, _ = make_provider(handler)
    provider.embed_batch_size = 2

    vectors = await provider.post_embeddings(["t0", "t1", "t2", "t3", "t4"])

    assert calls == [["t0", "t1"], ["t2", "t3"], ["t4"]]
    assert len(vectors) == 5


async def test_post_embeddings_empty_makes_no_request(make_provider):
    provider, transport = make_provider(
        lambda request: httpx.Response(200, json={"embeddings": []})
    )

    assert await provider.post_embeddings([]) == []
    assert transport.requests == []


async def test_flat_embedding_shape_is_wrapped(make_provider):
    # Defensive: some versions returned a single flat vector.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"embeddings": [0.1, 0.2, 0.3]})

    provider, _ = make_provider(handler)

    vectors = await provider.post_embeddings(["hello"])

    assert vectors == [[0.1, 0.2, 0.3]]


async def test_server_error_propagates(make_provider):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    provider, _ = make_provider(handler)

    with pytest.raises(httpx.HTTPStatusError):
        await provider.post_embedding("hello")


# =========================================================================
# Legacy /api/embeddings fallback
# =========================================================================


@pytest.mark.parametrize("status_code", [404, 501])
async def test_falls_back_to_legacy_when_embed_not_implemented(
    make_provider, status_code
):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/embed":
            return httpx.Response(status_code, json={"error": "not implemented"})
        return httpx.Response(200, json={"embedding": [9.0, 8.0]})

    provider, transport = make_provider(handler)

    vector = await provider.post_embedding("legacy text")

    assert vector == [9.0, 8.0]
    paths = [request.url.path for request in transport.requests]
    assert paths == ["/api/embed", "/api/embeddings"]
    legacy_payload = json.loads(transport.requests[-1].content)
    assert legacy_payload["prompt"] == "legacy text"


async def test_legacy_fallback_issues_one_request_per_text(make_provider):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/embed":
            return httpx.Response(501, json={"error": "not implemented"})
        return httpx.Response(200, json={"embedding": [1.0]})

    provider, transport = make_provider(handler)

    vectors = await provider.post_embeddings(["a", "b"])

    assert vectors == [[1.0], [1.0]]
    assert [request.url.path for request in transport.requests] == [
        "/api/embed",
        "/api/embeddings",
        "/api/embeddings",
    ]
