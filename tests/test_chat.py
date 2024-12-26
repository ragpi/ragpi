import pytest
from unittest.mock import Mock, patch
from fastapi import Depends
from src.chat.service import ChatService
from src.chat.router import chat
from src.chat.dependencies import get_chat_service
from src.chat.schemas import CreateChatInput, ChatMessage, ChatResponse
from src.common.openai import get_chat_openai_client
from src.config import Settings, get_settings
from src.source.service import SourceService

@pytest.fixture
def mock_source_service() -> Mock:
    return Mock(SourceService)

@pytest.fixture
def mock_settings() -> Mock:
    return Mock(Settings)

@pytest.fixture
def mock_openai_client() -> Mock:
    return Mock()

@pytest.fixture
def chat_service(mock_source_service: Mock, mock_settings: Mock, mock_openai_client: Mock) -> ChatService:
    return ChatService(
        source_service=mock_source_service,
        openai_client=mock_openai_client,
        base_system_prompt=mock_settings.BASE_SYSTEM_PROMPT,
        chat_history_limit=mock_settings.CHAT_HISTORY_LIMIT,
    )

def test_get_chat_service(mock_source_service: Mock, mock_settings: Mock, mock_openai_client: Mock) -> None:
    with patch("src.chat.dependencies.get_source_service", return_value=mock_source_service):
        with patch("src.chat.dependencies.get_settings", return_value=mock_settings):
            with patch("src.chat.dependencies.get_chat_openai_client", return_value=mock_openai_client):
                chat_service = get_chat_service()
                assert isinstance(chat_service, ChatService)

def test_chat_service_generate_response(chat_service: ChatService) -> None:
    chat_input = CreateChatInput(
        sources=["source1"],
        chat_model="gpt-4o-mini",
        system="system",
        messages=[ChatMessage(role="user", content="Hello")],
        max_attempts=3,
    )
    response = chat_service.generate_response(chat_input)
    assert isinstance(response, ChatResponse)

def test_chat_endpoint(chat_service: ChatService) -> None:
    chat_input = CreateChatInput(
        sources=["source1"],
        chat_model="gpt-4o-mini",
        system="system",
        messages=[ChatMessage(role="user", content="Hello")],
        max_attempts=3,
    )
    with patch("src.chat.router.get_chat_service", return_value=chat_service):
        response = chat(chat_input)
        assert isinstance(response, ChatResponse)
