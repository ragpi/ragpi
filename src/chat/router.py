from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from src.chat.dependencies import get_chat_service
from src.chat.exceptions import ChatException
from src.chat.schemas import CreateChatInput
from src.chat.service import ChatService


router = APIRouter(
    prefix="/chat",
    tags=[
        "chat",
    ],
)


@router.post("")
def chat(
    chat_input: CreateChatInput, chat_service: ChatService = Depends(get_chat_service)
):
    try:
        return chat_service.generate_response(chat_input)
    except ChatException as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(e)},
        )
