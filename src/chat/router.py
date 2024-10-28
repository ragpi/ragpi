from fastapi import APIRouter, Depends

from src.chat.schemas import CreateChatInput
from src.chat.service import ChatService


router = APIRouter(
    prefix="/chat",
    tags=[
        "chat",
    ],
)


@router.post("")
def chat(chat_input: CreateChatInput, chat_service: ChatService = Depends()):
    return chat_service.generate_response(chat_input)
