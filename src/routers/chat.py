from fastapi import APIRouter

from src.schemas.chat import CreateChatInput
from src.services.chat import get_chat_response


router = APIRouter(
    prefix="/chat",
    tags=[
        "chat",
    ],
)


@router.post("")
async def chat(chatInput: CreateChatInput):
    return await get_chat_response(chatInput)
