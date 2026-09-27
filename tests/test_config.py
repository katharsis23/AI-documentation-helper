"""Tests for :class:`documentation_helper.config.Config`.

Only the embedding-related wiring added for the RAG pipeline is covered here.
``Config`` reads environment variables, so each test passes explicit kwargs to
avoid depending on the developer's shell / ``.env``.
"""

from pydantic import SecretStr

from src.documentation_helper.config.config import Config


def test_embedding_provider_defaults_to_ollama():
    cfg = Config(ai_provider="ollama")

    assert cfg.embedding_provider == "ollama"


def test_embedding_base_url_falls_back_to_ollama_url():
    cfg = Config(
        ai_provider="ollama",
        ollama_url="http://localhost:11434",
        embedding_provider="ollama",
    )

    assert cfg.embedding_base_url == "http://localhost:11434/"


def test_embedding_url_override_wins():
    cfg = Config(
        ai_provider="ollama",
        ollama_url="http://localhost:11434",
        embedding_provider="ollama",
        embedding_url="http://gpu-box:11434",
    )

    assert cfg.embedding_base_url == "http://gpu-box:11434/"


def test_active_embedding_model_prefers_embedding_model():
    cfg = Config(
        ai_provider="deepseek",
        deepseek_api_key=SecretStr("sk-test"),
        deepseek_model="deepseek-chat",
        embedding_provider="ollama",
        ollama_model="llama3.1",
        embedding_model="bge-m3",
    )

    assert cfg.active_embedding_model == "bge-m3"


def test_active_embedding_model_falls_back_to_provider_model():
    cfg = Config(
        ai_provider="ollama",
        ollama_model="bge-m3",
        embedding_provider="ollama",
    )

    assert cfg.active_embedding_model == "bge-m3"


def test_embedding_api_key_none_for_ollama():
    cfg = Config(ai_provider="ollama", embedding_provider="ollama")

    assert cfg.embedding_api_key is None


def test_embedding_api_key_for_deepseek():
    cfg = Config(
        ai_provider="ollama",
        embedding_provider="deepseek",
        embedding_model="some-embedding-model",
        deepseek_api_key=SecretStr("sk-test"),
    )

    assert cfg.embedding_api_key is not None
    assert cfg.embedding_api_key.get_secret_value() == "sk-test"
