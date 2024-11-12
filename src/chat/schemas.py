from typing import Literal
from pydantic import BaseModel

from src.document.schemas import Document


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CreateChatInput(BaseModel):
    repository: str
    chat_model: str | None = None
    system: str | None = None
    messages: list[Message]
    retrieval_limit: int | None = None
    rerank_top_n: int | None = None
    use_reranking: bool = False
    reranking_model: str | None = None


class ChatResponse(BaseModel):
    message: str | None
    sources: list[Document]
