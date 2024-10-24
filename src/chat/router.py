from fastapi import APIRouter

from src.chat.schemas import CreateChatInput
from src.chat.service import get_chat_response


router = APIRouter(
    prefix="/chat",
    tags=[
        "chat",
    ],
)


@router.post("")
async def chat(chatInput: CreateChatInput):
    return await get_chat_response(chatInput)
