from typing import Literal
from pydantic import BaseModel

from src.document.schemas import Document


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CreateChatInput(BaseModel):
    repository: str
    chat_model: str | None = None
    system: str | None = None
    messages: list[ChatMessage]
    retrieval_limit: int | None = None
    use_reranking: bool = True
    reranking_model: str | None = None


class ChatResponse(BaseModel):
    message: str | None
    sources: list[Document]
