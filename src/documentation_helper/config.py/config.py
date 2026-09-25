import os
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    ai_provider: Literal["ollama", "deepseek"] = "ollama"

    ollama_url: HttpUrl | None = Field(default="http://localhost:11434")
    deepseek_url: HttpUrl | None = Field(default=None)
    deepseek_api_key: SecretStr | None = Field(default=None)

    model_config = SettingsConfigDict(env_file="./.env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def validate_selected_provider(self) -> "Config":
        # Check for chosen provider
        if self.ai_provider == "ollama" and not self.ollama_url:
            raise ValueError("Missed `ollama url` for `ollama` provider")

        if self.ai_provider == "deepseek":
            if not self.deepseek_url:
                raise ValueError("Missed `deepseek url` for `deepseek` provider")
            if (
                not self.deepseek_api_key
                or not self.deepseek_api_key.get_secret_value()
            ):
                raise ValueError("'deepseek' needed DEEPSEEK_API_KEY")

        return self

    @model_validator(mode="after")
    def load_api_key_strictly_from_os(self) -> "Config":
        if self.ai_provider == "deepseek":
            env_key = os.getenv("DEEPSEEK_API_KEY")

            if not env_key:
                raise ValueError(
                    "DEEPSEEK_API_KEY is not found in (OS/Shell) environment! "
                    "Export your api key to shell"
                )

            self.deepseek_api_key = SecretStr(env_key)

        return self
