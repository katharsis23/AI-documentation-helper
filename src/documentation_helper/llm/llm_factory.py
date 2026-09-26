from pydantic import HttpUrl, SecretStr

from src.documentation_helper.llm import deepseek_provider, ollama_provider
from src.documentation_helper.protocols.llm import ILLMRequest


def get_llm_provider(
    provider_name: str,  # Either ollama or deepseek, validation is from config
    url: HttpUrl | str,
    model: str,
    api_key: SecretStr | str | None = None,
) -> ILLMRequest:

    providers = {
        "ollama": ollama_provider.OllamaProvider,
        "deepseek": deepseek_provider.DeepSeekProvider,
    }

    provider_class = providers.get(provider_name)
    if not provider_class:
        raise ValueError(f"Unknown AI provider: {provider_name}")
    return provider_class(url=url, model=model, api_key=api_key)
