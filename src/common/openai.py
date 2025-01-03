from openai import OpenAI

from src.config import Settings, get_settings
from fastapi import Depends


def get_openai_client(*, api_key: str, base_url: str | None) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url)


def get_chat_openai_client(settings: Settings = Depends(get_settings)) -> OpenAI:
    provider = settings.CHAT_PROVIDER
    if provider == "ollama":
        return get_openai_client(api_key="ollama", base_url=settings.OLLAMA_BASE_URL)

    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set")

    return get_openai_client(api_key=settings.OPENAI_API_KEY, base_url=None)


def get_embedding_openai_client(settings: Settings = Depends(get_settings)) -> OpenAI:
    provider = settings.EMBEDDING_PROVIDER
    if provider == "ollama":
        return get_openai_client(api_key="ollama", base_url=settings.OLLAMA_BASE_URL)

    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set")

    return get_openai_client(api_key=settings.OPENAI_API_KEY, base_url=None)
