from typing import Literal
from pydantic import BaseModel

from src.config import settings


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CreateChatInput(BaseModel):
    sources: list[str]
    chat_model: str | None = None
    system: str | None = None
    messages: list[ChatMessage]
    max_attempts: int = settings.CHAT_MAX_ATTEMPTS


class ChatResponse(BaseModel):
    message: str | None
