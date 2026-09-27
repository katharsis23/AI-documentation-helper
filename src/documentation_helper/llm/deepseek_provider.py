import httpx as http
from logger import logger
from pydantic import SecretStr

from src.documentation_helper.protocols.llm import LLMResponse


class DeepSeekProvider:
    def __init__(
        self,
        model: str,
        url,  # HttpUrl
        api_key: SecretStr,
    ):
        self.model = model
        # Normalise the base URL and append the OpenAI-compatible chat path so
        # a bare base URL (e.g. "https://api.deepseek.com") still works.
        self.url = f"{str(url).rstrip('/')}/chat/completions"
        self.api_key = api_key.get_secret_value()
        self.timeout = http.Timeout(60)

    async def query(self, prompt: str) -> LLMResponse:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        try:
            async with http.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url=self.url, json=payload, headers=headers
                )
                response.raise_for_status()
                raw_json = response.json()
                return LLMResponse(
                    text=raw_json["choices"][0]["message"]["content"],
                    raw_response=raw_json,
                )
        except Exception as e:
            logger.error(msg=f"Could not send request to DeepSeek. {e}")
            raise
