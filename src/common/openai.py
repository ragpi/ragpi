from openai import OpenAI

from src.config import Settings, get_settings
from fastapi import Depends


def get_openai_client(*, provider: str, ollama_url: str) -> OpenAI:
    if provider == "openai":
        return OpenAI()
    elif provider == "ollama":
        return OpenAI(
            base_url=ollama_url,
            api_key="ollama",
        )
    else:
        raise ValueError(f"Unsupported chat provider: {provider}")


def get_chat_openai_client(settings: Settings = Depends(get_settings)) -> OpenAI:
    return get_openai_client(
        provider=settings.CHAT_PROVIDER,
        ollama_url=settings.OLLAMA_BASE_URL,
    )


def get_embedding_openai_client(settings: Settings = Depends(get_settings)) -> OpenAI:
    return get_openai_client(
        provider=settings.EMBEDDING_PROVIDER,
        ollama_url=settings.OLLAMA_BASE_URL,
    )
