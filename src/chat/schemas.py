from typing import Literal
from pydantic import BaseModel

from src.common.schemas import Document
from src.config import get_settings

settings = get_settings()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CreateChatInput(BaseModel):
    sources: list[str] | None = None
    chat_model: str = settings.DEFAULT_CHAT_MODEL
    messages: list[ChatMessage]
    max_attempts: int = settings.MAX_CHAT_ATTEMPTS


class ChatResponse(BaseModel):
    message: str | None
    retrieved_documents: list[Document]
