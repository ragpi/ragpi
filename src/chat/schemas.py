from typing import Literal
from pydantic import BaseModel

from src.repository.schemas import RepositoryDocument


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CreateChatInput(BaseModel):
    repository: str
    model: str | None = None
    system: str | None = None
    messages: list[Message]
    num_sources: int | None = None


class ChatResponse(BaseModel):
    message: str | None
    sources: list[RepositoryDocument]
