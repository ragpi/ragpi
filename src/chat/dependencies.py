from fastapi import Depends
from openai import OpenAI
from src.chat.service import ChatService
from src.chat.tools.definitions import TOOL_DEFINITIONS
from src.llm_providers.client import get_chat_openai_client
from src.config import Settings, get_settings
from src.sources.dependencies import get_source_service
from src.sources.service import SourceService


def get_chat_service(
    source_service: SourceService = Depends(get_source_service),
    settings: Settings = Depends(get_settings),
    openai_client: OpenAI = Depends(get_chat_openai_client),
) -> ChatService:
    return ChatService(
        source_service=source_service,
        openai_client=openai_client,
        project_name=settings.PROJECT_NAME,
        project_description=settings.PROJECT_DESCRIPTION,
        base_system_prompt=settings.BASE_SYSTEM_PROMPT,
        tool_definitions=TOOL_DEFINITIONS,
        chat_history_limit=settings.CHAT_HISTORY_LIMIT,
        max_iterations=settings.MAX_CHAT_ITERATIONS,
        retrieval_top_k=settings.RETRIEVAL_TOP_K,
    )
