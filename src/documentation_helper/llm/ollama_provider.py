import httpx as http
from logger import logger
from pydantic import HttpUrl, SecretStr


class OllamaProvider:
    def __init__(self, url: HttpUrl, model: str, api_key: SecretStr | None):
        self.model = model
        self.url = str(url)
        self.api_key = api_key.get_secret_value()

    async def query(self, prompt: str):
        try:
            async with http.AsyncClient() as client:
                response = await client.post(
                    url=self.url,
                    content={"model": self.model, "prompt": prompt, "stream": False},
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
        """Requests an embedding vector for ``text`` from the Ollama server.

        Returns the raw vector so that callers (e.g. an embedding provider)
        stay free of the concrete transfer/realization details.
        """
        try:
            async with http.AsyncClient() as client:
                response = await client.post(
                    url=f"{self.url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                return response.json().get("embedding", [])
        except Exception as e:
            logger.error(msg=f"Could not fetch embedding from Ollama. {e}")
            raise
