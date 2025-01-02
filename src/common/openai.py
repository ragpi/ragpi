from openai import OpenAI

from src.config import Settings, get_settings
from fastapi import Depends


def get_openai_client(*, api_key: str, base_url: str | None) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url)


def get_chat_openai_client(settings: Settings = Depends(get_settings)) -> OpenAI:
    provider = settings.CHAT_PROVIDER
    api_key = "ollama" if provider == "ollama" else settings.OPENAI_API_KEY
    base_url = settings.OLLAMA_BASE_URL if provider == "ollama" else None

    return get_openai_client(api_key=api_key, base_url=base_url)


def get_embedding_openai_client(settings: Settings = Depends(get_settings)) -> OpenAI:
    provider = settings.EMBEDDING_PROVIDER
    api_key = "ollama" if provider == "ollama" else settings.OPENAI_API_KEY
    base_url = settings.OLLAMA_BASE_URL if provider == "ollama" else None

    return get_openai_client(api_key=api_key, base_url=base_url)
