import os
from typing import Literal

from pydantic import (
    Field,
    HttpUrl,
    SecretStr,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    ai_provider: Literal["ollama", "deepseek"] = Field(default="ollama")

    # Ollama settings
    ollama_url: HttpUrl | None = Field(default="http://localhost:11434")
    ollama_model: str | None = Field(default="None")

    # Deepseek settings
    deepseek_url: HttpUrl | None = Field(default="https://api.deepseek.com")
    deepseek_api_key: SecretStr | None = Field(default=None)
    deepseek_model: str | None = Field(default="None")

    # Embedding
    embedding_provider: Literal["ollama", "deepseek"] = Field(default="ollama")
    # Which backend produces embeddings. Kept separate from ``ai_provider``
    # because generation and embedding routinely use different models/servers
    # (e.g. chat via DeepSeek, embeddings via a local Ollama).
    embedding_model: str | None = Field(default=None)
    embedding_url: HttpUrl | None = Field(default=None)
    # Optional override; falls back to the embedding provider's default URL.
    embedding_dim: int = Field(default=1024)
    # Vector dimension of the embedding model (all-MiniLM-L6-v2 -> 384,
    # bge-m3 -> 1024). MUST match the model actually in use, and the stored
    # vec0 table is fixed at creation, so changing it requires re-indexing.
    embedding_batch_size: int = Field(default=16)
    # How many chunks go into a single embedding request. Smaller values use
    # less peak RAM (long sequences), larger values improve GPU throughput.

    # Storage
    db_provider: str = Field(default="sqlite")
    # TODO: Add Literal with possible types
    # TODO: also consider adding db_url in future
    db_path: str = Field(default="./data/vector_store.db")
    uploads_dir: str = Field(default="./data/uploads")

    model_config = SettingsConfigDict(
        env_file="./.env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("*", mode="before")
    @classmethod
    def empty_string_uses_default(cls, value: object, info: ValidationInfo) -> object:
        """Treat empty env values (e.g. ``OLLAMA_URL=``) as "unset".

        An empty string is replaced with the field default, so a blank entry in
        ``.env`` does not override a sensible default (nor break ``HttpUrl``
        validation).
        """
        if isinstance(value, str) and not value.strip():
            field = cls.model_fields.get(info.field_name)
            return field.default if field is not None else None
        return value

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

        if self.embedding_provider == "ollama":
            if not self.ollama_url:
                raise ValueError("Missed `ollama_url` for `ollama` embedding provider")
        elif self.embedding_provider == "deepseek":
            if not self.deepseek_url:
                raise ValueError(
                    "Missed `deepseek_url` for `deepseek` embedding provider"
                )
            if not self.embedding_model:
                raise ValueError(
                    "Missed `embedding_model` for `deepseek` embedding provider"
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
            self.ollama_model if self.ai_provider == "ollama" else self.deepseek_model
        )
        return selected_model or ""

    @property
    def embedding_base_url(self) -> str:
        """Returns the URL of the active *embedding* provider.

        An explicit ``embedding_url`` always wins; otherwise the default URL of
        the selected embedding provider is used.
        """
        if self.embedding_url:
            return str(self.embedding_url)
        url = (
            self.ollama_url
            if self.embedding_provider == "ollama"
            else self.deepseek_url
        )
        return str(url) if url else ""

    @property
    def embedding_api_key(self) -> SecretStr | None:
        """Returns the API key needed by the embedding provider (if any)."""
        if self.embedding_provider == "deepseek":
            return self.deepseek_api_key
        return None

    @property
    def active_embedding_model(self) -> str:
        """Returns the model used to produce embeddings."""
        default = (
            self.ollama_model
            if self.embedding_provider == "ollama"
            else self.deepseek_model
        )
        return self.embedding_model or default or ""


config = Config()
