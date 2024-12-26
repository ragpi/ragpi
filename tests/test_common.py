import pytest
from unittest.mock import Mock, patch
from fastapi import Depends, HTTPException, Security, status
from src.common.api_key import get_api_key
from src.common.openai import get_chat_openai_client
from src.config import Settings, get_settings

@pytest.fixture
def mock_settings() -> Mock:
    return Mock(Settings)

def test_get_api_key_valid(mock_settings: Mock) -> None:
    mock_settings.API_KEY = "valid_api_key"
    with patch("src.common.api_key.get_settings", return_value=mock_settings):
        api_key = get_api_key(api_key="valid_api_key")
        assert api_key is None

def test_get_api_key_invalid(mock_settings: Mock) -> None:
    mock_settings.API_KEY = "valid_api_key"
    with patch("src.common.api_key.get_settings", return_value=mock_settings):
        with pytest.raises(HTTPException) as exc_info:
            get_api_key(api_key="invalid_api_key")
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_api_key_missing(mock_settings: Mock) -> None:
    mock_settings.API_KEY = "valid_api_key"
    with patch("src.common.api_key.get_settings", return_value=mock_settings):
        with pytest.raises(HTTPException) as exc_info:
            get_api_key(api_key=None)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_chat_openai_client(mock_settings: Mock) -> None:
    with patch("src.common.openai.get_settings", return_value=mock_settings):
        with patch("src.common.openai.get_openai_client") as mock_get_openai_client:
            get_chat_openai_client()
            mock_get_openai_client.assert_called_once_with(
                provider=mock_settings.CHAT_PROVIDER,
                ollama_url=mock_settings.OLLAMA_BASE_URL,
            )
