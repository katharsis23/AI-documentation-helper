import httpx as http
import logger
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
        self.url = str(url)
        self.api_key = api_key.get_secret_value()

    async def query(self, prompt: str):
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
            async with http.AsyncClient() as client:
                response = await client.post(
                    url=self.url, content=payload, headers=headers
                )
                if response.status_code == 200:
                    raw_json = response.json()
                    return LLMResponse(
                        text=raw_json["choices"][0]["message"]["content"],
                        raw_response=raw_json,
                    )
                else:
                    raise Exception(f"HTTP Error {response.status_code}")
        except Exception as e:
            logger.error(msg=f"Could not send request to DeepSeek. {e}")
            raise e
