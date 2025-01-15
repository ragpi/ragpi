from fastapi import Depends
from openai import OpenAI
from src.chat.service import ChatService
from src.chat.tools import TOOL_DEFINITIONS
from src.common.openai import get_chat_openai_client
from src.config import Settings, get_settings
from src.source_manager.dependencies import get_source_manager
from src.source_manager.service import SourceManagerService


def get_chat_service(
    source_manager: SourceManagerService = Depends(get_source_manager),
    settings: Settings = Depends(get_settings),
    openai_client: OpenAI = Depends(get_chat_openai_client),
) -> ChatService:
    return ChatService(
        source_manager=source_manager,
        openai_client=openai_client,
        base_system_prompt=settings.BASE_SYSTEM_PROMPT,
        tool_definitions=TOOL_DEFINITIONS,
        chat_history_limit=settings.CHAT_HISTORY_LIMIT,
    )
