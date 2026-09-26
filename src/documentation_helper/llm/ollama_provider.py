import httpx as http
import asyncio
from pydantic import HttpUrl, SecretStr
from logger import logger

class OllamaProvider:
    def __init__(
            self,
            url: HttpUrl,
            model: str,
            api_key: SecretStr | None
    ):
        self.model = model
        self.url = url
        self.api_key = api_key



    async def query(self, user_prompt: str):
        try:
            async with http.AsyncClient() as client:
                response = await client.post(
                    url=self.url,
                    content={
                        "model": self.model,
                        "prompt": user_prompt,
                        "stream": False
                    },
                    headers={
                        'Content-Type': 'application/json'
                    }
                )
                if response.status_code == 200:
                    raise NotImplementedError(
                        "Ollama request handler has not been implemented yet"
                    )
                else:
                    raise Exception
        except Exception as e:
            logger.error(
                msg=f"Could not send request to Ollama. {e}"
            )
