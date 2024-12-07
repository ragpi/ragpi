from typing import Literal
from pydantic import BaseModel

from src.config import RERANKING_MODELS
from src.document.schemas import Document


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CreateChatInput(BaseModel):
    sources: list[str]
    chat_model: str | None = None
    system: str | None = None
    messages: list[ChatMessage]
    retrieval_limit: int | None = None
    use_reranking: bool = True
    reranking_model: RERANKING_MODELS | None = None
    max_attempts: int = 5  # TODO: Get default from config


class ChatResponse(BaseModel):
    message: str | None
    source_documents: list[Document]
