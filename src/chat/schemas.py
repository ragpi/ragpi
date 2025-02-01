from typing import Literal
from pydantic import BaseModel

from src.document_store.schemas import Document
from src.config import get_settings

settings = get_settings()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CreateChatRequest(BaseModel):
    sources: list[str] | None = None
    chat_model: str = settings.DEFAULT_CHAT_MODEL
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    message: str | None
    retrieved_documents: list[Document]
