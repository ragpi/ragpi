from typing import Literal
from pydantic import BaseModel

from src.schemas.collections import CollectionDocument


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CreateChatInput(BaseModel):
    collection: str
    # model: str  # Should this be set at environment level? Or maybe default model and can be overridden?
    system: str | None = None
    messages: list[Message]


class ChatResponse(BaseModel):
    response: str
    citations: list[CollectionDocument] | None = None
