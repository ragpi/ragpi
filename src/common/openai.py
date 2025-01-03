from dataclasses import dataclass
from typing import Literal
from openai import OpenAI
from fastapi import Depends
from src.config import Settings, get_settings


@dataclass
class ClientConfig:
    api_key: str
    base_url: str | None = None


def create_client(config: ClientConfig) -> OpenAI:
    return OpenAI(api_key=config.api_key, base_url=config.base_url)


def get_provider_config(
    provider: Literal["openai", "ollama"],
    settings: Settings,
) -> ClientConfig:
    if provider == "ollama":
        if not settings.OLLAMA_BASE_URL:
            raise ValueError("OLLAMA_BASE_URL is not set")
        return ClientConfig(api_key="ollama", base_url=settings.OLLAMA_BASE_URL)

    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set")
    return ClientConfig(api_key=settings.OPENAI_API_KEY)


def get_chat_openai_client(settings: Settings = Depends(get_settings)) -> OpenAI:
    return create_client(get_provider_config(settings.CHAT_PROVIDER, settings))


def get_embedding_openai_client(settings: Settings = Depends(get_settings)) -> OpenAI:
    return create_client(get_provider_config(settings.EMBEDDING_PROVIDER, settings))
