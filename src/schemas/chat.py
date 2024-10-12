from typing import Literal
from pydantic import BaseModel

from src.schemas.repository import RepositoryDocument


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CreateChatInput(BaseModel):
    repository: str
    # model: str  # Should this be set at environment level? Or maybe default model and can be overridden?
    system: str | None = None
    messages: list[Message]


class ChatResponse(BaseModel):
    message: str | None
    sources: list[RepositoryDocument]
