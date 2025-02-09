from fastapi import APIRouter, Depends

from src.chat.dependencies import get_chat_service
from src.chat.schemas import ChatResponse, CreateChatRequest
from src.chat.service import ChatService
from src.common.exceptions import ResourceType, resource_not_found_response


router = APIRouter(
    prefix="/chat",
    tags=[
        "Chat",
    ],
)


@router.post("", responses={**resource_not_found_response(ResourceType.MODEL)})
def chat(
    chat_input: CreateChatRequest, chat_service: ChatService = Depends(get_chat_service)
) -> ChatResponse:
    return chat_service.generate_response(chat_input)
