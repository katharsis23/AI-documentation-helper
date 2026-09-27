import httpx as http
from logger import logger
from pydantic import HttpUrl, SecretStr

from src.documentation_helper.config import config


class OllamaProvider:
    def __init__(
        self,
        url: HttpUrl,
        model: str,
        api_key: SecretStr | None = None,
        embed_batch_size: int | None = None,
    ):
        self.model = model
        # Normalise the base URL so we can safely append "/api/...".
        self.url = str(url).rstrip("/")
        # Ollama does not require an API key; stay tolerant of ``None``.
        self.api_key = api_key.get_secret_value() if api_key is not None else None
        self.timeout = http.Timeout(60.0, connect=10.0)
        # How many chunks go into a single embedding request. Larger batches
        # keep CPU/GPU busy (fewer round-trips) while staying small enough not
        # to spike RAM or hit the request timeout on big documents.
        self.embed_batch_size = embed_batch_size or config.embedding_batch_size

    async def query(self, prompt: str):
        try:
            async with http.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url=f"{self.url}/api/generate",
                    json={"model": self.model, "prompt": prompt, "stream": False},
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code == 200:
                    raise NotImplementedError(
                        "Ollama request handler has not been implemented yet"
                    )
                else:
                    raise Exception
        except Exception as e:
            logger.error(msg=f"Could not send request to Ollama. {e}")

    async def post_embedding(self, text: str) -> list[float]:
        """Requests an embedding vector for a single ``text``.

        Prefers the modern ``/api/embed`` endpoint (used with the ``input``
        field) and transparently falls back to the legacy ``/api/embeddings``
        endpoint (``prompt`` field) when the Ollama server is too old to
        implement the former (it answers with ``404``/``501``).
        """
        embeddings = await self.post_embeddings([text])
        return embeddings[0] if embeddings else []

    async def post_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Requests embeddings for a batch of ``texts``.

        On a modern Ollama server the whole batch is sent in a single request
        to ``/api/embed`` (efficient, CPU/GPU friendly). When that endpoint is
        not available the provider falls back to the legacy ``/api/embeddings``
        endpoint, issuing one request per text.
        Requests larger than :attr:`embed_batch_size` are split so a single
        document cannot overload the server.
        """
        if not texts:
            return []

        results: list[list[float]] = []
        for start in range(0, len(texts), self.embed_batch_size):
            batch = texts[start : start + self.embed_batch_size]
            results.extend(await self._request_embeddings(batch))
        return results

    async def _request_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Embeds a batch using ``/api/embed``, falling back to the legacy API."""
        async with http.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url=f"{self.url}/api/embed",
                json={"model": self.model, "input": texts},
                headers={"Content-Type": "application/json"},
            )

            # Endpoint missing on older servers -> use the legacy API instead.
            if response.status_code in (404, 501):
                logger.info(
                    msg="Ollama /api/embed unavailable, "
                    "falling back to legacy /api/embeddings"
                )
                return await self._request_legacy_embeddings(client, texts)

            try:
                response.raise_for_status()
            except Exception as e:
                logger.error(msg=f"Could not fetch embeddings from Ollama. {e}")
                raise

            embeddings = response.json().get("embeddings", [])
            # Some Ollama versions return a single flat vector when ``input``
            # was a plain string; guard against that shape.
            if embeddings and not isinstance(embeddings[0], list):
                return [embeddings]
            return embeddings

    async def _request_legacy_embeddings(
        self, client: http.AsyncClient, texts: list[str]
    ) -> list[list[float]]:
        """Fallback for old Ollama servers: legacy ``/api/embeddings`` API."""
        vectors: list[list[float]] = []
        for text in texts:
            response = await client.post(
                url=f"{self.url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                headers={"Content-Type": "application/json"},
            )
            try:
                response.raise_for_status()
            except Exception as e:
                logger.error(msg=f"Could not fetch embeddings from Ollama. {e}")
                raise
            vectors.append(response.json().get("embedding", []))
        return vectors
