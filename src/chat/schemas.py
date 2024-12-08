from typing import Literal
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CreateChatInput(BaseModel):
    sources: list[str]
    chat_model: str | None = None
    system: str | None = None
    messages: list[ChatMessage]
    max_attempts: int = 5  # TODO: Get default from config


class ChatResponse(BaseModel):
    message: str | None
