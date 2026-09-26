import os
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    ai_provider: Literal["ollama", "deepseek"] = "ollama"

    # Ollama settings
    ollama_url: HttpUrl | None = Field(default="http://localhost:11434")
    model: str | None = Field(default="None")

    # Deepseek settings
    deepseek_url: HttpUrl | None = Field(default="https://api.deepseek.com")
    deepseek_api_key: SecretStr | None = Field(default=None)
    deepseek_model: str | None = Field(default="None")

    model_config = SettingsConfigDict(
        env_file="./.env", env_file_encoding="utf-8", extra="ignore"
    )

    @model_validator(mode="after")
    def validate_and_load_provider_config(self) -> "Config":
        if self.ai_provider == "ollama":
            if not self.ollama_url:
                raise ValueError("Missed `ollama_url` for `ollama` provider")

        elif self.ai_provider == "deepseek":
            if not self.deepseek_url:
                raise ValueError("Missed `deepseek_url` for `deepseek` provider")

            env_key = os.getenv("DEEPSEEK_API_KEY")
            # Looking for key in .env
            if env_key:
                self.deepseek_api_key = SecretStr(env_key)
            elif (
                not self.deepseek_api_key
                or not self.deepseek_api_key.get_secret_value()
            ):
                raise ValueError(
                    "DEEPSEEK_API_KEY is not found in OS/Shell environment! "
                    "Please run: export DEEPSEEK_API_KEY='your_key'"
                )

        return self

    # =========================================================================
    # Getters
    # =========================================================================
    @property
    def active_base_url(self) -> str:
        """Returns URL of active provider"""
        url = self.ollama_url if self.ai_provider == "ollama" else self.deepseek_url
        return str(url) if url else ""

    @property
    def active_model(self) -> str:
        """Returns activa model"""
        selected_model = (
            self.model if self.ai_provider == "ollama" else self.deepseek_model
        )
        return selected_model or ""


config = Config()
