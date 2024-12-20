from fastapi import Depends
from src.chat.service import ChatService
from src.source.dependencies import get_source_service
from src.source.service import SourceService


def get_chat_service(
    source_service: SourceService = Depends(get_source_service),
) -> ChatService:
    return ChatService(source_service=source_service)
