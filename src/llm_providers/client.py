from dataclasses import dataclass
from typing import Literal, Optional
from fastapi import Depends
from openai import OpenAI
from src.config import (
    Settings,
    get_settings,
    ChatProvider,
    EmbeddingProvider,
)


@dataclass
class OpenAIConfig:
    api_key: str
    base_url: Optional[str] = None


def create_client(config: OpenAIConfig) -> OpenAI:
    return OpenAI(api_key=config.api_key, base_url=config.base_url)


def get_openai_config(
    type: Literal["chat", "embedding"],
    provider: ChatProvider | EmbeddingProvider,
    settings: Settings,
) -> OpenAIConfig:
    if provider in (ChatProvider.OLLAMA, EmbeddingProvider.OLLAMA):
        return OpenAIConfig(api_key="ollama", base_url=settings.OLLAMA_BASE_URL)

    if provider in (ChatProvider.OPENAI, EmbeddingProvider.OPENAI):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set")
        return OpenAIConfig(api_key=settings.OPENAI_API_KEY)

    if provider == ChatProvider.DEEPSEEK:
        if not settings.DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY is not set")
        return OpenAIConfig(
            api_key=settings.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1"
        )

    if provider in (
        ChatProvider.OPENAI_COMPATIBLE,
        EmbeddingProvider.OPENAI_COMPATIBLE,
    ):
        if type == "chat":
            if not settings.CHAT_OPENAI_COMPATIBLE_API_KEY:
                raise ValueError("CHAT_OPENAI_COMPATIBLE_API_KEY is not set")
            return OpenAIConfig(
                api_key=settings.CHAT_OPENAI_COMPATIBLE_API_KEY,
                base_url=settings.CHAT_OPENAI_COMPATIBLE_BASE_URL,
            )
        else:
            if not settings.EMBEDDING_OPENAI_COMPATIBLE_API_KEY:
                raise ValueError("EMBEDDING_OPENAI_COMPATIBLE_API_KEY is not set")
            return OpenAIConfig(
                api_key=settings.EMBEDDING_OPENAI_COMPATIBLE_API_KEY,
                base_url=settings.EMBEDDING_OPENAI_COMPATIBLE_BASE_URL,
            )

    raise ValueError(f"Unknown provider: {provider}")


def get_chat_openai_client(settings: Settings = Depends(get_settings)) -> OpenAI:
    config = get_openai_config(
        type="chat", provider=settings.CHAT_PROVIDER, settings=settings
    )
    return create_client(config)


def get_embedding_openai_client(settings: Settings = Depends(get_settings)) -> OpenAI:
    config = get_openai_config(
        type="embedding", provider=settings.EMBEDDING_PROVIDER, settings=settings
    )
    return create_client(config)
